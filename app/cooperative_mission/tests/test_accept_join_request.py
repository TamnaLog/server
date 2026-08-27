"""PATCH /api/v1/cooperative-missions/{progressId}/participants/{participantId}/accept
- 참여 요청 수락 테스트.

기준 문서: app/cooperative_mission/docs/API_SPEC.md,
          app/cooperative_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    MissionStatus,
    ParticipantRole,
    ParticipantStatus,
)
from app.map.models import Location
from app.mission.models import Mission
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


COOPERATIVE_TYPE_ID = 1
COOPERATIVE_MISSION_ID = 11
LOCATION_ID = 1

PROGRESS_ID = 10
OTHER_PROGRESS_ID = 20

TEAM_TOKEN = "mock-team-token-10"
OTHER_TEAM_TOKEN = "mock-team-token-20"

# 현재 사용자(1)가 방장이다.
HOST_PARTICIPANT_ID = 1
MEMBER_USER_ID = 2
MEMBER_PARTICIPANT_ID = 2
OTHER_USER_ID = 3

JOINED_AT = datetime(2026, 8, 20, 11, 0, 0)


def _endpoint(progress_id: object, participant_id: object) -> str:
    return (
        f"/api/v1/cooperative-missions/{progress_id}/participants/{participant_id}/accept"
    )


@pytest.fixture
def accept_data(db_session: Session) -> None:
    """현재 사용자가 방장인 초대 단계 방 + 수락 대기 중인 팀원 하나."""
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
                nickname="몽글몽글파도",
                point=0,
            ),
            User(
                id=MEMBER_USER_ID,
                access_token_hash=access_token_hash(MEMBER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="오름러버",
                point=0,
            ),
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
                participant_status=ParticipantStatus.PENDING.value,
                participant_role=ParticipantRole.MEMBER.value,
                joined_at=None,
            ),
        ]
    )
    db_session.commit()


def _add_other_progress(db_session: Session, *, current_step: int = 1) -> None:
    """다른 방 하나와 그 방의 팀원(참여자 id 99)을 만든다."""
    db_session.add(
        CooperativeMissionProgress(
            id=OTHER_PROGRESS_ID,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=current_step,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token=OTHER_TEAM_TOKEN,
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=99,
            cooperative_mission_progress_id=OTHER_PROGRESS_ID,
            user_id=OTHER_USER_ID,
            participant_status=ParticipantStatus.PENDING.value,
            participant_role=ParticipantRole.MEMBER.value,
            joined_at=None,
        )
    )
    db_session.commit()


def _saved(db_session: Session, participant_id: int) -> CooperativeMissionParticipant:
    db_session.expire_all()
    participant = db_session.get(CooperativeMissionParticipant, participant_id)
    assert participant is not None
    return participant


def _set_step(db_session: Session, current_step: int) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.current_step = current_step
    db_session.commit()


def _accept(client: TestClient, participant_id: int = MEMBER_PARTICIPANT_ID) -> None:
    response = client.patch(
        _endpoint(PROGRESS_ID, participant_id), headers=auth_headers(CURRENT_USER_ID)
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------
# 수락 처리 (BUSINESS_RULES 7.)
# ---------------------------------------------------------------------


def test_방장이_수락하면_204로_응답하고_본문이_없다(
    client: TestClient, accept_data: None
) -> None:
    response = client.patch(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 204
    assert response.content == b""


def test_수락하면_참여자를_ACCEPTED로_바꾸고_수락_시각을_저장한다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    _accept(client)

    saved = _saved(db_session, MEMBER_PARTICIPANT_ID)
    assert saved.participant_status == ParticipantStatus.ACCEPTED.value
    assert saved.joined_at is not None
    # 역할과 소속 방은 그대로다.
    assert saved.participant_role == ParticipantRole.MEMBER.value
    assert saved.cooperative_mission_progress_id == PROGRESS_ID


def test_수락해도_새_참여자를_만들지_않는다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    _accept(client)

    db_session.expire_all()
    participants = db_session.query(CooperativeMissionParticipant).all()
    assert len(participants) == 2


# ---------------------------------------------------------------------
# 멱등 처리 (BUSINESS_RULES 8.)
# ---------------------------------------------------------------------


def test_이미_수락된_참여자를_다시_수락해도_204이고_수락_시각이_바뀌지_않는다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    participant.participant_status = ParticipantStatus.ACCEPTED.value
    participant.joined_at = JOINED_AT
    db_session.commit()

    _accept(client)

    saved = _saved(db_session, MEMBER_PARTICIPANT_ID)
    assert saved.participant_status == ParticipantStatus.ACCEPTED.value
    assert saved.joined_at == JOINED_AT


def test_수락_요청을_연속으로_두_번_보내도_결과가_같다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    _accept(client)
    first_joined_at = _saved(db_session, MEMBER_PARTICIPANT_ID).joined_at

    _accept(client)

    saved = _saved(db_session, MEMBER_PARTICIPANT_ID)
    assert saved.joined_at == first_joined_at
    assert len(db_session.query(CooperativeMissionParticipant).all()) == 2


# ---------------------------------------------------------------------
# 403 COOPERATIVE_MISSION_HOST_ONLY
# ---------------------------------------------------------------------


def test_방장이_아니면_403으로_응답하고_바꾸지_않는다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    # 수락 대기 중인 팀원 본인이 요청하는 경우
    response = client.patch(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(MEMBER_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}
    assert (
        _saved(db_session, MEMBER_PARTICIPANT_ID).participant_status
        == ParticipantStatus.PENDING.value
    )


def test_방에_참여하지_않은_사용자가_요청하면_403으로_응답한다(
    client: TestClient, accept_data: None
) -> None:
    response = client.patch(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(OTHER_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}


def test_다른_방의_방장이_요청하면_403으로_응답한다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    # 현재 사용자는 이 방의 방장이지만, 다른 방의 팀원을 수락할 수는 없다.
    _add_other_progress(db_session)

    response = client.patch(
        _endpoint(OTHER_PROGRESS_ID, 99), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}
    assert _saved(db_session, 99).participant_status == ParticipantStatus.PENDING.value


def test_토큰의_사용자가_없으면_401로_응답하고_바꾸지_않는다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    response = client.patch(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID), headers=auth_headers(999)
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert (
        _saved(db_session, MEMBER_PARTICIPANT_ID).participant_status
        == ParticipantStatus.PENDING.value
    )


# ---------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------


def test_진행도가_없으면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, accept_data: None
) -> None:
    response = client.patch(
        _endpoint(999, MEMBER_PARTICIPANT_ID), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_이미_완료된_방이면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.mission_status = MissionStatus.COMPLETED.value
    progress.completed_at = JOINED_AT
    db_session.commit()

    response = client.patch(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}
    assert (
        _saved(db_session, MEMBER_PARTICIPANT_ID).participant_status
        == ParticipantStatus.PENDING.value
    )


def test_참여자가_없으면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, accept_data: None
) -> None:
    response = client.patch(
        _endpoint(PROGRESS_ID, 999), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}


def test_다른_방의_참여자면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    # 참여자 99 는 다른 방 소속이라 이 방의 방장이 수락할 수 없다.
    _add_other_progress(db_session)

    response = client.patch(
        _endpoint(PROGRESS_ID, 99), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    assert _saved(db_session, 99).participant_status == ParticipantStatus.PENDING.value


def test_대상이_방장이면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, accept_data: None
) -> None:
    response = client.patch(
        _endpoint(PROGRESS_ID, HOST_PARTICIPANT_ID), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}


# ---------------------------------------------------------------------
# 409 COOPERATIVE_MISSION_JOIN_CLOSED
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_step",
    [pytest.param(2, id="역할_정하기_단계"), pytest.param(3, id="미션_수행_단계")],
)
def test_초대_단계를_지났으면_409로_응답하고_바꾸지_않는다(
    client: TestClient, db_session: Session, accept_data: None, current_step: int
) -> None:
    _set_step(db_session, current_step)

    response = client.patch(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_JOIN_CLOSED"}
    saved = _saved(db_session, MEMBER_PARTICIPANT_ID)
    assert saved.participant_status == ParticipantStatus.PENDING.value
    assert saved.joined_at is None


def test_방장이_아닌_사용자는_단계가_지나도_403이_먼저다(
    client: TestClient, db_session: Session, accept_data: None
) -> None:
    # 권한 검증이 단계 검증보다 앞이라 남의 방 단계를 알아낼 수 없다.
    _set_step(db_session, 2)

    response = client.patch(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(OTHER_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("progress_id", "participant_id"),
    [
        pytest.param(0, MEMBER_PARTICIPANT_ID, id="0인_진행도_id"),
        pytest.param("abc", MEMBER_PARTICIPANT_ID, id="정수가_아닌_진행도_id"),
        pytest.param(PROGRESS_ID, 0, id="0인_참여자_id"),
        pytest.param(PROGRESS_ID, "abc", id="정수가_아닌_참여자_id"),
    ],
)
def test_path_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient,
    db_session: Session,
    accept_data: None,
    progress_id: object,
    participant_id: object,
) -> None:
    response = client.patch(
        _endpoint(progress_id, participant_id), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert (
        _saved(db_session, MEMBER_PARTICIPANT_ID).participant_status
        == ParticipantStatus.PENDING.value
    )
