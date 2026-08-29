"""POST /api/v1/guestbooks - 방명록 작성 테스트.

기준 문서: app/guestbook/docs/API_SPEC.md, app/guestbook/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import audios, images
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantRole,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.guestbook import service
from app.guestbook.models import Guestbook, RoadGuestbook
from app.map.models import Location, VisitedLocation
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/guestbooks"

LOCATION_ID = 39
LOCATION_TITLE = "섭지코지"
OTHER_USER_ID = 2

VISITED_AT = "2026-08-29"

CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TYPE_ID = 3
UNPLAYED_MISSION_ID = 4

CULTURE_MISSION_ID = 11
COOPERATIVE_MISSION_ID = 12
TREASURE_MISSION_ID = 13

# 실제 파일 시그니처 (형식 판별은 파일 내용으로 한다)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"0" * 32
GIF_BYTES = b"GIF89a" + b"0" * 32

MP3_BYTES = b"ID3\x03\x00\x00\x00" + b"0" * 32
M4A_BYTES = b"\x00\x00\x00\x20" + b"ftyp" + b"M4A " + b"0" * 32
WAV_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"0" * 32
OGG_BYTES = b"OggS" + b"0" * 32
WEBM_BYTES = b"\x1a\x45\xdf\xa3" + b"0" * 32
AAC_BYTES = b"\xff\xf1" + b"0" * 32
TEXT_BYTES = b"just text" + b"0" * 32


@pytest.fixture
def uploads(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Blob 업로드를 가로채 호출 인자를 기록한다. (실제 Azure 로 나가지 않게)"""
    calls: list[dict[str, Any]] = []

    def fake_upload(data: bytes, **kwargs: Any) -> str:
        url = f"https://example.blob.core.windows.net/media/{kwargs['prefix']}/{len(calls)}{kwargs['extension']}"
        calls.append({"data": data, "url": url, **kwargs})
        return url

    monkeypatch.setattr(service.blob_storage, "upload_file", fake_upload)
    return calls


@pytest.fixture
def deletes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """되돌리기용 Blob 삭제 호출을 기록한다."""
    calls: list[str] = []
    monkeypatch.setattr(service.blob_storage, "delete_file", calls.append)
    return calls


@pytest.fixture
def guestbook_data(db_session: Session) -> None:
    """장소 / 사용자 / 유형별 미션. 방문 이력과 진행도는 각 테스트에서 만든다."""
    db_session.add_all(
        [
            Location(
                id=LOCATION_ID,
                content_id=126508,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 성산읍 섭지코지로 107",
                location_category="해변",
                radius=300,
                mx=126.9300,
                my=33.4250,
            ),
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
            Mission(
                id=CULTURE_TYPE_ID,
                mission_type="CULTURE",
                mission_title="제주 문화 퀴즈",
                description="설명",
                step_detail=[{"step": 1, "step_title": "퀴즈", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="설명",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title="보물 찾기",
                description="설명",
                step_detail=[{"step": 1, "step_title": "탐색", "description": "설명"}],
            ),
            Mission(
                id=UNPLAYED_MISSION_ID,
                mission_type="CULTURE",
                mission_title="아직 안 한 미션",
                description="설명",
                step_detail=[{"step": 1, "step_title": "퀴즈", "description": "설명"}],
            ),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            CultureMission(
                id=CULTURE_MISSION_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=3,
                quiz_detail=[],
                reward_detail={},
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=LOCATION_ID,
                reward_detail={},
            ),
            TreasureMission(
                id=TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=LOCATION_ID,
                item_total_count=3,
                reward_detail={},
            ),
        ]
    )
    db_session.commit()


def _add_visit(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    visited_at: datetime = datetime(2026, 8, 20, 10, 0, 0),
) -> None:
    db_session.add(
        VisitedLocation(user_id=user_id, location_id=LOCATION_ID, visited_at=visited_at)
    )
    db_session.commit()


def _complete_culture_mission(db_session: Session, user_id: int = CURRENT_USER_ID) -> None:
    db_session.add(
        CultureMissionProgress(
            culture_mission_id=CULTURE_MISSION_ID,
            user_id=user_id,
            mission_status=MissionStatus.COMPLETED.value,
            current_quiz_index=3,
            correct_number=3,
            completed_at=datetime(2026, 8, 21, 10, 0, 0),
        )
    )
    db_session.commit()


def _complete_treasure_mission(db_session: Session) -> None:
    db_session.add(
        TreasureMissionProgress(
            treasure_mission_id=TREASURE_MISSION_ID,
            user_id=CURRENT_USER_ID,
            item_detail=[{"index": 1, "mx": 126.93, "my": 33.42}],
            current_found_item_idx=[1],
            current_step=3,
            mission_status=MissionStatus.COMPLETED.value,
            completed_at=datetime(2026, 8, 21, 11, 0, 0),
        )
    )
    db_session.commit()


def _complete_cooperative_mission(
    db_session: Session, user_id: int = CURRENT_USER_ID
) -> None:
    progress = CooperativeMissionProgress(
        cooperative_mission_id=COOPERATIVE_MISSION_ID,
        current_step=4,
        mission_status=MissionStatus.COMPLETED.value,
        team_token=f"mock-team-token-{user_id}",
        completed_at=datetime(2026, 8, 21, 12, 0, 0),
    )
    db_session.add(progress)
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            cooperative_mission_progress_id=progress.id,
            user_id=user_id,
            participant_status=ParticipantStatus.ACCEPTED.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 21, 9, 0, 0),
        )
    )
    db_session.commit()


def _general_form(**overrides: object) -> dict[str, object]:
    form = {
        "guestbookType": "GENERAL",
        "locationId": LOCATION_ID,
        "visitedAt": VISITED_AT,
    }
    form.update(overrides)
    return {key: value for key, value in form.items() if value is not None}


def _road_form(**overrides: object) -> dict[str, object]:
    form = {
        "guestbookType": "ROAD",
        "locationAlias": "성산 바다 앞",
        "latitude": 33.4582,
        "longitude": 126.9331,
        "visitedAt": VISITED_AT,
    }
    form.update(overrides)
    return {key: value for key, value in form.items() if value is not None}


def _post(
    client: TestClient,
    data: dict[str, object],
    *,
    images_: list[tuple[str, bytes, str]] | None = None,
    audios_: list[tuple[str, bytes, str]] | None = None,
    user_id: int = CURRENT_USER_ID,
) -> Any:
    files = [
        ("imageFiles", (name, content, content_type))
        for name, content, content_type in images_ or []
    ] + [
        ("audioFiles", (name, content, content_type))
        for name, content, content_type in audios_ or []
    ]
    return client.post(
        ENDPOINT, data=data, files=files or None, headers=auth_headers(user_id)
    )


def _guestbooks(db_session: Session) -> list[Guestbook]:
    db_session.expire_all()
    return list(db_session.scalars(select(Guestbook).order_by(Guestbook.id)).all())


def _road_guestbooks(db_session: Session) -> list[RoadGuestbook]:
    db_session.expire_all()
    return list(db_session.scalars(select(RoadGuestbook).order_by(RoadGuestbook.id)).all())


# ---------------------------------------------------------------------
# 일반 방명록 (BUSINESS_RULES B.4·6)
# ---------------------------------------------------------------------


def test_방문한_장소에_일반_방명록을_작성하면_201과_저장값을_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    response = _post(
        client,
        _general_form(
            contentWriting="현애원 산책하기 좋았어요.",
            contentWeather="맑음",
            contentColorCode="#84C7AE",
        ),
    )

    assert response.status_code == 201
    body = response.json()
    saved = _guestbooks(db_session)[0]
    assert body == {
        "guestbookId": saved.id,
        "guestbookType": "GENERAL",
        "locationId": LOCATION_ID,
        # 유형에서 쓰지 않는 필드도 키를 지우지 않고 null 로 둔다.
        "locationAlias": None,
        "latitude": None,
        "longitude": None,
        "visitedAt": VISITED_AT,
        "contentImageUrls": None,
        "contentWriting": "현애원 산책하기 좋았어요.",
        "contentAudioUrls": None,
        "contentWeather": "맑음",
        "contentColorCode": "#84C7AE",
        "missionId": None,
        "savedAt": saved.saved_at.isoformat(),
    }
    assert saved.user_id == CURRENT_USER_ID
    assert saved.visited_at == date(2026, 8, 29)


def test_같은_장소에_여러_번_작성하면_매번_새_행이_생긴다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    first = _post(client, _general_form(contentWriting="첫 번째"))
    second = _post(client, _general_form(contentWriting="두 번째"))

    assert first.status_code == 201
    assert second.status_code == 201
    saved = _guestbooks(db_session)
    assert len(saved) == 2
    # 기존 행을 덮어쓰지 않는다.
    assert [guestbook.content_writing for guestbook in saved] == ["첫 번째", "두 번째"]


def test_방문_날짜와_요청_visitedAt이_달라도_작성된다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    # 방문은 8/20, 방명록에 적는 날짜는 8/29
    _add_visit(db_session, visited_at=datetime(2026, 8, 20, 10, 0, 0))

    response = _post(client, _general_form())

    assert response.status_code == 201
    assert response.json()["visitedAt"] == VISITED_AT


def test_콘텐츠를_전부_생략해도_작성된다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    body = _post(client, _general_form()).json()

    assert body["contentImageUrls"] is None
    assert body["contentWriting"] is None
    assert body["contentAudioUrls"] is None
    assert body["contentWeather"] is None
    assert body["contentColorCode"] is None
    assert uploads == []


# ---------------------------------------------------------------------
# 미션 처리 (BUSINESS_RULES B.5)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("complete", "mission_id"),
    [
        pytest.param(_complete_culture_mission, CULTURE_TYPE_ID, id="문화_미션"),
        pytest.param(_complete_treasure_mission, TREASURE_TYPE_ID, id="보물찾기_미션"),
        pytest.param(_complete_cooperative_mission, COOPERATIVE_TYPE_ID, id="협동_미션"),
    ],
)
def test_완료한_미션이면_missionId를_저장한다(
    client: TestClient,
    db_session: Session,
    guestbook_data: None,
    uploads: list,
    complete: Any,
    mission_id: int,
) -> None:
    _add_visit(db_session)
    complete(db_session)

    body = _post(client, _general_form(missionId=mission_id)).json()

    assert body["missionId"] == mission_id
    assert _guestbooks(db_session)[0].mission_id == mission_id


def test_미완료_미션이면_작성은_되고_missionId는_null이다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    response = _post(client, _general_form(missionId=UNPLAYED_MISSION_ID))

    assert response.status_code == 201
    assert response.json()["missionId"] is None
    assert _guestbooks(db_session)[0].mission_id is None


def test_다른_사용자만_완료한_미션은_미완료로_처리한다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)
    _complete_culture_mission(db_session, user_id=OTHER_USER_ID)

    body = _post(client, _general_form(missionId=CULTURE_TYPE_ID)).json()

    assert body["missionId"] is None


# ---------------------------------------------------------------------
# 길바닥 방명록 (BUSINESS_RULES B.7)
# ---------------------------------------------------------------------


def test_길바닥_방명록은_장소와_방문_이력_없이_저장된다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    response = _post(client, _road_form(contentWriting="바다가 잘 보이는 길이에요."))

    assert response.status_code == 201
    body = response.json()
    saved = _road_guestbooks(db_session)[0]
    assert body == {
        "guestbookId": saved.id,
        "guestbookType": "ROAD",
        "locationId": None,
        "locationAlias": "성산 바다 앞",
        "latitude": 33.4582,
        "longitude": 126.9331,
        "visitedAt": VISITED_AT,
        "contentImageUrls": None,
        "contentWriting": "바다가 잘 보이는 길이에요.",
        "contentAudioUrls": None,
        "contentWeather": None,
        "contentColorCode": None,
        "missionId": None,
        "savedAt": saved.saved_at.isoformat(),
    }
    # LOCATION 과 같게 mx = 경도, my = 위도로 저장한다.
    assert saved.location_id is None
    assert (saved.my, saved.mx) == (33.4582, 126.9331)
    assert _guestbooks(db_session) == []


def test_같은_좌표에_여러_번_작성해도_매번_새_행이_생긴다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _post(client, _road_form())
    _post(client, _road_form())

    assert len(_road_guestbooks(db_session)) == 2


# ---------------------------------------------------------------------
# 파일 저장 (BUSINESS_RULES B.8·9)
# ---------------------------------------------------------------------


def test_이미지와_오디오_URL은_요청_순서를_유지한다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    body = _post(
        client,
        _general_form(),
        images_=[
            ("a.jpg", JPEG_BYTES, "image/jpeg"),
            ("b.png", PNG_BYTES, "image/png"),
            ("c.webp", WEBP_BYTES, "image/webp"),
        ],
        audios_=[("memo.m4a", M4A_BYTES, "audio/mp4"), ("memo2.mp3", MP3_BYTES, "audio/mpeg")],
    ).json()

    assert [url.rsplit("/", 1)[-1] for url in body["contentImageUrls"]] == [
        "0.jpg",
        "1.png",
        "2.webp",
    ]
    assert [url.rsplit("/", 1)[-1] for url in body["contentAudioUrls"]] == ["3.m4a", "4.mp3"]

    saved = _guestbooks(db_session)[0]
    assert saved.content_img_url == body["contentImageUrls"]
    assert saved.content_audio_url == body["contentAudioUrls"]


def test_방명록_id가_들어간_경로에_업로드한다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    _post(
        client,
        _general_form(),
        images_=[("a.jpg", JPEG_BYTES, "image/jpeg")],
        audios_=[("memo.m4a", M4A_BYTES, "audio/mp4")],
    )

    guestbook_id = _guestbooks(db_session)[0].id
    assert uploads[0]["prefix"] == f"guestbook/general/{guestbook_id}/images"
    assert uploads[1]["prefix"] == f"guestbook/general/{guestbook_id}/audios"
    # 원본 파일명은 blob 이름에 쓰지 않는다.
    assert not uploads[0].get("filename")


def test_길바닥_방명록도_유형별_경로에_업로드한다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _post(client, _road_form(), images_=[("a.jpg", JPEG_BYTES, "image/jpeg")])

    guestbook_id = _road_guestbooks(db_session)[0].id
    assert uploads[0]["prefix"] == f"guestbook/road/{guestbook_id}/images"


@pytest.mark.parametrize(
    ("content", "extension", "content_type"),
    [
        pytest.param(JPEG_BYTES, ".jpg", "image/jpeg", id="JPEG"),
        pytest.param(PNG_BYTES, ".png", "image/png", id="PNG"),
        pytest.param(WEBP_BYTES, ".webp", "image/webp", id="WebP"),
    ],
)
def test_이미지는_실제_형식_기준으로_확장자를_정한다(
    client: TestClient,
    db_session: Session,
    guestbook_data: None,
    uploads: list,
    content: bytes,
    extension: str,
    content_type: str,
) -> None:
    _add_visit(db_session)

    # 파일명과 Content-Type 은 일부러 다르게 보낸다.
    response = _post(client, _general_form(), images_=[("a.txt", content, "text/plain")])

    assert response.status_code == 201
    assert uploads[0]["extension"] == extension
    assert uploads[0]["content_type"] == content_type


@pytest.mark.parametrize(
    ("content", "extension", "content_type"),
    [
        pytest.param(MP3_BYTES, ".mp3", "audio/mpeg", id="MP3"),
        pytest.param(M4A_BYTES, ".m4a", "audio/mp4", id="M4A"),
        pytest.param(AAC_BYTES, ".aac", "audio/aac", id="AAC"),
        pytest.param(WAV_BYTES, ".wav", "audio/wav", id="WAV"),
        pytest.param(OGG_BYTES, ".ogg", "audio/ogg", id="OGG"),
        pytest.param(WEBM_BYTES, ".webm", "audio/webm", id="WebM"),
    ],
)
def test_오디오는_실제_형식_기준으로_확장자를_정한다(
    client: TestClient,
    db_session: Session,
    guestbook_data: None,
    uploads: list,
    content: bytes,
    extension: str,
    content_type: str,
) -> None:
    _add_visit(db_session)

    response = _post(client, _general_form(), audios_=[("a.bin", content, "audio/x-unknown")])

    assert response.status_code == 201
    assert uploads[0]["extension"] == extension
    assert uploads[0]["content_type"] == content_type


# ---------------------------------------------------------------------
# 실패 시 되돌리기 (BUSINESS_RULES B.10)
# ---------------------------------------------------------------------


def test_뒤_파일_업로드가_실패하면_앞서_올린_파일을_모두_지운다(
    client: TestClient,
    db_session: Session,
    guestbook_data: None,
    deletes: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_visit(db_session)
    uploaded: list[str] = []

    def fail_on_second(data: bytes, **kwargs: Any) -> str:
        if len(uploaded) >= 1:
            raise RuntimeError("업로드 실패")
        url = f"https://example.blob.core.windows.net/media/{kwargs['prefix']}/first.jpg"
        uploaded.append(url)
        return url

    monkeypatch.setattr(service.blob_storage, "upload_file", fail_on_second)

    response = _post(
        client,
        _general_form(),
        images_=[("a.jpg", JPEG_BYTES, "image/jpeg"), ("b.png", PNG_BYTES, "image/png")],
    )

    assert response.status_code == 500
    assert deletes == uploaded
    assert _guestbooks(db_session) == []


def test_DB_커밋이_실패하면_올린_파일을_모두_지운다(
    client: TestClient,
    db_session: Session,
    guestbook_data: None,
    uploads: list,
    deletes: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_visit(db_session)

    def boom(self: Session) -> None:
        raise RuntimeError("DB 저장 실패")

    monkeypatch.setattr(Session, "commit", boom)

    response = _post(
        client,
        _general_form(),
        images_=[("a.jpg", JPEG_BYTES, "image/jpeg")],
        audios_=[("memo.mp3", MP3_BYTES, "audio/mpeg")],
    )

    assert response.status_code == 500
    assert deletes == [upload["url"] for upload in uploads]


# ---------------------------------------------------------------------
# 404 / 409
# ---------------------------------------------------------------------


def test_장소가_없으면_404이고_아무것도_남지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    response = _post(
        client,
        _general_form(locationId=999),
        images_=[("a.jpg", JPEG_BYTES, "image/jpeg")],
    )

    assert response.status_code == 404
    assert response.json() == {"code": "LOCATION_NOT_FOUND"}
    assert uploads == []
    assert _guestbooks(db_session) == []


def test_방문_이력이_없으면_409이고_아무것도_남지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    # 다른 사용자만 방문한 장소
    _add_visit(db_session, user_id=OTHER_USER_ID)

    response = _post(client, _general_form(), images_=[("a.jpg", JPEG_BYTES, "image/jpeg")])

    assert response.status_code == 409
    assert response.json() == {"code": "LOCATION_NOT_VISITED"}
    assert uploads == []
    assert _guestbooks(db_session) == []


def test_미션이_없으면_404이고_아무것도_남지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    response = _post(
        client,
        _general_form(missionId=999),
        images_=[("a.jpg", JPEG_BYTES, "image/jpeg")],
    )

    assert response.status_code == 404
    assert response.json() == {"code": "MISSION_NOT_FOUND"}
    assert uploads == []
    assert _guestbooks(db_session) == []


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({"guestbookType": "GENERAL", "visitedAt": VISITED_AT}, id="일반_장소_id_누락"),
        pytest.param(
            {
                "guestbookType": "GENERAL",
                "locationId": LOCATION_ID,
                "visitedAt": VISITED_AT,
                "latitude": 33.4,
                "longitude": 126.9,
                "locationAlias": "쓰면 안 되는 값",
            },
            id="일반에_길바닥_필드",
        ),
        pytest.param(
            {"guestbookType": "ROAD", "visitedAt": VISITED_AT, "locationAlias": "성산"},
            id="길바닥_좌표_누락",
        ),
        pytest.param(
            {
                "guestbookType": "ROAD",
                "locationAlias": "성산",
                "latitude": 33.4,
                "longitude": 126.9,
                "visitedAt": VISITED_AT,
                "locationId": LOCATION_ID,
            },
            id="길바닥에_장소_id",
        ),
        pytest.param(
            {
                "guestbookType": "ROAD",
                "locationAlias": "성산",
                "latitude": 33.4,
                "longitude": 126.9,
                "visitedAt": VISITED_AT,
                "missionId": CULTURE_TYPE_ID,
            },
            id="길바닥에_미션_id",
        ),
        pytest.param(
            {
                "guestbookType": "ROAD",
                "locationAlias": "성산",
                "latitude": 91,
                "longitude": 126.9,
                "visitedAt": VISITED_AT,
            },
            id="위도_범위_초과",
        ),
        pytest.param({"guestbookType": "MEMO", "visitedAt": VISITED_AT}, id="정의되지_않은_유형"),
        pytest.param({"guestbookType": "GENERAL", "locationId": LOCATION_ID}, id="방문_날짜_누락"),
        pytest.param(
            {
                "guestbookType": "GENERAL",
                "locationId": LOCATION_ID,
                "visitedAt": "2026-08-29T10:00:00",
            },
            id="날짜가_아닌_visitedAt",
        ),
    ],
)
def test_요청_형식이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list, data: dict
) -> None:
    _add_visit(db_session)

    response = _post(client, data, images_=[("a.jpg", JPEG_BYTES, "image/jpeg")])

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []
    assert _guestbooks(db_session) == []
    assert _road_guestbooks(db_session) == []


@pytest.mark.parametrize(
    ("images_", "audios_"),
    [
        pytest.param([("a.gif", GIF_BYTES, "image/gif")], None, id="허용하지_않는_이미지"),
        pytest.param([("a.jpg", b"", "image/jpeg")], None, id="빈_이미지"),
        pytest.param(None, [("a.txt", TEXT_BYTES, "audio/mpeg")], id="허용하지_않는_오디오"),
        pytest.param(None, [("a.mp3", b"", "audio/mpeg")], id="빈_오디오"),
    ],
)
def test_파일이_잘못되면_400이고_아무것도_남지_않는다(
    client: TestClient,
    db_session: Session,
    guestbook_data: None,
    uploads: list,
    images_: list | None,
    audios_: list | None,
) -> None:
    _add_visit(db_session)

    response = _post(client, _general_form(), images_=images_, audios_=audios_)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert uploads == []
    assert _guestbooks(db_session) == []


def test_이미지가_10MB를_넘으면_400이다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)
    oversized = JPEG_BYTES + b"0" * images.MAX_IMAGE_SIZE_BYTE

    response = _post(client, _general_form(), images_=[("a.jpg", oversized, "image/jpeg")])

    assert response.status_code == 400
    assert uploads == []


def test_오디오가_30MB를_넘으면_400이다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)
    oversized = MP3_BYTES + b"0" * audios.MAX_AUDIO_SIZE_BYTE

    response = _post(client, _general_form(), audios_=[("a.mp3", oversized, "audio/mpeg")])

    assert response.status_code == 400
    assert uploads == []


def test_토큰의_사용자가_없으면_401이고_아무것도_남지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None, uploads: list
) -> None:
    _add_visit(db_session)

    response = _post(client, _general_form(), user_id=999)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert uploads == []
    assert _guestbooks(db_session) == []
