"""GET /api/v1/map/contents - 지도 홈 조회 테스트.

기준 문서: app/map/docs/API_SPEC.md, app/map/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.common import distance
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantRole,
    ParticipantStatus,
)
from app.guestbook.models import Guestbook, RoadGuestbook
from app.map import service
from app.map.models import Location
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/map/contents"

OTHER_USER_ID = 2

TREASURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TITLE = "오구포구 보물찾기"
COOPERATIVE_TITLE = "함께 키우는 귤나무"

# 보물찾기 미션이 있는 장소
# (한 장소에는 보물찾기 "또는" 협동 미션이 최대 하나라 유형별로 장소를 나눈다)
MISSION_LOCATION_ID = 101
MISSION_LOCATION_TITLE = "현애원"
MISSION_LATITUDE = 33.4582
MISSION_LONGITUDE = 126.9331
MISSION_CONTENT_ID = 126273

# 협동 미션이 있는 장소
COOPERATIVE_LOCATION_ID = 105
COOPERATIVE_LATITUDE = 33.4700
COOPERATIVE_LONGITUDE = 126.9500
COOPERATIVE_CONTENT_ID = 555

# 미션은 없고 방명록만 있는 장소
GUESTBOOK_LOCATION_ID = 102
GUESTBOOK_LATITUDE = 33.4600
GUESTBOOK_LONGITUDE = 126.9400
GUESTBOOK_CONTENT_ID = 999

# 미션도 방명록도 없는 장소 (미션은 null, 방명록 개수는 0 으로 나온다)
EMPTY_LOCATION_ID = 103
EMPTY_LATITUDE = 33.4650
EMPTY_LONGITUDE = 126.9450
EMPTY_CONTENT_ID = 888

# 화면 밖 장소 (미션은 있다)
OUTSIDE_LOCATION_ID = 104
OUTSIDE_LATITUDE = 33.2000
OUTSIDE_LONGITUDE = 126.5000

TREASURE_MISSION_ID = 301
COOPERATIVE_MISSION_ID = 401
OUTSIDE_TREASURE_MISSION_ID = 302

ROAD_GUESTBOOK_ID = 131
ROAD_GUESTBOOK_ALIAS = "성산 바다 앞"
ROAD_GUESTBOOK_IMAGE_URL = "https://example.com/guestbooks/131/1.jpg"

REPRESENTATIVE_IMAGE_URL = "https://example.com/locations/101.jpg"

USER_LATITUDE = 33.4524
USER_LONGITUDE = 126.9248

# 화면 안 장소들을 모두 감싸는 화면. (축에 나란한 사각형)
VIEWPORT = {
    "leftTopLatitude": 33.50,
    "leftTopLongitude": 126.90,
    "rightTopLatitude": 33.50,
    "rightTopLongitude": 127.00,
    "rightBottomLatitude": 33.40,
    "rightBottomLongitude": 127.00,
    "leftBottomLatitude": 33.40,
    "leftBottomLongitude": 126.90,
}

# 마름모 화면. 꼭짓점은 (33.50,126.95) (33.45,127.00) (33.40,126.95) (33.45,126.90)
ROTATED_VIEWPORT = {
    "leftTopLatitude": 33.50,
    "leftTopLongitude": 126.95,
    "rightTopLatitude": 33.45,
    "rightTopLongitude": 127.00,
    "rightBottomLatitude": 33.40,
    "rightBottomLongitude": 126.95,
    "leftBottomLatitude": 33.45,
    "leftBottomLongitude": 126.90,
}


def _params(
    *,
    viewport: dict[str, float] | None = None,
    is_clustered: bool = False,
    **overrides: object,
) -> dict[str, object]:
    return {
        **(viewport or VIEWPORT),
        "userLatitude": USER_LATITUDE,
        "userLongitude": USER_LONGITUDE,
        "isClustered": is_clustered,
        **overrides,
    }


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """TourAPI 이미지 조회를 막고 호출된 content_id 를 기록한다."""
    called: list[int] = []

    def fake_get_location_image_url(content_id: int) -> str | None:
        called.append(content_id)
        return REPRESENTATIVE_IMAGE_URL if content_id == MISSION_CONTENT_ID else None

    monkeypatch.setattr(service, "get_location_image_url", fake_get_location_image_url)
    return called


@pytest.fixture
def users(db_session: Session) -> None:
    """현재 사용자와 비교용 다른 사용자."""
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="나민",
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="이서연",
                point=0,
            ),
        ]
    )
    db_session.commit()


@pytest.fixture
def map_data(db_session: Session, users: None) -> None:
    """미션 장소 / 방명록만 있는 장소 / 빈 장소 / 화면 밖 장소."""
    db_session.add_all(
        [
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title=TREASURE_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "시작", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title=COOPERATIVE_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
        ]
    )
    for location_id, content_id, title, latitude, longitude in (
        (
            MISSION_LOCATION_ID,
            MISSION_CONTENT_ID,
            MISSION_LOCATION_TITLE,
            MISSION_LATITUDE,
            MISSION_LONGITUDE,
        ),
        (
            GUESTBOOK_LOCATION_ID,
            GUESTBOOK_CONTENT_ID,
            "방명록 장소",
            GUESTBOOK_LATITUDE,
            GUESTBOOK_LONGITUDE,
        ),
        (
            COOPERATIVE_LOCATION_ID,
            COOPERATIVE_CONTENT_ID,
            "협동 장소",
            COOPERATIVE_LATITUDE,
            COOPERATIVE_LONGITUDE,
        ),
        (EMPTY_LOCATION_ID, EMPTY_CONTENT_ID, "빈 장소", EMPTY_LATITUDE, EMPTY_LONGITUDE),
        (OUTSIDE_LOCATION_ID, 777, "화면 밖", OUTSIDE_LATITUDE, OUTSIDE_LONGITUDE),
    ):
        db_session.add(
            Location(
                id=location_id,
                content_id=content_id,
                location_title=title,
                location_address="제주특별자치도",
                location_category="관광지",
                radius=300,
                mx=longitude,
                my=latitude,
            )
        )
    db_session.flush()

    db_session.add_all(
        [
            TreasureMission(
                id=TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=MISSION_LOCATION_ID,
                item_total_count=3,
                reward_detail={"point": 100},
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=COOPERATIVE_LOCATION_ID,
                reward_detail={"point": 200},
            ),
            TreasureMission(
                id=OUTSIDE_TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=OUTSIDE_LOCATION_ID,
                item_total_count=3,
                reward_detail={"point": 100},
            ),
        ]
    )
    db_session.flush()
    # 방명록만 있는 장소를 지도에 띄우려면 방명록이 하나 있어야 한다.
    _add_guestbook(db_session, guestbook_id=90, location_id=GUESTBOOK_LOCATION_ID)


def _add_guestbook(
    db_session: Session,
    *,
    guestbook_id: int,
    location_id: int = MISSION_LOCATION_ID,
    user_id: int = CURRENT_USER_ID,
    mission_id: int | None = None,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        Guestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=location_id,
            mission_id=mission_id,
            visited_at=date(2026, 8, 20),
            saved_at=datetime(2026, 8, 20, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_treasure_progress(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.COMPLETED,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            treasure_mission_id=TREASURE_MISSION_ID,
            user_id=user_id,
            item_detail=[{"index": 1, "mx": MISSION_LONGITUDE, "my": MISSION_LATITUDE}],
            current_found_item_idx=[1],
            current_step=3,
            mission_status=mission_status.value,
        )
    )
    db_session.commit()


def _add_cooperative_progress(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.COMPLETED,
    participant_status: ParticipantStatus = ParticipantStatus.ACCEPTED,
    progress_deleted_at: datetime | None = None,
    participant_deleted_at: datetime | None = None,
) -> None:
    progress = CooperativeMissionProgress(
        cooperative_mission_id=COOPERATIVE_MISSION_ID,
        current_step=4,
        mission_status=mission_status.value,
        team_token=f"mock-team-token-{user_id}-{mission_status.value}",
        completed_at=datetime(2026, 8, 21, 12, 0, 0),
        deleted_at=progress_deleted_at,
    )
    db_session.add(progress)
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            cooperative_mission_progress_id=progress.id,
            user_id=user_id,
            participant_status=participant_status.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
            deleted_at=participant_deleted_at,
        )
    )
    db_session.commit()


def _add_road_guestbook(
    db_session: Session,
    *,
    guestbook_id: int = ROAD_GUESTBOOK_ID,
    latitude: float = MISSION_LATITUDE,
    longitude: float = MISSION_LONGITUDE,
    content_img_url: list[str] | None = None,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        RoadGuestbook(
            id=guestbook_id,
            user_id=CURRENT_USER_ID,
            location_id=None,
            location_alias=ROAD_GUESTBOOK_ALIAS,
            visited_at=date(2026, 8, 20),
            content_img_url=content_img_url,
            mx=longitude,
            my=latitude,
            saved_at=datetime(2026, 8, 20, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_location(
    db_session: Session, *, location_id: int, latitude: float, longitude: float
) -> None:
    """좌표만 다른 장소. (조회 영역 판정 테스트용)"""
    db_session.add(
        Location(
            id=location_id,
            content_id=location_id,
            location_title=f"장소{location_id}",
            location_address="제주특별자치도",
            location_category="카페",
            radius=200,
            mx=longitude,
            my=latitude,
        )
    )
    db_session.commit()


def _get(client: TestClient, **kwargs: object) -> dict:
    response = client.get(ENDPOINT, params=_params(**kwargs))
    assert response.status_code == 200
    return response.json()


def _locations(body: dict) -> list[dict]:
    return body["locations"]


def _location(body: dict, location_id: int) -> dict:
    found = [location for location in _locations(body) if location["id"] == location_id]
    assert len(found) == 1
    return found[0]


# ---------------------------------------------------------------------
# isClustered = false (상세)
# ---------------------------------------------------------------------


def test_화면_안의_장소를_상세_정보와_함께_반환한다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1)
    _add_guestbook(db_session, guestbook_id=2)

    expected_distance = distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, MISSION_LATITUDE, MISSION_LONGITUDE
    )
    assert _location(_get(client), MISSION_LOCATION_ID) == {
        "id": MISSION_LOCATION_ID,
        "locationTitle": MISSION_LOCATION_TITLE,
        "latitude": MISSION_LATITUDE,
        "longitude": MISSION_LONGITUDE,
        "distanceMeter": expected_distance,
        "durationMinutes": distance.calculate_duration_minutes(expected_distance),
        "treasureMission": {
            "id": TREASURE_MISSION_ID,
            "missionTitle": TREASURE_TITLE,
            "isCompleted": False,
            "hasWrittenGuestbook": None,
        },
        # 한 장소에는 미션이 최대 하나라 다른 유형은 null 이다.
        "cooperativeMission": None,
        "guestbooksCount": 2,
        "representativeImageUrl": REPRESENTATIVE_IMAGE_URL,
    }


def test_거리와_예상_시간은_공통_모듈_결과와_같다(
    client: TestClient, map_data: None
) -> None:
    location = _location(_get(client), GUESTBOOK_LOCATION_ID)

    expected_distance = distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, GUESTBOOK_LATITUDE, GUESTBOOK_LONGITUDE
    )
    assert location["distanceMeter"] == expected_distance
    assert location["durationMinutes"] == distance.calculate_duration_minutes(
        expected_distance
    )


def test_사용자_좌표가_바뀌면_거리도_바뀐다(client: TestClient, map_data: None) -> None:
    near = _location(
        _get(client, userLatitude=MISSION_LATITUDE, userLongitude=MISSION_LONGITUDE),
        MISSION_LOCATION_ID,
    )
    far = _location(_get(client), MISSION_LOCATION_ID)

    assert near["distanceMeter"] == 0
    assert far["distanceMeter"] > near["distanceMeter"]


def test_미션이_없는_장소는_두_미션이_모두_null이다(
    client: TestClient, map_data: None
) -> None:
    location = _location(_get(client), GUESTBOOK_LOCATION_ID)

    # 필드를 생략하지 않고 값만 비운다.
    assert location["treasureMission"] is None
    assert location["cooperativeMission"] is None
    assert location["representativeImageUrl"] is None


def test_한_장소에_두_유형이_다_있으면_보물찾기만_반환한다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    # 명세상 한 장소에는 미션이 최대 하나지만, 데이터가 어긋난 경우를 확인한다.
    db_session.add(
        CooperativeMission(
            id=999,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=MISSION_LOCATION_ID,
            reward_detail={"point": 200},
        )
    )
    db_session.commit()

    location = _location(_get(client), MISSION_LOCATION_ID)

    assert location["treasureMission"]["id"] == TREASURE_MISSION_ID
    assert location["cooperativeMission"] is None


def test_클러스터링에서_두_유형이_다_있으면_보물찾기를_쓴다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    db_session.add(
        CooperativeMission(
            id=999,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=MISSION_LOCATION_ID,
            reward_detail={"point": 200},
        )
    )
    db_session.commit()

    body = _get(client, is_clustered=True)

    mission_location = next(
        location
        for location in body["locations"]
        if location["id"] == MISSION_LOCATION_ID
    )
    assert mission_location["missionId"] == TREASURE_MISSION_ID
    assert mission_location["missionType"] == "TREASURE"


def test_미션도_방명록도_없는_장소도_반환한다(
    client: TestClient, map_data: None
) -> None:
    body = _get(client)

    location_ids = sorted(location["id"] for location in _locations(body))
    assert location_ids == sorted(
        [
            MISSION_LOCATION_ID,
            GUESTBOOK_LOCATION_ID,
            COOPERATIVE_LOCATION_ID,
            EMPTY_LOCATION_ID,
        ]
    )

    # 미션도 방명록도 없으면 미션은 null, 개수는 0 이다.
    empty = _location(body, EMPTY_LOCATION_ID)
    assert empty["treasureMission"] is None
    assert empty["cooperativeMission"] is None
    assert empty["guestbooksCount"] == 0


def test_방명록이_모두_삭제돼도_장소는_남고_개수만_0이_된다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    guestbook = db_session.get(Guestbook, 90)
    assert guestbook is not None
    guestbook.deleted_at = datetime(2026, 8, 21, 9, 0, 0)
    db_session.commit()

    location = _location(_get(client), GUESTBOOK_LOCATION_ID)

    assert location["guestbooksCount"] == 0


def test_화면_밖의_장소는_반환하지_않는다(client: TestClient, map_data: None) -> None:
    location_ids = [location["id"] for location in _locations(_get(client))]

    assert OUTSIDE_LOCATION_ID not in location_ids


# ---------------------------------------------------------------------
# 미션 완료 여부
# ---------------------------------------------------------------------


def test_보물찾기를_완료하면_isCompleted가_true다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_treasure_progress(db_session)

    treasure = _location(_get(client), MISSION_LOCATION_ID)["treasureMission"]

    assert treasure["isCompleted"] is True
    # 완료했지만 방명록은 아직 안 썼다.
    assert treasure["hasWrittenGuestbook"] is False


def test_진행_중인_보물찾기는_완료로_보지_않는다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_treasure_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)

    treasure = _location(_get(client), MISSION_LOCATION_ID)["treasureMission"]

    assert treasure["isCompleted"] is False
    # 미완료면 방명록을 조회하지 않는다.
    assert treasure["hasWrittenGuestbook"] is None


def test_다른_사용자의_보물찾기_완료_이력은_반영하지_않는다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_treasure_progress(db_session, user_id=OTHER_USER_ID)

    assert (
        _location(_get(client), MISSION_LOCATION_ID)["treasureMission"]["isCompleted"]
        is False
    )


def test_완료_이력이_하나라도_있으면_완료로_본다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_treasure_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)
    _add_treasure_progress(db_session)

    assert (
        _location(_get(client), MISSION_LOCATION_ID)["treasureMission"]["isCompleted"]
        is True
    )


def test_협동_미션을_완료하면_isCompleted가_true다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_cooperative_progress(db_session)

    cooperative = _location(_get(client), COOPERATIVE_LOCATION_ID)["cooperativeMission"]

    assert cooperative["isCompleted"] is True
    assert cooperative["hasWrittenGuestbook"] is False


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"mission_status": MissionStatus.IN_PROGRESS}, id="진행_중인_방"),
        pytest.param({"user_id": OTHER_USER_ID}, id="다른_사용자의_방"),
        pytest.param(
            {"participant_status": ParticipantStatus.PENDING}, id="수락되지_않은_참가자"
        ),
        pytest.param(
            {"progress_deleted_at": datetime(2026, 8, 22, 9, 0, 0)}, id="삭제된_방"
        ),
        pytest.param(
            {"participant_deleted_at": datetime(2026, 8, 22, 9, 0, 0)}, id="나간_참가자"
        ),
    ],
)
def test_협동_미션_완료로_보지_않는_경우(
    client: TestClient, db_session: Session, map_data: None, kwargs: dict
) -> None:
    _add_cooperative_progress(db_session, **kwargs)

    cooperative = _location(_get(client), COOPERATIVE_LOCATION_ID)["cooperativeMission"]

    assert cooperative["isCompleted"] is False
    assert cooperative["hasWrittenGuestbook"] is None


# ---------------------------------------------------------------------
# 미션 방명록 작성 여부
# ---------------------------------------------------------------------


def test_완료한_미션의_방명록을_쓰면_hasWrittenGuestbook이_true다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_treasure_progress(db_session)
    _add_guestbook(db_session, guestbook_id=1, mission_id=TREASURE_TYPE_ID)

    location = _location(_get(client), MISSION_LOCATION_ID)

    assert location["treasureMission"]["hasWrittenGuestbook"] is True
    # 이 장소에는 협동 미션이 없다.
    assert location["cooperativeMission"] is None


def test_다른_유형_미션의_방명록은_반영하지_않는다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_treasure_progress(db_session)
    _add_cooperative_progress(db_session)
    # 보물찾기 장소에 "협동 미션"을 참조하는 방명록을 쓴다. (유형이 어긋난 방명록)
    _add_guestbook(db_session, guestbook_id=1, mission_id=COOPERATIVE_TYPE_ID)
    # 협동 장소에는 협동 미션 방명록을 제대로 쓴다.
    _add_guestbook(
        db_session,
        guestbook_id=2,
        location_id=COOPERATIVE_LOCATION_ID,
        mission_id=COOPERATIVE_TYPE_ID,
    )

    body = _get(client)

    treasure = _location(body, MISSION_LOCATION_ID)["treasureMission"]
    cooperative = _location(body, COOPERATIVE_LOCATION_ID)["cooperativeMission"]
    assert treasure["hasWrittenGuestbook"] is False
    assert cooperative["hasWrittenGuestbook"] is True


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"user_id": OTHER_USER_ID}, id="다른_사용자의_방명록"),
        pytest.param({"deleted_at": datetime(2026, 8, 22, 9, 0, 0)}, id="삭제된_방명록"),
        pytest.param({"mission_id": None}, id="미션을_참조하지_않는_방명록"),
        pytest.param({"location_id": GUESTBOOK_LOCATION_ID}, id="다른_장소의_방명록"),
    ],
)
def test_미션_방명록으로_보지_않는_경우(
    client: TestClient, db_session: Session, map_data: None, kwargs: dict
) -> None:
    _add_treasure_progress(db_session)
    _add_guestbook(
        db_session, guestbook_id=1, **{"mission_id": TREASURE_TYPE_ID, **kwargs}
    )

    treasure = _location(_get(client), MISSION_LOCATION_ID)["treasureMission"]

    assert treasure["isCompleted"] is True
    assert treasure["hasWrittenGuestbook"] is False


# ---------------------------------------------------------------------
# 방명록 개수 / 길바닥 방명록
# ---------------------------------------------------------------------


def test_삭제된_방명록은_개수에_넣지_않는다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1)
    _add_guestbook(db_session, guestbook_id=2, deleted_at=datetime(2026, 8, 21, 9, 0, 0))

    assert _location(_get(client), MISSION_LOCATION_ID)["guestbooksCount"] == 1


def test_다른_장소의_방명록은_개수에_넣지_않는다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1, location_id=MISSION_LOCATION_ID)

    body = _get(client)

    assert _location(body, MISSION_LOCATION_ID)["guestbooksCount"] == 1
    # 픽스처에서 만든 방명록 하나만 남아 있어야 한다.
    assert _location(body, GUESTBOOK_LOCATION_ID)["guestbooksCount"] == 1


def test_길바닥_방명록을_상세_정보와_함께_반환한다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_road_guestbook(
        db_session,
        content_img_url=[ROAD_GUESTBOOK_IMAGE_URL, "https://example.com/second.jpg"],
    )

    assert _get(client)["roadGuestbooks"] == [
        {
            "id": ROAD_GUESTBOOK_ID,
            "latitude": MISSION_LATITUDE,
            "longitude": MISSION_LONGITUDE,
            "locationAlias": ROAD_GUESTBOOK_ALIAS,
            # 첫 번째 이미지를 그대로 대표 이미지로 쓴다.
            "representativeGuestbookImageUrl": ROAD_GUESTBOOK_IMAGE_URL,
        }
    ]


@pytest.mark.parametrize(
    "content_img_url",
    [
        pytest.param(None, id="이미지_없음"),
        pytest.param([], id="빈_배열"),
    ],
)
def test_길바닥_방명록_이미지가_없으면_대표_이미지는_null이다(
    client: TestClient,
    db_session: Session,
    map_data: None,
    content_img_url: list[str] | None,
) -> None:
    _add_road_guestbook(db_session, content_img_url=content_img_url)

    assert _get(client)["roadGuestbooks"][0]["representativeGuestbookImageUrl"] is None


def test_삭제된_길바닥_방명록은_반환하지_않는다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_road_guestbook(db_session, deleted_at=datetime(2026, 8, 21, 9, 0, 0))

    assert _get(client)["roadGuestbooks"] == []


def test_화면_밖의_길바닥_방명록은_반환하지_않는다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_road_guestbook(db_session, latitude=OUTSIDE_LATITUDE, longitude=OUTSIDE_LONGITUDE)

    assert _get(client)["roadGuestbooks"] == []


def test_조회_결과가_없어도_200과_빈_배열을_반환한다(
    client: TestClient, users: None
) -> None:
    assert _get(client) == {"locations": [], "roadGuestbooks": []}


def test_TourAPI_이미지를_조회하지_못하면_null로_두고_실패시키지_않는다(
    client: TestClient, map_data: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "get_location_image_url", lambda content_id: None)

    assert _location(_get(client), MISSION_LOCATION_ID)["representativeImageUrl"] is None


# ---------------------------------------------------------------------
# isClustered = true (좌표만)
# ---------------------------------------------------------------------


def test_클러스터링이면_식별자와_좌표와_미션_정보만_반환한다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_treasure_progress(db_session)
    _add_road_guestbook(db_session, content_img_url=[ROAD_GUESTBOOK_IMAGE_URL])

    body = _get(client, is_clustered=True)

    assert sorted(body["locations"], key=lambda location: location["id"]) == [
        {
            "id": MISSION_LOCATION_ID,
            "latitude": MISSION_LATITUDE,
            "longitude": MISSION_LONGITUDE,
            "missionId": TREASURE_MISSION_ID,
            "missionType": "TREASURE",
        },
        {
            "id": GUESTBOOK_LOCATION_ID,
            "latitude": GUESTBOOK_LATITUDE,
            "longitude": GUESTBOOK_LONGITUDE,
            "missionId": None,
            "missionType": None,
        },
        {
            "id": EMPTY_LOCATION_ID,
            "latitude": EMPTY_LATITUDE,
            "longitude": EMPTY_LONGITUDE,
            "missionId": None,
            "missionType": None,
        },
        {
            "id": COOPERATIVE_LOCATION_ID,
            "latitude": COOPERATIVE_LATITUDE,
            "longitude": COOPERATIVE_LONGITUDE,
            "missionId": COOPERATIVE_MISSION_ID,
            "missionType": "COOPERATIVE",
        },
    ]
    # 길바닥 방명록은 별칭·이미지 없이 식별자와 좌표만 준다.
    assert body["roadGuestbooks"] == [
        {
            "id": ROAD_GUESTBOOK_ID,
            "latitude": MISSION_LATITUDE,
            "longitude": MISSION_LONGITUDE,
        }
    ]


def test_클러스터링의_미션_id는_LOCATION_id가_아니라_세부_미션_id다(
    client: TestClient, map_data: None
) -> None:
    body = _get(client, is_clustered=True)

    treasure = next(
        location
        for location in body["locations"]
        if location["id"] == MISSION_LOCATION_ID
    )
    assert treasure["missionId"] == TREASURE_MISSION_ID
    assert treasure["missionId"] != treasure["id"]


def test_클러스터링에서_미션이_없는_장소는_두_필드가_모두_null이다(
    client: TestClient, map_data: None
) -> None:
    body = _get(client, is_clustered=True)

    empty = next(
        location for location in body["locations"] if location["id"] == EMPTY_LOCATION_ID
    )
    assert empty["missionId"] is None
    assert empty["missionType"] is None


def test_클러스터링에서도_미션도_방명록도_없는_장소를_반환한다(
    client: TestClient, map_data: None
) -> None:
    latitudes = [point["latitude"] for point in _get(client, is_clustered=True)["locations"]]

    assert EMPTY_LATITUDE in latitudes


def test_클러스터링이면_TourAPI를_호출하지_않는다(
    client: TestClient, map_data: None, stub_location_image: list[int]
) -> None:
    _get(client, is_clustered=True)

    assert stub_location_image == []


def test_클러스터링이_아니면_장소마다_TourAPI를_호출한다(
    client: TestClient, map_data: None, stub_location_image: list[int]
) -> None:
    _get(client)

    # 화면 안 장소 4곳을 조회한다. (화면 밖 장소는 조회하지 않는다)
    assert sorted(stub_location_image) == sorted(
        [
            MISSION_CONTENT_ID,
            GUESTBOOK_CONTENT_ID,
            COOPERATIVE_CONTENT_ID,
            EMPTY_CONTENT_ID,
        ]
    )


def test_클러스터링이어도_삭제된_길바닥_방명록은_빠진다(
    client: TestClient, db_session: Session, map_data: None
) -> None:
    _add_road_guestbook(db_session, deleted_at=datetime(2026, 8, 21, 9, 0, 0))

    assert _get(client, is_clustered=True)["roadGuestbooks"] == []


# ---------------------------------------------------------------------
# 회전한 화면 (네 꼭짓점이 축과 나란하지 않은 경우)
# ---------------------------------------------------------------------


def test_회전한_화면에서는_사각형_안의_장소만_반환한다(
    client: TestClient, db_session: Session, users: None
) -> None:
    # 마름모 한가운데
    _add_location(db_session, location_id=1, latitude=33.45, longitude=126.95)
    # 위도·경도 범위 안이지만 마름모 밖(왼쪽 위 모서리)
    _add_location(db_session, location_id=2, latitude=33.495, longitude=126.905)

    body = _get(client, viewport=ROTATED_VIEWPORT)

    assert [location["id"] for location in _locations(body)] == [1]


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        pytest.param(33.45, 126.90, id="왼쪽_꼭짓점"),
        pytest.param(33.50, 126.95, id="위쪽_꼭짓점"),
        pytest.param(33.40, 126.95, id="아래쪽_꼭짓점"),
        pytest.param(33.475, 126.925, id="좌상_변_위"),
        pytest.param(33.425, 126.975, id="우하_변_위"),
    ],
)
def test_경계선_위의_좌표도_포함한다(
    client: TestClient,
    db_session: Session,
    users: None,
    latitude: float,
    longitude: float,
) -> None:
    _add_location(db_session, location_id=1, latitude=latitude, longitude=longitude)

    body = _get(client, viewport=ROTATED_VIEWPORT)

    assert [location["id"] for location in _locations(body)] == [1]


# ---------------------------------------------------------------------
# 400 / 401
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("isClustered", id="isClustered_누락"),
        pytest.param("userLatitude", id="userLatitude_누락"),
        pytest.param("userLongitude", id="userLongitude_누락"),
        pytest.param("leftTopLatitude", id="꼭짓점_누락"),
    ],
)
def test_필수_Query가_없으면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, users: None, field: str
) -> None:
    params = _params()
    del params[field]

    response = client.get(ENDPOINT, params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("leftTopLatitude", "abc", id="위도가_숫자가_아님"),
        pytest.param("leftTopLatitude", 91, id="위도_상한_초과"),
        pytest.param("leftBottomLatitude", -91, id="위도_하한_미만"),
        pytest.param("leftTopLongitude", 181, id="경도_상한_초과"),
        pytest.param("leftBottomLongitude", -181, id="경도_하한_미만"),
        pytest.param("userLatitude", 91, id="사용자_위도_범위_밖"),
        pytest.param("userLongitude", -181, id="사용자_경도_범위_밖"),
        pytest.param("userLatitude", "abc", id="사용자_위도가_숫자가_아님"),
        pytest.param("isClustered", "maybe", id="boolean이_아님"),
    ],
)
def test_Query_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, users: None, field: str, value: object
) -> None:
    response = client.get(ENDPOINT, params=_params(**{field: value}))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    "corners",
    [
        pytest.param(
            {
                "leftTopLatitude": 33.45,
                "leftTopLongitude": 126.95,
                "rightTopLatitude": 33.45,
                "rightTopLongitude": 126.95,
                "rightBottomLatitude": 33.45,
                "rightBottomLongitude": 126.95,
                "leftBottomLatitude": 33.45,
                "leftBottomLongitude": 126.95,
            },
            id="네_점이_모두_같음",
        ),
        pytest.param(
            {
                "leftTopLatitude": 33.40,
                "leftTopLongitude": 126.90,
                "rightTopLatitude": 33.45,
                "rightTopLongitude": 126.95,
                "rightBottomLatitude": 33.50,
                "rightBottomLongitude": 127.00,
                "leftBottomLatitude": 33.55,
                "leftBottomLongitude": 127.05,
            },
            id="네_점이_한_직선_위",
        ),
    ],
)
def test_영역을_구성하지_못하면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, users: None, corners: dict[str, float]
) -> None:
    response = client.get(ENDPOINT, params=_params(viewport=corners))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_인증_헤더가_없으면_401로_응답한다(client: TestClient, map_data: None) -> None:
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT, params=_params())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, map_data: None
) -> None:
    response = client.get(ENDPOINT, params=_params(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_문서에_401을_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"][ENDPOINT]["get"]["responses"]

    assert "401" in responses
    assert "400" in responses
    assert "500" in responses
