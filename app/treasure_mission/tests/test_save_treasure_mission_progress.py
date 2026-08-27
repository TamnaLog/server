"""PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress - 보물찾기 진행도 저장 테스트.

기준 문서: app/treasure_mission/docs/API_SPEC.md, app/treasure_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import distance, next_location
from app.cooperative_mission.models import CooperativeMission
from app.map.models import Location
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.models import (
    AcquiredArCharacter,
    ArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash


TREASURE_TYPE_ID = 3
COOPERATIVE_TYPE_ID = 2

TREASURE_MISSION_ID = 12
ITEM_TOTAL_COUNT = 3

PROGRESS_ID = 31
OTHER_USER_ID = 2

LOCATION_ID = 7
LOCATION_TITLE = "새별 오름"
LOCATION_LAT = 33.3663
LOCATION_LNG = 126.3577
COOPERATIVE_MISSION_ID = 41

USER_LATITUDE = 33.3663
USER_LONGITUDE = 126.3582

LOCATION_IMAGE_URL = "https://example.com/locations/saebyeol.jpg"

AR_CHARACTER_ID = 8
CHARACTER_IMG_URL = "https://example.com/characters/mulbangul.png"
REWARD_POINT = 150
INITIAL_USER_POINT = 30

COUPON_LOCATION = "서귀포 올레시장 분식"
COUPON_PRICE = 3000

REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": REWARD_POINT,
    "coupon_location": COUPON_LOCATION,
    "coupon_price": COUPON_PRICE,
}

ITEM_DETAIL = [
    {"index": 1, "mx": 126.3579, "my": 33.3665},
    {"index": 2, "mx": 126.3574, "my": 33.3661},
    {"index": 3, "mx": 126.3581, "my": 33.3668},
]


def _endpoint(progress_id: object) -> str:
    return f"/api/v1/treasure-missions/{progress_id}/progress"


def _params(**overrides: object) -> dict[str, object]:
    return {"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE, **overrides}


def _ar_character_reward() -> dict[str, object]:
    return {"id": AR_CHARACTER_ID, "name": "천지연 물방울", "imageUrl": CHARACTER_IMG_URL}


def _coupon_reward() -> dict[str, object]:
    return {"couponLocation": COUPON_LOCATION, "couponPrice": COUPON_PRICE}


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """장소 이미지 조회(TourAPI)를 막아 외부 네트워크를 타지 않게 한다."""
    monkeypatch.setattr(
        next_location, "get_location_image_url", lambda content_id: LOCATION_IMAGE_URL
    )


@pytest.fixture
def progress_data(db_session: Session) -> None:
    """공통 미션 / 장소 / 보물찾기 미션 / 사용자 / 보상 캐릭터 목업 데이터."""
    db_session.add_all(
        [
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title="보물 찾기",
                description="주변에 숨겨진 AR 보물을 찾아보세요.",
                step_detail=[{"step": 1, "step_title": "보물 찾기", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="일행과 역할을 나눠보세요.",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
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
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=INITIAL_USER_POINT,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name="천지연 물방울",
                character_description="폭포에서 튀어나온 물방울 캐릭터입니다.",
                acquire_condition="보물 찾기 미션을 완료하면 만날 수 있어요.",
                character_img_url=CHARACTER_IMG_URL,
                hashtags=["#물방울"],
            ),
        ]
    )
    db_session.flush()

    db_session.add(
        TreasureMission(
            id=TREASURE_MISSION_ID,
            mission_id=TREASURE_TYPE_ID,
            location_id=LOCATION_ID,
            item_total_count=ITEM_TOTAL_COUNT,
            reward_detail=REWARD_DETAIL,
        )
    )
    db_session.commit()


def _add_progress(
    db_session: Session,
    *,
    progress_id: int = PROGRESS_ID,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
    user_id: int = CURRENT_USER_ID,
    treasure_mission_id: int = TREASURE_MISSION_ID,
    found_item_idx: list[int] | None = None,
    current_step: int = 1,
    ar_character_granted: bool = False,
    point_granted: bool = False,
    coupon_granted: bool = False,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=treasure_mission_id,
            user_id=user_id,
            item_detail=ITEM_DETAIL,
            current_found_item_idx=found_item_idx or [],
            current_step=current_step,
            mission_status=status.value,
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            coupon_reward_granted=coupon_granted,
            completed_at=(
                datetime(2026, 8, 20, 12, 0, 0) if status is MissionStatus.COMPLETED else None
            ),
        )
    )
    db_session.commit()


def _saved(db_session: Session) -> TreasureMissionProgress:
    db_session.expire_all()
    progress = db_session.get(TreasureMissionProgress, PROGRESS_ID)
    assert progress is not None
    return progress


def _user_point(db_session: Session) -> int:
    db_session.expire_all()
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    return user.point


def _acquired(db_session: Session) -> list[AcquiredArCharacter]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(AcquiredArCharacter).where(AcquiredArCharacter.user_id == CURRENT_USER_ID)
        ).all()
    )


def _find(client: TestClient, treasure_index: int) -> dict:
    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"treasureIndex": treasure_index}
    )
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------
# 진행 중 처리 (BUSINESS_RULES 7.)
# ---------------------------------------------------------------------


def test_보물을_찾으면_명세의_필드를_모두_반환한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session)

    body = _find(client, treasure_index=1)

    assert body == {
        "missionProgressStatus": "IN_PROGRESS",
        "treasureCount": ITEM_TOTAL_COUNT,
        "foundTreasureIndexes": [1],
        "nextLocation": None,
        # 첫 보물에서는 지급 순서상 첫 보상인 AR 캐릭터를 지급한다.
        "reward": {"arCharacter": _ar_character_reward(), "point": None, "coupon": None},
    }


def test_찾은_보물을_진행도에_저장하고_진행_단계를_2로_바꾼다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_step=1)

    _find(client, treasure_index=2)

    saved = _saved(db_session)
    assert saved.current_found_item_idx == [2]
    assert saved.current_step == 2
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.completed_at is None


def test_찾은_보물_목록은_오름차순으로_반환한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, found_item_idx=[3], current_step=2)

    body = _find(client, treasure_index=1)

    assert body["foundTreasureIndexes"] == [1, 3]
    assert _saved(db_session).current_found_item_idx == [1, 3]


# ---------------------------------------------------------------------
# 보상 지급 (BUSINESS_RULES 4~6.)
# ---------------------------------------------------------------------


def test_보물을_찾을_때마다_우선순위가_높은_보상을_하나씩_지급한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session)

    first = _find(client, treasure_index=1)
    second = _find(client, treasure_index=2)
    third = _find(client, treasure_index=3)

    assert first["reward"] == {
        "arCharacter": _ar_character_reward(),
        "point": None,
        "coupon": None,
    }
    assert second["reward"] == {"arCharacter": None, "point": REWARD_POINT, "coupon": None}
    assert third["reward"] == {"arCharacter": None, "point": None, "coupon": _coupon_reward()}

    assert _user_point(db_session) == INITIAL_USER_POINT + REWARD_POINT
    acquired = _acquired(db_session)
    assert len(acquired) == 1
    # 획득 기록에는 보물찾기 미션 id가 아니라 공통 MISSION.id 를 남긴다.
    assert acquired[0].acquired_mission_id == TREASURE_TYPE_ID

    saved = _saved(db_session)
    assert saved.ar_character_reward_granted is True
    assert saved.point_reward_granted is True
    assert saved.coupon_reward_granted is True


def test_지급한_보상의_지급_여부만_true로_저장한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session)

    _find(client, treasure_index=1)

    saved = _saved(db_session)
    assert saved.ar_character_reward_granted is True
    assert saved.point_reward_granted is False
    assert saved.coupon_reward_granted is False


def test_없는_보상_항목은_건너뛰고_다음_보상을_지급한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # AR 캐릭터 보상이 없는 미션이면 첫 보물에서 포인트를 지급한다.
    treasure_mission = db_session.get(TreasureMission, TREASURE_MISSION_ID)
    assert treasure_mission is not None
    treasure_mission.reward_detail = {
        "point": REWARD_POINT,
        "coupon_location": COUPON_LOCATION,
        "coupon_price": COUPON_PRICE,
    }
    db_session.commit()
    _add_progress(db_session)

    body = _find(client, treasure_index=1)

    assert body["reward"] == {"arCharacter": None, "point": REWARD_POINT, "coupon": None}
    assert _acquired(db_session) == []


def test_과거_진행도에서_지급된_보상은_재도전에서_다시_지급하지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 이전 시도에서 AR 캐릭터를 이미 받았으므로 이번 첫 보물은 포인트를 받는다.
    _add_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.COMPLETED,
        found_item_idx=[1, 2, 3],
        current_step=3,
        ar_character_granted=True,
    )
    _add_progress(db_session)

    body = _find(client, treasure_index=1)

    assert body["reward"] == {"arCharacter": None, "point": REWARD_POINT, "coupon": None}
    assert _acquired(db_session) == []


def test_보상을_모두_받았으면_보물을_찾아도_추가_보상이_없다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.COMPLETED,
        found_item_idx=[1, 2, 3],
        current_step=3,
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
    )
    _add_progress(db_session)

    body = _find(client, treasure_index=1)

    # 보상은 없지만 보물 발견과 진행도 갱신은 정상 처리한다.
    assert body["reward"] == {"arCharacter": None, "point": None, "coupon": None}
    assert body["foundTreasureIndexes"] == [1]
    assert _user_point(db_session) == INITIAL_USER_POINT
    assert _acquired(db_session) == []


def test_이미_보유한_캐릭터는_기록을_또_남기지_않고_지급_처리한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    db_session.add(
        AcquiredArCharacter(
            ar_character_id=AR_CHARACTER_ID,
            user_id=CURRENT_USER_ID,
            acquired_mission_id=COOPERATIVE_TYPE_ID,
        )
    )
    db_session.commit()
    _add_progress(db_session)

    body = _find(client, treasure_index=1)

    assert body["reward"]["arCharacter"] == _ar_character_reward()
    assert len(_acquired(db_session)) == 1
    assert _saved(db_session).ar_character_reward_granted is True


def test_보상_지급에_실패하면_보물_발견도_저장되지_않는다(
    client: TestClient, db_session: Session, progress_data: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.treasure_mission import service

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("보상 지급 실패")

    monkeypatch.setattr(service.reward_granter, "grant_next_treasure_reward", boom)
    _add_progress(db_session)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"treasureIndex": 1}
    )

    assert response.status_code == 500
    saved = _saved(db_session)
    assert saved.current_found_item_idx == []
    assert saved.current_step == 1
    assert _user_point(db_session) == INITIAL_USER_POINT


# ---------------------------------------------------------------------
# 완료 처리 (BUSINESS_RULES 8~9.)
# ---------------------------------------------------------------------


def test_마지막_보물을_찾으면_완료로_바꾸고_다음_장소를_반환한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, found_item_idx=[1, 2], current_step=2)

    body = _find(client, treasure_index=3)

    assert body["missionProgressStatus"] == "COMPLETED"
    assert body["foundTreasureIndexes"] == [1, 2, 3]

    saved_location = db_session.get(Location, LOCATION_ID)
    assert saved_location is not None
    assert body["nextLocation"] == {
        "id": LOCATION_ID,
        "locationTitle": LOCATION_TITLE,
        "locationImageUrl": LOCATION_IMAGE_URL,
        "distanceMeter": distance.calculate_distance_meter(
            USER_LATITUDE, USER_LONGITUDE, saved_location.my, saved_location.mx
        ),
        # 이 장소에 연결된 세부 미션은 지금 진행한 보물찾기 미션뿐이다.
        "mission": {"id": TREASURE_MISSION_ID, "missionType": "TREASURE"},
    }

    saved = _saved(db_session)
    assert saved.mission_status == MissionStatus.COMPLETED.value
    assert saved.current_step == 3
    assert saved.completed_at is not None


def test_완료_시에도_지급_가능한_보상_하나를_지급한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 앞선 두 보물에서 캐릭터/포인트를 받았다면 마지막 보물에서는 쿠폰을 받는다.
    _add_progress(
        db_session,
        found_item_idx=[1, 2],
        current_step=2,
        ar_character_granted=True,
        point_granted=True,
    )

    body = _find(client, treasure_index=3)

    assert body["reward"] == {"arCharacter": None, "point": None, "coupon": _coupon_reward()}
    assert _saved(db_session).coupon_reward_granted is True


def test_다음_장소에_연결된_미션이_있으면_유형과_세부_미션_id를_반환한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    db_session.add(
        CooperativeMission(
            id=COOPERATIVE_MISSION_ID,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=LOCATION_ID,
            reward_detail={},
        )
    )
    db_session.commit()
    _add_progress(db_session, found_item_idx=[1, 2], current_step=2)

    mission = _find(client, treasure_index=3)["nextLocation"]["mission"]

    # 연결된 미션이 여러 개면 그중 하나가 무작위로 선정된다.
    assert (mission["missionType"], mission["id"]) in {
        ("COOPERATIVE", COOPERATIVE_MISSION_ID),
        ("TREASURE", TREASURE_MISSION_ID),
    }


def test_장소_이미지를_조회하지_못하면_locationImageUrl은_null이다(
    client: TestClient,
    db_session: Session,
    progress_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(next_location, "get_location_image_url", lambda content_id: None)
    _add_progress(db_session, found_item_idx=[1, 2], current_step=2)

    body = _find(client, treasure_index=3)

    assert body["nextLocation"]["locationImageUrl"] is None
    assert body["missionProgressStatus"] == "COMPLETED"


def test_추천할_장소가_없으면_완료_응답을_만들지_않고_500으로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, found_item_idx=[1, 2], current_step=2)
    db_session.query(Location).delete()
    db_session.commit()

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"treasureIndex": 3}
    )

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}
    saved = _saved(db_session)
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.current_found_item_idx == [1, 2]


# ---------------------------------------------------------------------
# 404 / 409
# ---------------------------------------------------------------------


def test_진행도가_없으면_404로_응답한다(client: TestClient, progress_data: None) -> None:
    response = client.patch(_endpoint(999), params=_params(), json={"treasureIndex": 1})

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_MISSION_PROGRESS_NOT_FOUND"}


def test_다른_사용자의_진행도면_404로_응답하고_바꾸지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, user_id=OTHER_USER_ID)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"treasureIndex": 1}
    )

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_MISSION_PROGRESS_NOT_FOUND"}
    assert _saved(db_session).current_found_item_idx == []


def test_이미_완료된_진행도면_404로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(
        db_session, status=MissionStatus.COMPLETED, found_item_idx=[1, 2, 3], current_step=3
    )

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"treasureIndex": 1}
    )

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_MISSION_PROGRESS_NOT_FOUND"}


def test_진행도에_없는_보물이면_404_TREASURE_ITEM_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"treasureIndex": 99}
    )

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_ITEM_NOT_FOUND"}
    assert _saved(db_session).current_found_item_idx == []


def test_이미_찾은_보물이면_409로_응답하고_보상을_다시_주지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, found_item_idx=[1], current_step=2, ar_character_granted=True)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"treasureIndex": 1}
    )

    assert response.status_code == 409
    assert response.json() == {"code": "TREASURE_ITEM_ALREADY_FOUND"}
    assert _saved(db_session).current_found_item_idx == [1]
    assert _user_point(db_session) == INITIAL_USER_POINT


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("params", "body"),
    [
        pytest.param(_params(), {}, id="보물_번호_누락"),
        pytest.param(_params(), {"treasureIndex": 0}, id="0인_보물_번호"),
        pytest.param(_params(), {"treasureIndex": "abc"}, id="정수가_아닌_보물_번호"),
        pytest.param({"longitude": USER_LONGITUDE}, {"treasureIndex": 1}, id="위도_누락"),
        pytest.param(_params(latitude=90.1), {"treasureIndex": 1}, id="위도_범위_초과"),
        pytest.param(_params(longitude=-180.1), {"treasureIndex": 1}, id="경도_범위_초과"),
    ],
)
def test_요청_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, progress_data: None, params: dict, body: dict
) -> None:
    _add_progress(db_session)

    response = client.patch(_endpoint(PROGRESS_ID), params=params, json=body)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _saved(db_session).current_found_item_idx == []


@pytest.mark.parametrize(
    "progress_id",
    [pytest.param(0, id="0인_진행도_id"), pytest.param("abc", id="정수가_아닌_진행도_id")],
)
def test_진행도_id가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, progress_data: None, progress_id: object
) -> None:
    response = client.patch(
        _endpoint(progress_id), params=_params(), json={"treasureIndex": 1}
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
