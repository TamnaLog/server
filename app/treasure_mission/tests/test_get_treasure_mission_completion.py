"""GET /api/v1/missions/{missionType}/{missionId}/completion - 완료한 보물찾기 추천 화면 테스트.

기준 문서: app/treasure_mission/docs/API_SPEC.md, app/treasure_mission/docs/BUSINESS_RULES.md

TourAPI 는 외부 서비스라 호출하지 않고 대체한다. (content id 로 이미지 URL 을 돌려주는 가짜 함수)
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.distance import calculate_distance_meter, calculate_duration_minutes
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantRole,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.map.models import Location
from app.mission.models import Mission, MissionStatus
from app.treasure_mission import service
from app.treasure_mission.models import (
    ArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


OTHER_USER_ID = 2

# 공통 MISSION id 와 유형별 세부 미션 id 를 일부러 다르게 둔다.
CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TYPE_ID = 3

CULTURE_MISSION_ID = 11
COOPERATIVE_MISSION_ID = 12

# 완료한(= 지금 보고 있는) 보물찾기와 추천 후보들
TREASURE_MISSION_ID = 13
NEAR_MISSION_ID = 14
MID_MISSION_ID = 15
FAR_MISSION_ID = 16
EMPTY_MISSION_ID = 17

LOCATION_ID = 21
NEAR_LOCATION_ID = 22
MID_LOCATION_ID = 23
FAR_LOCATION_ID = 24
EMPTY_LOCATION_ID = 25
COUPON_LOCATION_ID = 26
COUPON_LOCATION_DUPLICATE_ID = 27

# 사용자 위치 (제주시청 근처)
USER_LATITUDE = 33.4996
USER_LONGITUDE = 126.5312

CHARACTER_ID = 5
CHARACTER_NAME = "돌멩이 정령"
CHARACTER_IMAGE_URL = "https://example.com/characters/stone-spirit.png"

COUPON_LOCATION_TITLE = "타라 소품"
COUPON_LOCATION_ADDRESS = "제주특별자치도 제주시 예시로 44"

# 유형별 미션 보상. 문화/협동은 쿠폰이 있고 보물찾기는 캐릭터+포인트만 있다.
CULTURE_REWARD = {"point": 100, "coupon_location": COUPON_LOCATION_TITLE, "coupon_price": 1000}
COOPERATIVE_REWARD = {
    "point": 200,
    "coupon_location": "없는 사용처",
    "coupon_price": 2000,
}
TREASURE_REWARD = {"ar_character_id": CHARACTER_ID, "point": 150}
NEAR_REWARD = {
    "ar_character_id": CHARACTER_ID,
    "point": 300,
    "coupon_location": COUPON_LOCATION_TITLE,
    "coupon_price": 3000,
}

SAVED_ITEM_DETAIL = [
    {"index": 1, "mx": 126.5313, "my": 33.4997},
    {"index": 2, "mx": 126.5314, "my": 33.4998},
    {"index": 3, "mx": 126.5315, "my": 33.4999},
]

COMPLETED_AT = datetime(2026, 8, 25, 14, 30, 0)


def _endpoint(
    mission_type: object = "TREASURE", mission_id: object = TREASURE_MISSION_ID
) -> str:
    return f"/api/v1/missions/{mission_type}/{mission_id}/completion"


def _params(**overrides: object) -> dict[str, object]:
    return {"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE, **overrides}


def _location(
    location_id: int, title: str, latitude: float, longitude: float, *, content_id: int
) -> Location:
    return Location(
        id=location_id,
        content_id=content_id,
        location_title=title,
        location_address=f"제주특별자치도 제주시 {title}로",
        location_category="관광지",
        radius=300,
        mx=longitude,
        my=latitude,
    )


@pytest.fixture
def completion_data(db_session: Session) -> None:
    """사용자 2명 + 장소 + 유형별 미션 + 추천 후보 보물찾기."""
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
            ArCharacter(
                id=CHARACTER_ID,
                character_name=CHARACTER_NAME,
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="획득 조건",
                character_img_url=CHARACTER_IMAGE_URL,
                hashtags=["#돌멩이"],
            ),
            # 완료한 미션의 장소 (사용자 위치와 같은 지점)
            _location(LOCATION_ID, "제주시청", USER_LATITUDE, USER_LONGITUDE, content_id=101),
            # 추천 후보. 위도 차이로 거리 순서를 만든다. (가까움 → 중간 → 멂)
            _location(NEAR_LOCATION_ID, "가까운 오름", 33.5006, USER_LONGITUDE, content_id=102),
            _location(MID_LOCATION_ID, "중간 오름", 33.5096, USER_LONGITUDE, content_id=103),
            _location(FAR_LOCATION_ID, "먼 오름", 33.5996, USER_LONGITUDE, content_id=104),
            _location(EMPTY_LOCATION_ID, "보물없는 오름", 33.4997, USER_LONGITUDE, content_id=105),
            # 쿠폰 사용처와 이름이 같은 장소 (id 가 작은 쪽을 써야 한다)
            _location(
                COUPON_LOCATION_ID,
                COUPON_LOCATION_TITLE,
                33.4900,
                126.5200,
                content_id=106,
            ),
            _location(
                COUPON_LOCATION_DUPLICATE_ID,
                COUPON_LOCATION_TITLE,
                33.4800,
                126.5100,
                content_id=107,
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
                mission_title="보물 찾기",
                description="설명",
                step_detail=[{"step": 1, "step_title": "보물", "description": "설명"}],
            ),
        ]
    )
    db_session.flush()

    # 장소 주소는 명세대로 LOCATION.location_address 를 쓴다.
    coupon_location = db_session.get(Location, COUPON_LOCATION_ID)
    assert coupon_location is not None
    coupon_location.location_address = COUPON_LOCATION_ADDRESS

    db_session.add_all(
        [
            CultureMission(
                id=CULTURE_MISSION_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=2,
                quiz_detail=[{"quiz_index": 1}],
                reward_detail=CULTURE_REWARD,
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=LOCATION_ID,
                reward_detail=COOPERATIVE_REWARD,
            ),
            TreasureMission(
                id=TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=LOCATION_ID,
                item_total_count=3,
                reward_detail=TREASURE_REWARD,
            ),
            TreasureMission(
                id=NEAR_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=NEAR_LOCATION_ID,
                item_total_count=3,
                reward_detail=NEAR_REWARD,
            ),
            TreasureMission(
                id=MID_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=MID_LOCATION_ID,
                item_total_count=3,
                reward_detail={"point": 100},
            ),
            TreasureMission(
                id=FAR_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=FAR_LOCATION_ID,
                item_total_count=3,
                reward_detail={},
            ),
            # 찾을 보물이 없어서 추천하지 않는 미션
            TreasureMission(
                id=EMPTY_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=EMPTY_LOCATION_ID,
                item_total_count=0,
                reward_detail={"point": 100},
            ),
        ]
    )
    db_session.commit()


@pytest.fixture
def completed_progress(db_session: Session, completion_data: None) -> None:
    """보물 3개를 모두 찾은 완료 진행도 1건."""
    _add_progress(db_session, progress_id=1, found_item_idx=[1, 2, 3])
    db_session.commit()


def _add_progress(
    db_session: Session,
    *,
    progress_id: int,
    treasure_mission_id: int = TREASURE_MISSION_ID,
    user_id: int = CURRENT_USER_ID,
    status: MissionStatus = MissionStatus.COMPLETED,
    found_item_idx: list[int] | None = None,
    completed_at: datetime | None = COMPLETED_AT,
    ar_character_granted: bool = False,
    point_granted: bool = False,
    coupon_granted: bool = False,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=treasure_mission_id,
            user_id=user_id,
            item_detail=SAVED_ITEM_DETAIL,
            current_found_item_idx=found_item_idx or [],
            current_step=3,
            mission_status=status.value,
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            coupon_reward_granted=coupon_granted,
            completed_at=completed_at,
        )
    )


def _add_culture_progress(
    db_session: Session,
    *,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
    coupon_granted: bool = True,
) -> None:
    db_session.add(
        CultureMissionProgress(
            id=progress_id,
            culture_mission_id=CULTURE_MISSION_ID,
            user_id=user_id,
            mission_status=MissionStatus.COMPLETED.value,
            current_quiz_index=2,
            correct_number=2,
            coupon_reward_granted=coupon_granted,
            completed_at=COMPLETED_AT,
        )
    )


def _add_cooperative_progress(
    db_session: Session,
    *,
    progress_id: int,
    participant_id: int,
    user_id: int = CURRENT_USER_ID,
    coupon_granted: bool = True,
    participant_status: ParticipantStatus = ParticipantStatus.ACCEPTED,
    participant_deleted_at: datetime | None = None,
    progress_deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        CooperativeMissionProgress(
            id=progress_id,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=1,
            mission_status=MissionStatus.COMPLETED.value,
            team_token=f"team-token-{progress_id}",
            coupon_reward_granted=coupon_granted,
            completed_at=COMPLETED_AT,
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


@pytest.fixture
def fake_kto(monkeypatch: pytest.MonkeyPatch) -> dict[int, str]:
    """TourAPI 대표 이미지 조회를 대신한다. content id 로 URL 을 돌려준다."""
    image_urls = {
        102: "https://tour.example.com/near.jpg",
        103: "https://tour.example.com/mid.jpg",
        106: "https://tour.example.com/coupon.jpg",
        # 104(먼 오름), 101, 107 은 이미지가 없는 장소로 둔다.
    }
    monkeypatch.setattr(
        service.kto, "get_location_image_url", lambda content_id: image_urls.get(content_id)
    )
    return image_urls


def _get(client: TestClient, **overrides: object) -> dict[str, Any]:
    response = client.get(
        _endpoint(), params=_params(**overrides), headers=auth_headers(CURRENT_USER_ID)
    )
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------
# 완료 미션 정보
# ---------------------------------------------------------------------


def test_완료한_보물찾기_정보를_명세대로_반환한다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    body = _get(client)

    assert body["completedMission"] == {
        "missionId": TREASURE_MISSION_ID,
        "missionType": "TREASURE",
        "completedAt": "2026-08-25T14:30:00",
        "arCharacterImageUrl": CHARACTER_IMAGE_URL,
    }


def test_캐릭터_보상이_없으면_이미지가_null이다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    treasure_mission = db_session.get(TreasureMission, TREASURE_MISSION_ID)
    assert treasure_mission is not None
    treasure_mission.reward_detail = {"point": 150}
    db_session.commit()

    assert _get(client)["completedMission"]["arCharacterImageUrl"] is None


def test_가장_최근_완료_진행도의_완료_시각을_쓴다(
    client: TestClient,
    db_session: Session,
    completion_data: None,
    fake_kto: dict[int, str],
) -> None:
    _add_progress(
        db_session,
        progress_id=1,
        found_item_idx=[1, 2, 3],
        completed_at=datetime(2026, 8, 20, 9, 0, 0),
    )
    _add_progress(
        db_session,
        progress_id=2,
        found_item_idx=[1, 2, 3],
        completed_at=datetime(2026, 8, 26, 10, 0, 0),
    )
    db_session.commit()

    assert _get(client)["completedMission"]["completedAt"] == "2026-08-26T10:00:00"


def test_완료_시각이_같으면_id가_큰_진행도를_쓴다(
    client: TestClient,
    db_session: Session,
    completion_data: None,
    fake_kto: dict[int, str],
) -> None:
    # 완료 시각이 같지만 id 가 큰 2번은 보물을 다 찾았고, 1번은 하나 빠졌다.
    _add_progress(db_session, progress_id=1, found_item_idx=[1, 2])
    _add_progress(db_session, progress_id=2, found_item_idx=[1, 2, 3])
    db_session.commit()

    response = client.get(
        _endpoint(), params=_params(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 200


# ---------------------------------------------------------------------
# 근처 보물찾기 추천
# ---------------------------------------------------------------------


def test_추천_미션은_명세의_필드를_모두_반환한다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    body = _get(client)

    near_location = db_session.get(Location, NEAR_LOCATION_ID)
    assert near_location is not None
    distance = calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, near_location.my, near_location.mx
    )
    assert body["nearbyTreasureMissions"][0] == {
        "missionId": NEAR_MISSION_ID,
        "missionType": "TREASURE",
        "locationId": NEAR_LOCATION_ID,
        "missionTitle": "보물 찾기",
        "representativeImageUrl": fake_kto[102],
        "distanceMeter": distance,
        "durationMinutes": calculate_duration_minutes(distance),
        "rewardDetail": {
            "arCharacter": {
                "id": CHARACTER_ID,
                "name": CHARACTER_NAME,
                "imageUrl": CHARACTER_IMAGE_URL,
                "isReceived": False,
            },
            "point": {"amount": 300, "isReceived": False},
            "coupon": {
                "couponLocation": COUPON_LOCATION_TITLE,
                "couponPrice": 3000,
                "isReceived": False,
            },
        },
    }
    # 난이도는 반환하지 않는다.
    assert "difficulty" not in body["nearbyTreasureMissions"][0]


def test_추천은_거리순_최대_3개이고_현재_미션과_보물없는_미션은_제외한다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    body = _get(client)

    assert [mission["missionId"] for mission in body["nearbyTreasureMissions"]] == [
        NEAR_MISSION_ID,
        MID_MISSION_ID,
        FAR_MISSION_ID,
    ]


def test_거리가_같으면_미션_id_오름차순이다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    # 먼 오름을 가까운 오름과 같은 좌표로 옮긴다. (거리 동률)
    far_location = db_session.get(Location, FAR_LOCATION_ID)
    near_location = db_session.get(Location, NEAR_LOCATION_ID)
    assert far_location is not None and near_location is not None
    far_location.my, far_location.mx = near_location.my, near_location.mx
    db_session.commit()

    body = _get(client)

    ids = [mission["missionId"] for mission in body["nearbyTreasureMissions"]]
    assert ids.index(NEAR_MISSION_ID) < ids.index(FAR_MISSION_ID)


def test_이미_완료한_다른_보물찾기도_추천에_포함한다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_progress(
        db_session,
        progress_id=2,
        treasure_mission_id=NEAR_MISSION_ID,
        found_item_idx=[1, 2, 3],
    )
    db_session.commit()

    body = _get(client)

    assert NEAR_MISSION_ID in [
        mission["missionId"] for mission in body["nearbyTreasureMissions"]
    ]


def test_대표_이미지를_얻지_못하면_그_값만_null이다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    body = _get(client)

    # 먼 오름(content_id=104)은 TourAPI 이미지가 없는 장소다.
    far = next(
        mission
        for mission in body["nearbyTreasureMissions"]
        if mission["missionId"] == FAR_MISSION_ID
    )
    assert far["representativeImageUrl"] is None
    assert far["missionTitle"] == "보물 찾기"


def test_추천할_미션이_없으면_빈_배열이다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    for mission_id in (NEAR_MISSION_ID, MID_MISSION_ID, FAR_MISSION_ID, EMPTY_MISSION_ID):
        treasure_mission = db_session.get(TreasureMission, mission_id)
        assert treasure_mission is not None
        db_session.delete(treasure_mission)
    db_session.commit()

    assert _get(client)["nearbyTreasureMissions"] == []


# ---------------------------------------------------------------------
# 추천 미션 보상 수령 여부
# ---------------------------------------------------------------------


def test_수령_여부는_해당_미션_전체_진행도를_OR한다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    # 추천 미션(가까운 오름)의 진행도 두 건에서 각각 다른 보상을 받았다.
    _add_progress(
        db_session,
        progress_id=2,
        treasure_mission_id=NEAR_MISSION_ID,
        status=MissionStatus.IN_PROGRESS,
        completed_at=None,
        ar_character_granted=True,
    )
    _add_progress(
        db_session,
        progress_id=3,
        treasure_mission_id=NEAR_MISSION_ID,
        found_item_idx=[1, 2, 3],
        point_granted=True,
    )
    db_session.commit()

    body = _get(client)

    reward = body["nearbyTreasureMissions"][0]["rewardDetail"]
    assert reward["arCharacter"]["isReceived"] is True
    assert reward["point"]["isReceived"] is True
    # 쿠폰은 아직 받지 않았지만 보상 정보는 그대로 준다.
    assert reward["coupon"]["isReceived"] is False


def test_다른_사용자의_수령_이력은_반영하지_않는다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_progress(
        db_session,
        progress_id=2,
        treasure_mission_id=NEAR_MISSION_ID,
        user_id=OTHER_USER_ID,
        found_item_idx=[1, 2, 3],
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
    )
    db_session.commit()

    reward = _get(client)["nearbyTreasureMissions"][0]["rewardDetail"]

    assert reward["arCharacter"]["isReceived"] is False
    assert reward["point"]["isReceived"] is False
    assert reward["coupon"]["isReceived"] is False


def test_설정되지_않은_보상만_null이다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    body = _get(client)

    # 중간 오름은 포인트만, 먼 오름은 아무 보상도 설정돼 있지 않다.
    mid = body["nearbyTreasureMissions"][1]["rewardDetail"]
    assert mid["arCharacter"] is None
    assert mid["point"] == {"amount": 100, "isReceived": False}
    assert mid["coupon"] is None

    far = body["nearbyTreasureMissions"][2]["rewardDetail"]
    assert far == {"arCharacter": None, "point": None, "coupon": None}


# ---------------------------------------------------------------------
# 받은 쿠폰
# ---------------------------------------------------------------------


def test_세_유형에서_받은_쿠폰을_모두_반환한다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_culture_progress(db_session, progress_id=1)
    _add_cooperative_progress(db_session, progress_id=2, participant_id=1)
    _add_progress(
        db_session,
        progress_id=2,
        treasure_mission_id=NEAR_MISSION_ID,
        found_item_idx=[1, 2, 3],
        coupon_granted=True,
    )
    db_session.commit()

    body = _get(client)

    assert body["receivedCoupons"] == [
        # 협동: 이름이 같은 장소가 없어서 장소 값이 모두 null 이다.
        {
            "couponLocation": "없는 사용처",
            "couponPrice": 2000,
            "locationId": None,
            "locationAddress": None,
            "locationImageUrl": None,
        },
        # 문화
        {
            "couponLocation": COUPON_LOCATION_TITLE,
            "couponPrice": 1000,
            "locationId": COUPON_LOCATION_ID,
            "locationAddress": COUPON_LOCATION_ADDRESS,
            "locationImageUrl": fake_kto[106],
        },
        # 보물찾기 (같은 사용처지만 다른 미션이라 별개 항목이다)
        {
            "couponLocation": COUPON_LOCATION_TITLE,
            "couponPrice": 3000,
            "locationId": COUPON_LOCATION_ID,
            "locationAddress": COUPON_LOCATION_ADDRESS,
            "locationImageUrl": fake_kto[106],
        },
    ]


def test_같은_미션을_여러_번_해도_쿠폰은_한_번만_넣는다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_culture_progress(db_session, progress_id=1)
    _add_culture_progress(db_session, progress_id=2)
    db_session.commit()

    assert len(_get(client)["receivedCoupons"]) == 1


def test_받지_않은_쿠폰은_넣지_않는다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_culture_progress(db_session, progress_id=1, coupon_granted=False)
    db_session.commit()

    assert _get(client)["receivedCoupons"] == []


def test_다른_사용자가_받은_쿠폰은_넣지_않는다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_culture_progress(db_session, progress_id=1, user_id=OTHER_USER_ID)
    db_session.commit()

    assert _get(client)["receivedCoupons"] == []


@pytest.mark.parametrize(
    ("participant_status", "participant_deleted_at", "progress_deleted_at"),
    [
        pytest.param(ParticipantStatus.PENDING, None, None, id="수락되지_않은_참가"),
        pytest.param(
            ParticipantStatus.ACCEPTED, datetime(2026, 8, 26, 9, 0, 0), None, id="삭제된_참가"
        ),
        pytest.param(
            ParticipantStatus.ACCEPTED, None, datetime(2026, 8, 26, 9, 0, 0), id="삭제된_방"
        ),
    ],
)
def test_협동_미션의_제외_대상은_쿠폰_수령으로_보지_않는다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
    participant_status: ParticipantStatus,
    participant_deleted_at: datetime | None,
    progress_deleted_at: datetime | None,
) -> None:
    _add_cooperative_progress(
        db_session,
        progress_id=1,
        participant_id=1,
        participant_status=participant_status,
        participant_deleted_at=participant_deleted_at,
        progress_deleted_at=progress_deleted_at,
    )
    db_session.commit()

    assert _get(client)["receivedCoupons"] == []


def test_쿠폰_사용처와_이름이_같은_장소가_여러_개면_id가_작은_장소를_쓴다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_culture_progress(db_session, progress_id=1)
    db_session.commit()

    coupon = _get(client)["receivedCoupons"][0]

    assert coupon["locationId"] == COUPON_LOCATION_ID
    assert coupon["locationAddress"] == COUPON_LOCATION_ADDRESS


def test_장소는_찾았지만_이미지가_없으면_이미지만_null이다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    # 쿠폰 장소의 content id 를 이미지가 없는 값으로 바꾼다.
    coupon_location = db_session.get(Location, COUPON_LOCATION_ID)
    assert coupon_location is not None
    coupon_location.content_id = 999
    _add_culture_progress(db_session, progress_id=1)
    db_session.commit()

    coupon = _get(client)["receivedCoupons"][0]

    assert coupon["locationId"] == COUPON_LOCATION_ID
    assert coupon["locationAddress"] == COUPON_LOCATION_ADDRESS
    assert coupon["locationImageUrl"] is None


def test_받은_쿠폰이_없으면_빈_배열이다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    assert _get(client)["receivedCoupons"] == []


# ---------------------------------------------------------------------
# N+1 / 읽기 전용
# ---------------------------------------------------------------------


def test_추천과_쿠폰이_늘어도_쿼리_수가_늘지_않는다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
    executed_queries: list[str],
) -> None:
    """미션이나 쿠폰마다 보상 이력·장소를 다시 조회하면 여기서 걸린다."""
    _add_culture_progress(db_session, progress_id=1)
    db_session.commit()

    executed_queries.clear()
    _get(client)
    before = len(executed_queries)

    _add_cooperative_progress(db_session, progress_id=2, participant_id=1)
    _add_progress(
        db_session,
        progress_id=3,
        treasure_mission_id=NEAR_MISSION_ID,
        found_item_idx=[1, 2, 3],
        coupon_granted=True,
        point_granted=True,
    )
    db_session.commit()

    executed_queries.clear()
    body = _get(client)

    assert len(body["receivedCoupons"]) == 3
    assert len(body["nearbyTreasureMissions"]) == 3
    assert len(executed_queries) == before


def test_조회해도_DB_상태가_바뀌지_않는다(
    client: TestClient,
    db_session: Session,
    completed_progress: None,
    fake_kto: dict[int, str],
) -> None:
    _add_culture_progress(db_session, progress_id=1)
    db_session.commit()

    _get(client)

    db_session.expire_all()
    progress = db_session.get(TreasureMissionProgress, 1)
    assert progress is not None
    assert progress.mission_status == MissionStatus.COMPLETED.value
    assert progress.ar_character_reward_granted is False
    assert progress.current_found_item_idx == [1, 2, 3]

    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    assert user.point == 0

    culture = db_session.get(CultureMissionProgress, 1)
    assert culture is not None
    assert culture.coupon_reward_granted is True

    assert len(list(db_session.scalars(select(TreasureMissionProgress)).all())) == 1


# ---------------------------------------------------------------------
# 404 TREASURE_MISSION_NOT_FOUND
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "mission_type",
    [pytest.param("CULTURE", id="문화"), pytest.param("COOPERATIVE", id="협동")],
)
def test_missionType이_TREASURE가_아니면_404다(
    client: TestClient,
    completed_progress: None,
    fake_kto: dict[int, str],
    mission_type: str,
) -> None:
    response = client.get(
        _endpoint(mission_type, CULTURE_MISSION_ID),
        params=_params(),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_MISSION_NOT_FOUND"}


def test_없는_보물찾기_미션이면_404다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    response = client.get(
        _endpoint("TREASURE", 999), params=_params(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_MISSION_NOT_FOUND"}


def test_완료_진행도가_없으면_404다(
    client: TestClient,
    db_session: Session,
    completion_data: None,
    fake_kto: dict[int, str],
) -> None:
    # 진행 중인 기록만 있다.
    _add_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.IN_PROGRESS,
        found_item_idx=[1, 2, 3],
        completed_at=None,
    )
    db_session.commit()

    response = client.get(
        _endpoint(), params=_params(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "TREASURE_MISSION_NOT_FOUND"}


def test_다른_사용자의_완료_진행도는_인정하지_않는다(
    client: TestClient,
    db_session: Session,
    completion_data: None,
    fake_kto: dict[int, str],
) -> None:
    _add_progress(
        db_session, progress_id=1, user_id=OTHER_USER_ID, found_item_idx=[1, 2, 3]
    )
    db_session.commit()

    response = client.get(
        _endpoint(), params=_params(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------
# 409 TREASURE_ITEMS_REMAINING
# ---------------------------------------------------------------------


def test_찾지_않은_보물이_남아_있으면_409다(
    client: TestClient,
    db_session: Session,
    completion_data: None,
    fake_kto: dict[int, str],
) -> None:
    _add_progress(db_session, progress_id=1, found_item_idx=[1, 2])
    db_session.commit()

    response = client.get(
        _endpoint(), params=_params(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 409
    assert response.json() == {"code": "TREASURE_ITEMS_REMAINING"}


def test_중복된_index는_다른_보물을_대신하지_못한다(
    client: TestClient,
    db_session: Session,
    completion_data: None,
    fake_kto: dict[int, str],
) -> None:
    # 개수는 3개지만 실제로 찾은 보물은 1, 2번뿐이다.
    _add_progress(db_session, progress_id=1, found_item_idx=[1, 2, 2])
    db_session.commit()

    response = client.get(
        _endpoint(), params=_params(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 409
    assert response.json() == {"code": "TREASURE_ITEMS_REMAINING"}


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST / 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"latitude": 91}, id="위도_범위_초과"),
        pytest.param({"longitude": -181}, id="경도_범위_미만"),
        pytest.param({"latitude": "north"}, id="숫자가_아닌_좌표"),
    ],
)
def test_좌표가_유효하지_않으면_400이다(
    client: TestClient,
    completed_progress: None,
    fake_kto: dict[int, str],
    overrides: dict[str, object],
) -> None:
    response = client.get(
        _endpoint(),
        params=_params(**overrides),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_좌표가_없으면_400이다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    response = client.get(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_어떤_사용자의_토큰도_아니면_401을_반환한다(
    client: TestClient, completed_progress: None, fake_kto: dict[int, str]
) -> None:
    response = client.get(_endpoint(), params=_params(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
