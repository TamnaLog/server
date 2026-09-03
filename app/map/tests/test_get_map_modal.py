"""GET /api/v1/map/modals - 지도 모달 조회 테스트.

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
from app.map.models import Location, VisitedLocation
from app.map.service import LOCATION_MODAL_GUESTBOOK_LIMIT
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.models import (
    ArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/map/modals"

MISSION_ID = 1
MISSION_TITLE = "현애원의 숨은 보물 찾기"

LOCATION_ID = 39
LOCATION_TITLE = "현애원"
LOCATION_CATEGORY = "관광지"
LOCATION_LATITUDE = 33.4582
LOCATION_LONGITUDE = 126.9331

OTHER_LOCATION_ID = 40

TREASURE_MISSION_ID = 12
COOPERATIVE_MISSION_ID = 21
COOPERATIVE_COMMON_MISSION_ID = 2
COOPERATIVE_MISSION_TITLE = "현애원 협동 미션"

AR_CHARACTER_ID = 3
AR_CHARACTER_NAME = "점박이 물범"
AR_CHARACTER_IMAGE_URL = "https://example.com/ar-characters/3.png"
COUPON_LOCATION = "현애원 카페"
COUPON_PRICE = 3000
REWARD_POINT = 100

# 세 종류 보상이 모두 설정된 미션.
REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": REWARD_POINT,
    "coupon_location": COUPON_LOCATION,
    "coupon_price": COUPON_PRICE,
}

ROAD_GUESTBOOK_ID = 100
ROAD_GUESTBOOK_ALIAS = "성산 바다 앞"
ROAD_LATITUDE = 33.4600
ROAD_LONGITUDE = 126.9400

OTHER_USER_ID = 2
NICKNAME = "여행자종화"
OTHER_NICKNAME = "제주도종화"

USER_LATITUDE = 33.4524
USER_LONGITUDE = 126.9248


def _params(**overrides: object) -> dict[str, object]:
    return {
        "targetType": "LOCATION",
        "targetId": LOCATION_ID,
        "userLatitude": USER_LATITUDE,
        "userLongitude": USER_LONGITUDE,
        **overrides,
    }


def _road_params(**overrides: object) -> dict[str, object]:
    return _params(
        **{"targetType": "ROAD_GUESTBOOK", "targetId": ROAD_GUESTBOOK_ID, **overrides}
    )


@pytest.fixture
def modal_data(db_session: Session) -> None:
    """장소 2곳 + 사용자 2명 + 미션 1개. 방명록은 테스트마다 직접 붙인다."""
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname=NICKNAME,
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname=OTHER_NICKNAME,
                point=0,
            ),
            Mission(
                id=MISSION_ID,
                mission_type="TREASURE",
                mission_title=MISSION_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "시작", "description": "설명"}],
            ),
            Location(
                id=LOCATION_ID,
                content_id=126273,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 표선면",
                location_category=LOCATION_CATEGORY,
                radius=300,
                mx=LOCATION_LONGITUDE,
                my=LOCATION_LATITUDE,
            ),
            Location(
                id=OTHER_LOCATION_ID,
                content_id=999,
                location_title="다른 장소",
                location_address="제주특별자치도 제주시",
                location_category="카페",
                radius=200,
                mx=126.95,
                my=33.47,
            ),
        ]
    )
    db_session.commit()


def _add_guestbook(
    db_session: Session,
    *,
    guestbook_id: int,
    location_id: int = LOCATION_ID,
    user_id: int = CURRENT_USER_ID,
    mission_id: int | None = None,
    visited_at: date = date(2026, 8, 25),
    content_img_url: list[str] | None = None,
    content_writing: str | None = None,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        Guestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=location_id,
            mission_id=mission_id,
            visited_at=visited_at,
            content_img_url=content_img_url,
            content_writing=content_writing,
            saved_at=datetime(2026, 8, 25, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_road_guestbook(
    db_session: Session,
    *,
    guestbook_id: int = ROAD_GUESTBOOK_ID,
    user_id: int = CURRENT_USER_ID,
    visited_at: date = date(2026, 8, 25),
    content_img_url: list[str] | None = None,
    content_writing: str | None = None,
    content_audio_url: list[str] | None = None,
    content_weather: str | None = None,
    content_color_code: str | None = None,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        RoadGuestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=None,
            location_alias=ROAD_GUESTBOOK_ALIAS,
            visited_at=visited_at,
            content_img_url=content_img_url,
            content_writing=content_writing,
            content_audio_url=content_audio_url,
            content_weather=content_weather,
            content_color_code=content_color_code,
            mx=ROAD_LONGITUDE,
            my=ROAD_LATITUDE,
            saved_at=datetime(2026, 8, 25, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_visited_location(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    location_id: int = LOCATION_ID,
    visited_at: datetime = datetime(2026, 8, 25, 10, 0, 0),
) -> None:
    db_session.add(
        VisitedLocation(
            user_id=user_id, location_id=location_id, visited_at=visited_at
        )
    )
    db_session.commit()


def _assign_ar_character(
    db_session: Session,
    *,
    user_id: int,
    ar_character_id: int | None = AR_CHARACTER_ID,
) -> None:
    """방명록 작성자에게 AR 캐릭터를 배정한다. (`USER.ar_character_id`)"""
    _add_ar_character(db_session)
    user = db_session.get(User, user_id)
    assert user is not None
    user.ar_character_id = ar_character_id
    db_session.commit()


def _get(client: TestClient, params: dict[str, object]) -> dict:
    response = client.get(ENDPOINT, params=params)
    assert response.status_code == 200
    return response.json()


def _expected_distance(latitude: float, longitude: float) -> int:
    return distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, latitude, longitude
    )


# ---------------------------------------------------------------------
# targetType = LOCATION
# ---------------------------------------------------------------------


def test_장소_모달을_조회하면_기본_정보와_방명록을_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_guestbook(
        db_session,
        guestbook_id=300,
        mission_id=MISSION_ID,
        visited_at=date(2026, 8, 25),
        content_img_url=["https://example.com/guestbooks/300-1.jpg"],
        content_writing="현애원 산책하기 좋았어요.",
    )
    _add_guestbook(
        db_session,
        guestbook_id=302,
        user_id=OTHER_USER_ID,
        visited_at=date(2026, 8, 23),
    )

    expected_distance = _expected_distance(LOCATION_LATITUDE, LOCATION_LONGITUDE)
    assert _get(client, _params()) == {
        "id": LOCATION_ID,
        "locationTitle": LOCATION_TITLE,
        "locationCategory": LOCATION_CATEGORY,
        "distanceMeter": expected_distance,
        "durationMinutes": distance.calculate_duration_minutes(expected_distance),
        "isVisited": False,
        "mission": None,
        "guestbooksCount": 2,
        "guestbooks": [
            {
                "id": 300,
                "representativeImageUrl": "https://example.com/guestbooks/300-1.jpg",
                "userId": CURRENT_USER_ID,
                "userNickname": NICKNAME,
                "characterImgUrl": None,
                "missionTitle": MISSION_TITLE,
                "visitedAt": "2026-08-25",
                "contentWriting": "현애원 산책하기 좋았어요.",
            },
            {
                "id": 302,
                "representativeImageUrl": None,
                "userId": OTHER_USER_ID,
                "userNickname": OTHER_NICKNAME,
                "characterImgUrl": None,
                "missionTitle": None,
                "visitedAt": "2026-08-23",
                "contentWriting": None,
            },
        ],
    }


def test_방명록이_없어도_200과_빈_배열을_반환한다(
    client: TestClient, modal_data: None
) -> None:
    body = _get(client, _params())

    assert body["guestbooksCount"] == 0
    assert body["guestbooks"] == []


def test_방명록은_방문일_최신순으로_최대_3개만_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    for guestbook_id, day in ((1, 20), (2, 24), (3, 22), (4, 25), (5, 21)):
        _add_guestbook(
            db_session, guestbook_id=guestbook_id, visited_at=date(2026, 8, day)
        )

    body = _get(client, _params())

    # 전체 개수는 목록 길이가 아니라 5 다.
    assert body["guestbooksCount"] == 5
    assert len(body["guestbooks"]) == LOCATION_MODAL_GUESTBOOK_LIMIT
    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [4, 2, 3]


def test_방문일이_같으면_id가_큰_방명록이_먼저다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    same_day = date(2026, 8, 25)
    for guestbook_id in (10, 12, 11):
        _add_guestbook(db_session, guestbook_id=guestbook_id, visited_at=same_day)

    body = _get(client, _params())

    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [12, 11, 10]


def test_최신순은_저장_시각이_아니라_방문일_기준이다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    # 나중에 저장했지만 방문일은 더 과거인 방명록
    db_session.add(
        Guestbook(
            id=1,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=date(2026, 8, 20),
            saved_at=datetime(2026, 8, 30, 12, 0, 0),
        )
    )
    db_session.add(
        Guestbook(
            id=2,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=date(2026, 8, 25),
            saved_at=datetime(2026, 8, 26, 12, 0, 0),
        )
    )
    db_session.commit()

    body = _get(client, _params())

    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [2, 1]


def test_삭제된_방명록은_개수와_목록에서_모두_빠진다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1)
    _add_guestbook(
        db_session, guestbook_id=2, deleted_at=datetime(2026, 8, 26, 9, 0, 0)
    )

    body = _get(client, _params())

    assert body["guestbooksCount"] == 1
    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [1]


def test_다른_장소의_방명록은_섞이지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1, location_id=LOCATION_ID)
    _add_guestbook(db_session, guestbook_id=2, location_id=OTHER_LOCATION_ID)

    body = _get(client, _params())

    assert body["guestbooksCount"] == 1
    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [1]


@pytest.mark.parametrize(
    "content_img_url",
    [
        pytest.param(None, id="이미지_없음"),
        pytest.param([], id="빈_배열"),
    ],
)
def test_방명록_이미지가_없으면_대표_이미지는_null이다(
    client: TestClient,
    db_session: Session,
    modal_data: None,
    content_img_url: list[str] | None,
) -> None:
    _add_guestbook(db_session, guestbook_id=1, content_img_url=content_img_url)

    body = _get(client, _params())

    assert body["guestbooks"][0]["representativeImageUrl"] is None


def test_방명록_이미지는_첫_번째_URL을_그대로_쓴다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    first = "https://example.com/guestbooks/1-1.jpg"
    _add_guestbook(
        db_session,
        guestbook_id=1,
        content_img_url=[first, "https://example.com/guestbooks/1-2.jpg"],
    )

    body = _get(client, _params())

    assert body["guestbooks"][0]["representativeImageUrl"] == first


def test_방명록마다_작성자_id와_닉네임을_함께_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1, user_id=OTHER_USER_ID)

    guestbook = _get(client, _params())["guestbooks"][0]

    assert guestbook["userId"] == OTHER_USER_ID
    assert guestbook["userNickname"] == OTHER_NICKNAME


def test_방명록마다_작성자의_AR_캐릭터_이미지를_함께_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _assign_ar_character(db_session, user_id=OTHER_USER_ID)
    _add_guestbook(db_session, guestbook_id=1, user_id=OTHER_USER_ID)

    body = _get(client, _params())

    assert body["guestbooks"][0]["characterImgUrl"] == AR_CHARACTER_IMAGE_URL


def test_작성자에게_배정된_AR_캐릭터가_없으면_characterImgUrl은_null이다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    # modal_data 의 사용자는 AR 캐릭터를 배정받지 않은 상태다.
    _add_guestbook(db_session, guestbook_id=1)

    body = _get(client, _params())

    assert body["guestbooks"][0]["characterImgUrl"] is None


def test_방명록마다_작성자의_AR_캐릭터를_각각_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _assign_ar_character(db_session, user_id=CURRENT_USER_ID)
    _add_guestbook(db_session, guestbook_id=1, visited_at=date(2026, 8, 25))
    _add_guestbook(
        db_session, guestbook_id=2, user_id=OTHER_USER_ID, visited_at=date(2026, 8, 23)
    )

    body = _get(client, _params())

    # 작성자가 다르면 배정된 캐릭터도 각각 따라간다.
    assert [guestbook["characterImgUrl"] for guestbook in body["guestbooks"]] == [
        AR_CHARACTER_IMAGE_URL,
        None,
    ]


def test_방문_기록이_있으면_isVisited가_true다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_visited_location(db_session)

    assert _get(client, _params())["isVisited"] is True


def test_방문_기록이_여러_건이어도_isVisited는_true다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_visited_location(db_session, visited_at=datetime(2026, 8, 25, 10, 0, 0))
    _add_visited_location(db_session, visited_at=datetime(2026, 8, 27, 9, 0, 0))

    assert _get(client, _params())["isVisited"] is True


def test_방문_기록이_없으면_isVisited가_false다(
    client: TestClient, modal_data: None
) -> None:
    assert _get(client, _params())["isVisited"] is False


def test_다른_사용자의_방문_기록은_isVisited에_반영되지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_visited_location(db_session, user_id=OTHER_USER_ID)

    assert _get(client, _params())["isVisited"] is False


def test_다른_장소의_방문_기록은_isVisited에_반영되지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_visited_location(db_session, location_id=OTHER_LOCATION_ID)

    assert _get(client, _params())["isVisited"] is False


def test_방명록만_있고_방문_기록이_없으면_isVisited가_false다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    # 방명록 작성 여부는 isVisited 판정에 쓰지 않는다.
    _add_guestbook(db_session, guestbook_id=1)

    assert _get(client, _params())["isVisited"] is False


def test_장소_거리와_예상_시간은_공통_모듈_결과와_같다(
    client: TestClient, modal_data: None
) -> None:
    body = _get(client, _params())

    expected_distance = _expected_distance(LOCATION_LATITUDE, LOCATION_LONGITUDE)
    assert body["distanceMeter"] == expected_distance
    assert body["durationMinutes"] == distance.calculate_duration_minutes(
        expected_distance
    )


def test_사용자_좌표가_장소와_같으면_거리가_0이다(
    client: TestClient, modal_data: None
) -> None:
    body = _get(
        client,
        _params(userLatitude=LOCATION_LATITUDE, userLongitude=LOCATION_LONGITUDE),
    )

    assert body["distanceMeter"] == 0


# ---------------------------------------------------------------------
# 장소 미션
# ---------------------------------------------------------------------


def _add_ar_character(db_session: Session) -> None:
    """보상 캐릭터. 두 유형 미션을 함께 만드는 경우를 위해 한 번만 넣는다."""
    if db_session.get(ArCharacter, AR_CHARACTER_ID) is not None:
        return

    db_session.add(
        ArCharacter(
            id=AR_CHARACTER_ID,
            character_name=AR_CHARACTER_NAME,
            character_description="설명",
            character_story_title="이야기 제목",
            acquire_condition="미션 완료",
            character_img_url=AR_CHARACTER_IMAGE_URL,
            hashtags=["#물범"],
        )
    )
    db_session.commit()


def _add_treasure_mission(
    db_session: Session,
    *,
    location_id: int = LOCATION_ID,
    reward_detail: dict[str, object] | None = None,
) -> None:
    """장소에 보물찾기 미션을 붙인다. (fixture 의 공통 미션이 TREASURE 유형이다)"""
    _add_ar_character(db_session)
    db_session.add(
        TreasureMission(
            id=TREASURE_MISSION_ID,
            mission_id=MISSION_ID,
            location_id=location_id,
            item_total_count=3,
            reward_detail=REWARD_DETAIL if reward_detail is None else reward_detail,
        )
    )
    db_session.commit()


def _add_treasure_progress(
    db_session: Session,
    *,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.IN_PROGRESS,
    ar_character_granted: bool = False,
    point_granted: bool = False,
    coupon_granted: bool = False,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=TREASURE_MISSION_ID,
            user_id=user_id,
            item_detail=[
                {"index": 1, "mx": LOCATION_LONGITUDE, "my": LOCATION_LATITUDE}
            ],
            current_found_item_idx=[],
            current_step=1,
            mission_status=mission_status.value,
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            coupon_reward_granted=coupon_granted,
        )
    )
    db_session.commit()


def _add_cooperative_mission(
    db_session: Session,
    *,
    location_id: int = LOCATION_ID,
    reward_detail: dict[str, object] | None = None,
) -> None:
    """장소에 협동 미션을 붙인다. 공통 미션도 COOPERATIVE 유형으로 함께 만든다."""
    _add_ar_character(db_session)
    db_session.add_all(
        [
            Mission(
                id=COOPERATIVE_COMMON_MISSION_ID,
                mission_type="COOPERATIVE",
                mission_title=COOPERATIVE_MISSION_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "시작", "description": "설명"}],
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_COMMON_MISSION_ID,
                location_id=location_id,
                reward_detail=REWARD_DETAIL if reward_detail is None else reward_detail,
            ),
        ]
    )
    db_session.commit()


def _add_cooperative_progress(
    db_session: Session,
    *,
    progress_id: int,
    mission_status: MissionStatus = MissionStatus.IN_PROGRESS,
    ar_character_granted: bool = False,
    point_granted: bool = False,
    coupon_granted: bool = False,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        CooperativeMissionProgress(
            id=progress_id,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=1,
            mission_status=mission_status.value,
            team_token=f"team-token-{progress_id}",
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            coupon_reward_granted=coupon_granted,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_participant(
    db_session: Session,
    *,
    participant_id: int,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
    participant_status: ParticipantStatus = ParticipantStatus.ACCEPTED,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        CooperativeMissionParticipant(
            id=participant_id,
            cooperative_mission_progress_id=progress_id,
            user_id=user_id,
            participant_status=participant_status.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 25, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _mission(client: TestClient) -> dict | None:
    return _get(client, _params())["mission"]


def test_미션이_없는_장소는_mission이_null이다(
    client: TestClient, modal_data: None
) -> None:
    assert _mission(client) is None


def test_보물찾기_미션이_있으면_세부_미션_id와_TREASURE를_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)

    # 배열이 아니라 단일 객체이고, missionId 는 공통 MISSION.id 가 아니라 세부 미션 id 다.
    assert _mission(client) == {
        "missionId": TREASURE_MISSION_ID,
        "missionType": "TREASURE",
        "missionTitle": MISSION_TITLE,
        "isCompleted": False,
        "rewardDetail": {
            "arCharacter": {
                "id": AR_CHARACTER_ID,
                "name": AR_CHARACTER_NAME,
                "imageUrl": AR_CHARACTER_IMAGE_URL,
                "isReceived": False,
            },
            "point": {"amount": REWARD_POINT, "isReceived": False},
            "coupon": {
                "couponLocation": COUPON_LOCATION,
                "couponPrice": COUPON_PRICE,
                "isReceived": False,
            },
        },
    }


def test_협동_미션이_있으면_세부_미션_id와_COOPERATIVE를_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_cooperative_mission(db_session)

    mission = _mission(client)

    assert mission is not None
    assert mission["missionId"] == COOPERATIVE_MISSION_ID
    assert mission["missionType"] == "COOPERATIVE"
    assert mission["missionTitle"] == COOPERATIVE_MISSION_TITLE
    assert mission["isCompleted"] is False


def test_다른_장소의_미션은_섞이지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session, location_id=OTHER_LOCATION_ID)

    assert _mission(client) is None


def test_미션에_설정되지_않은_보상_항목만_null이다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session, reward_detail={"point": REWARD_POINT})

    mission = _mission(client)

    assert mission is not None
    assert mission["rewardDetail"] == {
        "arCharacter": None,
        "point": {"amount": REWARD_POINT, "isReceived": False},
        "coupon": None,
    }


# ---------------------------------------------------------------------
# 장소 미션 - 완료 여부
# ---------------------------------------------------------------------


def test_진행_중_이력만_있으면_isCompleted가_false다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, progress_id=1)

    mission = _mission(client)

    assert mission is not None
    assert mission["isCompleted"] is False


def test_완료_이력이_하나라도_있으면_isCompleted가_true다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, progress_id=1)
    _add_treasure_progress(
        db_session, progress_id=2, mission_status=MissionStatus.COMPLETED
    )
    # 가장 최근 진행도 하나가 아니라 이력 전체를 본다.
    _add_treasure_progress(db_session, progress_id=3)

    mission = _mission(client)

    assert mission is not None
    assert mission["isCompleted"] is True


def test_다른_사용자의_완료_이력은_반영되지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(
        db_session,
        progress_id=1,
        user_id=OTHER_USER_ID,
        mission_status=MissionStatus.COMPLETED,
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
    )

    mission = _mission(client)

    assert mission is not None
    assert mission["isCompleted"] is False
    assert mission["rewardDetail"]["arCharacter"]["isReceived"] is False
    assert mission["rewardDetail"]["point"]["isReceived"] is False
    assert mission["rewardDetail"]["coupon"]["isReceived"] is False


def test_완료했어도_보상을_안_받았으면_isReceived는_false다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(
        db_session, progress_id=1, mission_status=MissionStatus.COMPLETED
    )

    mission = _mission(client)

    # isCompleted 와 보상별 isReceived 는 서로 독립적이다.
    assert mission is not None
    assert mission["isCompleted"] is True
    assert mission["rewardDetail"]["arCharacter"]["isReceived"] is False


# ---------------------------------------------------------------------
# 장소 미션 - 보상 수령 여부
# ---------------------------------------------------------------------


def test_진행도_이력이_없으면_보상_수령_여부가_모두_false다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)

    mission = _mission(client)

    assert mission is not None
    reward_detail = mission["rewardDetail"]
    assert [reward["isReceived"] for reward in reward_detail.values()] == [
        False,
        False,
        False,
    ]


def test_서로_다른_진행도에서_지급된_보상은_각각_true가_된다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, progress_id=1, ar_character_granted=True)
    _add_treasure_progress(db_session, progress_id=2, coupon_granted=True)

    mission = _mission(client)

    # 종류별 OR 이라 포인트만 아직 안 받은 상태로 남는다.
    assert mission is not None
    assert mission["rewardDetail"]["arCharacter"]["isReceived"] is True
    assert mission["rewardDetail"]["point"]["isReceived"] is False
    assert mission["rewardDetail"]["coupon"]["isReceived"] is True


def test_이미_수령한_보상도_상세_정보를_그대로_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(
        db_session,
        progress_id=1,
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
    )

    mission = _mission(client)

    # 수령한 보상을 null 로 바꾸거나 빼지 않는다. (remainingReward 와 다른 점)
    assert mission is not None
    assert mission["rewardDetail"] == {
        "arCharacter": {
            "id": AR_CHARACTER_ID,
            "name": AR_CHARACTER_NAME,
            "imageUrl": AR_CHARACTER_IMAGE_URL,
            "isReceived": True,
        },
        "point": {"amount": REWARD_POINT, "isReceived": True},
        "coupon": {
            "couponLocation": COUPON_LOCATION,
            "couponPrice": COUPON_PRICE,
            "isReceived": True,
        },
    }


# ---------------------------------------------------------------------
# 장소 미션 - 협동 미션 이력 범위
# ---------------------------------------------------------------------


def test_협동_미션은_수락한_참가자의_이력을_반영한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_cooperative_mission(db_session)
    _add_cooperative_progress(
        db_session,
        progress_id=1,
        mission_status=MissionStatus.COMPLETED,
        point_granted=True,
    )
    _add_participant(db_session, participant_id=1, progress_id=1)

    mission = _mission(client)

    assert mission is not None
    assert mission["isCompleted"] is True
    assert mission["rewardDetail"]["point"]["isReceived"] is True


@pytest.mark.parametrize(
    ("participant_status", "participant_deleted_at", "progress_deleted_at"),
    [
        pytest.param(
            ParticipantStatus.ACCEPTED,
            datetime(2026, 8, 26, 12, 0, 0),
            None,
            id="deleted-participant",
        ),
        pytest.param(ParticipantStatus.PENDING, None, None, id="pending-participant"),
        pytest.param(
            ParticipantStatus.ACCEPTED,
            None,
            datetime(2026, 8, 26, 12, 0, 0),
            id="deleted-progress",
        ),
    ],
)
def test_협동_미션의_제외_대상_이력은_반영하지_않는다(
    client: TestClient,
    db_session: Session,
    modal_data: None,
    participant_status: ParticipantStatus,
    participant_deleted_at: datetime | None,
    progress_deleted_at: datetime | None,
) -> None:
    _add_cooperative_mission(db_session)
    _add_cooperative_progress(
        db_session,
        progress_id=1,
        mission_status=MissionStatus.COMPLETED,
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
        deleted_at=progress_deleted_at,
    )
    _add_participant(
        db_session,
        participant_id=1,
        progress_id=1,
        participant_status=participant_status,
        deleted_at=participant_deleted_at,
    )

    mission = _mission(client)

    assert mission is not None
    assert mission["isCompleted"] is False
    assert mission["rewardDetail"]["point"]["isReceived"] is False


# ---------------------------------------------------------------------
# 장소 미션 - 조회 전용
# ---------------------------------------------------------------------


def test_모달_조회는_보상_지급_여부를_바꾸지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, progress_id=1, point_granted=True)

    _get(client, _params())

    db_session.expire_all()
    progress = db_session.get(TreasureMissionProgress, 1)
    user = db_session.get(User, CURRENT_USER_ID)
    assert progress is not None
    assert user is not None
    # 조회만 하고 보상을 지급하거나 지급 여부를 바꾸지 않는다.
    assert progress.ar_character_reward_granted is False
    assert progress.point_reward_granted is True
    assert progress.coupon_reward_granted is False
    assert progress.mission_status == MissionStatus.IN_PROGRESS.value
    assert user.point == 0


# ---------------------------------------------------------------------
# targetType = ROAD_GUESTBOOK
# ---------------------------------------------------------------------


def test_길바닥_방명록_모달을_조회하면_상세_콘텐츠를_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    image_urls = [
        "https://example.com/road/100-1.jpg",
        "https://example.com/road/100-2.jpg",
    ]
    _add_road_guestbook(
        db_session,
        content_img_url=image_urls,
        content_writing="잠시 쉬어가기 좋았어요.",
        content_weather="SUNNY",
    )

    expected_distance = _expected_distance(ROAD_LATITUDE, ROAD_LONGITUDE)
    assert _get(client, _road_params()) == {
        "id": ROAD_GUESTBOOK_ID,
        "userNickname": NICKNAME,
        "locationAlias": ROAD_GUESTBOOK_ALIAS,
        "distanceMeter": expected_distance,
        "durationMinutes": distance.calculate_duration_minutes(expected_distance),
        "visitedAt": "2026-08-25",
        # 저장된 순서를 바꾸지 않는다.
        "contentImageUrls": image_urls,
        "contentWriting": "잠시 쉬어가기 좋았어요.",
        "contentAudioUrls": None,
        "contentWeather": "SUNNY",
        "contentColorCode": None,
    }


def test_길바닥_방명록_응답에는_isVisited를_넣지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    # 방문 여부는 장소 모달에만 있는 값이다.
    _add_road_guestbook(db_session)
    _add_visited_location(db_session)

    assert "isVisited" not in _get(client, _road_params())


def test_콘텐츠가_없으면_필드를_생략하지_않고_null로_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session)

    body = _get(client, _road_params())

    assert body.keys() >= {
        "contentImageUrls",
        "contentWriting",
        "contentAudioUrls",
        "contentWeather",
        "contentColorCode",
    }
    for field in (
        "contentImageUrls",
        "contentWriting",
        "contentAudioUrls",
        "contentWeather",
        "contentColorCode",
    ):
        assert body[field] is None


def test_빈_배열로_저장된_콘텐츠는_null로_정규화한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session, content_img_url=[], content_audio_url=[])

    body = _get(client, _road_params())

    assert body["contentImageUrls"] is None
    assert body["contentAudioUrls"] is None


def test_길바닥_방명록_거리와_예상_시간은_공통_모듈_결과와_같다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session)

    body = _get(client, _road_params())

    expected_distance = _expected_distance(ROAD_LATITUDE, ROAD_LONGITUDE)
    assert body["distanceMeter"] == expected_distance
    assert body["durationMinutes"] == distance.calculate_duration_minutes(
        expected_distance
    )


def test_작성일은_저장_시각이_아니라_방문일이다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session, visited_at=date(2026, 8, 20))

    assert _get(client, _road_params())["visitedAt"] == "2026-08-20"


# ---------------------------------------------------------------------
# 404 MAP_MODAL_TARGET_NOT_FOUND
# ---------------------------------------------------------------------


def test_장소가_없으면_404로_응답한다(client: TestClient, modal_data: None) -> None:
    response = client.get(ENDPOINT, params=_params(targetId=999))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_길바닥_방명록이_없으면_404로_응답한다(
    client: TestClient, modal_data: None
) -> None:
    response = client.get(ENDPOINT, params=_road_params(targetId=999))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_삭제된_길바닥_방명록이면_404로_응답한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session, deleted_at=datetime(2026, 8, 26, 9, 0, 0))

    response = client.get(ENDPOINT, params=_road_params())

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_다른_테이블에_같은_id가_있어도_targetType을_따른다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    # 장소 39 는 있지만 길바닥 방명록 39 는 없다.
    response = client.get(ENDPOINT, params=_road_params(targetId=LOCATION_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_길바닥_방명록_id로_장소를_조회하면_404다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session)

    response = client.get(ENDPOINT, params=_params(targetId=ROAD_GUESTBOOK_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("targetType", id="targetType_누락"),
        pytest.param("targetId", id="targetId_누락"),
        pytest.param("userLatitude", id="userLatitude_누락"),
        pytest.param("userLongitude", id="userLongitude_누락"),
    ],
)
def test_필수_Query가_없으면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, modal_data: None, field: str
) -> None:
    params = _params()
    del params[field]

    response = client.get(ENDPOINT, params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("targetType", "MISSION", id="지원하지_않는_targetType"),
        pytest.param("targetType", "location", id="소문자_targetType"),
        pytest.param("targetId", "abc", id="targetId가_정수가_아님"),
        pytest.param("targetId", 0, id="targetId가_0"),
        pytest.param("targetId", -1, id="targetId가_음수"),
        pytest.param("userLatitude", "abc", id="위도가_숫자가_아님"),
        pytest.param("userLatitude", 91, id="위도_상한_초과"),
        pytest.param("userLatitude", -91, id="위도_하한_미만"),
        pytest.param("userLongitude", 181, id="경도_상한_초과"),
        pytest.param("userLongitude", -181, id="경도_하한_미만"),
    ],
)
def test_Query_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, modal_data: None, field: str, value: object
) -> None:
    response = client.get(ENDPOINT, params=_params(**{field: value}))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_인증_헤더가_없으면_401로_응답한다(client: TestClient, modal_data: None) -> None:
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT, params=_params())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, modal_data: None
) -> None:
    response = client.get(ENDPOINT, params=_params(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_문서에_401을_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"][ENDPOINT]["get"]["responses"]

    assert sorted(responses) == ["200", "400", "401", "404", "500"]
