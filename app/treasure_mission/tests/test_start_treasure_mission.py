"""POST /api/v1/treasure-missions/{treasureMissionId}/progress - 보물찾기 시작/이어하기 테스트.

기준 문서: app/treasure_mission/docs/API_SPEC.md, app/treasure_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.distance import calculate_distance_meter
from app.core.deps import CURRENT_USER_ID
from app.map.models import Location
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.constants import TREASURE_APPEAR_RADIUS_METER
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress
from app.user.models import User


TREASURE_TYPE_ID = 3

TREASURE_MISSION_ID = 12
ITEM_TOTAL_COUNT = 3

LOCATION_ID = 7
LOCATION_TITLE = "새별 오름"
LOCATION_LAT = 33.3663
LOCATION_LNG = 126.3577

OTHER_USER_ID = 2

# 장소에서 동쪽으로 약 50m 떨어진 사용자 위치
USER_LATITUDE = 33.3663
USER_LONGITUDE = 126.3582

# 진행도에 저장돼 있는 보물 좌표. [{index, mx, my}]
SAVED_ITEM_DETAIL = [
    {"index": 1, "mx": 126.3579, "my": 33.3665},
    {"index": 2, "mx": 126.3574, "my": 33.3661},
    {"index": 3, "mx": 126.3581, "my": 33.3668},
]


def _endpoint(treasure_mission_id: object) -> str:
    return f"/api/v1/treasure-missions/{treasure_mission_id}/progress"


def _params(**overrides: object) -> dict[str, object]:
    return {"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE, **overrides}


@pytest.fixture
def treasure_mission_data(db_session: Session) -> None:
    """공통 미션 / 장소 / 보물찾기 미션 / 사용자 목업 데이터."""
    db_session.add_all(
        [
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title="보물 찾기",
                description="주변에 숨겨진 AR 보물을 찾아보세요.",
                step_detail=[{"step": 1, "step_title": "보물 찾기", "description": "설명"}],
            ),
            Location(
                id=LOCATION_ID,
                content_id=2686931,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 제주시 애월읍 봉성리 산 59-8",
                location_category="오름",
                radius=300,
                mx=LOCATION_LNG,
                my=LOCATION_LAT,
            ),
            User(id=CURRENT_USER_ID, nickname="몽글몽글파도", point=0),
            User(id=OTHER_USER_ID, nickname="한라봉주스", point=0),
        ]
    )
    db_session.flush()

    db_session.add(
        TreasureMission(
            id=TREASURE_MISSION_ID,
            mission_id=TREASURE_TYPE_ID,
            location_id=LOCATION_ID,
            item_total_count=ITEM_TOTAL_COUNT,
            reward_detail={"ar_character_id": 8, "point": 150},
        )
    )
    db_session.commit()


def _add_progress(
    db_session: Session,
    *,
    progress_id: int = 1,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
    user_id: int = CURRENT_USER_ID,
    treasure_mission_id: int = TREASURE_MISSION_ID,
    found_item_idx: list[int] | None = None,
    current_step: int = 1,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=treasure_mission_id,
            user_id=user_id,
            item_detail=SAVED_ITEM_DETAIL,
            current_found_item_idx=found_item_idx or [],
            current_step=current_step,
            mission_status=status.value,
            completed_at=(
                datetime(2026, 8, 20, 12, 0, 0) if status is MissionStatus.COMPLETED else None
            ),
        )
    )
    db_session.commit()


def _progresses(db_session: Session) -> list[TreasureMissionProgress]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(TreasureMissionProgress)
            .where(
                TreasureMissionProgress.user_id == CURRENT_USER_ID,
                TreasureMissionProgress.treasure_mission_id == TREASURE_MISSION_ID,
            )
            .order_by(TreasureMissionProgress.id)
        ).all()
    )


# ---------------------------------------------------------------------
# 응답 형식
# ---------------------------------------------------------------------


def test_보물찾기를_처음_시작하면_명세의_필드를_모두_반환한다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    response = client.post(_endpoint(TREASURE_MISSION_ID), params=_params())

    assert response.status_code == 201
    body = response.json()

    progresses = _progresses(db_session)
    assert len(progresses) == 1

    assert body["treasureMissionProgressId"] == progresses[0].id
    assert body["missionProgressStatus"] == "IN_PROGRESS"
    assert body["location"] == {
        "locationTitle": LOCATION_TITLE,
        "lat": LOCATION_LAT,
        "lng": LOCATION_LNG,
    }
    assert body["treasureCount"] == ITEM_TOTAL_COUNT
    assert [item["treasureIndex"] for item in body["treasureItems"]] == [1, 2, 3]
    assert all(set(item["location"]) == {"lat", "lng"} for item in body["treasureItems"])
    # 새로 만든 진행도는 아직 찾은 보물이 없다.
    assert all(item["isFound"] is False for item in body["treasureItems"])
    # 반경 값은 프론트가 관리하므로 응답에 넣지 않는다.
    assert "radius" not in body


def test_신규_진행도는_보물_좌표와_빈_발견_목록을_저장한다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    body = client.post(_endpoint(TREASURE_MISSION_ID), params=_params()).json()

    saved = _progresses(db_session)[0]
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.current_found_item_idx == []
    assert saved.current_step == 1
    assert saved.completed_at is None

    # 저장된 좌표와 응답 좌표가 같아야 한다. (index 는 1부터 중복 없이)
    assert [item["index"] for item in saved.item_detail] == [1, 2, 3]
    assert [
        {"lat": item["my"], "lng": item["mx"]} for item in saved.item_detail
    ] == [item["location"] for item in body["treasureItems"]]


# ---------------------------------------------------------------------
# 보물 좌표 생성 (BUSINESS_RULES 5.)
# ---------------------------------------------------------------------


def test_생성된_보물은_장소_중심의_등장_반경_안에_있다(
    client: TestClient, treasure_mission_data: None
) -> None:
    # 좌표가 랜덤이므로 값 자체가 아니라 규칙을 만족하는지로 검증한다.
    body = client.post(_endpoint(TREASURE_MISSION_ID), params=_params()).json()

    for item in body["treasureItems"]:
        distance = calculate_distance_meter(
            LOCATION_LAT, LOCATION_LNG, item["location"]["lat"], item["location"]["lng"]
        )
        assert distance <= TREASURE_APPEAR_RADIUS_METER


def test_생성된_보물은_사용자가_있는_쪽_반원에_있다(
    client: TestClient, treasure_mission_data: None
) -> None:
    # 사용자 방향 벡터와 보물 방향 벡터의 내적이 0 이상이어야 한다.
    body = client.post(_endpoint(TREASURE_MISSION_ID), params=_params()).json()

    user_x = USER_LONGITUDE - LOCATION_LNG
    user_y = USER_LATITUDE - LOCATION_LAT
    for item in body["treasureItems"]:
        treasure_x = item["location"]["lng"] - LOCATION_LNG
        treasure_y = item["location"]["lat"] - LOCATION_LAT
        assert treasure_x * user_x + treasure_y * user_y >= 0


def test_사용자가_장소와_같은_위치여도_보물을_생성한다(
    client: TestClient, treasure_mission_data: None
) -> None:
    # 방향 벡터를 정할 수 없으면 원 전체에서 생성한다.
    response = client.post(
        _endpoint(TREASURE_MISSION_ID),
        params=_params(latitude=LOCATION_LAT, longitude=LOCATION_LNG),
    )

    assert response.status_code == 201
    items = response.json()["treasureItems"]
    assert len(items) == ITEM_TOTAL_COUNT
    for item in items:
        distance = calculate_distance_meter(
            LOCATION_LAT, LOCATION_LNG, item["location"]["lat"], item["location"]["lng"]
        )
        assert distance <= TREASURE_APPEAR_RADIUS_METER


def test_보물은_미션의_전체_보물_개수만큼_생성한다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    treasure_mission = db_session.get(TreasureMission, TREASURE_MISSION_ID)
    assert treasure_mission is not None
    treasure_mission.item_total_count = 5
    db_session.commit()

    body = client.post(_endpoint(TREASURE_MISSION_ID), params=_params()).json()

    assert body["treasureCount"] == 5
    assert [item["treasureIndex"] for item in body["treasureItems"]] == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------
# 이어하기 (BUSINESS_RULES 6.)
# ---------------------------------------------------------------------


def test_진행_중인_기록이_있으면_새로_만들지_않고_200으로_이어서_반환한다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    _add_progress(db_session, progress_id=1, found_item_idx=[1])

    response = client.post(_endpoint(TREASURE_MISSION_ID), params=_params())

    assert response.status_code == 200
    body = response.json()
    assert body["treasureMissionProgressId"] == 1
    # 진행도가 새로 생기지 않아야 한다.
    assert len(_progresses(db_session)) == 1


def test_이어하기는_저장된_보물_좌표를_그대로_반환한다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    # 요청 좌표로 보물 위치를 다시 계산하면 안 된다.
    _add_progress(db_session, progress_id=1)

    body = client.post(
        _endpoint(TREASURE_MISSION_ID), params=_params(latitude=33.5, longitude=126.5)
    ).json()

    assert [item["location"] for item in body["treasureItems"]] == [
        {"lat": item["my"], "lng": item["mx"]} for item in SAVED_ITEM_DETAIL
    ]
    saved = _progresses(db_session)[0]
    assert saved.item_detail == SAVED_ITEM_DETAIL


def test_찾은_보물은_isFound가_true로_반환된다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    _add_progress(db_session, progress_id=1, found_item_idx=[1, 3])

    body = client.post(_endpoint(TREASURE_MISSION_ID), params=_params()).json()

    assert {
        item["treasureIndex"]: item["isFound"] for item in body["treasureItems"]
    } == {1: True, 2: False, 3: True}


def test_완료_기록만_있으면_재도전_진행도를_새로_만든다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    _add_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.COMPLETED,
        found_item_idx=[1, 2, 3],
        current_step=3,
    )

    response = client.post(_endpoint(TREASURE_MISSION_ID), params=_params())

    assert response.status_code == 201
    body = response.json()
    assert body["treasureMissionProgressId"] != 1
    assert all(item["isFound"] is False for item in body["treasureItems"])

    progresses = _progresses(db_session)
    assert len(progresses) == 2
    # 기존 완료 기록은 그대로 남아 있어야 한다.
    completed = progresses[0]
    assert completed.id == 1
    assert completed.mission_status == MissionStatus.COMPLETED.value
    assert completed.current_found_item_idx == [1, 2, 3]


def test_시작_API를_연속으로_호출해도_진행도는_하나만_남는다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    first = client.post(_endpoint(TREASURE_MISSION_ID), params=_params())
    second = client.post(_endpoint(TREASURE_MISSION_ID), params=_params())

    assert first.status_code == 201
    assert second.status_code == 200
    assert (
        first.json()["treasureMissionProgressId"]
        == second.json()["treasureMissionProgressId"]
    )
    assert len(_progresses(db_session)) == 1


# ---------------------------------------------------------------------
# 사용자 / 미션 구분
# ---------------------------------------------------------------------


def test_다른_사용자의_진행도는_이어받지_않는다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    _add_progress(db_session, progress_id=1, user_id=OTHER_USER_ID)

    response = client.post(_endpoint(TREASURE_MISSION_ID), params=_params())

    assert response.status_code == 201
    assert response.json()["treasureMissionProgressId"] != 1


def test_다른_보물찾기_미션의_진행도는_이어받지_않는다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    other_mission_id = 13
    db_session.add(
        TreasureMission(
            id=other_mission_id,
            mission_id=TREASURE_TYPE_ID,
            location_id=LOCATION_ID,
            item_total_count=ITEM_TOTAL_COUNT,
            reward_detail={},
        )
    )
    db_session.commit()
    _add_progress(db_session, progress_id=1, treasure_mission_id=other_mission_id)

    response = client.post(_endpoint(TREASURE_MISSION_ID), params=_params())

    assert response.status_code == 201
    assert response.json()["treasureMissionProgressId"] != 1


# ---------------------------------------------------------------------
# 404 TREASURE_MISSION_NOT_FOUND
# ---------------------------------------------------------------------


def test_보물찾기_미션이_없으면_404로_응답하고_진행도를_만들지_않는다(
    client: TestClient, db_session: Session, treasure_mission_data: None
) -> None:
    response = client.post(_endpoint(999), params=_params())

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_MISSION_NOT_FOUND"}
    assert _progresses(db_session) == []


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"longitude": USER_LONGITUDE}, id="위도_누락"),
        pytest.param({"latitude": USER_LATITUDE}, id="경도_누락"),
        pytest.param(_params(latitude=90.1), id="위도_범위_초과"),
        pytest.param(_params(longitude=-180.1), id="경도_범위_초과"),
        pytest.param(_params(latitude="abc"), id="숫자가_아닌_위도"),
    ],
)
def test_위치_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, treasure_mission_data: None, params: dict
) -> None:
    response = client.post(_endpoint(TREASURE_MISSION_ID), params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _progresses(db_session) == []


@pytest.mark.parametrize(
    "treasure_mission_id",
    [pytest.param(0, id="0인_미션_id"), pytest.param("abc", id="정수가_아닌_미션_id")],
)
def test_미션_id가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, treasure_mission_data: None, treasure_mission_id: object
) -> None:
    response = client.post(_endpoint(treasure_mission_id), params=_params())

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
