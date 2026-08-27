"""POST /api/v1/cooperative-missions/join-requests - URL로 참여 요청 테스트.

기준 문서: app/cooperative_mission/docs/API_SPEC.md,
          app/cooperative_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cooperative_mission import service
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


ENDPOINT = "/api/v1/cooperative-missions/join-requests"

COOPERATIVE_TYPE_ID = 1
COOPERATIVE_MISSION_ID = 11
LOCATION_ID = 1

PROGRESS_ID = 10
TEAM_TOKEN = "mock-team-token-10"

HOST_USER_ID = 2
# 현재 사용자(1)는 아직 참여하지 않은 팀원 후보다.
EXTRA_USER_IDS = [3, 4, 5, 6, 7]


def _body(team_token: str = TEAM_TOKEN) -> dict[str, str]:
    return {"teamToken": team_token}


@pytest.fixture
def join_data(db_session: Session) -> None:
    """협동 미션 방 하나와 방장, 그리고 참여 가능한 사용자들."""
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
                id=HOST_USER_ID,
                access_token_hash=access_token_hash(HOST_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
            *[
                User(
                    id=user_id,
                    access_token_hash=access_token_hash(user_id),
                    nickname=f"사용자{user_id}",
                    point=0,
                )
                for user_id in EXTRA_USER_IDS
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

    # 방장은 항상 존재한다.
    db_session.add(
        CooperativeMissionParticipant(
            id=1,
            cooperative_mission_progress_id=PROGRESS_ID,
            user_id=HOST_USER_ID,
            participant_status=ParticipantStatus.ACCEPTED.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
    )
    db_session.commit()


def _add_participant(
    db_session: Session,
    *,
    participant_id: int,
    user_id: int,
    status: ParticipantStatus = ParticipantStatus.PENDING,
    role: ParticipantRole = ParticipantRole.MEMBER,
    progress_id: int = PROGRESS_ID,
) -> None:
    db_session.add(
        CooperativeMissionParticipant(
            id=participant_id,
            cooperative_mission_progress_id=progress_id,
            user_id=user_id,
            participant_status=status.value,
            participant_role=role.value,
            joined_at=(
                datetime(2026, 8, 20, 11, 0, 0)
                if status is ParticipantStatus.ACCEPTED
                else None
            ),
        )
    )
    db_session.commit()


def _participants(db_session: Session) -> list[CooperativeMissionParticipant]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(CooperativeMissionParticipant).order_by(CooperativeMissionParticipant.id)
        ).all()
    )


def _set_step(db_session: Session, current_step: int) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.current_step = current_step
    db_session.commit()


# ---------------------------------------------------------------------
# 신규 참여 요청 (BUSINESS_RULES 5.)
# ---------------------------------------------------------------------


def test_참여를_요청하면_201로_응답하고_명세의_필드를_반환한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"missionProgressId", "participantId", "participantStatus"}
    assert body["missionProgressId"] == PROGRESS_ID
    assert body["participantStatus"] == "PENDING"


def test_수락_대기_상태의_팀원으로_저장한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    body = client.post(ENDPOINT, json=_body()).json()

    participants = _participants(db_session)
    assert len(participants) == 2

    created = db_session.get(CooperativeMissionParticipant, body["participantId"])
    assert created is not None
    assert created.cooperative_mission_progress_id == PROGRESS_ID
    assert created.user_id == CURRENT_USER_ID
    assert created.participant_status == ParticipantStatus.PENDING.value
    assert created.participant_role == ParticipantRole.MEMBER.value
    # 아직 수락 전이라 참여 시각은 없다.
    assert created.joined_at is None


def test_요청자는_Body가_아니라_액세스_토큰으로_식별한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    other_user_id = EXTRA_USER_IDS[0]

    response = client.post(
        ENDPOINT, json=_body(), headers=auth_headers(other_user_id)
    )

    assert response.status_code == 201
    created = db_session.get(
        CooperativeMissionParticipant, response.json()["participantId"]
    )
    assert created is not None
    assert created.user_id == other_user_id


# ---------------------------------------------------------------------
# 기존 참여자 (BUSINESS_RULES 4.)
# ---------------------------------------------------------------------


def test_이미_참여_요청한_사용자는_200으로_기존_정보를_반환한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    _add_participant(db_session, participant_id=2, user_id=CURRENT_USER_ID)

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 200
    assert response.json() == {
        "missionProgressId": PROGRESS_ID,
        "participantId": 2,
        "participantStatus": "PENDING",
    }
    # 참여자가 늘지 않는다.
    assert len(_participants(db_session)) == 2


def test_이미_수락된_사용자는_200에_ACCEPTED로_반환한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    _add_participant(
        db_session, participant_id=2, user_id=CURRENT_USER_ID, status=ParticipantStatus.ACCEPTED
    )

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 200
    assert response.json()["participantStatus"] == "ACCEPTED"
    # 상태를 되돌리지 않는다.
    saved = db_session.get(CooperativeMissionParticipant, 2)
    assert saved is not None
    assert saved.participant_status == ParticipantStatus.ACCEPTED.value


def test_방장이_자신의_초대_링크를_열면_200에_HOST_정보를_반환한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    response = client.post(
        ENDPOINT, json=_body(), headers=auth_headers(HOST_USER_ID)
    )

    assert response.status_code == 200
    assert response.json()["participantId"] == 1
    assert response.json()["participantStatus"] == "ACCEPTED"
    assert len(_participants(db_session)) == 1


def test_같은_요청을_두_번_보내도_참여자는_하나만_생긴다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    first = client.post(ENDPOINT, json=_body())
    second = client.post(ENDPOINT, json=_body())

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["participantId"] == second.json()["participantId"]
    assert len(_participants(db_session)) == 2


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(ParticipantStatus.PENDING, id="수락_대기"),
        pytest.param(ParticipantStatus.ACCEPTED, id="수락됨"),
    ],
)
def test_기존_참여자는_인원이_가득_차도_409가_아니다(
    client: TestClient, db_session: Session, join_data: None, status: ParticipantStatus
) -> None:
    # 방장 + 나 + 4명 = 6명 (최대 인원)
    _add_participant(db_session, participant_id=2, user_id=CURRENT_USER_ID, status=status)
    for index, user_id in enumerate(EXTRA_USER_IDS[:4], start=3):
        _add_participant(db_session, participant_id=index, user_id=user_id)
    assert len(_participants(db_session)) == service.COOPERATIVE_MISSION_MAX_PARTICIPANTS

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 200
    assert response.json()["participantId"] == 2


def test_기존_참여자는_참여_단계가_지나도_409가_아니다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    _add_participant(db_session, participant_id=2, user_id=CURRENT_USER_ID)
    _set_step(db_session, 3)

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 200
    assert response.json()["participantId"] == 2


# ---------------------------------------------------------------------
# 409 참여를 받을 수 없는 경우
# ---------------------------------------------------------------------


@pytest.mark.parametrize("current_step", [2, 3, 4])
def test_초대_단계가_지나면_409_JOIN_CLOSED로_응답한다(
    client: TestClient, db_session: Session, join_data: None, current_step: int
) -> None:
    _set_step(db_session, current_step)

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_JOIN_CLOSED"}
    assert len(_participants(db_session)) == 1


def test_최대_인원이면_409_FULL로_응답한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    # 방장 + 5명 = 6명
    for index, user_id in enumerate(EXTRA_USER_IDS, start=2):
        _add_participant(db_session, participant_id=index, user_id=user_id)
    assert len(_participants(db_session)) == service.COOPERATIVE_MISSION_MAX_PARTICIPANTS

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_FULL"}
    assert len(_participants(db_session)) == service.COOPERATIVE_MISSION_MAX_PARTICIPANTS


def test_수락_대기_인원도_최대_인원_계산에_포함한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    # 방장(ACCEPTED) 1명 + PENDING 5명 = 6명
    for index, user_id in enumerate(EXTRA_USER_IDS, start=2):
        _add_participant(
            db_session, participant_id=index, user_id=user_id, status=ParticipantStatus.PENDING
        )

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_FULL"}


def test_최대_인원_직전이면_참여할_수_있다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    # 방장 + 4명 = 5명이므로 한 자리 남는다.
    for index, user_id in enumerate(EXTRA_USER_IDS[:4], start=2):
        _add_participant(db_session, participant_id=index, user_id=user_id)

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 201
    assert len(_participants(db_session)) == service.COOPERATIVE_MISSION_MAX_PARTICIPANTS


# ---------------------------------------------------------------------
# 404 유효하지 않은 초대
# ---------------------------------------------------------------------


def test_없는_팀_토큰이면_404_INVALID_INVITE_TOKEN으로_응답한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    response = client.post(ENDPOINT, json=_body("no-such-token"))

    assert response.status_code == 404
    assert response.json() == {"code": "INVALID_INVITE_TOKEN"}
    assert len(_participants(db_session)) == 1


def test_이미_완료된_방이면_404_INVALID_INVITE_TOKEN으로_응답한다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.mission_status = MissionStatus.COMPLETED.value
    progress.completed_at = datetime(2026, 8, 20, 12, 0, 0)
    db_session.commit()

    response = client.post(ENDPOINT, json=_body())

    assert response.status_code == 404
    assert response.json() == {"code": "INVALID_INVITE_TOKEN"}
    assert len(_participants(db_session)) == 1


# ---------------------------------------------------------------------
# 400 / 401
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="팀_토큰_누락"),
        pytest.param({"teamToken": ""}, id="빈_팀_토큰"),
        pytest.param({"teamToken": None}, id="null_팀_토큰"),
    ],
)
def test_팀_토큰이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, join_data: None, body: dict[str, object]
) -> None:
    response = client.post(ENDPOINT, json=body)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert len(_participants(db_session)) == 1


def test_토큰의_사용자가_없으면_401로_응답하고_참여자를_만들지_않는다(
    client: TestClient, db_session: Session, join_data: None
) -> None:
    response = client.post(ENDPOINT, json=_body(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert len(_participants(db_session)) == 1
