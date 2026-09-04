"""POST /api/v1/users/me/travel-ending-contents - 여행 마무리 엽서 저장 테스트.

기준 문서: app/mypage/docs/API_SPEC.md, app/mypage/docs/BUSINESS_RULES.md

OpenAI / TourAPI / Azure Blob 은 외부 서비스라 호출하지 않고 대체한다.
(호출 여부와 넘긴 값까지 확인해야 해서 기록하는 가짜 함수를 쓴다)
"""

import json
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantRole,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.map.models import Location, VisitedLocation
from app.mission.models import Mission, MissionStatus
from app.mypage import service, travel_ending_image_generator
from app.mypage.constants import TRAVEL_ENDING_CREATION_POINT_COST
from app.mypage.models import TravelEndingContent
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me/travel-ending-contents"

OTHER_USER_ID = 2

POINT = 2000

CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TYPE_ID = 3

CULTURE_MISSION_ID = 11
COOPERATIVE_MISSION_ID = 12
TREASURE_MISSION_ID = 13

LOCATION_ID = 21
OTHER_LOCATION_ID = 22
THIRD_LOCATION_ID = 23
LOCATION_TITLE = "성산일출봉"
OTHER_LOCATION_TITLE = "애월 해변"
THIRD_LOCATION_TITLE = "한라산"

LOCATION_CONTENT_ID = 1001
OTHER_LOCATION_CONTENT_ID = 1002
THIRD_LOCATION_CONTENT_ID = 1003

QUIZ_IMAGE_URL = "https://cdn.example.com/quizzes/jeju-1.jpg"
TRAVEL_NOTE = "잠깐 머문, 오래 남는 순간."

BLOB_URL = "https://example.blob.core.windows.net/media/travel-ending/1/abcdef.png"

# 파일 시그니처만 맞춘 최소 이미지. (형식 판별은 내용 앞부분만 본다)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
GIF_BYTES = b"GIF89a" + b"0" * 32


@pytest.fixture
def ending_data(db_session: Session) -> None:
    """사용자 2명 + 장소 3곳 + 유형별 미션 3개."""
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=POINT,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=POINT,
            ),
            Location(
                id=LOCATION_ID,
                content_id=LOCATION_CONTENT_ID,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 성산읍",
                location_category="관광지",
                radius=300,
                mx=126.9410,
                my=33.4580,
            ),
            Location(
                id=OTHER_LOCATION_ID,
                content_id=OTHER_LOCATION_CONTENT_ID,
                location_title=OTHER_LOCATION_TITLE,
                location_address="제주특별자치도 제주시 애월읍",
                location_category="해변",
                radius=300,
                mx=126.3300,
                my=33.4600,
            ),
            Location(
                id=THIRD_LOCATION_ID,
                content_id=THIRD_LOCATION_CONTENT_ID,
                location_title=THIRD_LOCATION_TITLE,
                location_address="제주특별자치도 제주시 1100로",
                location_category="자연",
                radius=500,
                mx=126.5312,
                my=33.3617,
            ),
            Mission(
                id=CULTURE_TYPE_ID,
                mission_type="CULTURE",
                mission_title="성산일출봉 문화 퀴즈",
                description="설명",
                step_detail=[{"step": 1, "step_title": "퀴즈", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="설명",
                step_detail=[{"step": 1, "step_title": "1단계", "description": "설명"}],
            ),
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title="한라산 보물찾기",
                description="설명",
                step_detail=[{"step": 1, "step_title": "보물", "description": "설명"}],
            ),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            CultureMission(
                id=CULTURE_MISSION_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=2,
                # 첫 번째 퀴즈에는 이미지가 없다. (두 번째의 이미지를 써야 한다)
                quiz_detail=[
                    {"quiz_index": 1, "question": "질문"},
                    {"quiz_index": 2, "question": "질문", "img_url": QUIZ_IMAGE_URL},
                ],
                reward_detail={"point": 100},
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=OTHER_LOCATION_ID,
                reward_detail={"point": 200},
            ),
            TreasureMission(
                id=TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=THIRD_LOCATION_ID,
                item_total_count=3,
                reward_detail={"point": 150},
            ),
        ]
    )
    db_session.commit()


@pytest.fixture
def visited_and_completed(db_session: Session, ending_data: None) -> None:
    """현재 사용자가 장소 3곳을 방문하고 미션 3개를 완료한 상태."""
    db_session.add_all(
        [
            VisitedLocation(
                id=1,
                user_id=CURRENT_USER_ID,
                location_id=LOCATION_ID,
                visited_at=datetime(2026, 8, 18, 10, 0, 0),
            ),
            # 같은 장소를 두 번 방문해도 선택 가능 여부에는 영향이 없다.
            VisitedLocation(
                id=2,
                user_id=CURRENT_USER_ID,
                location_id=LOCATION_ID,
                visited_at=datetime(2026, 8, 19, 10, 0, 0),
            ),
            VisitedLocation(
                id=3,
                user_id=CURRENT_USER_ID,
                location_id=OTHER_LOCATION_ID,
                visited_at=datetime(2026, 8, 20, 10, 0, 0),
            ),
            VisitedLocation(
                id=4,
                user_id=CURRENT_USER_ID,
                location_id=THIRD_LOCATION_ID,
                visited_at=datetime(2026, 8, 21, 10, 0, 0),
            ),
        ]
    )
    _add_culture_progress(db_session, progress_id=1)
    _add_treasure_progress(db_session, progress_id=2)
    _add_cooperative_progress(db_session, progress_id=3, participant_id=1)
    db_session.commit()


def _add_culture_progress(
    db_session: Session,
    *,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
    status: MissionStatus = MissionStatus.COMPLETED,
) -> None:
    db_session.add(
        CultureMissionProgress(
            id=progress_id,
            culture_mission_id=CULTURE_MISSION_ID,
            user_id=user_id,
            mission_status=status.value,
            current_quiz_index=2,
            correct_number=2,
            completed_at=(
                datetime(2026, 8, 20, 14, 20, 0)
                if status is MissionStatus.COMPLETED
                else None
            ),
        )
    )


def _add_treasure_progress(
    db_session: Session,
    *,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
    status: MissionStatus = MissionStatus.COMPLETED,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=TREASURE_MISSION_ID,
            user_id=user_id,
            item_detail=[{"index": 1, "mx": 126.5, "my": 33.3}],
            current_found_item_idx=[1],
            current_step=3,
            mission_status=status.value,
            completed_at=(
                datetime(2026, 8, 19, 11, 30, 0)
                if status is MissionStatus.COMPLETED
                else None
            ),
        )
    )


def _add_cooperative_progress(
    db_session: Session,
    *,
    progress_id: int,
    participant_id: int,
    user_id: int = CURRENT_USER_ID,
    status: MissionStatus = MissionStatus.COMPLETED,
    participant_status: ParticipantStatus = ParticipantStatus.ACCEPTED,
    participant_deleted_at: datetime | None = None,
    progress_deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        CooperativeMissionProgress(
            id=progress_id,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=1,
            mission_status=status.value,
            team_token=f"team-token-{progress_id}",
            completed_at=(
                datetime(2026, 8, 18, 9, 0, 0)
                if status is MissionStatus.COMPLETED
                else None
            ),
            deleted_at=progress_deleted_at,
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=participant_id,
            cooperative_mission_progress_id=progress_id,
            user_id=user_id,
            participant_role=ParticipantRole.HOST.value,
            participant_status=participant_status.value,
            deleted_at=participant_deleted_at,
        )
    )


class _FakeOpenAI:
    """OpenAI 이미지 생성을 대신한다. 호출 여부와 넘긴 값을 기록한다."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[Any], str | None]] = []

    def __call__(
        self, sources: list[Any], travel_note: str | None
    ) -> bytes:
        self.calls.append((sources, travel_note))
        return PNG_BYTES

    @property
    def called(self) -> bool:
        return bool(self.calls)


class _FakeBlob:
    """Blob 업로드/삭제를 대신한다."""

    def __init__(self) -> None:
        self.uploaded: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self.upload_count = 0

    def upload_file(self, data: bytes, **kwargs: Any) -> str:
        self.upload_count += 1
        url = f"{BLOB_URL}?n={self.upload_count}"
        self.uploaded.append({"data": data, "url": url, **kwargs})
        return url

    def delete_file(self, blob_url: str) -> None:
        self.deleted.append(blob_url)


@pytest.fixture
def fake_openai(monkeypatch: pytest.MonkeyPatch) -> _FakeOpenAI:
    fake = _FakeOpenAI()
    monkeypatch.setattr(
        service.travel_ending_image_generator, "generate_travel_ending_image", fake
    )
    return fake


@pytest.fixture
def fake_blob(monkeypatch: pytest.MonkeyPatch) -> _FakeBlob:
    fake = _FakeBlob()
    monkeypatch.setattr(service.blob_storage, "upload_file", fake.upload_file)
    monkeypatch.setattr(service.blob_storage, "delete_file", fake.delete_file)
    return fake


@pytest.fixture
def fake_kto(monkeypatch: pytest.MonkeyPatch) -> dict[int, str]:
    """TourAPI 대표 이미지 조회를 대신한다. content id 로 URL 을 돌려준다."""
    image_urls = {
        LOCATION_CONTENT_ID: "https://tour.example.com/seongsan.jpg",
        OTHER_LOCATION_CONTENT_ID: "https://tour.example.com/aewol.jpg",
        # 한라산은 대표 이미지가 없는 장소로 둔다.
    }
    monkeypatch.setattr(
        service.kto, "get_location_image_url", lambda content_id: image_urls.get(content_id)
    )
    return image_urls


def _photo(name: str = "photo.jpg", data: bytes = JPEG_BYTES) -> tuple[str, bytes, str]:
    return (name, data, "image/jpeg")


def _files(
    *,
    visited_location_ids: object = None,
    missions: object = None,
    photos: list[tuple[str, bytes, str]] | None = None,
    travel_note: str | None = None,
) -> list[tuple[str, Any]]:
    """multipart 요청 폼을 만든다. 배열 두 개는 JSON 문자열 한 필드로 보낸다."""
    if visited_location_ids is None:
        visited_location_ids = [LOCATION_ID]
    if missions is None:
        missions = [{"missionType": "CULTURE", "missionId": CULTURE_MISSION_ID}]
    if photos is None:
        photos = [_photo()]

    form: list[tuple[str, Any]] = [
        (
            "visitedLocationIds",
            (
                None,
                visited_location_ids
                if isinstance(visited_location_ids, str)
                else json.dumps(visited_location_ids),
            ),
        ),
        (
            "missions",
            (None, missions if isinstance(missions, str) else json.dumps(missions)),
        ),
    ]
    form.extend(("photos", photo) for photo in photos)
    if travel_note is not None:
        form.append(("travelNote", (None, travel_note)))
    return form


def _post(client: TestClient, **kwargs: Any) -> Any:
    return client.post(
        ENDPOINT, files=_files(**kwargs), headers=auth_headers(CURRENT_USER_ID)
    )


def _contents(db_session: Session) -> list[TravelEndingContent]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(TravelEndingContent).order_by(TravelEndingContent.id)
        ).all()
    )


def _point(db_session: Session, user_id: int = CURRENT_USER_ID) -> int:
    db_session.expire_all()
    user = db_session.get(User, user_id)
    assert user is not None
    return user.point


# ---------------------------------------------------------------------
# 정상 저장
# ---------------------------------------------------------------------


def test_엽서를_만들면_201과_id_이미지_URL_잔여_포인트를_반환한다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    response = _post(client, travel_note=TRAVEL_NOTE)

    assert response.status_code == 201
    contents = _contents(db_session)
    assert len(contents) == 1
    assert response.json() == {
        "id": contents[0].id,
        "imageUrl": fake_blob.uploaded[0]["url"],
        "remainingPoint": POINT - TRAVEL_ENDING_CREATION_POINT_COST,
    }


def test_생성된_PNG만_Blob에_올리고_URL을_저장한다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    _post(client)

    # 사용자 원본 사진과 외부 대표 이미지는 올리지 않는다.
    assert len(fake_blob.uploaded) == 1
    uploaded = fake_blob.uploaded[0]
    assert uploaded["data"] == PNG_BYTES
    assert uploaded["prefix"] == f"travel-ending/{CURRENT_USER_ID}"
    assert uploaded["extension"] == ".png"
    assert uploaded["content_type"] == "image/png"

    saved = _contents(db_session)[0]
    assert saved.user_id == CURRENT_USER_ID
    assert saved.image_url == uploaded["url"]


def test_생성마다_100포인트를_차감한다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    _post(client)

    assert _point(db_session) == POINT - TRAVEL_ENDING_CREATION_POINT_COST


def test_카테고리마다_3개까지_선택할_수_있다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    response = _post(
        client,
        visited_location_ids=[LOCATION_ID, OTHER_LOCATION_ID, THIRD_LOCATION_ID],
        missions=[
            {"missionType": "CULTURE", "missionId": CULTURE_MISSION_ID},
            {"missionType": "TREASURE", "missionId": TREASURE_MISSION_ID},
            {"missionType": "COOPERATIVE", "missionId": COOPERATIVE_MISSION_ID},
        ],
        photos=[_photo("1.jpg"), _photo("2.png", PNG_BYTES), _photo("3.jpg")],
    )

    assert response.status_code == 201
    sources, _ = fake_openai.calls[0]
    assert len(sources) == 9


def test_같은_요청을_두_번_보내면_행과_Blob이_각각_생기고_200포인트가_차감된다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    first = _post(client)
    second = _post(client)

    assert first.status_code == second.status_code == 201
    assert first.json()["imageUrl"] != second.json()["imageUrl"]
    assert len(_contents(db_session)) == 2
    assert _point(db_session) == POINT - TRAVEL_ENDING_CREATION_POINT_COST * 2


# ---------------------------------------------------------------------
# 프롬프트 재료 (manifest 입력)
# ---------------------------------------------------------------------


def test_방문_장소는_이름과_TourAPI_대표_이미지를_재료로_넘긴다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    _post(client, visited_location_ids=[LOCATION_ID])

    sources, _ = fake_openai.calls[0]
    location_source = sources[0]
    assert location_source.source_type is travel_ending_image_generator.SourceType.VISITED_LOCATION
    assert location_source.display_name == LOCATION_TITLE
    assert location_source.location_name == LOCATION_TITLE
    assert location_source.image_url == fake_kto[LOCATION_CONTENT_ID]


def test_대표_이미지가_없는_장소도_이름만_남기고_계속_진행한다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    # 한라산은 TourAPI 대표 이미지가 없는 장소다.
    response = _post(client, visited_location_ids=[THIRD_LOCATION_ID])

    assert response.status_code == 201
    sources, _ = fake_openai.calls[0]
    assert sources[0].display_name == THIRD_LOCATION_TITLE
    assert sources[0].image_url is None


def test_보물찾기_미션은_미션명과_장소명_장소_이미지를_넘긴다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    _post(
        client,
        missions=[{"missionType": "TREASURE", "missionId": TREASURE_MISSION_ID}],
    )

    sources, _ = fake_openai.calls[0]
    mission_source = sources[1]
    assert mission_source.source_type is travel_ending_image_generator.SourceType.MISSION
    assert mission_source.display_name == "한라산 보물찾기"
    assert mission_source.location_name == THIRD_LOCATION_TITLE


def test_협동_미션은_연결된_장소의_대표_이미지를_넘긴다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    _post(
        client,
        missions=[{"missionType": "COOPERATIVE", "missionId": COOPERATIVE_MISSION_ID}],
    )

    sources, _ = fake_openai.calls[0]
    mission_source = sources[1]
    assert mission_source.location_name == OTHER_LOCATION_TITLE
    assert mission_source.image_url == fake_kto[OTHER_LOCATION_CONTENT_ID]


def test_문화_미션은_장소_없이_첫_유효_퀴즈_이미지를_넘긴다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    _post(client, missions=[{"missionType": "CULTURE", "missionId": CULTURE_MISSION_ID}])

    sources, _ = fake_openai.calls[0]
    mission_source = sources[1]
    assert mission_source.display_name == "성산일출봉 문화 퀴즈"
    # 장소를 추론하지 않는다.
    assert mission_source.location_name is None
    # 첫 번째 퀴즈에는 이미지가 없어서 두 번째 퀴즈의 이미지를 쓴다.
    assert mission_source.image_url == QUIZ_IMAGE_URL


def test_사용자_사진은_검증한_바이트를_그대로_넘기고_여행_한_줄도_원문_그대로_넘긴다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    _post(client, photos=[_photo("1.jpg"), _photo("2.png", PNG_BYTES)], travel_note=TRAVEL_NOTE)

    sources, travel_note = fake_openai.calls[0]
    photo_sources = [
        source
        for source in sources
        if source.source_type is travel_ending_image_generator.SourceType.USER_PHOTO
    ]
    assert [source.image_data for source in photo_sources] == [JPEG_BYTES, PNG_BYTES]
    assert travel_note == TRAVEL_NOTE


def test_여행_한_줄은_생략할_수_있다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    response = _post(client)

    assert response.status_code == 201
    _, travel_note = fake_openai.calls[0]
    assert travel_note is None


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "case"),
    [
        pytest.param({"visited_location_ids": []}, "장소_0개", id="장소_0개"),
        pytest.param(
            {
                "visited_location_ids": [
                    LOCATION_ID,
                    OTHER_LOCATION_ID,
                    THIRD_LOCATION_ID,
                    LOCATION_ID + 100,
                ]
            },
            "장소_4개",
            id="장소_4개",
        ),
        pytest.param({"missions": []}, "미션_0개", id="미션_0개"),
        pytest.param(
            {
                "missions": [
                    {"missionType": "CULTURE", "missionId": CULTURE_MISSION_ID},
                    {"missionType": "TREASURE", "missionId": TREASURE_MISSION_ID},
                    {"missionType": "COOPERATIVE", "missionId": COOPERATIVE_MISSION_ID},
                    {"missionType": "CULTURE", "missionId": CULTURE_MISSION_ID + 1},
                ]
            },
            "미션_4개",
            id="미션_4개",
        ),
        pytest.param({"photos": []}, "사진_0개", id="사진_0개"),
        pytest.param(
            {"photos": [_photo("1.jpg"), _photo("2.jpg"), _photo("3.jpg"), _photo("4.jpg")]},
            "사진_4개",
            id="사진_4개",
        ),
    ],
)
def test_선택_개수가_1개_미만이거나_3개를_넘으면_400이다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
    kwargs: dict[str, Any],
    case: str,
) -> None:
    response = _post(client, **kwargs)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert not fake_openai.called
    assert _point(db_session) == POINT
    assert _contents(db_session) == []


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"visited_location_ids": "[15, 22"}, id="장소_잘못된_JSON"),
        pytest.param({"visited_location_ids": '{"id": 15}'}, id="장소_배열이_아님"),
        pytest.param({"missions": "not-json"}, id="미션_잘못된_JSON"),
        pytest.param(
            {"visited_location_ids": [LOCATION_ID, LOCATION_ID]}, id="중복_장소"
        ),
        pytest.param(
            {
                "missions": [
                    {"missionType": "CULTURE", "missionId": CULTURE_MISSION_ID},
                    {"missionType": "CULTURE", "missionId": CULTURE_MISSION_ID},
                ]
            },
            id="중복_미션_쌍",
        ),
        pytest.param(
            {"missions": [{"missionType": "QUIZ", "missionId": 1}]},
            id="허용되지_않은_미션_유형",
        ),
        pytest.param(
            {"missions": [{"missionType": "CULTURE", "missionId": True}]},
            id="미션_id가_bool",
        ),
        pytest.param(
            {"missions": [{"missionType": "CULTURE", "missionId": 0}]},
            id="미션_id가_0",
        ),
        pytest.param({"visited_location_ids": [True]}, id="장소_id가_bool"),
        pytest.param({"visited_location_ids": [1.5]}, id="장소_id가_소수"),
    ],
)
def test_잘못된_JSON이나_중복_잘못된_값은_400이다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
    kwargs: dict[str, Any],
) -> None:
    response = _post(client, **kwargs)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert not fake_openai.called
    assert _point(db_session) == POINT


@pytest.mark.parametrize(
    "photo",
    [
        pytest.param(("photo.gif", GIF_BYTES, "image/gif"), id="허용되지_않은_형식"),
        pytest.param(("photo.jpg", b"", "image/jpeg"), id="빈_파일"),
        pytest.param(
            ("photo.jpg", b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024), "image/jpeg"),
            id="10MB_초과",
        ),
    ],
)
def test_허용되지_않는_사진이면_400이고_OpenAI를_호출하지_않는다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
    photo: tuple[str, bytes, str],
) -> None:
    response = _post(client, photos=[photo])

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert not fake_openai.called
    assert fake_blob.uploaded == []
    assert _point(db_session) == POINT


def test_방문하지_않은_장소가_있으면_전체_요청이_400이다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    # 장소 하나만 다른 사용자가 방문한 장소로 만든다.
    db_session.add(
        VisitedLocation(
            id=10,
            user_id=OTHER_USER_ID,
            location_id=LOCATION_ID,
            visited_at=datetime(2026, 8, 22, 10, 0, 0),
        )
    )
    db_session.commit()
    db_session.execute(
        VisitedLocation.__table__.delete().where(
            VisitedLocation.user_id == CURRENT_USER_ID,
            VisitedLocation.location_id == LOCATION_ID,
        )
    )
    db_session.commit()

    response = _post(client, visited_location_ids=[LOCATION_ID, OTHER_LOCATION_ID])

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert not fake_openai.called
    assert _point(db_session) == POINT
    assert _contents(db_session) == []


def test_완료하지_않은_미션이_있으면_전체_요청이_400이다(
    client: TestClient,
    db_session: Session,
    ending_data: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    db_session.add(
        VisitedLocation(
            id=1,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=datetime(2026, 8, 18, 10, 0, 0),
        )
    )
    # 문화 미션은 아직 진행 중이다.
    _add_culture_progress(db_session, progress_id=1, status=MissionStatus.IN_PROGRESS)
    db_session.commit()

    response = _post(client)

    assert response.status_code == 400
    assert not fake_openai.called
    assert _point(db_session) == POINT


def test_다른_사용자가_완료한_미션은_400이다(
    client: TestClient,
    db_session: Session,
    ending_data: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    db_session.add(
        VisitedLocation(
            id=1,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=datetime(2026, 8, 18, 10, 0, 0),
        )
    )
    _add_culture_progress(db_session, progress_id=1, user_id=OTHER_USER_ID)
    db_session.commit()

    response = _post(client)

    assert response.status_code == 400
    assert not fake_openai.called


@pytest.mark.parametrize(
    ("participant_status", "participant_deleted_at", "progress_deleted_at"),
    [
        pytest.param(ParticipantStatus.PENDING, None, None, id="수락되지_않은_참가"),
        pytest.param(
            ParticipantStatus.ACCEPTED, datetime(2026, 8, 20, 9, 0, 0), None, id="삭제된_참가"
        ),
        pytest.param(
            ParticipantStatus.ACCEPTED, None, datetime(2026, 8, 20, 9, 0, 0), id="삭제된_방"
        ),
    ],
)
def test_협동_미션의_제외_대상은_400이다(
    client: TestClient,
    db_session: Session,
    ending_data: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
    participant_status: ParticipantStatus,
    participant_deleted_at: datetime | None,
    progress_deleted_at: datetime | None,
) -> None:
    db_session.add(
        VisitedLocation(
            id=1,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=datetime(2026, 8, 18, 10, 0, 0),
        )
    )
    _add_cooperative_progress(
        db_session,
        progress_id=1,
        participant_id=1,
        participant_status=participant_status,
        participant_deleted_at=participant_deleted_at,
        progress_deleted_at=progress_deleted_at,
    )
    db_session.commit()

    response = _post(
        client,
        missions=[{"missionType": "COOPERATIVE", "missionId": COOPERATIVE_MISSION_ID}],
    )

    assert response.status_code == 400
    assert not fake_openai.called
    assert _point(db_session) == POINT


# ---------------------------------------------------------------------
# 409 INSUFFICIENT_POINT
# ---------------------------------------------------------------------


def test_포인트가_100_미만이면_409이고_아무것도_바뀌지_않는다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.point = TRAVEL_ENDING_CREATION_POINT_COST - 1
    db_session.commit()

    response = _post(client)

    assert response.status_code == 409
    assert response.json() == {"code": "INSUFFICIENT_POINT"}
    # 이미지 생성과 Blob 업로드를 시작하지 않는다.
    assert not fake_openai.called
    assert fake_blob.uploaded == []
    assert _point(db_session) == TRAVEL_ENDING_CREATION_POINT_COST - 1
    assert _contents(db_session) == []


def test_포인트가_정확히_100이면_성공하고_0이_된다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.point = TRAVEL_ENDING_CREATION_POINT_COST
    db_session.commit()

    response = _post(client)

    assert response.status_code == 201
    assert response.json()["remainingPoint"] == 0
    assert _point(db_session) == 0


# ---------------------------------------------------------------------
# 실패 시 되돌리기
# ---------------------------------------------------------------------


def test_이미지_생성이_실패하면_Blob과_포인트와_DB가_그대로다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any, **kwargs: Any) -> bytes:
        raise travel_ending_image_generator.TravelEndingImageError("생성 실패")

    monkeypatch.setattr(
        service.travel_ending_image_generator, "generate_travel_ending_image", fail
    )

    response = _post(client)

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}
    assert fake_blob.uploaded == []
    assert _point(db_session) == POINT
    assert _contents(db_session) == []


def test_Blob_업로드가_실패하면_포인트와_DB가_그대로다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_kto: dict[int, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("blob 업로드 실패")

    monkeypatch.setattr(service.blob_storage, "upload_file", fail)

    response = _post(client)

    assert response.status_code == 500
    assert _point(db_session) == POINT
    assert _contents(db_session) == []


def test_DB_저장이_실패하면_포인트가_롤백되고_올린_Blob을_지운다(
    client: TestClient,
    db_session: Session,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
    fake_kto: dict[int, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(self: Session) -> None:
        raise RuntimeError("commit 실패")

    monkeypatch.setattr(Session, "commit", fail)

    response = _post(client)

    assert response.status_code == 500
    assert len(fake_blob.uploaded) == 1
    # 방금 올린 Blob 을 지운다.
    assert fake_blob.deleted == [fake_blob.uploaded[0]["url"]]

    monkeypatch.undo()
    assert _point(db_session) == POINT
    assert _contents(db_session) == []


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


def test_어떤_사용자의_토큰도_아니면_401을_반환한다(
    client: TestClient,
    visited_and_completed: None,
    fake_openai: _FakeOpenAI,
    fake_blob: _FakeBlob,
) -> None:
    response = client.post(ENDPOINT, files=_files(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert not fake_openai.called
