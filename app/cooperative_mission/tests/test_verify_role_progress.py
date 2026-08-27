"""POST /api/v1/cooperative-missions/{progressId}/role-progresses/{roleProgressId}/verification
- 협동 미션 역할 진행도 저장(사진 인증) 테스트.

기준 문서: app/cooperative_mission/docs/API_SPEC_2.md,
          app/cooperative_mission/docs/BUSINESS_RULES_2.md
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.common import images
from app.cooperative_mission import service
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    CooperativeRoleCard,
    CooperativeRoleProgress,
    MissionStatus,
    ParticipantRole,
    ParticipantStatus,
)
from app.map.models import Location
from app.mission.models import Mission
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


COOPERATIVE_TYPE_ID = 1
COOPERATIVE_MISSION_ID = 12
LOCATION_ID = 1

PROGRESS_ID = 10
OTHER_PROGRESS_ID = 20
TEAM_TOKEN = "mock-team-token-10"
OTHER_TEAM_TOKEN = "mock-team-token-20"

# 현재 사용자(1)가 방장이고, 역할 진행도 1을 맡았다.
HOST_PARTICIPANT_ID = 1
HOST_ROLE_PROGRESS_ID = 1
MEMBER_USER_ID = 2
MEMBER_PARTICIPANT_ID = 2
MEMBER_ROLE_PROGRESS_ID = 2
OUTSIDER_USER_ID = 3
OTHER_PROGRESS_ROLE_PROGRESS_ID = 99

ROLE_CARD_COUNT = 6
UPLOADED_URL = (
    "https://example.blob.core.windows.net/media/cooperative_mission_role/10/1/abc.jpg"
)

# 실제 이미지 시그니처 (형식 판별은 파일 내용으로 한다)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"0" * 32
GIF_BYTES = b"GIF89a" + b"0" * 32


def _endpoint(
    progress_id: object = PROGRESS_ID, role_progress_id: object = HOST_ROLE_PROGRESS_ID
) -> str:
    return (
        f"/api/v1/cooperative-missions/{progress_id}"
        f"/role-progresses/{role_progress_id}/verification"
    )


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
def verification_data(db_session: Session) -> None:
    """미션 수행 단계(3단계) 방 + 방장/팀원에게 각각 배정된 역할."""
    db_session.add_all(
        [
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="일행과 역할을 나눠보세요.",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
            Location(
                id=LOCATION_ID,
                content_id=126273,
                location_title="종화네 과수원",
                location_address="제주특별자치도 제주시 조천읍 감귤밭길 12",
                location_category="농장",
                radius=400,
                mx=126.5707,
                my=33.4507,
            ),
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="나민",
                point=0,
            ),
            User(
                id=MEMBER_USER_ID,
                access_token_hash=access_token_hash(MEMBER_USER_ID),
                nickname="이서연",
                point=0,
            ),
            User(
                id=OUTSIDER_USER_ID,
                access_token_hash=access_token_hash(OUTSIDER_USER_ID),
                nickname="김민우",
                point=0,
            ),
            *[
                CooperativeRoleCard(
                    id=role_card_id,
                    role_name=f"역할{role_card_id}",
                    role_description=f"역할{role_card_id} 설명",
                    location_to_find=[f"장소{role_card_id}"],
                )
                for role_card_id in range(1, ROLE_CARD_COUNT + 1)
            ],
        ]
    )
    db_session.flush()

    db_session.add(
        CooperativeMission(
            id=COOPERATIVE_MISSION_ID,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=LOCATION_ID,
            reward_detail={},
        )
    )
    db_session.flush()

    db_session.add(
        CooperativeMissionProgress(
            id=PROGRESS_ID,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=3,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token=TEAM_TOKEN,
        )
    )
    db_session.flush()

    db_session.add_all(
        [
            CooperativeMissionParticipant(
                id=HOST_PARTICIPANT_ID,
                cooperative_mission_progress_id=PROGRESS_ID,
                user_id=CURRENT_USER_ID,
                participant_status=ParticipantStatus.ACCEPTED.value,
                participant_role=ParticipantRole.HOST.value,
                joined_at=datetime(2026, 8, 20, 10, 0, 0),
            ),
            CooperativeMissionParticipant(
                id=MEMBER_PARTICIPANT_ID,
                cooperative_mission_progress_id=PROGRESS_ID,
                user_id=MEMBER_USER_ID,
                participant_status=ParticipantStatus.ACCEPTED.value,
                participant_role=ParticipantRole.MEMBER.value,
                joined_at=datetime(2026, 8, 20, 11, 0, 0),
            ),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            CooperativeRoleProgress(
                id=HOST_ROLE_PROGRESS_ID,
                participant_id=HOST_PARTICIPANT_ID,
                cooperative_role_card_id=1,
                progress_status=MissionStatus.IN_PROGRESS.value,
            ),
            CooperativeRoleProgress(
                id=MEMBER_ROLE_PROGRESS_ID,
                participant_id=MEMBER_PARTICIPANT_ID,
                cooperative_role_card_id=2,
                progress_status=MissionStatus.IN_PROGRESS.value,
            ),
        ]
    )
    db_session.commit()


def _add_other_progress(db_session: Session) -> None:
    """다른 방과 그 방 참가자의 역할 진행도를 만든다."""
    db_session.add(
        CooperativeMissionProgress(
            id=OTHER_PROGRESS_ID,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=3,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token=OTHER_TEAM_TOKEN,
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=98,
            cooperative_mission_progress_id=OTHER_PROGRESS_ID,
            user_id=OUTSIDER_USER_ID,
            participant_status=ParticipantStatus.ACCEPTED.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeRoleProgress(
            id=OTHER_PROGRESS_ROLE_PROGRESS_ID,
            participant_id=98,
            cooperative_role_card_id=1,
            progress_status=MissionStatus.IN_PROGRESS.value,
        )
    )
    db_session.commit()


def _set_step(
    db_session: Session,
    current_step: int,
    *,
    mission_status: MissionStatus = MissionStatus.IN_PROGRESS,
) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.current_step = current_step
    progress.mission_status = mission_status.value
    db_session.commit()


def _saved(db_session: Session, role_progress_id: int) -> CooperativeRoleProgress:
    db_session.expire_all()
    role_progress = db_session.get(CooperativeRoleProgress, role_progress_id)
    assert role_progress is not None
    return role_progress


def _post(
    client: TestClient,
    *,
    progress_id: object = PROGRESS_ID,
    role_progress_id: object = HOST_ROLE_PROGRESS_ID,
    content: bytes = JPEG_BYTES,
    filename: str = "material.jpg",
    content_type: str = "image/jpeg",
    user_id: int = CURRENT_USER_ID,
    with_file: bool = True,
) -> Any:
    files = {"itemImage": (filename, content, content_type)} if with_file else None
    return client.post(
        _endpoint(progress_id, role_progress_id),
        files=files,
        headers=auth_headers(user_id),
    )


# ---------------------------------------------------------------------
# 인증 성공 (BUSINESS_RULES_2 11·12.)
# ---------------------------------------------------------------------


def test_인증에_성공하면_200에_isVerified가_true다(
    client: TestClient, verification_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = _post(client)

    assert response.status_code == 200
    assert response.json() == {"isVerified": True}


def test_인증에_성공하면_사진_URL과_완료_상태를_저장한다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    _post(client)

    saved = _saved(db_session, HOST_ROLE_PROGRESS_ID)
    assert saved.item_img_url == UPLOADED_URL
    assert saved.progress_status == MissionStatus.COMPLETED.value
    assert saved.completed_at is not None


def test_진행도와_역할_진행도별_경로와_실제_형식_확장자로_업로드한다(
    client: TestClient, verification_data: None, uploads: list[dict[str, Any]]
) -> None:
    _post(client)

    assert len(uploads) == 1
    upload = uploads[0]
    assert upload["prefix"] == f"cooperative_mission_role/{PROGRESS_ID}/{HOST_ROLE_PROGRESS_ID}"
    assert upload["extension"] == ".jpg"
    assert upload["content_type"] == "image/jpeg"
    assert upload["data"] == JPEG_BYTES
    # 원본 파일명은 blob 이름에 쓰지 않는다.
    assert not upload.get("filename")


@pytest.mark.parametrize(
    ("content", "extension"),
    [
        pytest.param(JPEG_BYTES, ".jpg", id="JPEG"),
        pytest.param(PNG_BYTES, ".png", id="PNG"),
        pytest.param(WEBP_BYTES, ".webp", id="WebP"),
    ],
)
def test_허용_형식은_모두_인증한다(
    client: TestClient,
    verification_data: None,
    uploads: list[dict[str, Any]],
    content: bytes,
    extension: str,
) -> None:
    response = _post(client, content=content)

    assert response.status_code == 200
    assert uploads[0]["extension"] == extension


def test_확장자와_ContentType이_실제_형식과_달라도_실제_형식을_따른다(
    client: TestClient, verification_data: None, uploads: list[dict[str, Any]]
) -> None:
    _post(client, content=JPEG_BYTES, filename="a.png", content_type="image/png")

    assert uploads[0]["extension"] == ".jpg"
    assert uploads[0]["content_type"] == "image/jpeg"


def test_팀원도_자기_역할을_인증할_수_있다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    response = _post(
        client, role_progress_id=MEMBER_ROLE_PROGRESS_ID, user_id=MEMBER_USER_ID
    )

    assert response.status_code == 200
    assert (
        _saved(db_session, MEMBER_ROLE_PROGRESS_ID).progress_status
        == MissionStatus.COMPLETED.value
    )


def test_인증해도_협동_미션_단계와_상태는_바뀌지_않는다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    # 마지막 역할까지 인증해도 3 → 4 는 방장이 따로 넘겨야 한다.
    _post(client)
    _post(client, role_progress_id=MEMBER_ROLE_PROGRESS_ID, user_id=MEMBER_USER_ID)

    db_session.expire_all()
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    assert progress.current_step == 3
    assert progress.mission_status == MissionStatus.IN_PROGRESS.value
    assert progress.completed_at is None


# ---------------------------------------------------------------------
# 인증 실패 (BUSINESS_RULES_2 10.)
# ---------------------------------------------------------------------


def test_인증에_실패하면_200에_isVerified가_false이고_아무것도_바꾸지_않는다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service.photo_verifier, "verify_role_image", lambda **kwargs: False
    )

    response = _post(client)

    assert response.status_code == 200
    assert response.json() == {"isVerified": False}
    # 사진을 올리지도, 진행도를 바꾸지도 않는다.
    assert uploads == []
    saved = _saved(db_session, HOST_ROLE_PROGRESS_ID)
    assert saved.item_img_url is None
    assert saved.progress_status == MissionStatus.IN_PROGRESS.value
    assert saved.completed_at is None


def test_인증_모듈에_역할_카드_정보를_전달한다(
    client: TestClient,
    verification_data: None,
    uploads: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_verify(**kwargs: Any) -> bool:
        calls.append(kwargs)
        return True

    monkeypatch.setattr(service.photo_verifier, "verify_role_image", fake_verify)

    _post(client)

    assert len(calls) == 1
    call = calls[0]
    assert call["image_bytes"] == JPEG_BYTES
    assert call["content_type"] == "image/jpeg"
    # 역할 카드는 요청이 아니라 역할 진행도 관계로 조회한다.
    assert call["role_name"] == "역할1"
    assert call["role_description"] == "역할1 설명"
    assert call["location_to_find"] == ["장소1"]


# ---------------------------------------------------------------------
# 실패 시 되돌리기 (BUSINESS_RULES_2 13.)
# ---------------------------------------------------------------------


def test_Blob_업로드가_실패하면_진행도를_바꾸지_않는다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("업로드 실패")

    monkeypatch.setattr(service.blob_storage, "upload_file", boom)

    response = _post(client)

    assert response.status_code == 500
    saved = _saved(db_session, HOST_ROLE_PROGRESS_ID)
    assert saved.item_img_url is None
    assert saved.progress_status == MissionStatus.IN_PROGRESS.value


def test_DB_저장이_실패하면_올린_사진을_지운다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
    deletes: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(self: Session) -> None:
        raise RuntimeError("DB 저장 실패")

    monkeypatch.setattr(Session, "commit", boom)

    response = _post(client)

    assert response.status_code == 500
    assert _saved(db_session, HOST_ROLE_PROGRESS_ID).item_img_url is None
    # DB 가 참조하지 않는 파일이 남지 않도록 지워야 한다.
    assert deletes == [UPLOADED_URL]


# ---------------------------------------------------------------------
# 403 / 409
# ---------------------------------------------------------------------


def test_다른_사람의_역할이면_403으로_응답한다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    # 방장이라도 팀원의 역할을 대신 인증할 수 없다.
    response = _post(client, role_progress_id=MEMBER_ROLE_PROGRESS_ID)

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED"}
    assert uploads == []
    assert (
        _saved(db_session, MEMBER_ROLE_PROGRESS_ID).progress_status
        == MissionStatus.IN_PROGRESS.value
    )


def test_담당자가_수락_상태가_아니면_403으로_응답한다(
    client: TestClient, db_session: Session, verification_data: None
) -> None:
    participant = db_session.get(CooperativeMissionParticipant, HOST_PARTICIPANT_ID)
    assert participant is not None
    participant.participant_status = ParticipantStatus.PENDING.value
    db_session.commit()

    response = _post(client)

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED"}


def test_이미_인증한_역할이면_409로_응답하고_사진을_덮어쓰지_않는다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    role_progress = db_session.get(CooperativeRoleProgress, HOST_ROLE_PROGRESS_ID)
    assert role_progress is not None
    role_progress.progress_status = MissionStatus.COMPLETED.value
    role_progress.item_img_url = "https://example.com/items/old.jpg"
    role_progress.completed_at = datetime(2026, 8, 21, 10, 0, 0)
    db_session.commit()

    response = _post(client)

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED"}
    assert uploads == []
    assert (
        _saved(db_session, HOST_ROLE_PROGRESS_ID).item_img_url
        == "https://example.com/items/old.jpg"
    )


@pytest.mark.parametrize(
    "current_step",
    [pytest.param(1, id="초대_단계"), pytest.param(2, id="역할_배정_단계")],
)
def test_미션_수행_단계가_아니면_409로_응답한다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
    current_step: int,
) -> None:
    _set_step(db_session, current_step)

    response = _post(client)

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"}
    assert uploads == []


def test_이미_완료된_미션이면_409_ALREADY_COMPLETED로_응답한다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    _set_step(db_session, 4, mission_status=MissionStatus.COMPLETED)

    response = _post(client)

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"}
    assert uploads == []


# ---------------------------------------------------------------------
# 404 / 401
# ---------------------------------------------------------------------


def test_진행도가_없으면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, verification_data: None
) -> None:
    response = _post(client, progress_id=999)

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_역할_진행도가_없으면_404_ROLE_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, verification_data: None
) -> None:
    response = _post(client, role_progress_id=999)

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_ROLE_PROGRESS_NOT_FOUND"}


def test_다른_방의_역할_진행도면_404로_응답한다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    _add_other_progress(db_session)

    response = _post(client, role_progress_id=OTHER_PROGRESS_ROLE_PROGRESS_ID)

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_ROLE_PROGRESS_NOT_FOUND"}
    assert uploads == []
    assert (
        _saved(db_session, OTHER_PROGRESS_ROLE_PROGRESS_ID).progress_status
        == MissionStatus.IN_PROGRESS.value
    )


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, verification_data: None
) -> None:
    response = _post(client, user_id=999)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


def test_사진이_없으면_400으로_응답한다(
    client: TestClient, verification_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = _post(client, with_file=False)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []


def test_허용하지_않는_형식이면_400으로_응답하고_업로드하지_않는다(
    client: TestClient,
    db_session: Session,
    verification_data: None,
    uploads: list[dict[str, Any]],
) -> None:
    response = _post(client, content=GIF_BYTES, filename="a.gif", content_type="image/gif")

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []
    assert (
        _saved(db_session, HOST_ROLE_PROGRESS_ID).progress_status
        == MissionStatus.IN_PROGRESS.value
    )


def test_빈_파일이면_400으로_응답한다(
    client: TestClient, verification_data: None, uploads: list[dict[str, Any]]
) -> None:
    response = _post(client, content=b"")

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []


def test_10MB를_초과하면_400으로_응답하고_업로드하지_않는다(
    client: TestClient, verification_data: None, uploads: list[dict[str, Any]]
) -> None:
    oversized = JPEG_BYTES + b"0" * images.MAX_IMAGE_SIZE_BYTE

    response = _post(client, content=oversized)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []


@pytest.mark.parametrize(
    ("progress_id", "role_progress_id"),
    [
        pytest.param(0, HOST_ROLE_PROGRESS_ID, id="0인_진행도_id"),
        pytest.param("abc", HOST_ROLE_PROGRESS_ID, id="정수가_아닌_진행도_id"),
        pytest.param(PROGRESS_ID, 0, id="0인_역할_진행도_id"),
        pytest.param(PROGRESS_ID, "abc", id="정수가_아닌_역할_진행도_id"),
    ],
)
def test_path_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient,
    verification_data: None,
    uploads: list[dict[str, Any]],
    progress_id: object,
    role_progress_id: object,
) -> None:
    response = _post(client, progress_id=progress_id, role_progress_id=role_progress_id)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []
