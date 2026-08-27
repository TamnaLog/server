"""POST /api/v1/treasure-missions/pictures-with-character - AR 캐릭터와 사진 저장 테스트.

기준 문서: app/treasure_mission/docs/API_SPEC.md, app/treasure_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import images
from app.treasure_mission import service
from app.treasure_mission.models import PictureWithCharacter
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash


ENDPOINT = "/api/v1/treasure-missions/pictures-with-character"

TAKEN_AT = "2026-08-26T14:32:10"
UPLOADED_URL = "https://example.blob.core.windows.net/media/ar_character_picture/1/abc.jpg"

OTHER_USER_ID = 2

# 실제 이미지 시그니처 (형식 판별은 파일 내용으로 한다)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"0" * 32
GIF_BYTES = b"GIF89a" + b"0" * 32


@pytest.fixture
def uploads(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Blob 업로드를 가로채 호출 인자를 기록한다. (실제 Azure 로 나가지 않게)"""
    calls: list[dict[str, Any]] = []

    def fake_upload(data: bytes, **kwargs: Any) -> str:
        calls.append({"data": data, **kwargs})
        return UPLOADED_URL

    monkeypatch.setattr(service.blob_storage, "upload_file", fake_upload)
    return calls


@pytest.fixture
def deletes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """되돌리기용 Blob 삭제 호출을 기록한다."""
    calls: list[str] = []
    monkeypatch.setattr(service.blob_storage, "delete_file", calls.append)
    return calls


@pytest.fixture
def user_data(db_session: Session) -> None:
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
        ]
    )
    db_session.commit()


def _post(
    client: TestClient,
    *,
    content: bytes = JPEG_BYTES,
    filename: str = "picture-with-character.jpg",
    content_type: str = "image/jpeg",
    taken_at: str | None = TAKEN_AT,
) -> Any:
    data = {} if taken_at is None else {"takenAt": taken_at}
    return client.post(
        ENDPOINT, files={"picture": (filename, content, content_type)}, data=data
    )


def _saved(db_session: Session) -> list[PictureWithCharacter]:
    db_session.expire_all()
    return list(db_session.scalars(select(PictureWithCharacter)).all())


# ---------------------------------------------------------------------
# 정상 저장
# ---------------------------------------------------------------------


def test_사진을_저장하면_204로_응답하고_본문이_없다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = _post(client)

    assert response.status_code == 204
    assert response.content == b""


def test_사용자_id와_업로드_URL과_촬영_시각을_저장한다(
    client: TestClient, db_session: Session, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    _post(client)

    pictures = _saved(db_session)
    assert len(pictures) == 1
    saved = pictures[0]
    assert saved.user_id == CURRENT_USER_ID
    assert saved.picture_url == UPLOADED_URL
    # takenAt 은 KST 기준 offset 없는 값 그대로 저장한다.
    assert saved.saved_at == datetime(2026, 8, 26, 14, 32, 10)


def test_사용자별_경로와_실제_형식_확장자로_업로드한다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    _post(client)

    assert len(uploads) == 1
    upload = uploads[0]
    assert upload["prefix"] == f"ar_character_picture/{CURRENT_USER_ID}"
    assert upload["extension"] == ".jpg"
    assert upload["content_type"] == "image/jpeg"
    # 파일 내용은 변환하지 않고 그대로 올린다.
    assert upload["data"] == JPEG_BYTES
    # 원본 파일명은 blob 이름에 쓰지 않는다.
    assert not upload.get("filename")


@pytest.mark.parametrize(
    ("content", "extension", "content_type"),
    [
        pytest.param(JPEG_BYTES, ".jpg", "image/jpeg", id="JPEG"),
        pytest.param(PNG_BYTES, ".png", "image/png", id="PNG"),
        pytest.param(WEBP_BYTES, ".webp", "image/webp", id="WebP"),
    ],
)
def test_허용_형식은_모두_저장한다(
    client: TestClient,
    user_data: None,
    uploads: list[dict[str, Any]],
    content: bytes,
    extension: str,
    content_type: str,
) -> None:
    response = _post(client, content=content)

    assert response.status_code == 204
    assert uploads[0]["extension"] == extension
    assert uploads[0]["content_type"] == content_type


def test_확장자와_ContentType이_실제_형식과_달라도_실제_형식을_따른다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    # 파일명은 png, Content-Type 도 png 지만 내용은 JPEG 인 경우
    response = _post(client, content=JPEG_BYTES, filename="a.png", content_type="image/png")

    assert response.status_code == 204
    assert uploads[0]["extension"] == ".jpg"
    assert uploads[0]["content_type"] == "image/jpeg"


def test_jpeg_확장자로_보내도_jpg로_통일한다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    _post(client, filename="a.jpeg")

    assert uploads[0]["extension"] == ".jpg"


# ---------------------------------------------------------------------
# 실패 시 되돌리기
# ---------------------------------------------------------------------


def test_Blob_업로드가_실패하면_DB에_저장하지_않는다(
    client: TestClient,
    db_session: Session,
    user_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("업로드 실패")

    monkeypatch.setattr(service.blob_storage, "upload_file", boom)

    response = _post(client)

    assert response.status_code == 500
    assert _saved(db_session) == []


def test_DB_저장이_실패하면_올린_Blob을_지운다(
    client: TestClient,
    db_session: Session,
    user_data: None,
    uploads: list[dict[str, Any]],
    deletes: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(self: Session) -> None:
        raise RuntimeError("DB 저장 실패")

    monkeypatch.setattr(Session, "commit", boom)

    response = _post(client)

    assert response.status_code == 500
    assert _saved(db_session) == []
    # DB가 참조하지 않는 파일이 남지 않도록 지워야 한다.
    assert deletes == [UPLOADED_URL]


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


def test_허용하지_않는_형식이면_400으로_응답하고_업로드하지_않는다(
    client: TestClient, db_session: Session, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = _post(client, content=GIF_BYTES, filename="a.gif", content_type="image/gif")

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []
    assert _saved(db_session) == []


def test_빈_파일이면_400으로_응답한다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = _post(client, content=b"")

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []


def test_10MB를_초과하면_400으로_응답하고_업로드하지_않는다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    oversized = JPEG_BYTES + b"0" * images.MAX_IMAGE_SIZE_BYTE

    response = _post(client, content=oversized)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []


def test_10MB_이하는_저장한다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    limit_size = JPEG_BYTES + b"0" * (images.MAX_IMAGE_SIZE_BYTE - len(JPEG_BYTES))

    response = _post(client, content=limit_size)

    assert response.status_code == 204
    assert len(uploads[0]["data"]) == images.MAX_IMAGE_SIZE_BYTE


@pytest.mark.parametrize(
    "taken_at",
    [
        pytest.param("2026-08-26T14:32:10+09:00", id="offset_포함"),
        pytest.param("2026-08-26T14:32:10Z", id="UTC_표기"),
        pytest.param("2026-08-26", id="날짜만"),
        pytest.param("어제", id="형식_아님"),
        pytest.param("2026-13-99T99:99:99", id="존재하지_않는_시각"),
    ],
)
def test_촬영_시각_형식이_잘못되면_400으로_응답한다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]], taken_at: str
) -> None:
    response = _post(client, taken_at=taken_at)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []


def test_촬영_시각이_없으면_400으로_응답한다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = _post(client, taken_at=None)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []


def test_사진_파일이_없으면_400으로_응답한다(
    client: TestClient, user_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = client.post(ENDPOINT, data={"takenAt": TAKEN_AT})

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []
