"""PUT /api/v1/cooperative-missions/{progressId}/role-assignments/{roleCardId}
- 협동 미션 역할 배정 저장 테스트.

기준 문서: app/cooperative_mission/docs/API_SPEC_2.md,
          app/cooperative_mission/docs/BUSINESS_RULES_2.md
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
OTHER_PROGRESS_ID = 20
TEAM_TOKEN = "mock-team-token-10"
OTHER_TEAM_TOKEN = "mock-team-token-20"

# 현재 사용자(1)가 방장이다.
HOST_PARTICIPANT_ID = 1
MEMBER_USER_ID = 2
MEMBER_PARTICIPANT_ID = 2
PENDING_USER_ID = 3
PENDING_PARTICIPANT_ID = 3
OUTSIDER_USER_ID = 4
OTHER_PROGRESS_PARTICIPANT_ID = 99

ROLE_CARD_COUNT = 6
ROLE_CARD_ID = 1


def _endpoint(
    progress_id: object = PROGRESS_ID, role_card_id: object = ROLE_CARD_ID
) -> str:
    return f"/api/v1/cooperative-missions/{progress_id}/role-assignments/{role_card_id}"


@pytest.fixture
def assignment_data(db_session: Session) -> None:
    """역할 배정 단계(2단계) 방 + 방장/수락 팀원/대기 팀원."""
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
                id=PENDING_USER_ID,
                access_token_hash=access_token_hash(PENDING_USER_ID),
                nickname="김민우",
                point=0,
            ),
            User(
                id=OUTSIDER_USER_ID,
                access_token_hash=access_token_hash(OUTSIDER_USER_ID),
                nickname="한라봉주스",
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
            current_step=2,
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
            CooperativeMissionParticipant(
                id=PENDING_PARTICIPANT_ID,
                cooperative_mission_progress_id=PROGRESS_ID,
                user_id=PENDING_USER_ID,
                participant_status=ParticipantStatus.PENDING.value,
                participant_role=ParticipantRole.MEMBER.value,
                joined_at=None,
            ),
        ]
    )
    db_session.commit()


def _add_other_progress(db_session: Session) -> None:
    """다른 방과 그 방의 수락된 팀원을 만든다."""
    db_session.add(
        CooperativeMissionProgress(
            id=OTHER_PROGRESS_ID,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=2,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token=OTHER_TEAM_TOKEN,
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=OTHER_PROGRESS_PARTICIPANT_ID,
            cooperative_mission_progress_id=OTHER_PROGRESS_ID,
            user_id=OUTSIDER_USER_ID,
            participant_status=ParticipantStatus.ACCEPTED.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
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


def _role_progresses(db_session: Session) -> list[CooperativeRoleProgress]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(CooperativeRoleProgress).order_by(CooperativeRoleProgress.id)
        ).all()
    )


def _assign(
    client: TestClient,
    *,
    participant_id: int = MEMBER_PARTICIPANT_ID,
    role_card_id: int = ROLE_CARD_ID,
    user_id: int = CURRENT_USER_ID,
) -> None:
    response = client.put(
        _endpoint(role_card_id=role_card_id),
        json={"participantId": participant_id},
        headers=auth_headers(user_id),
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------
# 최초 배정 (BUSINESS_RULES_2 9.)
# ---------------------------------------------------------------------


def test_역할을_배정하면_204로_응답하고_본문이_없다(
    client: TestClient, assignment_data: None
) -> None:
    response = client.put(
        _endpoint(),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 204
    assert response.content == b""


def test_처음_배정하면_역할_진행도를_새로_만든다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _assign(client)

    role_progresses = _role_progresses(db_session)
    assert len(role_progresses) == 1
    saved = role_progresses[0]
    assert saved.participant_id == MEMBER_PARTICIPANT_ID
    assert saved.cooperative_role_card_id == ROLE_CARD_ID
    assert saved.progress_status == MissionStatus.IN_PROGRESS.value
    assert saved.item_img_url is None
    assert saved.completed_at is None


def test_방장도_역할을_배정받을_수_있다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _assign(client, participant_id=HOST_PARTICIPANT_ID)

    assert _role_progresses(db_session)[0].participant_id == HOST_PARTICIPANT_ID


def test_한_참가자가_여러_역할_카드를_맡을_수_있다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _assign(client, participant_id=MEMBER_PARTICIPANT_ID, role_card_id=1)
    _assign(client, participant_id=MEMBER_PARTICIPANT_ID, role_card_id=2)

    role_progresses = _role_progresses(db_session)
    assert len(role_progresses) == 2
    assert {progress.cooperative_role_card_id for progress in role_progresses} == {1, 2}
    assert {progress.participant_id for progress in role_progresses} == {
        MEMBER_PARTICIPANT_ID
    }


def test_역할_카드를_모두_배정하지_않아도_된다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _assign(client, role_card_id=3)

    # 요청하지 않은 카드는 역할 진행도가 생기지 않는다.
    assert len(_role_progresses(db_session)) == 1


# ---------------------------------------------------------------------
# 담당자 변경 / 멱등 (BUSINESS_RULES_2 10·11.)
# ---------------------------------------------------------------------


def test_이미_배정된_역할_카드는_담당자만_바꾼다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _assign(client, participant_id=MEMBER_PARTICIPANT_ID)
    first_id = _role_progresses(db_session)[0].id

    _assign(client, participant_id=HOST_PARTICIPANT_ID)

    role_progresses = _role_progresses(db_session)
    # 새 row 를 만들지 않고 기존 row 를 그대로 쓴다.
    assert len(role_progresses) == 1
    saved = role_progresses[0]
    assert saved.id == first_id
    assert saved.participant_id == HOST_PARTICIPANT_ID
    assert saved.cooperative_role_card_id == ROLE_CARD_ID


def test_담당자를_바꿔도_인증_정보는_유지한다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    db_session.add(
        CooperativeRoleProgress(
            id=1,
            participant_id=MEMBER_PARTICIPANT_ID,
            cooperative_role_card_id=ROLE_CARD_ID,
            item_img_url="https://example.com/items/1.jpg",
            progress_status=MissionStatus.COMPLETED.value,
            completed_at=datetime(2026, 8, 21, 10, 0, 0),
        )
    )
    db_session.commit()

    _assign(client, participant_id=HOST_PARTICIPANT_ID)

    saved = _role_progresses(db_session)[0]
    assert saved.participant_id == HOST_PARTICIPANT_ID
    assert saved.item_img_url == "https://example.com/items/1.jpg"
    assert saved.progress_status == MissionStatus.COMPLETED.value
    assert saved.completed_at is not None


def test_같은_배정을_다시_요청해도_204이고_바뀌지_않는다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _assign(client)
    saved = _role_progresses(db_session)[0]
    first_id, first_updated_at = saved.id, saved.updated_at

    _assign(client)

    role_progresses = _role_progresses(db_session)
    assert len(role_progresses) == 1
    assert role_progresses[0].id == first_id
    assert role_progresses[0].updated_at == first_updated_at


def test_다른_방의_같은_역할_카드_배정은_건드리지_않는다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    # 역할 카드는 공용 마스터라 다른 방에도 같은 카드가 배정될 수 있다.
    _add_other_progress(db_session)
    db_session.add(
        CooperativeRoleProgress(
            id=1,
            participant_id=OTHER_PROGRESS_PARTICIPANT_ID,
            cooperative_role_card_id=ROLE_CARD_ID,
            progress_status=MissionStatus.IN_PROGRESS.value,
        )
    )
    db_session.commit()

    _assign(client, participant_id=MEMBER_PARTICIPANT_ID)

    role_progresses = _role_progresses(db_session)
    # 다른 방 배정은 그대로 두고 이 방 배정을 새로 만든다.
    assert len(role_progresses) == 2
    assert role_progresses[0].participant_id == OTHER_PROGRESS_PARTICIPANT_ID
    assert role_progresses[1].participant_id == MEMBER_PARTICIPANT_ID


# ---------------------------------------------------------------------
# 403 / 409 단계
# ---------------------------------------------------------------------


def test_방장이_아니면_403으로_응답하고_배정하지_않는다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    response = client.put(
        _endpoint(),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(MEMBER_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}
    assert _role_progresses(db_session) == []


@pytest.mark.parametrize(
    "current_step",
    [
        pytest.param(1, id="초대_단계"),
        pytest.param(3, id="미션_수행_단계"),
    ],
)
def test_역할_배정_단계가_아니면_409로_응답한다(
    client: TestClient, db_session: Session, assignment_data: None, current_step: int
) -> None:
    _set_step(db_session, current_step)

    response = client.put(
        _endpoint(),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"}
    assert _role_progresses(db_session) == []


def test_이미_완료된_미션이면_409_ALREADY_COMPLETED로_응답한다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _set_step(db_session, 4, mission_status=MissionStatus.COMPLETED)

    response = client.put(
        _endpoint(),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"}
    assert _role_progresses(db_session) == []


# ---------------------------------------------------------------------
# 404
# ---------------------------------------------------------------------


def test_진행도가_없으면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, assignment_data: None
) -> None:
    response = client.put(
        _endpoint(progress_id=999),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_역할_카드가_없으면_404_ROLE_CARD_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    response = client.put(
        _endpoint(role_card_id=999),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_ROLE_CARD_NOT_FOUND"}
    assert _role_progresses(db_session) == []


def test_참가자가_없으면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    response = client.put(
        _endpoint(),
        json={"participantId": 999},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    assert _role_progresses(db_session) == []


def test_수락_대기_참가자에게는_배정할_수_없다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    response = client.put(
        _endpoint(),
        json={"participantId": PENDING_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    assert _role_progresses(db_session) == []


def test_다른_방의_참가자에게는_배정할_수_없다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    _add_other_progress(db_session)

    response = client.put(
        _endpoint(),
        json={"participantId": OTHER_PROGRESS_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    assert _role_progresses(db_session) == []


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, db_session: Session, assignment_data: None
) -> None:
    response = client.put(
        _endpoint(),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(999),
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _role_progresses(db_session) == []


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="참가자_id_누락"),
        pytest.param({"participantId": 0}, id="0인_참가자_id"),
        pytest.param({"participantId": -1}, id="음수_참가자_id"),
        pytest.param({"participantId": "abc"}, id="정수가_아닌_참가자_id"),
        pytest.param({"participantId": None}, id="null_참가자_id"),
    ],
)
def test_요청_Body가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, assignment_data: None, body: dict
) -> None:
    response = client.put(_endpoint(), json=body, headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _role_progresses(db_session) == []


@pytest.mark.parametrize(
    ("progress_id", "role_card_id"),
    [
        pytest.param(0, ROLE_CARD_ID, id="0인_진행도_id"),
        pytest.param("abc", ROLE_CARD_ID, id="정수가_아닌_진행도_id"),
        pytest.param(PROGRESS_ID, 0, id="0인_역할_카드_id"),
        pytest.param(PROGRESS_ID, "abc", id="정수가_아닌_역할_카드_id"),
    ],
)
def test_path_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient,
    db_session: Session,
    assignment_data: None,
    progress_id: object,
    role_card_id: object,
) -> None:
    response = client.put(
        _endpoint(progress_id=progress_id, role_card_id=role_card_id),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _role_progresses(db_session) == []
