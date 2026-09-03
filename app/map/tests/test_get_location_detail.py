"""GET /api/v1/map/locations/{locationId} - 지도 장소 상세 조회 테스트.

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
from app.guestbook.models import Guestbook
from app.map import service
from app.map.mission_recommender import RECOMMEND_COUNT
from app.map.models import Location, VisitedLocation
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.models import (
    ArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


LOCATION_ID = 39
LOCATION_TITLE = "성산일출봉"
LOCATION_CATEGORY = "자연"
LOCATION_ADDRESS = "제주특별자치도 서귀포시 성산읍 일출로 284-12"
LOCATION_CONTENT_ID = 126273
LOCATION_LATITUDE = 33.4582
LOCATION_LONGITUDE = 126.9331

# 미션이 없는 장소
PLAIN_LOCATION_ID = 40
PLAIN_CONTENT_ID = 999

USER_LATITUDE = 33.4524
USER_LONGITUDE = 126.9248

OVERVIEW = "제주 동쪽 바다 위로 솟아오른 응회구입니다."
DETAIL_IMAGE_URLS = [
    "https://example.com/locations/39/detail-1.jpg",
    "https://example.com/locations/39/detail-2.jpg",
]
REPRESENTATIVE_IMAGE_URL = "https://example.com/locations/39/firstimage.jpg"

OTHER_USER_ID = 2
NICKNAME = "활발한 귤돌이"
OTHER_NICKNAME = "씩씩한 고래"

# 공통 MISSION.id
TREASURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TITLE = "오구포구 보물찾기"
COOPERATIVE_TITLE = "함께 키우는 귤나무"
TREASURE_DESCRIPTION = "성산일출봉 곳곳에 숨겨진 보물을 찾아보세요."
COOPERATIVE_DESCRIPTION = "역할을 나누어 제주 귤나무를 함께 완성하는 미션입니다."

# 세부 미션 id
TREASURE_MISSION_ID = 5
COOPERATIVE_MISSION_ID = 3

AR_CHARACTER_ID = 3
AR_CHARACTER_NAME = "점박이 물범"
AR_CHARACTER_IMAGE_URL = "https://example.com/ar-characters/3.png"
COUPON_LOCATION = "성산 카페"
COUPON_PRICE = 3000
REWARD_POINT = 100

# 세 종류 보상이 모두 설정된 미션 보상
REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": REWARD_POINT,
    "coupon_location": COUPON_LOCATION,
    "coupon_price": COUPON_PRICE,
}

NOT_RECEIVED_REWARD_DETAIL = {
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
}


def _endpoint(location_id: object = LOCATION_ID) -> str:
    return f"/api/v1/map/locations/{location_id}"


def _params(**overrides: object) -> dict[str, object]:
    return {
        "userLatitude": USER_LATITUDE,
        "userLongitude": USER_LONGITUDE,
        **overrides,
    }


@pytest.fixture(autouse=True)
def stub_overview(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """TourAPI 상세 설명 조회를 막고 호출된 content_id 를 기록한다."""
    called: list[int] = []

    def fake_get_location_overview(content_id: int) -> str | None:
        called.append(content_id)
        return OVERVIEW if content_id == LOCATION_CONTENT_ID else None

    monkeypatch.setattr(service, "get_location_overview", fake_get_location_overview)
    return called


@pytest.fixture(autouse=True)
def stub_detail_images(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    """TourAPI 상세 이미지 조회를 막고 (content_id, limit) 을 기록한다."""
    called: list[tuple[int, int]] = []

    def fake_get_location_detail_image_urls(
        content_id: int, limit: int = 5
    ) -> list[str] | None:
        called.append((content_id, limit))
        return list(DETAIL_IMAGE_URLS) if content_id == LOCATION_CONTENT_ID else None

    monkeypatch.setattr(
        service,
        "get_location_detail_image_urls",
        fake_get_location_detail_image_urls,
    )
    return called


@pytest.fixture(autouse=True)
def stub_representative_image(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """추천 미션 대표 이미지 조회를 막고 호출된 content_id 를 기록한다."""
    called: list[int] = []

    def fake_get_location_image_url(content_id: int) -> str | None:
        called.append(content_id)
        return REPRESENTATIVE_IMAGE_URL if content_id == LOCATION_CONTENT_ID else None

    monkeypatch.setattr(service, "get_location_image_url", fake_get_location_image_url)
    return called


@pytest.fixture
def detail_data(db_session: Session) -> None:
    """장소 2곳 + 사용자 2명 + 공통 미션 2개 + 보상 캐릭터. 세부 미션은 테스트마다 붙인다."""
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
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name=AR_CHARACTER_NAME,
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="미션 완료",
                character_img_url=AR_CHARACTER_IMAGE_URL,
                hashtags=["#물범"],
            ),
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title=TREASURE_TITLE,
                description=TREASURE_DESCRIPTION,
                step_detail=[{"step": 1, "step_title": "시작", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title=COOPERATIVE_TITLE,
                description=COOPERATIVE_DESCRIPTION,
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
            Location(
                id=LOCATION_ID,
                content_id=LOCATION_CONTENT_ID,
                location_title=LOCATION_TITLE,
                location_address=LOCATION_ADDRESS,
                location_category=LOCATION_CATEGORY,
                radius=300,
                mx=LOCATION_LONGITUDE,
                my=LOCATION_LATITUDE,
            ),
            Location(
                id=PLAIN_LOCATION_ID,
                content_id=PLAIN_CONTENT_ID,
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


def _add_treasure_mission(
    db_session: Session,
    *,
    mission_id: int = TREASURE_MISSION_ID,
    location_id: int = LOCATION_ID,
    reward_detail: dict[str, object] | None = None,
) -> None:
    db_session.add(
        TreasureMission(
            id=mission_id,
            mission_id=TREASURE_TYPE_ID,
            location_id=location_id,
            item_total_count=3,
            reward_detail=REWARD_DETAIL if reward_detail is None else reward_detail,
        )
    )
    db_session.commit()


def _add_cooperative_mission(
    db_session: Session,
    *,
    mission_id: int = COOPERATIVE_MISSION_ID,
    location_id: int = LOCATION_ID,
    reward_detail: dict[str, object] | None = None,
) -> None:
    db_session.add(
        CooperativeMission(
            id=mission_id,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=location_id,
            reward_detail=REWARD_DETAIL if reward_detail is None else reward_detail,
        )
    )
    db_session.commit()


def _add_treasure_progress(
    db_session: Session,
    *,
    progress_id: int | None = None,
    mission_id: int = TREASURE_MISSION_ID,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.COMPLETED,
    ar_character_granted: bool = False,
    point_granted: bool = False,
    coupon_granted: bool = False,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=mission_id,
            user_id=user_id,
            item_detail=[],
            current_found_item_idx=[],
            current_step=3,
            mission_status=mission_status.value,
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            coupon_reward_granted=coupon_granted,
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
    point_granted: bool = False,
) -> None:
    progress = CooperativeMissionProgress(
        cooperative_mission_id=COOPERATIVE_MISSION_ID,
        current_step=4,
        mission_status=mission_status.value,
        team_token=f"mock-team-token-{user_id}-{mission_status.value}",
        point_reward_granted=point_granted,
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


def _add_guestbook(
    db_session: Session,
    *,
    guestbook_id: int,
    location_id: int = LOCATION_ID,
    user_id: int = CURRENT_USER_ID,
    mission_id: int | None = None,
    visited_at: date = date(2026, 1, 15),
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
            saved_at=datetime(2026, 1, 15, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_visited_location(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    location_id: int = LOCATION_ID,
    visited_at: datetime = datetime(2026, 1, 15, 10, 0, 0),
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
    user = db_session.get(User, user_id)
    assert user is not None
    user.ar_character_id = ar_character_id
    db_session.commit()


def _get(
    client: TestClient,
    location_id: object = LOCATION_ID,
    params: dict[str, object] | None = None,
) -> dict:
    response = client.get(
        _endpoint(location_id), params=_params() if params is None else params
    )
    assert response.status_code == 200
    return response.json()


def _expected_distance(latitude: float, longitude: float) -> int:
    return distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, latitude, longitude
    )


# ---------------------------------------------------------------------
# 정상 응답
# ---------------------------------------------------------------------


def test_장소_상세를_조회하면_기본_정보와_방명록을_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_guestbook(
        db_session,
        guestbook_id=300,
        mission_id=COOPERATIVE_TYPE_ID,
        visited_at=date(2026, 1, 15),
        content_img_url=["https://example.com/guestbooks/300.jpg"],
        content_writing="귤나무 심기 체험이 정말 재미있었어요!",
    )
    _add_guestbook(
        db_session,
        guestbook_id=302,
        user_id=OTHER_USER_ID,
        visited_at=date(2026, 1, 12),
    )

    expected_distance = _expected_distance(LOCATION_LATITUDE, LOCATION_LONGITUDE)
    assert _get(client) == {
        # 모달에서 이미 준 값도 상세에서 다시 모두 내려준다.
        "locationTitle": LOCATION_TITLE,
        "locationCategory": LOCATION_CATEGORY,
        "distanceMeter": expected_distance,
        "durationMinutes": distance.calculate_duration_minutes(expected_distance),
        "locationAddress": LOCATION_ADDRESS,
        "isVisited": False,
        "locationDescription": OVERVIEW,
        "locationImageUrls": DETAIL_IMAGE_URLS,
        "nearbyMissions": [],
        "guestbooks": [
            {
                "id": 300,
                "missionTitle": COOPERATIVE_TITLE,
                "representativeImageUrl": "https://example.com/guestbooks/300.jpg",
                "userId": CURRENT_USER_ID,
                "userNickname": NICKNAME,
                "characterImgUrl": None,
                "visitedAt": "2026-01-15",
                "contentWriting": "귤나무 심기 체험이 정말 재미있었어요!",
            },
            {
                "id": 302,
                "missionTitle": None,
                "representativeImageUrl": None,
                "userId": OTHER_USER_ID,
                "userNickname": OTHER_NICKNAME,
                "characterImgUrl": None,
                "visitedAt": "2026-01-12",
                "contentWriting": None,
            },
        ],
        "locationMission": None,
    }


def test_거리와_예상_시간은_요청_좌표로_계산한다(
    client: TestClient, detail_data: None
) -> None:
    body = _get(client)

    expected_distance = _expected_distance(LOCATION_LATITUDE, LOCATION_LONGITUDE)
    assert body["distanceMeter"] == expected_distance
    assert body["durationMinutes"] == distance.calculate_duration_minutes(
        expected_distance
    )


def test_사용자_좌표가_장소와_같으면_거리가_0이다(
    client: TestClient, detail_data: None
) -> None:
    body = _get(
        client,
        params=_params(
            userLatitude=LOCATION_LATITUDE, userLongitude=LOCATION_LONGITUDE
        ),
    )

    assert body["distanceMeter"] == 0


def test_미션도_방명록도_없는_장소도_정상_응답이다(
    client: TestClient, detail_data: None
) -> None:
    body = _get(client, PLAIN_LOCATION_ID)

    # 404 가 아니라 200 이고 비어 있는 값만 null / 빈 배열이다.
    assert body["locationMission"] is None
    assert body["nearbyMissions"] == []
    assert body["guestbooks"] == []


# ---------------------------------------------------------------------
# TourAPI 설명 / 상세 이미지
# ---------------------------------------------------------------------


def test_TourAPI_설명을_조회하지_못하면_null이다(
    client: TestClient, detail_data: None
) -> None:
    # 스텁이 이 장소의 content_id 에만 설명을 준다.
    assert _get(client, PLAIN_LOCATION_ID)["locationDescription"] is None


def test_상세_설명_조회에_장소의_content_id를_쓴다(
    client: TestClient, detail_data: None, stub_overview: list[int]
) -> None:
    _get(client)

    assert stub_overview == [LOCATION_CONTENT_ID]


def test_상세_이미지_조회에_장소의_content_id와_5를_쓴다(
    client: TestClient, detail_data: None, stub_detail_images: list[tuple[int, int]]
) -> None:
    _get(client)

    assert stub_detail_images == [(LOCATION_CONTENT_ID, 5)]


def test_상세_이미지를_조회하지_못하면_빈_배열이_아니라_null이다(
    client: TestClient, detail_data: None
) -> None:
    assert _get(client, PLAIN_LOCATION_ID)["locationImageUrls"] is None


def test_TourAPI_조회가_실패해도_나머지_응답을_200으로_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 설명·상세 이미지·추천 미션 이미지 모두 조회하지 못하는 장소다.
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)
    _add_guestbook(db_session, guestbook_id=1, location_id=PLAIN_LOCATION_ID)

    body = _get(client, PLAIN_LOCATION_ID)

    assert body["locationDescription"] is None
    assert body["locationImageUrls"] is None
    assert body["nearbyMissions"][0]["representativeImageUrl"] is None
    # 이미지가 없어도 나머지 값은 그대로 내려온다.
    assert body["locationTitle"] == "다른 장소"
    assert body["locationMission"]["missionId"] == TREASURE_MISSION_ID
    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [1]


# ---------------------------------------------------------------------
# 방명록
# ---------------------------------------------------------------------


def test_방명록이_없으면_빈_배열을_반환한다(
    client: TestClient, detail_data: None
) -> None:
    assert _get(client)["guestbooks"] == []


def test_방명록은_개수_제한_없이_모두_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    for guestbook_id in range(1, 11):
        _add_guestbook(
            db_session,
            guestbook_id=guestbook_id,
            visited_at=date(2026, 1, guestbook_id),
        )

    body = _get(client)

    # 모달 조회와 달리 3개로 자르지 않는다.
    assert len(body["guestbooks"]) == 10


def test_방명록은_방문일_최신순이고_같으면_id가_큰_순이다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1, visited_at=date(2026, 1, 10))
    _add_guestbook(db_session, guestbook_id=2, visited_at=date(2026, 1, 20))
    _add_guestbook(db_session, guestbook_id=3, visited_at=date(2026, 1, 20))

    body = _get(client)

    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [3, 2, 1]


def test_최신순은_저장_시각이_아니라_방문일_기준이다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 나중에 저장했지만 방문일은 더 과거인 방명록
    db_session.add(
        Guestbook(
            id=1,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=date(2026, 1, 10),
            saved_at=datetime(2026, 2, 1, 12, 0, 0),
        )
    )
    db_session.add(
        Guestbook(
            id=2,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=date(2026, 1, 20),
            saved_at=datetime(2026, 1, 21, 12, 0, 0),
        )
    )
    db_session.commit()

    assert [guestbook["id"] for guestbook in _get(client)["guestbooks"]] == [2, 1]


def test_삭제된_방명록은_반환하지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1)
    _add_guestbook(
        db_session, guestbook_id=2, deleted_at=datetime(2026, 1, 16, 9, 0, 0)
    )

    assert [guestbook["id"] for guestbook in _get(client)["guestbooks"]] == [1]


def test_다른_장소의_방명록은_섞이지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1, location_id=LOCATION_ID)
    _add_guestbook(db_session, guestbook_id=2, location_id=PLAIN_LOCATION_ID)

    assert [guestbook["id"] for guestbook in _get(client)["guestbooks"]] == [1]


def test_방명록마다_작성자_id와_닉네임을_함께_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1, user_id=OTHER_USER_ID)

    guestbook = _get(client)["guestbooks"][0]

    assert guestbook["userId"] == OTHER_USER_ID
    assert guestbook["userNickname"] == OTHER_NICKNAME


def test_방명록마다_작성자의_AR_캐릭터_이미지를_함께_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _assign_ar_character(db_session, user_id=OTHER_USER_ID)
    _add_guestbook(db_session, guestbook_id=1, user_id=OTHER_USER_ID)

    assert _get(client)["guestbooks"][0]["characterImgUrl"] == AR_CHARACTER_IMAGE_URL


def test_작성자에게_배정된_AR_캐릭터가_없으면_characterImgUrl은_null이다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # detail_data 의 사용자는 AR 캐릭터를 배정받지 않은 상태다.
    _add_guestbook(db_session, guestbook_id=1)

    assert _get(client)["guestbooks"][0]["characterImgUrl"] is None


def test_방명록마다_작성자의_AR_캐릭터를_각각_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _assign_ar_character(db_session, user_id=CURRENT_USER_ID)
    _add_guestbook(db_session, guestbook_id=1, visited_at=date(2026, 1, 15))
    _add_guestbook(
        db_session, guestbook_id=2, user_id=OTHER_USER_ID, visited_at=date(2026, 1, 12)
    )

    guestbooks = _get(client)["guestbooks"]

    # 작성자가 다르면 배정된 캐릭터도 각각 따라간다.
    assert [guestbook["characterImgUrl"] for guestbook in guestbooks] == [
        AR_CHARACTER_IMAGE_URL,
        None,
    ]


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
    detail_data: None,
    content_img_url: list[str] | None,
) -> None:
    _add_guestbook(db_session, guestbook_id=1, content_img_url=content_img_url)

    assert _get(client)["guestbooks"][0]["representativeImageUrl"] is None


# ---------------------------------------------------------------------
# isVisited
# ---------------------------------------------------------------------


def test_방문_기록이_있으면_isVisited가_true다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_visited_location(db_session)

    assert _get(client)["isVisited"] is True


def test_방문_기록이_여러_건이어도_isVisited는_true다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_visited_location(db_session, visited_at=datetime(2026, 1, 15, 10, 0, 0))
    _add_visited_location(db_session, visited_at=datetime(2026, 2, 3, 9, 0, 0))

    assert _get(client)["isVisited"] is True


def test_방문_기록이_없으면_isVisited가_false다(
    client: TestClient, detail_data: None
) -> None:
    assert _get(client)["isVisited"] is False


def test_다른_사용자의_방문_기록은_isVisited에_반영되지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_visited_location(db_session, user_id=OTHER_USER_ID)

    assert _get(client)["isVisited"] is False


def test_다른_장소의_방문_기록은_isVisited에_반영되지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_visited_location(db_session, location_id=PLAIN_LOCATION_ID)

    assert _get(client)["isVisited"] is False


def test_방명록만_있고_방문_기록이_없으면_isVisited가_false다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 방명록 작성 여부는 isVisited 판정에 쓰지 않는다.
    _add_guestbook(db_session, guestbook_id=1)

    assert _get(client)["isVisited"] is False


def test_미션을_완료해도_방문_기록이_없으면_isVisited가_false다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 미션 완료 여부도 isVisited 판정에 쓰지 않는다.
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session)

    body = _get(client)

    assert body["locationMission"]["isCompleted"] is True
    assert body["isVisited"] is False


# ---------------------------------------------------------------------
# locationMission
# ---------------------------------------------------------------------


def test_장소에_미션이_없으면_locationMission은_null이다(
    client: TestClient, detail_data: None
) -> None:
    assert _get(client)["locationMission"] is None


def test_보물찾기_미션이_있으면_제목과_설명과_보상을_모두_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)

    # 배열이 아니라 단일 객체이고, missionId 는 공통 MISSION.id 가 아니라 세부 미션 id 다.
    assert _get(client)["locationMission"] == {
        "missionId": TREASURE_MISSION_ID,
        "missionType": "TREASURE",
        "missionTitle": TREASURE_TITLE,
        "description": TREASURE_DESCRIPTION,
        "isCompleted": False,
        "rewardDetail": NOT_RECEIVED_REWARD_DETAIL,
    }


def test_협동_미션만_있으면_협동_미션을_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_cooperative_mission(db_session)

    assert _get(client)["locationMission"] == {
        "missionId": COOPERATIVE_MISSION_ID,
        "missionType": "COOPERATIVE",
        "missionTitle": COOPERATIVE_TITLE,
        "description": COOPERATIVE_DESCRIPTION,
        "isCompleted": False,
        "rewardDetail": NOT_RECEIVED_REWARD_DETAIL,
    }


def test_두_유형이_모두_연결된_비정상_데이터는_임의로_하나를_고르지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_cooperative_mission(db_session)

    # 한 장소에 최대 한 건이라는 무결성 전제를 깬 데이터라 500 으로 드러낸다.
    response = client.get(_endpoint(), params=_params())

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}


def test_다른_장소의_미션은_locationMission이_아니다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)

    assert _get(client)["locationMission"] is None


def test_locationMission에는_대표_이미지를_붙이지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)

    # 장소 이미지는 locationImageUrls 로 이미 내려준다.
    assert "representativeImageUrl" not in _get(client)["locationMission"]


# ---------------------------------------------------------------------
# 미션 완료 여부 / 보상 수령 여부
# ---------------------------------------------------------------------


def test_완료_이력이_있으면_isCompleted가_true다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session)

    assert _get(client)["locationMission"]["isCompleted"] is True


def test_진행_중_이력만_있으면_isCompleted가_false다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)

    assert _get(client)["locationMission"]["isCompleted"] is False


def test_완료했어도_보상을_안_받았으면_isReceived는_false다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session)

    mission = _get(client)["locationMission"]

    # isCompleted 와 보상별 isReceived 는 독립적으로 계산한다.
    assert mission["isCompleted"] is True
    assert mission["rewardDetail"] == NOT_RECEIVED_REWARD_DETAIL


def test_진행도_이력이_없으면_보상_수령_여부가_모두_false다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)

    reward_detail = _get(client)["locationMission"]["rewardDetail"]

    assert [reward["isReceived"] for reward in reward_detail.values()] == [
        False,
        False,
        False,
    ]


def test_서로_다른_진행도에서_지급된_보상은_각각_true가_된다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, ar_character_granted=True)
    _add_treasure_progress(db_session, coupon_granted=True)

    reward_detail = _get(client)["locationMission"]["rewardDetail"]

    # 종류별 OR 이라 포인트만 아직 안 받은 상태로 남는다.
    assert reward_detail["arCharacter"]["isReceived"] is True
    assert reward_detail["point"]["isReceived"] is False
    assert reward_detail["coupon"]["isReceived"] is True


def test_이미_수령한_보상도_상세_정보를_그대로_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(
        db_session,
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
    )

    # 수령한 보상을 null 로 바꾸거나 빼지 않는다.
    assert _get(client)["locationMission"]["rewardDetail"] == {
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


def test_다른_사용자의_이력은_반영되지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(
        db_session,
        user_id=OTHER_USER_ID,
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
    )

    mission = _get(client)["locationMission"]

    assert mission["isCompleted"] is False
    assert mission["rewardDetail"] == NOT_RECEIVED_REWARD_DETAIL


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param(
            {"participant_status": ParticipantStatus.PENDING}, id="pending-participant"
        ),
        pytest.param(
            {"participant_deleted_at": datetime(2026, 8, 22, 9, 0, 0)},
            id="deleted-participant",
        ),
        pytest.param(
            {"progress_deleted_at": datetime(2026, 8, 22, 9, 0, 0)},
            id="deleted-progress",
        ),
    ],
)
def test_협동_미션의_제외_대상_이력은_반영하지_않는다(
    client: TestClient, db_session: Session, detail_data: None, kwargs: dict
) -> None:
    _add_cooperative_mission(db_session)
    _add_cooperative_progress(db_session, point_granted=True, **kwargs)

    mission = _get(client)["locationMission"]

    assert mission["isCompleted"] is False
    assert mission["rewardDetail"]["point"]["isReceived"] is False


def test_상세_조회는_보상_지급_여부를_바꾸지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, progress_id=1, point_granted=True)

    _get(client)

    db_session.expire_all()
    progress = db_session.get(TreasureMissionProgress, 1)
    user = db_session.get(User, CURRENT_USER_ID)
    assert progress is not None
    assert user is not None
    # 조회만 하고 보상을 지급하거나 지급 여부를 바꾸지 않는다.
    assert progress.ar_character_reward_granted is False
    assert progress.point_reward_granted is True
    assert progress.coupon_reward_granted is False
    assert user.point == 0


def test_미션에_설정되지_않은_보상_항목만_null이다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session, reward_detail={"point": REWARD_POINT})

    assert _get(client)["locationMission"]["rewardDetail"] == {
        "arCharacter": None,
        "point": {"amount": REWARD_POINT, "isReceived": False},
        "coupon": None,
    }


# ---------------------------------------------------------------------
# nearbyMissions (임시 추천)
# ---------------------------------------------------------------------


def test_추천할_미션이_없으면_빈_배열이다(
    client: TestClient, detail_data: None
) -> None:
    assert _get(client)["nearbyMissions"] == []


def test_추천_미션도_제목과_설명과_보상을_모두_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)

    assert _get(client)["nearbyMissions"] == [
        {
            "missionId": TREASURE_MISSION_ID,
            "missionType": "TREASURE",
            "missionTitle": TREASURE_TITLE,
            "description": TREASURE_DESCRIPTION,
            "isCompleted": False,
            "rewardDetail": NOT_RECEIVED_REWARD_DETAIL,
            "locationTitle": LOCATION_TITLE,
            "representativeImageUrl": REPRESENTATIVE_IMAGE_URL,
        }
    ]


def test_추천_미션의_장소명과_이미지는_미션_장소_기준이다(
    client: TestClient,
    db_session: Session,
    detail_data: None,
    stub_representative_image: list[int],
) -> None:
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)

    mission = _get(client)["nearbyMissions"][0]

    # 보고 있는 장소가 아니라 미션이 있는 장소의 이름과 content_id 를 쓴다.
    assert mission["locationTitle"] == "다른 장소"
    assert stub_representative_image == [PLAIN_CONTENT_ID]
    assert mission["representativeImageUrl"] is None


def test_locationMission에는_장소명을_붙이지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)

    # 보고 있는 장소의 이름은 최상위 locationTitle 로 이미 준다.
    assert "locationTitle" not in _get(client)["locationMission"]


def test_추천_미션은_DB에_있는_미션_중에서_고른다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)
    _add_cooperative_mission(db_session)

    nearby = _get(client)["nearbyMissions"]

    # 랜덤이라 값 자체가 아니라 후보 안에 있는지로 확인한다.
    expected = {
        (TREASURE_MISSION_ID, "TREASURE", TREASURE_TITLE),
        (COOPERATIVE_MISSION_ID, "COOPERATIVE", COOPERATIVE_TITLE),
    }
    assert len(nearby) == 2
    for mission in nearby:
        assert (
            mission["missionId"],
            mission["missionType"],
            mission["missionTitle"],
        ) in expected


def test_현재_장소의_미션도_추천_후보에_들어간다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)

    nearby = _get(client)["nearbyMissions"]

    assert [mission["missionId"] for mission in nearby] == [TREASURE_MISSION_ID]


def test_추천_미션은_최대_3개다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    for mission_id in range(10, 20):
        _add_treasure_mission(db_session, mission_id=mission_id)

    nearby = _get(client)["nearbyMissions"]

    assert len(nearby) == RECOMMEND_COUNT
    # 같은 미션이 두 번 나오지 않는다.
    assert len({mission["missionId"] for mission in nearby}) == RECOMMEND_COUNT


def test_완료한_보물찾기는_추천에서_빠진다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)
    _add_cooperative_mission(db_session)
    _add_treasure_progress(db_session)

    nearby = _get(client)["nearbyMissions"]

    assert [mission["missionId"] for mission in nearby] == [COOPERATIVE_MISSION_ID]


def test_완료한_협동_미션은_추천에서_빠진다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)
    _add_cooperative_mission(db_session)
    _add_cooperative_progress(db_session)

    nearby = _get(client)["nearbyMissions"]

    assert [mission["missionId"] for mission in nearby] == [TREASURE_MISSION_ID]


def test_완료한_미션도_추천에_남으면_isCompleted를_그대로_내려준다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 추천 후보 필터는 추천 모듈이 정하고, 응답 필드는 언제나 채운다.
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)

    assert _get(client)["nearbyMissions"][0]["isCompleted"] is False


def test_진행_중인_미션은_추천에서_빼지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)

    assert [mission["missionId"] for mission in _get(client)["nearbyMissions"]] == [
        TREASURE_MISSION_ID
    ]


def test_다른_사용자가_완료한_미션은_추천에서_빼지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_treasure_progress(db_session, user_id=OTHER_USER_ID)

    assert [mission["missionId"] for mission in _get(client)["nearbyMissions"]] == [
        TREASURE_MISSION_ID
    ]


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
def test_협동_미션_완료로_보지_않으면_추천에_남는다(
    client: TestClient, db_session: Session, detail_data: None, kwargs: dict
) -> None:
    _add_cooperative_mission(db_session)
    _add_cooperative_progress(db_session, **kwargs)

    assert [mission["missionId"] for mission in _get(client)["nearbyMissions"]] == [
        COOPERATIVE_MISSION_ID
    ]


def test_다른_장소의_미션도_추천_후보다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 지금 보고 있는 장소가 아니라 다른 장소의 미션
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)

    assert [mission["missionId"] for mission in _get(client)["nearbyMissions"]] == [
        TREASURE_MISSION_ID
    ]


# ---------------------------------------------------------------------
# 404 / 400 / 401
# ---------------------------------------------------------------------


def test_장소가_없으면_404_LOCATION_NOT_FOUND로_응답한다(
    client: TestClient, detail_data: None
) -> None:
    response = client.get(_endpoint(999), params=_params())

    assert response.status_code == 404
    assert response.json() == {"code": "LOCATION_NOT_FOUND"}


@pytest.mark.parametrize(
    "location_id",
    [
        pytest.param("abc", id="정수가_아님"),
        pytest.param(0, id="0"),
        pytest.param(-1, id="음수"),
    ],
)
def test_path_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, detail_data: None, location_id: object
) -> None:
    response = client.get(_endpoint(location_id), params=_params())

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"userLongitude": USER_LONGITUDE}, id="위도_누락"),
        pytest.param({"userLatitude": USER_LATITUDE}, id="경도_누락"),
        pytest.param({}, id="둘_다_누락"),
    ],
)
def test_사용자_좌표가_없으면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, detail_data: None, params: dict[str, object]
) -> None:
    response = client.get(_endpoint(), params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    "params",
    [
        pytest.param(_params(userLatitude=91), id="위도_범위_초과"),
        pytest.param(_params(userLatitude=-91), id="위도_범위_미만"),
        pytest.param(_params(userLongitude=181), id="경도_범위_초과"),
        pytest.param(_params(userLongitude=-181), id="경도_범위_미만"),
        pytest.param(_params(userLatitude="북위"), id="숫자가_아님"),
    ],
)
def test_사용자_좌표가_범위_밖이면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, detail_data: None, params: dict[str, object]
) -> None:
    response = client.get(_endpoint(), params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_인증_헤더가_없으면_401로_응답한다(
    client: TestClient, detail_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.get(_endpoint(), params=_params())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, detail_data: None
) -> None:
    response = client.get(_endpoint(), params=_params(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_문서에_401을_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/api/v1/map/locations/{location_id}"]["get"]["responses"]

    assert sorted(responses) == ["200", "400", "401", "404", "500"]
