"""DELETE /api/v1/cooperative-missions/{progressId}/participants/{participantId}
- 참여 요청 거절 테스트.

기준 문서: app/cooperative_mission/docs/BUSINESS_RULES.md
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
OTHER_PROGRESS_PARTICIPANT_ID = 99


def _endpoint(progress_id: object, participant_id: object) -> str:
    return f"/api/v1/cooperative-missions/{progress_id}/participants/{participant_id}"


@pytest.fixture
def reject_data(db_session: Session) -> None:
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


def _add_other_progress(db_session: Session) -> None:
    """다른 방 하나와 그 방의 수락 대기 팀원을 만든다."""
    db_session.add(
        CooperativeMissionProgress(
            id=OTHER_PROGRESS_ID,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=1,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token=OTHER_TEAM_TOKEN,
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=OTHER_PROGRESS_PARTICIPANT_ID,
            cooperative_mission_progress_id=OTHER_PROGRESS_ID,
            user_id=OTHER_USER_ID,
            participant_status=ParticipantStatus.PENDING.value,
            participant_role=ParticipantRole.MEMBER.value,
            joined_at=None,
        )
    )
    db_session.commit()


def _participants(db_session: Session, progress_id: int = PROGRESS_ID) -> list[int]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(CooperativeMissionParticipant.id)
            .where(
                CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id
            )
            .order_by(CooperativeMissionParticipant.id)
        ).all()
    )


def _accept_member(db_session: Session) -> None:
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    participant.participant_status = ParticipantStatus.ACCEPTED.value
    participant.joined_at = datetime(2026, 8, 20, 11, 0, 0)
    db_session.commit()


def _set_step(db_session: Session, current_step: int) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.current_step = current_step
    db_session.commit()


def _reject(client: TestClient, participant_id: int = MEMBER_PARTICIPANT_ID) -> None:
    response = client.delete(
        _endpoint(PROGRESS_ID, participant_id), headers=auth_headers(CURRENT_USER_ID)
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------
# 거절 처리 (BUSINESS_RULES 7.)
# ---------------------------------------------------------------------


def test_방장이_거절하면_204로_응답하고_본문이_없다(
    client: TestClient, reject_data: None
) -> None:
    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 204
    assert response.content == b""


def test_거절하면_참여자_row를_삭제한다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    _reject(client)

    # REJECTED 상태를 남기지 않고 지운다. 방장은 그대로 남는다.
    assert _participants(db_session) == [HOST_PARTICIPANT_ID]
    assert db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID) is None


def test_거절한_사용자는_같은_초대_URL로_다시_요청할_수_있다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    _reject(client)

    response = client.post(
        "/api/v1/cooperative-missions/join-requests",
        json={"teamToken": TEAM_TOKEN},
        headers=auth_headers(MEMBER_USER_ID),
    )

    # 거절로 자리가 비었으므로 새 PENDING 참여 요청이 만들어진다.
    assert response.status_code == 201
    assert response.json()["participantStatus"] == "PENDING"
    assert len(_participants(db_session)) == 2


def test_이미_거절한_참여자를_다시_거절하면_404로_응답한다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    _reject(client)

    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID]


# ---------------------------------------------------------------------
# 409 COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED (BUSINESS_RULES 8.)
# ---------------------------------------------------------------------


def test_이미_수락된_팀원은_409로_응답하고_삭제하지_않는다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    _accept_member(db_session)

    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID, MEMBER_PARTICIPANT_ID]


# ---------------------------------------------------------------------
# 403 COOPERATIVE_MISSION_HOST_ONLY
# ---------------------------------------------------------------------


def test_방장이_아니면_403으로_응답하고_삭제하지_않는다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    # 수락 대기 중인 팀원이 자기 요청을 지우려는 경우
    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(MEMBER_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID, MEMBER_PARTICIPANT_ID]


def test_방에_참여하지_않은_사용자가_요청하면_403으로_응답한다(
    client: TestClient, reject_data: None
) -> None:
    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(OTHER_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}


def test_다른_방의_방장이_요청하면_403으로_응답한다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    # 현재 사용자는 이 방의 방장이지만 다른 방의 참여 요청은 거절할 수 없다.
    _add_other_progress(db_session)

    response = client.delete(
        _endpoint(OTHER_PROGRESS_ID, OTHER_PROGRESS_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}
    assert _participants(db_session, OTHER_PROGRESS_ID) == [OTHER_PROGRESS_PARTICIPANT_ID]


def test_토큰의_사용자가_없으면_401로_응답하고_삭제하지_않는다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID), headers=auth_headers(999)
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID, MEMBER_PARTICIPANT_ID]


# ---------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------


def test_진행도가_없으면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, reject_data: None
) -> None:
    response = client.delete(
        _endpoint(999, MEMBER_PARTICIPANT_ID), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_이미_완료된_방이면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.mission_status = MissionStatus.COMPLETED.value
    progress.completed_at = datetime(2026, 8, 20, 12, 0, 0)
    db_session.commit()

    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID, MEMBER_PARTICIPANT_ID]


def test_참여자가_없으면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, reject_data: None
) -> None:
    response = client.delete(
        _endpoint(PROGRESS_ID, 999), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}


def test_다른_방의_참여자면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    _add_other_progress(db_session)

    response = client.delete(
        _endpoint(PROGRESS_ID, OTHER_PROGRESS_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    assert _participants(db_session, OTHER_PROGRESS_ID) == [OTHER_PROGRESS_PARTICIPANT_ID]


def test_대상이_방장이면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    # 방장이 자기 자신을 거절할 수는 없다.
    response = client.delete(
        _endpoint(PROGRESS_ID, HOST_PARTICIPANT_ID), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID, MEMBER_PARTICIPANT_ID]


# ---------------------------------------------------------------------
# 409 COOPERATIVE_MISSION_JOIN_CLOSED
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_step",
    [pytest.param(2, id="역할_정하기_단계"), pytest.param(3, id="미션_수행_단계")],
)
def test_초대_단계를_지났으면_409로_응답하고_삭제하지_않는다(
    client: TestClient, db_session: Session, reject_data: None, current_step: int
) -> None:
    _set_step(db_session, current_step)

    response = client.delete(
        _endpoint(PROGRESS_ID, MEMBER_PARTICIPANT_ID),
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_JOIN_CLOSED"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID, MEMBER_PARTICIPANT_ID]


def test_방장이_아닌_사용자는_단계가_지나도_403이_먼저다(
    client: TestClient, db_session: Session, reject_data: None
) -> None:
    # 권한 검증이 단계 검증보다 앞이라 남의 방 단계를 알아낼 수 없다.
    _set_step(db_session, 2)

    response = client.delete(
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
    reject_data: None,
    progress_id: object,
    participant_id: object,
) -> None:
    response = client.delete(
        _endpoint(progress_id, participant_id), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _participants(db_session) == [HOST_PARTICIPANT_ID, MEMBER_PARTICIPANT_ID]
