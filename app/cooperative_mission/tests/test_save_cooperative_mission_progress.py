"""PATCH /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress
- 협동 미션 진행도 저장(단계 변경) 테스트.

기준 문서: app/cooperative_mission/docs/API_SPEC_2.md,
          app/cooperative_mission/docs/BUSINESS_RULES_2.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


COOPERATIVE_TYPE_ID = 1
COOPERATIVE_MISSION_ID = 12
LOCATION_ID = 1

PROGRESS_ID = 10
TEAM_TOKEN = "mock-team-token-10"

# 현재 사용자(1)가 방장이다.
HOST_PARTICIPANT_ID = 1
MEMBER_USER_ID = 2
MEMBER_PARTICIPANT_ID = 2
OUTSIDER_USER_ID = 3

ROLE_CARD_COUNT = 6


def _endpoint(progress_id: object = PROGRESS_ID) -> str:
    return f"/api/v1/cooperative-missions/{progress_id}/progress"


@pytest.fixture
def progress_data(db_session: Session) -> None:
    """방장(현재 사용자) + 수락된 팀원 한 명이 있는 초대 단계 방."""
    db_session.add_all(
        [
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="일행과 역할을 나눠보세요.",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
            Location(
                id=LOCATION_ID,
                content_id=126273,
                location_title="종화네 과수원",
                location_address="제주특별자치도 제주시 조천읍 감귤밭길 12",
                location_category="농장",
                radius=400,
                mx=126.5707,
                my=33.4507,
            ),
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="나민",
                point=0,
            ),
            User(
                id=MEMBER_USER_ID,
                access_token_hash=access_token_hash(MEMBER_USER_ID),
                nickname="이서연",
                point=0,
            ),
            User(
                id=OUTSIDER_USER_ID,
                access_token_hash=access_token_hash(OUTSIDER_USER_ID),
                nickname="김민우",
                point=0,
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
            reward_detail={},
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
    db_session.commit()


def _set_participant_status(
    db_session: Session, participant_id: int, status: ParticipantStatus
) -> None:
    participant = db_session.get(CooperativeMissionParticipant, participant_id)
    assert participant is not None
    participant.participant_status = status.value
    db_session.commit()


def _assign_role(
    db_session: Session,
    *,
    role_progress_id: int,
    participant_id: int,
    role_card_id: int,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
) -> None:
    db_session.add(
        CooperativeRoleProgress(
            id=role_progress_id,
            participant_id=participant_id,
            cooperative_role_card_id=role_card_id,
            progress_status=status.value,
        )
    )
    db_session.commit()


def _assign_roles_to_everyone(db_session: Session) -> None:
    """방장과 팀원에게 역할을 하나씩 배정한다."""
    _assign_role(
        db_session, role_progress_id=1, participant_id=HOST_PARTICIPANT_ID, role_card_id=1
    )
    _assign_role(
        db_session, role_progress_id=2, participant_id=MEMBER_PARTICIPANT_ID, role_card_id=2
    )


def _saved(db_session: Session) -> CooperativeMissionProgress:
    db_session.expire_all()
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    return progress


def _change_step(
    client: TestClient, current_step: int, user_id: int = CURRENT_USER_ID
) -> None:
    response = client.patch(
        _endpoint(), json={"currentStep": current_step}, headers=auth_headers(user_id)
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------
# 1 → 2 (BUSINESS_RULES_2 7.)
# ---------------------------------------------------------------------


def test_방장이_단계를_올리면_204로_응답하고_본문이_없다(
    client: TestClient, progress_data: None
) -> None:
    response = client.patch(
        _endpoint(), json={"currentStep": 2}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 204
    assert response.content == b""


def test_1단계에서_2단계로_올리면_단계만_바뀐다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _change_step(client, 2)

    saved = _saved(db_session)
    assert saved.current_step == 2
    # 완료 처리는 3 → 4 에서만 한다.
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.completed_at is None


def test_수락_대기_참여_요청이_남아_있으면_409로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_participant_status(db_session, MEMBER_PARTICIPANT_ID, ParticipantStatus.PENDING)

    response = client.patch(
        _endpoint(), json={"currentStep": 2}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS"}
    assert _saved(db_session).current_step == 1
    # 남은 요청을 자동으로 수락하거나 지우지 않는다.
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    assert participant.participant_status == ParticipantStatus.PENDING.value


def test_방장_혼자여도_2단계로_올릴_수_있다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    db_session.delete(participant)
    db_session.commit()

    _change_step(client, 2)

    assert _saved(db_session).current_step == 2


# ---------------------------------------------------------------------
# 2 → 3 (BUSINESS_RULES_2 8·10.)
# ---------------------------------------------------------------------


def test_모든_수락_참가자가_역할을_받았으면_3단계로_올린다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_step(db_session, 2)
    _assign_roles_to_everyone(db_session)

    _change_step(client, 3)

    saved = _saved(db_session)
    assert saved.current_step == 3
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value


def test_역할을_못_받은_참가자가_있으면_409로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_step(db_session, 2)
    # 방장만 역할을 받은 상태
    _assign_role(
        db_session, role_progress_id=1, participant_id=HOST_PARTICIPANT_ID, role_card_id=1
    )

    response = client.patch(
        _endpoint(), json={"currentStep": 3}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_PARTICIPANT_ROLE_REQUIRED"}
    assert _saved(db_session).current_step == 2


def test_역할_배정이_하나도_없으면_409로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_step(db_session, 2)

    response = client.patch(
        _endpoint(), json={"currentStep": 3}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_PARTICIPANT_ROLE_REQUIRED"}


def test_역할_카드가_남아_있어도_3단계로_올릴_수_있다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 역할 카드 6종 중 2개만 배정한 상태여도 막지 않는다.
    _set_step(db_session, 2)
    _assign_roles_to_everyone(db_session)

    _change_step(client, 3)

    assert _saved(db_session).current_step == 3


def test_한_참가자가_역할을_여러_개_맡아도_3단계로_올릴_수_있다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_step(db_session, 2)
    _assign_roles_to_everyone(db_session)
    _assign_role(
        db_session, role_progress_id=3, participant_id=HOST_PARTICIPANT_ID, role_card_id=3
    )

    _change_step(client, 3)

    assert _saved(db_session).current_step == 3


def test_수락_대기_참가자는_역할_검증_대상이_아니다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 정상 흐름에서는 없지만, PENDING 참가자가 있어도 2 → 3 을 막지 않는다.
    _set_step(db_session, 2)
    _assign_role(
        db_session, role_progress_id=1, participant_id=HOST_PARTICIPANT_ID, role_card_id=1
    )
    _set_participant_status(db_session, MEMBER_PARTICIPANT_ID, ParticipantStatus.PENDING)

    _change_step(client, 3)

    assert _saved(db_session).current_step == 3


# ---------------------------------------------------------------------
# 3 → 4 (BUSINESS_RULES_2 9.)
# ---------------------------------------------------------------------


def test_3단계에서_4단계로_올리면_완료_상태와_완료_시각을_저장한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_step(db_session, 3)
    _assign_roles_to_everyone(db_session)

    _change_step(client, 4)

    saved = _saved(db_session)
    assert saved.current_step == 4
    assert saved.mission_status == MissionStatus.COMPLETED.value
    assert saved.completed_at is not None


def test_인증하지_않은_역할이_남아도_완료할_수_있다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_step(db_session, 3)
    _assign_roles_to_everyone(db_session)
    # 두 역할 모두 아직 IN_PROGRESS 다.

    _change_step(client, 4)

    assert _saved(db_session).mission_status == MissionStatus.COMPLETED.value


def test_완료해도_보상을_지급하지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 보상은 상태 조회 API 의 4단계 처리에서 정산한다.
    _set_step(db_session, 3)
    _assign_roles_to_everyone(db_session)

    _change_step(client, 4)

    saved = _saved(db_session)
    assert saved.ar_character_reward_granted is False
    assert saved.point_reward_granted is False
    assert saved.coupon_reward_granted is False
    db_session.expire_all()
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    assert user.point == 0


# ---------------------------------------------------------------------
# 409 COOPERATIVE_MISSION_STEP_NOT_ALLOWED / ALREADY_COMPLETED
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current_step", "requested_step"),
    [
        pytest.param(1, 3, id="1에서_3으로_건너뛰기"),
        pytest.param(1, 4, id="1에서_4로_건너뛰기"),
        pytest.param(2, 4, id="2에서_4로_건너뛰기"),
        pytest.param(2, 2, id="같은_단계_요청"),
        pytest.param(3, 2, id="이전_단계로_역행"),
    ],
)
def test_순차적인_다음_단계가_아니면_409로_응답한다(
    client: TestClient,
    db_session: Session,
    progress_data: None,
    current_step: int,
    requested_step: int,
) -> None:
    _set_step(db_session, current_step)

    response = client.patch(
        _endpoint(),
        json={"currentStep": requested_step},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"}
    assert _saved(db_session).current_step == current_step


def test_같은_요청을_두_번_보내면_두_번째는_409로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _change_step(client, 2)

    response = client.patch(
        _endpoint(), json={"currentStep": 2}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"}
    assert _saved(db_session).current_step == 2


def test_이미_완료된_미션이면_409_ALREADY_COMPLETED로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _set_step(db_session, 4, mission_status=MissionStatus.COMPLETED)

    response = client.patch(
        _endpoint(), json={"currentStep": 2}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"}
    assert _saved(db_session).current_step == 4


# ---------------------------------------------------------------------
# 403 / 404 / 401
# ---------------------------------------------------------------------


def test_방장이_아니면_403으로_응답하고_단계를_바꾸지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    response = client.patch(
        _endpoint(), json={"currentStep": 2}, headers=auth_headers(MEMBER_USER_ID)
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}
    assert _saved(db_session).current_step == 1


def test_방에_참여하지_않은_사용자가_요청하면_403으로_응답한다(
    client: TestClient, progress_data: None
) -> None:
    response = client.patch(
        _endpoint(), json={"currentStep": 2}, headers=auth_headers(OUTSIDER_USER_ID)
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}


def test_진행도가_없으면_404로_응답한다(client: TestClient, progress_data: None) -> None:
    response = client.patch(
        _endpoint(999), json={"currentStep": 2}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    response = client.patch(
        _endpoint(), json={"currentStep": 2}, headers=auth_headers(999)
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _saved(db_session).current_step == 1


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="단계_누락"),
        pytest.param({"currentStep": 1}, id="1단계_요청"),
        pytest.param({"currentStep": 5}, id="5단계_요청"),
        pytest.param({"currentStep": 0}, id="0단계_요청"),
        pytest.param({"currentStep": "abc"}, id="정수가_아닌_단계"),
        pytest.param({"currentStep": None}, id="null_단계"),
    ],
)
def test_요청_Body가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, progress_data: None, body: dict
) -> None:
    response = client.patch(_endpoint(), json=body, headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _saved(db_session).current_step == 1


@pytest.mark.parametrize(
    "progress_id",
    [pytest.param(0, id="0인_진행도_id"), pytest.param("abc", id="정수가_아닌_진행도_id")],
)
def test_진행도_id가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, progress_data: None, progress_id: object
) -> None:
    response = client.patch(
        _endpoint(progress_id),
        json={"currentStep": 2},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
