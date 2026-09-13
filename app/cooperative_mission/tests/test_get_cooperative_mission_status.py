"""GET /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress
- 협동 미션 상태 조회 테스트.

기준 문서: app/cooperative_mission/docs/API_SPEC_2.md,
          app/cooperative_mission/docs/BUSINESS_RULES_2.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import distance, next_location
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    CooperativeRoleCard,
    CooperativeRoleProgress,
    MissionStatus,
    ParticipantRole,
    ParticipantStatus,
)
from app.map.models import Location
from app.mission.models import Mission
from app.treasure_mission.models import AcquiredArCharacter, ArCharacter
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


COOPERATIVE_TYPE_ID = 1
COOPERATIVE_MISSION_ID = 12
MISSION_TITLE = "함께 키우는 귤나무"
LOCATION_ID = 1
LOCATION_TITLE = "종화네 과수원"
LOCATION_IMAGE_URL = "https://example.com/locations/gwaeon.jpg"
LOCATION_MX = 126.5707
LOCATION_MY = 33.4507

# 완료한 미션의 장소와 다른 값인지 확인할 추천 전용 장소
OTHER_LOCATION_ID = 2
OTHER_LOCATION_TITLE = "협재 해수욕장"
OTHER_LOCATION_MX = 126.2396
OTHER_LOCATION_MY = 33.3937

# 다음 장소까지의 직선거리를 계산할 사용자 현재 위치
USER_LATITUDE = 33.4996
USER_LONGITUDE = 126.5312

PROGRESS_ID = 10
TEAM_TOKEN = "mock-team-token-10"

# 현재 사용자(1)가 방장이다.
HOST_PARTICIPANT_ID = 1
MEMBER_USER_ID = 2
MEMBER_PARTICIPANT_ID = 2
OUTSIDER_USER_ID = 3

ROLE_CARD_COUNT = 6

AR_CHARACTER_ID = 5
CHARACTER_IMG_URL = "https://example.com/characters/wave.png"
REWARD_POINT = 200
COUPON_LOCATION = "협재 바다뷰 카페"
COUPON_PRICE = 4000
INITIAL_USER_POINT = 30

REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": REWARD_POINT,
    "coupon_location": COUPON_LOCATION,
    "coupon_price": COUPON_PRICE,
}


def _endpoint(progress_id: object = PROGRESS_ID) -> str:
    return f"/api/v1/cooperative-missions/{progress_id}/progress"


def _location_query() -> dict[str, float]:
    """다음 장소까지의 거리 계산에 쓰는 사용자 현재 위치 Query."""
    return {"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE}


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """장소 이미지 조회(TourAPI)를 막아 외부 네트워크를 타지 않게 한다."""
    monkeypatch.setattr(
        next_location, "get_location_image_url", lambda content_id: LOCATION_IMAGE_URL
    )


@pytest.fixture
def status_data(db_session: Session) -> None:
    """방장(현재 사용자) + 수락된 팀원 한 명이 있는 협동 미션 방."""
    db_session.add_all(
        [
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title=MISSION_TITLE,
                description="일행과 역할을 나눠보세요.",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
            Location(
                id=LOCATION_ID,
                content_id=126273,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 제주시 조천읍 감귤밭길 12",
                location_category="농장",
                radius=400,
                mx=LOCATION_MX,
                my=LOCATION_MY,
            ),
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="나민",
                point=INITIAL_USER_POINT,
            ),
            User(
                id=MEMBER_USER_ID,
                access_token_hash=access_token_hash(MEMBER_USER_ID),
                nickname="이서연",
                point=INITIAL_USER_POINT,
            ),
            User(
                id=OUTSIDER_USER_ID,
                access_token_hash=access_token_hash(OUTSIDER_USER_ID),
                nickname="김민우",
                point=0,
            ),
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name="협재 파도지기",
                character_description="팀의 사진 미션을 응원하는 캐릭터입니다.",
                character_story_title="이야기 제목",
                acquire_condition="협동 미션을 완료하면 만날 수 있어요.",
                character_img_url=CHARACTER_IMG_URL,
                hashtags=["#협동"],
            ),
            *[
                CooperativeRoleCard(
                    id=role_card_id,
                    role_name=f"역할{role_card_id}",
                    role_description=f"역할{role_card_id} 설명",
                    location_to_find=[f"장소{role_card_id}"],
                )
                for role_card_id in range(1, ROLE_CARD_COUNT + 1)
            ],
        ]
    )
    db_session.flush()

    db_session.add(
        CooperativeMission(
            id=COOPERATIVE_MISSION_ID,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=LOCATION_ID,
            reward_detail=REWARD_DETAIL,
        )
    )
    db_session.flush()

    db_session.add(
        CooperativeMissionProgress(
            id=PROGRESS_ID,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=1,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token=TEAM_TOKEN,
        )
    )
    db_session.flush()

    db_session.add_all(
        [
            CooperativeMissionParticipant(
                id=HOST_PARTICIPANT_ID,
                cooperative_mission_progress_id=PROGRESS_ID,
                user_id=CURRENT_USER_ID,
                participant_status=ParticipantStatus.ACCEPTED.value,
                participant_role=ParticipantRole.HOST.value,
                joined_at=datetime(2026, 8, 20, 10, 0, 0),
            ),
            CooperativeMissionParticipant(
                id=MEMBER_PARTICIPANT_ID,
                cooperative_mission_progress_id=PROGRESS_ID,
                user_id=MEMBER_USER_ID,
                participant_status=ParticipantStatus.ACCEPTED.value,
                participant_role=ParticipantRole.MEMBER.value,
                joined_at=datetime(2026, 8, 20, 11, 0, 0),
            ),
        ]
    )
    db_session.commit()


def _set_step(
    db_session: Session,
    current_step: int,
    *,
    mission_status: MissionStatus = MissionStatus.IN_PROGRESS,
) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.current_step = current_step
    progress.mission_status = mission_status.value
    progress.completed_at = (
        datetime(2026, 8, 21, 12, 0, 0)
        if mission_status is MissionStatus.COMPLETED
        else None
    )
    db_session.commit()


def _complete(db_session: Session) -> None:
    """미션 완료 단계로 만든다."""
    _set_step(db_session, 4, mission_status=MissionStatus.COMPLETED)


def _add_role_progress(
    db_session: Session,
    *,
    role_progress_id: int,
    participant_id: int,
    role_card_id: int,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
    item_img_url: str | None = None,
) -> None:
    db_session.add(
        CooperativeRoleProgress(
            id=role_progress_id,
            participant_id=participant_id,
            cooperative_role_card_id=role_card_id,
            item_img_url=item_img_url,
            progress_status=status.value,
            completed_at=(
                datetime(2026, 8, 21, 10, 0, 0)
                if status is MissionStatus.COMPLETED
                else None
            ),
        )
    )
    db_session.commit()


def _add_completed_roles(db_session: Session, count: int) -> None:
    """인증까지 끝난 역할 진행도를 `count` 개 만든다. (역할 카드는 서로 다르게)"""
    for index in range(count):
        _add_role_progress(
            db_session,
            role_progress_id=index + 1,
            # 역할 카드 하나당 한 명이지만, 한 참가자가 여러 역할을 맡을 수 있다.
            participant_id=HOST_PARTICIPANT_ID if index % 2 == 0 else MEMBER_PARTICIPANT_ID,
            role_card_id=index + 1,
            status=MissionStatus.COMPLETED,
        )


def _get(client: TestClient, user_id: int = CURRENT_USER_ID) -> dict:
    response = client.get(
        _endpoint(), params=_location_query(), headers=auth_headers(user_id)
    )
    assert response.status_code == 200
    return response.json()


def _user_point(db_session: Session, user_id: int) -> int:
    db_session.expire_all()
    user = db_session.get(User, user_id)
    assert user is not None
    return user.point


def _acquired(db_session: Session) -> list[AcquiredArCharacter]:
    db_session.expire_all()
    return list(db_session.scalars(select(AcquiredArCharacter)).all())


def _saved_progress(db_session: Session) -> CooperativeMissionProgress:
    db_session.expire_all()
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    return progress


# ---------------------------------------------------------------------
# 1단계: 초대 (BUSINESS_RULES_2 7.)
# ---------------------------------------------------------------------


def test_1단계는_참가자_정보만_반환하고_나머지는_null이다(
    client: TestClient, status_data: None
) -> None:
    body = _get(client)

    assert body == {
        "missionProgressId": PROGRESS_ID,
        "missionId": COOPERATIVE_MISSION_ID,
        "missionTitle": MISSION_TITLE,
        "missionProgressStatus": "IN_PROGRESS",
        "currentStep": 1,
        "completedLocation": None,
        "currentParticipant": {
            "participantId": HOST_PARTICIPANT_ID,
            "participantRole": "HOST",
            "participantStatus": "ACCEPTED",
        },
        "participants": [
            {
                "participantId": HOST_PARTICIPANT_ID,
                "name": "나민",
                "participantRole": "HOST",
                "participantStatus": "ACCEPTED",
            },
            {
                "participantId": MEMBER_PARTICIPANT_ID,
                "name": "이서연",
                "participantRole": "MEMBER",
                "participantStatus": "ACCEPTED",
            },
        ],
        "roleCards": None,
        "roleProgresses": None,
        "completedRoleCount": None,
        "totalRoleCount": None,
        "reward": None,
        "nextLocation": None,
    }


def test_현재_사용자에_따라_currentParticipant가_달라진다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    # 수락 대기 중인 팀원이 자기 상태를 폴링하는 경우
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    participant.participant_status = ParticipantStatus.PENDING.value
    participant.joined_at = None
    db_session.commit()

    body = _get(client, user_id=MEMBER_USER_ID)

    assert body["currentParticipant"] == {
        "participantId": MEMBER_PARTICIPANT_ID,
        "participantRole": "MEMBER",
        "participantStatus": "PENDING",
    }


def test_참가자_목록은_방장을_먼저_두고_PENDING도_포함한다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    participant.participant_status = ParticipantStatus.PENDING.value
    db_session.commit()

    participants = _get(client)["participants"]

    assert [p["participantRole"] for p in participants] == ["HOST", "MEMBER"]
    assert participants[1]["participantStatus"] == "PENDING"


# ---------------------------------------------------------------------
# 2·3단계: 역할 배정 / 미션 수행 (BUSINESS_RULES_2 8·10·11.)
# ---------------------------------------------------------------------


def test_2단계는_역할_카드_전체와_역할_진행도를_반환한다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    _set_step(db_session, 2)
    _add_role_progress(
        db_session,
        role_progress_id=1,
        participant_id=HOST_PARTICIPANT_ID,
        role_card_id=1,
    )

    body = _get(client)

    assert [card["roleCardId"] for card in body["roleCards"]] == [1, 2, 3, 4, 5, 6]
    assert body["roleProgresses"] == [
        {
            "roleProgressId": 1,
            "participantId": HOST_PARTICIPANT_ID,
            "participantName": "나민",
            "roleCardId": 1,
            "roleName": "역할1",
            "progressStatus": "IN_PROGRESS",
            "itemImgUrl": None,
        }
    ]
    assert body["totalRoleCount"] == 1
    assert body["completedRoleCount"] == 0
    # 2·3단계에서는 완료 장소와 보상, 다음 장소를 내려주지 않는다.
    assert body["completedLocation"] is None
    assert body["reward"] is None
    assert body["nextLocation"] is None


def test_2단계에서_아직_배정이_없으면_빈_배열과_0을_반환한다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    _set_step(db_session, 2)

    body = _get(client)

    # null 이 아니라 빈 배열이어야 한다.
    assert body["roleProgresses"] == []
    assert body["totalRoleCount"] == 0
    assert body["completedRoleCount"] == 0
    assert len(body["roleCards"]) == ROLE_CARD_COUNT


def test_3단계_역할_집계는_인증_완료_수와_생성된_역할_수를_센다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    _set_step(db_session, 3)
    _add_role_progress(
        db_session,
        role_progress_id=1,
        participant_id=HOST_PARTICIPANT_ID,
        role_card_id=1,
        status=MissionStatus.COMPLETED,
        item_img_url="https://example.com/items/1.jpg",
    )
    _add_role_progress(
        db_session,
        role_progress_id=2,
        participant_id=MEMBER_PARTICIPANT_ID,
        role_card_id=2,
    )
    # 한 참가자가 서로 다른 역할 카드를 여러 개 맡을 수 있다.
    _add_role_progress(
        db_session,
        role_progress_id=3,
        participant_id=HOST_PARTICIPANT_ID,
        role_card_id=3,
    )

    body = _get(client)

    assert body["currentStep"] == 3
    assert body["totalRoleCount"] == 3
    assert body["completedRoleCount"] == 1
    assert body["roleProgresses"][0]["itemImgUrl"] == "https://example.com/items/1.jpg"
    # 배정하지 않은 역할 카드는 집계에 넣지 않는다.
    assert len(body["roleCards"]) == ROLE_CARD_COUNT


# ---------------------------------------------------------------------
# 4단계: 완료 (BUSINESS_RULES_2 12~15.)
# ---------------------------------------------------------------------


def test_4단계는_참가자_역할_정보를_null로_두고_보상과_다음_장소를_반환한다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    _add_completed_roles(db_session, 3)
    _complete(db_session)

    body = _get(client)

    assert body["missionProgressStatus"] == "COMPLETED"
    assert body["currentStep"] == 4
    assert body["currentParticipant"] is None
    assert body["participants"] is None
    assert body["roleCards"] is None
    assert body["roleProgresses"] is None
    assert body["completedRoleCount"] is None
    assert body["totalRoleCount"] is None
    # 방금 완료한 협동 미션이 진행된 장소
    assert body["completedLocation"] == {
        "locationId": LOCATION_ID,
        "locationTitle": LOCATION_TITLE,
    }
    # 완료 역할 3개 → AR 캐릭터 + 포인트
    assert body["reward"] == {
        "arCharacter": {
            "id": AR_CHARACTER_ID,
            "name": "협재 파도지기",
            "imageUrl": CHARACTER_IMG_URL,
        },
        "point": REWARD_POINT,
        "coupon": None,
    }
    assert body["nextLocation"] == {
        "id": LOCATION_ID,
        "locationTitle": LOCATION_TITLE,
        "locationImageUrl": LOCATION_IMAGE_URL,
        # Query 로 받은 사용자 위치에서 추천 장소까지의 직선거리(m)
        "distanceMeter": distance.calculate_distance_meter(
            USER_LATITUDE, USER_LONGITUDE, LOCATION_MY, LOCATION_MX
        ),
        # 이 장소에 연결된 세부 미션은 이 협동 미션뿐이다.
        "mission": {"id": COOPERATIVE_MISSION_ID, "missionType": "COOPERATIVE"},
    }


def test_completedLocation은_추천_장소가_아니라_완료한_미션의_장소다(
    client: TestClient,
    db_session: Session,
    status_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 추천 장소를 미션 장소와 다른 곳으로 고정해 두 필드가 섞이지 않는지 확인한다.
    db_session.add(
        Location(
            id=OTHER_LOCATION_ID,
            content_id=126280,
            location_title=OTHER_LOCATION_TITLE,
            location_address="제주특별자치도 제주시 한림읍 협재리",
            location_category="해수욕장",
            radius=400,
            mx=OTHER_LOCATION_MX,
            my=OTHER_LOCATION_MY,
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        next_location, "_pick_location", lambda db: db.get(Location, OTHER_LOCATION_ID)
    )
    _add_completed_roles(db_session, 3)
    _complete(db_session)

    body = _get(client)

    assert body["completedLocation"] == {
        "locationId": LOCATION_ID,
        "locationTitle": LOCATION_TITLE,
    }
    assert body["nextLocation"]["id"] == OTHER_LOCATION_ID
    assert body["nextLocation"]["locationTitle"] == OTHER_LOCATION_TITLE


@pytest.mark.parametrize(
    ("completed_count", "expected"),
    [
        pytest.param(0, (False, False, False), id="0개_보상_없음"),
        pytest.param(1, (True, False, False), id="1개_AR캐릭터"),
        pytest.param(2, (True, False, False), id="2개_AR캐릭터"),
        pytest.param(3, (True, True, False), id="3개_AR캐릭터_포인트"),
        pytest.param(4, (True, True, False), id="4개_AR캐릭터_포인트"),
        pytest.param(5, (True, True, True), id="5개_AR캐릭터_포인트_쿠폰"),
        pytest.param(6, (True, True, True), id="6개_AR캐릭터_포인트_쿠폰"),
    ],
)
def test_완료_역할_수로_보상_등급이_정해진다(
    client: TestClient,
    db_session: Session,
    status_data: None,
    completed_count: int,
    expected: tuple[bool, bool, bool],
) -> None:
    _add_completed_roles(db_session, completed_count)
    _complete(db_session)

    reward = _get(client)["reward"]

    has_character, has_point, has_coupon = expected
    assert (reward["arCharacter"] is not None) is has_character
    assert (reward["point"] is not None) is has_point
    assert (reward["coupon"] is not None) is has_coupon


def test_보상은_수락된_참가자_전원에게_지급한다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    _add_completed_roles(db_session, 3)
    _complete(db_session)

    _get(client)

    # 방장과 팀원 모두 포인트와 캐릭터를 받는다.
    assert _user_point(db_session, CURRENT_USER_ID) == INITIAL_USER_POINT + REWARD_POINT
    assert _user_point(db_session, MEMBER_USER_ID) == INITIAL_USER_POINT + REWARD_POINT
    acquired_user_ids = {record.user_id for record in _acquired(db_session)}
    assert acquired_user_ids == {CURRENT_USER_ID, MEMBER_USER_ID}


def test_수락_대기_참가자에게는_보상을_지급하지_않는다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    participant.participant_status = ParticipantStatus.PENDING.value
    db_session.commit()
    _add_completed_roles(db_session, 3)
    _complete(db_session)

    _get(client)

    assert _user_point(db_session, MEMBER_USER_ID) == INITIAL_USER_POINT
    assert {record.user_id for record in _acquired(db_session)} == {CURRENT_USER_ID}


def test_정산이_끝나면_지급_여부_세_개를_모두_true로_바꾼다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    # 완료 역할 1개면 포인트/쿠폰은 소멸하지만 지급 여부는 모두 마감한다.
    _add_completed_roles(db_session, 1)
    _complete(db_session)

    _get(client)

    saved = _saved_progress(db_session)
    assert saved.ar_character_reward_granted is True
    assert saved.point_reward_granted is True
    assert saved.coupon_reward_granted is True
    # 등급에 없는 포인트는 지급되지 않는다.
    assert _user_point(db_session, CURRENT_USER_ID) == INITIAL_USER_POINT


def test_폴링을_여러_번_해도_보상은_한_번만_지급한다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    _add_completed_roles(db_session, 3)
    _complete(db_session)

    first = _get(client)
    second = _get(client, user_id=MEMBER_USER_ID)
    third = _get(client)

    assert _user_point(db_session, CURRENT_USER_ID) == INITIAL_USER_POINT + REWARD_POINT
    assert _user_point(db_session, MEMBER_USER_ID) == INITIAL_USER_POINT + REWARD_POINT
    assert len(_acquired(db_session)) == 2
    # 정산 이후에도 같은 등급의 보상 정보를 계속 반환한다.
    assert first["reward"] == second["reward"] == third["reward"]


def test_완료_역할이_없으면_보상_항목이_모두_null이다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    _add_role_progress(
        db_session, role_progress_id=1, participant_id=HOST_PARTICIPANT_ID, role_card_id=1
    )
    _complete(db_session)

    body = _get(client)

    assert body["reward"] == {"arCharacter": None, "point": None, "coupon": None}
    assert _user_point(db_session, CURRENT_USER_ID) == INITIAL_USER_POINT
    assert _acquired(db_session) == []
    # 지급할 보상이 없어도 정산은 마감한다.
    assert _saved_progress(db_session).ar_character_reward_granted is True


def test_추천할_장소가_없으면_nextLocation은_null이다(
    client: TestClient,
    db_session: Session,
    status_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_completed_roles(db_session, 3)
    _complete(db_session)
    # 미션이 참조하는 장소는 FK(RESTRICT) 때문에 지울 수 없어서, 추천할 장소가 하나도
    # 없는 상황만 따로 만든다.
    monkeypatch.setattr(next_location, "_pick_location", lambda db: None)

    body = _get(client)

    # 추천할 장소가 없어도 완료 상태 조회 자체는 성공한다. (보상은 정상 지급)
    assert body["nextLocation"] is None
    assert body["reward"]["point"] == REWARD_POINT
    # 완료 장소는 추천 로직과 무관하게 그대로 내려준다.
    assert body["completedLocation"]["locationId"] == LOCATION_ID


# ---------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------


def test_진행도가_없으면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, status_data: None
) -> None:
    response = client.get(
        _endpoint(999), params=_location_query(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_참가자가_아니면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, status_data: None
) -> None:
    response = client.get(
        _endpoint(), params=_location_query(), headers=auth_headers(OUTSIDER_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}


def test_거절로_참가자가_삭제되면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    # 거절당한 팀원이 폴링하면 이 오류로 거절을 알 수 있다.
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    db_session.delete(participant)
    db_session.commit()

    response = client.get(
        _endpoint(), params=_location_query(), headers=auth_headers(MEMBER_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}


def test_완료된_방도_조회할_수_있다(
    client: TestClient, db_session: Session, status_data: None
) -> None:
    # 진행 중인 방으로 제한하면 완료 화면을 볼 수 없다.
    _complete(db_session)

    response = client.get(
        _endpoint(), params=_location_query(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 200


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, status_data: None
) -> None:
    response = client.get(
        _endpoint(), params=_location_query(), headers=auth_headers(999)
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "progress_id",
    [pytest.param(0, id="0인_진행도_id"), pytest.param("abc", id="정수가_아닌_진행도_id")],
)
def test_진행도_id가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, status_data: None, progress_id: object
) -> None:
    response = client.get(
        _endpoint(progress_id),
        params=_location_query(),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="좌표_누락"),
        pytest.param({"latitude": USER_LATITUDE}, id="경도_누락"),
        pytest.param({"longitude": USER_LONGITUDE}, id="위도_누락"),
        pytest.param(
            {"latitude": 91, "longitude": USER_LONGITUDE}, id="범위를_벗어난_위도"
        ),
        pytest.param(
            {"latitude": USER_LATITUDE, "longitude": 181}, id="범위를_벗어난_경도"
        ),
        pytest.param(
            {"latitude": "abc", "longitude": USER_LONGITUDE}, id="숫자가_아닌_위도"
        ),
    ],
)
def test_사용자_좌표가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, status_data: None, params: dict
) -> None:
    response = client.get(
        _endpoint(), params=params, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
