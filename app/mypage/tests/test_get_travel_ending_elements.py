"""GET /api/v1/users/me/travel-ending-elements - 여행 마무리 엽서 요소 조회 테스트.

기준 문서: app/mypage/docs/API_SPEC.md, app/mypage/docs/BUSINESS_RULES.md
"""

from datetime import datetime

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
from app.treasure_mission.models import (
    ArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me/travel-ending-elements"

OTHER_USER_ID = 2
UNKNOWN_USER_ID = 999

POINT = 2000

# 공통 MISSION id 와 유형별 세부 미션 id 를 일부러 다르게 둔다.
CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TYPE_ID = 3

CULTURE_MISSION_ID = 11
COOPERATIVE_MISSION_ID = 12
TREASURE_MISSION_ID = 13

LOCATION_ID = 21
OTHER_LOCATION_ID = 22
LOCATION_TITLE = "성산일출봉"
OTHER_LOCATION_TITLE = "애월 해변"

CHARACTER_ID = 5
CHARACTER_NAME = "바람 정령"
CHARACTER_IMAGE_URL = "https://example.com/characters/wind-spirit.png"

# 유형별 미션 보상. 문화는 포인트만, 보물찾기는 세 종류 모두, 협동은 쿠폰이 없다.
CULTURE_REWARD = {"point": 100}
TREASURE_REWARD = {
    "ar_character_id": CHARACTER_ID,
    "point": 150,
    "coupon_location": "한라산 기념품숍",
    "coupon_price": 3000,
}
COOPERATIVE_REWARD = {"ar_character_id": CHARACTER_ID, "point": 200}


@pytest.fixture
def ending_data(db_session: Session) -> None:
    """사용자 2명 + 장소 2곳 + 캐릭터 1개 + 유형별 미션 3개."""
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
                point=10,
            ),
            Location(
                id=LOCATION_ID,
                content_id=1001,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 성산읍",
                location_category="관광지",
                radius=300,
                mx=126.9410,
                my=33.4580,
            ),
            Location(
                id=OTHER_LOCATION_ID,
                content_id=1002,
                location_title=OTHER_LOCATION_TITLE,
                location_address="제주특별자치도 제주시 애월읍",
                location_category="해변",
                radius=300,
                mx=126.3300,
                my=33.4600,
            ),
            ArCharacter(
                id=CHARACTER_ID,
                character_name=CHARACTER_NAME,
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="획득 조건",
                character_img_url=CHARACTER_IMAGE_URL,
                hashtags=["#오름"],
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
                step_detail=[
                    {"step": 1, "step_title": "1단계", "description": "설명"},
                    {"step": 2, "step_title": "2단계", "description": "설명"},
                ],
            ),
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title="한라산 보물찾기",
                description="설명",
                step_detail=[{"step": 1, "step_title": "보물 찾기", "description": "설명"}],
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
                quiz_detail=[{"index": 1}],
                reward_detail=CULTURE_REWARD,
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=OTHER_LOCATION_ID,
                reward_detail=COOPERATIVE_REWARD,
            ),
            TreasureMission(
                id=TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=LOCATION_ID,
                item_total_count=3,
                reward_detail=TREASURE_REWARD,
            ),
        ]
    )
    db_session.commit()


def _add_visit(
    db_session: Session,
    *,
    visit_id: int,
    location_id: int = LOCATION_ID,
    user_id: int = CURRENT_USER_ID,
    visited_at: datetime = datetime(2026, 8, 20, 10, 0, 0),
) -> None:
    db_session.add(
        VisitedLocation(
            id=visit_id,
            user_id=user_id,
            location_id=location_id,
            visited_at=visited_at,
        )
    )
    db_session.commit()


def _add_culture_progress(
    db_session: Session,
    *,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
    status: MissionStatus = MissionStatus.COMPLETED,
    completed_at: datetime | None = datetime(2026, 8, 20, 14, 20, 0),
    point_granted: bool = True,
) -> None:
    db_session.add(
        CultureMissionProgress(
            id=progress_id,
            culture_mission_id=CULTURE_MISSION_ID,
            user_id=user_id,
            mission_status=status.value,
            current_quiz_index=3,
            correct_number=3,
            point_reward_granted=point_granted,
            completed_at=completed_at,
        )
    )
    db_session.commit()


def _add_treasure_progress(
    db_session: Session,
    *,
    progress_id: int,
    treasure_mission_id: int = TREASURE_MISSION_ID,
    user_id: int = CURRENT_USER_ID,
    status: MissionStatus = MissionStatus.COMPLETED,
    completed_at: datetime | None = datetime(2026, 8, 19, 11, 30, 0),
    ar_character_granted: bool = True,
    point_granted: bool = True,
    coupon_granted: bool = False,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=treasure_mission_id,
            user_id=user_id,
            item_detail=[{"index": 1, "mx": 126.94, "my": 33.45}],
            current_found_item_idx=[1],
            current_step=3,
            mission_status=status.value,
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            coupon_reward_granted=coupon_granted,
            completed_at=completed_at,
        )
    )
    db_session.commit()


def _add_cooperative_progress(
    db_session: Session,
    *,
    progress_id: int,
    participant_id: int,
    user_id: int = CURRENT_USER_ID,
    status: MissionStatus = MissionStatus.COMPLETED,
    completed_at: datetime | None = datetime(2026, 8, 18, 9, 0, 0),
    participant_status: ParticipantStatus = ParticipantStatus.ACCEPTED,
    participant_deleted_at: datetime | None = None,
    progress_deleted_at: datetime | None = None,
    ar_character_granted: bool = False,
    point_granted: bool = False,
) -> None:
    db_session.add(
        CooperativeMissionProgress(
            id=progress_id,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=2,
            mission_status=status.value,
            team_token=f"team-token-{progress_id}",
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            completed_at=completed_at,
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
    db_session.commit()


def _add_extra_treasure_mission(db_session: Session, *, mission_id: int) -> None:
    """같은 공통 미션에 속한 보물찾기 세부 미션을 하나 더 만든다. (쿼리 수 확인용)"""
    db_session.add(
        TreasureMission(
            id=mission_id,
            mission_id=TREASURE_TYPE_ID,
            location_id=LOCATION_ID,
            item_total_count=3,
            reward_detail=TREASURE_REWARD,
        )
    )
    db_session.commit()


def _get(client: TestClient, user_id: int = CURRENT_USER_ID) -> dict:
    response = client.get(ENDPOINT, headers=auth_headers(user_id))
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------
# 응답 형식 / 빈 결과
# ---------------------------------------------------------------------


def test_요소가_하나도_없으면_count는_0이고_목록은_빈_배열이다(
    client: TestClient, ending_data: None
) -> None:
    body = _get(client)

    assert body == {
        "point": POINT,
        "visitedLocationCount": 0,
        "visitedLocations": [],
        "completedMissionCount": 0,
        "completedMissions": [],
    }


def test_포인트는_합산하지_않고_USER_point를_그대로_쓴다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    # 완료 미션의 포인트 보상(100)을 더하지 않아야 한다.
    _add_culture_progress(db_session, progress_id=1)

    assert _get(client)["point"] == POINT


def test_사진_정보는_반환하지_않는다(client: TestClient, ending_data: None) -> None:
    body = _get(client)

    assert "pictures" not in body
    assert "pictureCount" not in body


# ---------------------------------------------------------------------
# 방문 장소
# ---------------------------------------------------------------------


def test_같은_장소를_여러_번_방문해도_한_번만_반환한다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_visit(db_session, visit_id=1, visited_at=datetime(2026, 8, 1, 9, 0, 0))
    _add_visit(db_session, visit_id=2, visited_at=datetime(2026, 8, 3, 9, 0, 0))

    body = _get(client)

    assert body["visitedLocations"] == [{"id": LOCATION_ID, "locationTitle": LOCATION_TITLE}]
    # count 는 별도 집계가 아니라 목록 길이와 같다.
    assert body["visitedLocationCount"] == 1


def test_방문_장소는_장소별_최근_방문_시각_내림차순이다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    # 장소 21 의 최근 방문(8/5)이 장소 22 의 방문(8/4)보다 나중이라 먼저 온다.
    _add_visit(db_session, visit_id=1, visited_at=datetime(2026, 8, 1, 9, 0, 0))
    _add_visit(db_session, visit_id=2, visited_at=datetime(2026, 8, 5, 9, 0, 0))
    _add_visit(
        db_session,
        visit_id=3,
        location_id=OTHER_LOCATION_ID,
        visited_at=datetime(2026, 8, 4, 9, 0, 0),
    )

    body = _get(client)

    assert [location["id"] for location in body["visitedLocations"]] == [
        LOCATION_ID,
        OTHER_LOCATION_ID,
    ]


def test_최근_방문_시각이_같으면_장소_id_내림차순이다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    same_time = datetime(2026, 8, 5, 9, 0, 0)
    _add_visit(db_session, visit_id=1, visited_at=same_time)
    _add_visit(db_session, visit_id=2, location_id=OTHER_LOCATION_ID, visited_at=same_time)

    body = _get(client)

    assert [location["id"] for location in body["visitedLocations"]] == [
        OTHER_LOCATION_ID,
        LOCATION_ID,
    ]


def test_다른_사용자의_방문_기록은_넣지_않는다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_visit(db_session, visit_id=1, user_id=OTHER_USER_ID)

    body = _get(client)

    assert body["visitedLocations"] == []
    assert body["visitedLocationCount"] == 0


# ---------------------------------------------------------------------
# 완료 미션
# ---------------------------------------------------------------------


def test_완료_미션은_명세의_필드를_모두_반환한다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_treasure_progress(db_session, progress_id=1)

    body = _get(client)

    assert body["completedMissionCount"] == 1
    assert body["completedMissions"] == [
        {
            # 공통 MISSION.id(3) 가 아니라 세부 미션 id 다.
            "missionId": TREASURE_MISSION_ID,
            "missionType": "TREASURE",
            "missionTitle": "한라산 보물찾기",
            "completedLocation": LOCATION_TITLE,
            "completedAt": "2026-08-19T11:30:00",
            "rewardDetail": {
                "arCharacter": {
                    "id": CHARACTER_ID,
                    "name": CHARACTER_NAME,
                    "imageUrl": CHARACTER_IMAGE_URL,
                    "isReceived": True,
                },
                "point": {"amount": 150, "isReceived": True},
                "coupon": {
                    "couponLocation": "한라산 기념품숍",
                    "couponPrice": 3000,
                    "isReceived": False,
                },
            },
        }
    ]


def test_장소가_없는_문화_미션은_완료_장소가_null이다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_culture_progress(db_session, progress_id=1)

    mission = _get(client)["completedMissions"][0]

    assert mission["missionId"] == CULTURE_MISSION_ID
    assert mission["completedLocation"] is None


def test_협동_미션의_완료_장소는_미션에_연결된_장소다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_cooperative_progress(db_session, progress_id=1, participant_id=1)

    mission = _get(client)["completedMissions"][0]

    assert mission["missionId"] == COOPERATIVE_MISSION_ID
    assert mission["missionType"] == "COOPERATIVE"
    assert mission["completedLocation"] == OTHER_LOCATION_TITLE


def test_진행_중인_미션은_넣지_않는다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_culture_progress(
        db_session, progress_id=1, status=MissionStatus.IN_PROGRESS, completed_at=None
    )

    body = _get(client)

    assert body["completedMissions"] == []
    assert body["completedMissionCount"] == 0


def test_다른_사용자의_완료_미션은_넣지_않는다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_culture_progress(db_session, progress_id=1, user_id=OTHER_USER_ID)
    _add_treasure_progress(db_session, progress_id=2, user_id=OTHER_USER_ID)
    _add_cooperative_progress(
        db_session, progress_id=3, participant_id=1, user_id=OTHER_USER_ID
    )

    body = _get(client)

    assert body["completedMissions"] == []


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
def test_협동_미션의_제외_대상은_넣지_않는다(
    client: TestClient,
    db_session: Session,
    ending_data: None,
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

    assert _get(client)["completedMissions"] == []


# ---------------------------------------------------------------------
# 중복 제거 / 정렬
# ---------------------------------------------------------------------


def test_같은_미션의_완료_기록이_여러_건이면_가장_최근_것만_남는다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_treasure_progress(
        db_session, progress_id=1, completed_at=datetime(2026, 8, 10, 9, 0, 0)
    )
    _add_treasure_progress(
        db_session, progress_id=2, completed_at=datetime(2026, 8, 21, 15, 0, 0)
    )

    body = _get(client)

    assert body["completedMissionCount"] == 1
    assert body["completedMissions"][0]["completedAt"] == "2026-08-21T15:00:00"


def test_완료_미션은_완료_시각_내림차순이다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_cooperative_progress(
        db_session,
        progress_id=1,
        participant_id=1,
        completed_at=datetime(2026, 8, 18, 9, 0, 0),
    )
    _add_treasure_progress(
        db_session, progress_id=2, completed_at=datetime(2026, 8, 19, 11, 30, 0)
    )
    _add_culture_progress(
        db_session, progress_id=3, completed_at=datetime(2026, 8, 20, 14, 20, 0)
    )

    body = _get(client)

    assert [mission["missionType"] for mission in body["completedMissions"]] == [
        "CULTURE",
        "TREASURE",
        "COOPERATIVE",
    ]
    assert body["completedMissionCount"] == 3


def test_완료_시각이_같으면_미션_유형_오름차순이다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    same_time = datetime(2026, 8, 20, 14, 20, 0)
    _add_culture_progress(db_session, progress_id=1, completed_at=same_time)
    _add_treasure_progress(db_session, progress_id=2, completed_at=same_time)
    _add_cooperative_progress(
        db_session, progress_id=3, participant_id=1, completed_at=same_time
    )

    body = _get(client)

    assert [mission["missionType"] for mission in body["completedMissions"]] == [
        "COOPERATIVE",
        "CULTURE",
        "TREASURE",
    ]


# ---------------------------------------------------------------------
# 보상과 수령 여부
# ---------------------------------------------------------------------


def test_미션에_설정되지_않은_보상은_null이다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    # 문화 미션은 포인트 보상만 설정돼 있다.
    _add_culture_progress(db_session, progress_id=1)

    reward = _get(client)["completedMissions"][0]["rewardDetail"]

    assert reward["arCharacter"] is None
    assert reward["coupon"] is None
    assert reward["point"] == {"amount": 100, "isReceived": True}


def test_아직_받지_않은_보상도_정보를_그대로_주고_isReceived로_구분한다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_cooperative_progress(
        db_session,
        progress_id=1,
        participant_id=1,
        ar_character_granted=False,
        point_granted=False,
    )

    reward = _get(client)["completedMissions"][0]["rewardDetail"]

    assert reward["arCharacter"] == {
        "id": CHARACTER_ID,
        "name": CHARACTER_NAME,
        "imageUrl": CHARACTER_IMAGE_URL,
        "isReceived": False,
    }
    assert reward["point"] == {"amount": 200, "isReceived": False}
    assert reward["coupon"] is None


def test_수령_여부는_최신_완료_행이_아니라_전체_진행도를_OR_한다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    # 예전 진행도에서 캐릭터·포인트를 받았고, 응답에 쓰이는 최근 완료 진행도는 쿠폰만 받았다.
    _add_treasure_progress(
        db_session,
        progress_id=1,
        completed_at=datetime(2026, 8, 10, 9, 0, 0),
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=False,
    )
    _add_treasure_progress(
        db_session,
        progress_id=2,
        completed_at=datetime(2026, 8, 21, 15, 0, 0),
        ar_character_granted=False,
        point_granted=False,
        coupon_granted=True,
    )

    reward = _get(client)["completedMissions"][0]["rewardDetail"]

    assert reward["arCharacter"]["isReceived"] is True
    assert reward["point"]["isReceived"] is True
    assert reward["coupon"]["isReceived"] is True


def test_진행_중인_진행도의_수령_이력도_반영한다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    # 완료 진행도는 미지급이지만 같은 미션의 다른 진행도에서 이미 받았다.
    _add_treasure_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.IN_PROGRESS,
        completed_at=None,
        ar_character_granted=True,
        point_granted=False,
        coupon_granted=False,
    )
    _add_treasure_progress(
        db_session,
        progress_id=2,
        ar_character_granted=False,
        point_granted=False,
        coupon_granted=False,
    )

    reward = _get(client)["completedMissions"][0]["rewardDetail"]

    assert reward["arCharacter"]["isReceived"] is True
    assert reward["point"]["isReceived"] is False


def test_다른_사용자의_수령_이력은_반영하지_않는다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_treasure_progress(
        db_session,
        progress_id=1,
        user_id=OTHER_USER_ID,
        ar_character_granted=True,
        point_granted=True,
        coupon_granted=True,
    )
    _add_treasure_progress(
        db_session,
        progress_id=2,
        ar_character_granted=False,
        point_granted=False,
        coupon_granted=False,
    )

    reward = _get(client)["completedMissions"][0]["rewardDetail"]

    assert reward["arCharacter"]["isReceived"] is False
    assert reward["point"]["isReceived"] is False
    assert reward["coupon"]["isReceived"] is False


# ---------------------------------------------------------------------
# N+1 / 읽기 전용
# ---------------------------------------------------------------------


def test_완료_미션과_방문_장소가_늘어도_쿼리_수가_늘지_않는다(
    client: TestClient,
    db_session: Session,
    ending_data: None,
    executed_queries: list[str],
) -> None:
    """미션마다 보상 지급 이력을 다시 조회하면 여기서 걸린다.

    쿼리 수는 미션 유형 수(3)로 고정이고, 유형 안의 미션 수나 방문 장소 수에는 늘지 않는다.
    """
    _add_treasure_progress(db_session, progress_id=1)
    _add_culture_progress(db_session, progress_id=2)
    _add_cooperative_progress(db_session, progress_id=3, participant_id=1)
    _add_visit(db_session, visit_id=1)

    executed_queries.clear()
    body = _get(client)
    before = len(executed_queries)
    assert body["completedMissionCount"] == 3

    # 같은 유형(보물찾기)의 미션과 방문 장소를 늘린다.
    _add_extra_treasure_mission(db_session, mission_id=14)
    _add_extra_treasure_mission(db_session, mission_id=15)
    _add_treasure_progress(db_session, progress_id=4, treasure_mission_id=14)
    _add_treasure_progress(db_session, progress_id=5, treasure_mission_id=15)
    _add_visit(db_session, visit_id=2, location_id=OTHER_LOCATION_ID)

    executed_queries.clear()
    body = _get(client)

    assert body["completedMissionCount"] == 5
    assert body["visitedLocationCount"] == 2
    assert len(executed_queries) == before


def test_조회해도_DB_상태가_바뀌지_않는다(
    client: TestClient, db_session: Session, ending_data: None
) -> None:
    _add_visit(db_session, visit_id=1)
    _add_treasure_progress(db_session, progress_id=1, coupon_granted=False)

    _get(client)

    db_session.expire_all()
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    assert user.point == POINT

    progress = db_session.get(TreasureMissionProgress, 1)
    assert progress is not None
    assert progress.coupon_reward_granted is False
    assert progress.mission_status == MissionStatus.COMPLETED.value

    assert len(list(db_session.scalars(select(VisitedLocation)).all())) == 1


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


def test_어떤_사용자의_토큰도_아니면_401을_반환한다(
    client: TestClient, ending_data: None
) -> None:
    response = client.get(ENDPOINT, headers=auth_headers(UNKNOWN_USER_ID))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
