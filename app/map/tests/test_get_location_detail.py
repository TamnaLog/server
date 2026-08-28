"""GET /api/v1/map/locations/{locationId} - 지도 장소 상세 조회 테스트.

기준 문서: app/map/docs/API_SPEC.md, app/map/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
from app.map.models import Location
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


LOCATION_ID = 39
LOCATION_ADDRESS = "제주특별자치도 서귀포시 성산읍 일출로 284-12"
LOCATION_CONTENT_ID = 126273

# 미션이 없는 장소
PLAIN_LOCATION_ID = 40

OVERVIEW = "제주 동쪽 바다 위로 솟아오른 응회구입니다."

OTHER_USER_ID = 2
NICKNAME = "활발한 귤돌이"
OTHER_NICKNAME = "씩씩한 고래"

# 공통 MISSION.id
TREASURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TITLE = "오구포구 보물찾기"
COOPERATIVE_TITLE = "함께 키우는 귤나무"

# 세부 미션 id
TREASURE_MISSION_ID = 5
COOPERATIVE_MISSION_ID = 3
EXTRA_TREASURE_MISSION_ID = 7


def _endpoint(location_id: object = LOCATION_ID) -> str:
    return f"/api/v1/map/locations/{location_id}"


@pytest.fixture(autouse=True)
def stub_overview(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """TourAPI 상세 설명 조회를 막고 호출된 content_id 를 기록한다."""
    called: list[int] = []

    def fake_get_location_overview(content_id: int) -> str | None:
        called.append(content_id)
        return OVERVIEW if content_id == LOCATION_CONTENT_ID else None

    monkeypatch.setattr(service, "get_location_overview", fake_get_location_overview)
    return called


@pytest.fixture
def detail_data(db_session: Session) -> None:
    """장소 2곳 + 사용자 2명 + 공통 미션 2개. 세부 미션은 테스트마다 붙인다."""
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
            Location(
                id=LOCATION_ID,
                content_id=LOCATION_CONTENT_ID,
                location_title="성산일출봉",
                location_address=LOCATION_ADDRESS,
                location_category="자연",
                radius=300,
                mx=126.9331,
                my=33.4582,
            ),
            Location(
                id=PLAIN_LOCATION_ID,
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


def _add_treasure_mission(
    db_session: Session,
    *,
    mission_id: int = TREASURE_MISSION_ID,
    location_id: int = LOCATION_ID,
) -> None:
    db_session.add(
        TreasureMission(
            id=mission_id,
            mission_id=TREASURE_TYPE_ID,
            location_id=location_id,
            item_total_count=3,
            reward_detail={"point": 100},
        )
    )
    db_session.commit()


def _add_cooperative_mission(
    db_session: Session,
    *,
    mission_id: int = COOPERATIVE_MISSION_ID,
    location_id: int = LOCATION_ID,
) -> None:
    db_session.add(
        CooperativeMission(
            id=mission_id,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=location_id,
            reward_detail={"point": 200},
        )
    )
    db_session.commit()


def _complete_treasure_mission(
    db_session: Session,
    *,
    mission_id: int = TREASURE_MISSION_ID,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.COMPLETED,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            treasure_mission_id=mission_id,
            user_id=user_id,
            item_detail=[],
            current_found_item_idx=[],
            current_step=3,
            mission_status=mission_status.value,
        )
    )
    db_session.commit()


def _complete_cooperative_mission(
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


def _get(client: TestClient, location_id: object = LOCATION_ID) -> dict:
    response = client.get(_endpoint(location_id))
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------
# 정상 응답
# ---------------------------------------------------------------------


def test_장소_상세를_조회하면_주소와_설명과_방명록을_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
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

    body = _get(client)

    assert body["locationAddress"] == LOCATION_ADDRESS
    assert body["locationDescription"] == OVERVIEW
    assert body["guestbooks"] == [
        {
            "id": 300,
            "missionTitle": COOPERATIVE_TITLE,
            "representativeImageUrl": "https://example.com/guestbooks/300.jpg",
            "userNickname": NICKNAME,
            "visitedAt": "2026-01-15",
            "contentWriting": "귤나무 심기 체험이 정말 재미있었어요!",
        },
        {
            "id": 302,
            "missionTitle": None,
            "representativeImageUrl": None,
            "userNickname": OTHER_NICKNAME,
            "visitedAt": "2026-01-12",
            "contentWriting": None,
        },
    ]
    assert body["locationMission"] == {
        "id": TREASURE_MISSION_ID,
        "missionType": "TREASURE",
    }


def test_모달에서_준_값은_다시_내려주지_않는다(
    client: TestClient, detail_data: None
) -> None:
    body = _get(client)

    # 장소명·분류·거리·예상 시간은 모달 조회 응답에 이미 있다.
    assert body.keys() == {
        "locationAddress",
        "locationDescription",
        "nearbyMissions",
        "guestbooks",
        "locationMission",
    }


def test_TourAPI_설명을_조회하지_못하면_null이다(
    client: TestClient, detail_data: None
) -> None:
    # 스텁이 이 장소의 content_id 에만 설명을 준다.
    body = _get(client, PLAIN_LOCATION_ID)

    assert body["locationDescription"] is None


def test_상세_설명_조회에_장소의_content_id를_쓴다(
    client: TestClient, detail_data: None, stub_overview: list[int]
) -> None:
    _get(client)

    assert stub_overview == [LOCATION_CONTENT_ID]


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
# locationMission
# ---------------------------------------------------------------------


def test_장소에_미션이_없으면_locationMission은_null이다(
    client: TestClient, detail_data: None
) -> None:
    assert _get(client)["locationMission"] is None


def test_협동_미션만_있으면_협동_미션을_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_cooperative_mission(db_session)

    assert _get(client)["locationMission"] == {
        "id": COOPERATIVE_MISSION_ID,
        "missionType": "COOPERATIVE",
    }


def test_두_유형이_모두_있으면_세부_미션_id가_작은_쪽을_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 보물찾기 5, 협동 3 -> 유형과 관계없이 id 가 작은 협동 미션
    _add_treasure_mission(db_session)
    _add_cooperative_mission(db_session)

    assert _get(client)["locationMission"] == {
        "id": COOPERATIVE_MISSION_ID,
        "missionType": "COOPERATIVE",
    }


def test_같은_유형이_둘_이상이면_id가_작은_쪽을_반환한다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session, mission_id=EXTRA_TREASURE_MISSION_ID)
    _add_treasure_mission(db_session, mission_id=TREASURE_MISSION_ID)

    assert _get(client)["locationMission"] == {
        "id": TREASURE_MISSION_ID,
        "missionType": "TREASURE",
    }


def test_다른_장소의_미션은_locationMission이_아니다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)

    assert _get(client)["locationMission"] is None


# ---------------------------------------------------------------------
# nearbyMissions (임시 추천)
# ---------------------------------------------------------------------


def test_추천할_미션이_없으면_빈_배열이다(
    client: TestClient, detail_data: None
) -> None:
    assert _get(client)["nearbyMissions"] == []


def test_추천_미션은_DB에_있는_미션_중에서_고른다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
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
            mission["id"],
            mission["missionType"],
            mission["missionTitle"],
        ) in expected


def test_현재_장소의_미션도_추천_후보에_들어간다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)

    nearby = _get(client)["nearbyMissions"]

    assert [mission["id"] for mission in nearby] == [TREASURE_MISSION_ID]


def test_추천_미션은_최대_3개다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    for mission_id in range(10, 20):
        _add_treasure_mission(db_session, mission_id=mission_id)

    nearby = _get(client)["nearbyMissions"]

    assert len(nearby) == RECOMMEND_COUNT
    # 같은 미션이 두 번 나오지 않는다.
    assert len({mission["id"] for mission in nearby}) == RECOMMEND_COUNT


def test_완료한_보물찾기는_추천에서_빠진다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_cooperative_mission(db_session)
    _complete_treasure_mission(db_session)

    nearby = _get(client)["nearbyMissions"]

    assert [mission["id"] for mission in nearby] == [COOPERATIVE_MISSION_ID]


def test_완료한_협동_미션은_추천에서_빠진다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _add_cooperative_mission(db_session)
    _complete_cooperative_mission(db_session)

    nearby = _get(client)["nearbyMissions"]

    assert [mission["id"] for mission in nearby] == [TREASURE_MISSION_ID]


def test_진행_중인_미션은_추천에서_빼지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _complete_treasure_mission(db_session, mission_status=MissionStatus.IN_PROGRESS)

    assert [mission["id"] for mission in _get(client)["nearbyMissions"]] == [
        TREASURE_MISSION_ID
    ]


def test_다른_사용자가_완료한_미션은_추천에서_빼지_않는다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    _add_treasure_mission(db_session)
    _complete_treasure_mission(db_session, user_id=OTHER_USER_ID)

    assert [mission["id"] for mission in _get(client)["nearbyMissions"]] == [
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
    _complete_cooperative_mission(db_session, **kwargs)

    assert [mission["id"] for mission in _get(client)["nearbyMissions"]] == [
        COOPERATIVE_MISSION_ID
    ]


def test_장소가_없는_미션도_추천_후보다(
    client: TestClient, db_session: Session, detail_data: None
) -> None:
    # 지금 보고 있는 장소가 아니라 다른 장소의 미션
    _add_treasure_mission(db_session, location_id=PLAIN_LOCATION_ID)

    assert [mission["id"] for mission in _get(client)["nearbyMissions"]] == [
        TREASURE_MISSION_ID
    ]


# ---------------------------------------------------------------------
# 404 / 400 / 401
# ---------------------------------------------------------------------


def test_장소가_없으면_404_LOCATION_NOT_FOUND로_응답한다(
    client: TestClient, detail_data: None
) -> None:
    response = client.get(_endpoint(999))

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
    response = client.get(_endpoint(location_id))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_인증_헤더가_없으면_401로_응답한다(
    client: TestClient, detail_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.get(_endpoint())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, detail_data: None
) -> None:
    response = client.get(_endpoint(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_문서에_401을_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/api/v1/map/locations/{location_id}"]["get"]["responses"]

    assert sorted(responses) == ["200", "400", "401", "404", "500"]
