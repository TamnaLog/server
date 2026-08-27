"""협동 미션 소프트 삭제(`deleted_at`) 필터 테스트.

세 테이블(`COOPERATIVE_MISSION_PROGRESS`, `COOPERATIVE_MISSION_PARTICIPANT`,
`COOPERATIVE_ROLE_PROGRESS`)은 행을 지우지 않고 `deleted_at` 으로 삭제를 표현한다.
삭제된 행이 조회에 섞이면 인원 수·참여 자격·완료 판정이 모두 어긋나므로
API 단위로 "조회에서 빠지는지"를 확인한다.
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import next_location
from app.common.datetimes import now_kst
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
from app.cooperative_mission.service import COOPERATIVE_MISSION_MAX_PARTICIPANTS
from app.map.models import Location
from app.mission.models import Mission
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


COOPERATIVE_TYPE_ID = 1
COOPERATIVE_MISSION_ID = 12
MISSION_TITLE = "함께 키우는 귤나무"
LOCATION_ID = 1

PROGRESS_ID = 10
TEAM_TOKEN = "mock-team-token-10"

# 현재 사용자(1)가 방장이다.
HOST_PARTICIPANT_ID = 1
MEMBER_USER_ID = 2
MEMBER_PARTICIPANT_ID = 2
OUTSIDER_USER_ID = 3

ROLE_CARD_ID = 1
ROLE_PROGRESS_ID = 100

HOME_ENDPOINT = "/api/v1/users/me/home"
HOME_PARAMS = {"latitude": 33.4507, "longitude": 126.5707}
JOIN_ENDPOINT = "/api/v1/cooperative-missions/join-requests"
START_ENDPOINT = f"/api/v1/cooperative-missions/{COOPERATIVE_MISSION_ID}/progress"

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _status_endpoint(progress_id: object = PROGRESS_ID) -> str:
    return f"/api/v1/cooperative-missions/{progress_id}/progress"


def _role_assignment_endpoint(role_card_id: int = ROLE_CARD_ID) -> str:
    return f"/api/v1/cooperative-missions/{PROGRESS_ID}/role-assignments/{role_card_id}"


def _verification_endpoint(role_progress_id: int = ROLE_PROGRESS_ID) -> str:
    return (
        f"/api/v1/cooperative-missions/{PROGRESS_ID}"
        f"/role-progresses/{role_progress_id}/verification"
    )


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """장소 이미지 조회(TourAPI)를 막아 외부 네트워크를 타지 않게 한다."""
    monkeypatch.setattr(next_location, "get_location_image_url", lambda content_id: None)


@pytest.fixture
def room(db_session: Session) -> None:
    """방장(현재 사용자) + 수락된 팀원 한 명이 있는 초대 단계 방."""
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
            CooperativeRoleCard(
                id=ROLE_CARD_ID,
                role_name="사진 담당",
                role_description="풍경 사진을 찍어요.",
                location_to_find=["과수원"],
            ),
        ]
    )
    db_session.flush()

    db_session.add(
        CooperativeMission(
            id=COOPERATIVE_MISSION_ID,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=LOCATION_ID,
            reward_detail={"point": 100},
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


def _soft_delete(db_session: Session, instance: Any) -> None:
    """행을 지우지 않고 `deleted_at` 만 남긴다."""
    instance.deleted_at = now_kst()
    db_session.commit()


def _soft_delete_participant(db_session: Session, participant_id: int) -> None:
    participant = db_session.get(CooperativeMissionParticipant, participant_id)
    assert participant is not None
    _soft_delete(db_session, participant)


def _soft_delete_progress(db_session: Session) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    _soft_delete(db_session, progress)


def _soft_delete_role_progress(db_session: Session, role_progress_id: int) -> None:
    role_progress = db_session.get(CooperativeRoleProgress, role_progress_id)
    assert role_progress is not None
    _soft_delete(db_session, role_progress)


def _set_step(db_session: Session, current_step: int) -> None:
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    progress.current_step = current_step
    db_session.commit()


def _add_role_progress(
    db_session: Session, *, role_progress_id: int, participant_id: int
) -> None:
    db_session.add(
        CooperativeRoleProgress(
            id=role_progress_id,
            participant_id=participant_id,
            cooperative_role_card_id=ROLE_CARD_ID,
            item_img_url=None,
            progress_status=MissionStatus.IN_PROGRESS.value,
            completed_at=None,
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------
# 참여자 소프트 삭제
# ---------------------------------------------------------------------


def test_삭제된_참여자는_상태_조회의_참가자_목록에서_빠진다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_participant(db_session, MEMBER_PARTICIPANT_ID)

    response = client.get(_status_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 200
    participant_ids = [
        participant["participantId"] for participant in response.json()["participants"]
    ]
    assert participant_ids == [HOST_PARTICIPANT_ID]


def test_삭제된_참여자_본인이_상태를_조회하면_404로_응답한다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_participant(db_session, MEMBER_PARTICIPANT_ID)

    response = client.get(_status_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}


def test_삭제된_참여자는_홈_조회의_진행중_미션에서_빠진다(
    client: TestClient, db_session: Session, room: None
) -> None:
    before = client.get(
        HOME_ENDPOINT, params=HOME_PARAMS, headers=auth_headers(MEMBER_USER_ID)
    )
    assert [mission["missionId"] for mission in before.json()["progressMission"]] == [
        COOPERATIVE_MISSION_ID
    ]

    _soft_delete_participant(db_session, MEMBER_PARTICIPANT_ID)

    after = client.get(
        HOME_ENDPOINT, params=HOME_PARAMS, headers=auth_headers(MEMBER_USER_ID)
    )
    assert after.status_code == 200
    assert after.json()["progressMission"] == []


def test_삭제된_참여자는_인원_수에_들어가지_않는다(
    client: TestClient, db_session: Session, room: None
) -> None:
    # 남은 자리를 모두 채워 정원을 만든다.
    db_session.add_all(
        [
            CooperativeMissionParticipant(
                id=10 + index,
                cooperative_mission_progress_id=PROGRESS_ID,
                user_id=CURRENT_USER_ID,
                participant_status=ParticipantStatus.PENDING.value,
                participant_role=ParticipantRole.MEMBER.value,
                joined_at=None,
            )
            for index in range(COOPERATIVE_MISSION_MAX_PARTICIPANTS - 2)
        ]
    )
    db_session.commit()

    full = client.post(
        JOIN_ENDPOINT,
        json={"teamToken": TEAM_TOKEN},
        headers=auth_headers(OUTSIDER_USER_ID),
    )
    assert full.status_code == 409
    assert full.json() == {"code": "COOPERATIVE_MISSION_FULL"}

    # 한 명을 삭제하면 자리가 하나 비어야 한다.
    _soft_delete_participant(db_session, MEMBER_PARTICIPANT_ID)

    response = client.post(
        JOIN_ENDPOINT,
        json={"teamToken": TEAM_TOKEN},
        headers=auth_headers(OUTSIDER_USER_ID),
    )
    assert response.status_code == 201


def test_방장_참여자가_삭제되면_이어하기가_아니라_새_방을_만든다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_participant(db_session, HOST_PARTICIPANT_ID)

    response = client.post(START_ENDPOINT, headers=auth_headers(CURRENT_USER_ID))

    # 기존 방을 이어받지 않으므로 201(신규)이고 진행도 id도 다르다.
    assert response.status_code == 201
    assert response.json()["missionProgressId"] != PROGRESS_ID


def test_삭제된_참여자는_수락_대기로_잡히지_않는다(
    client: TestClient, db_session: Session, room: None
) -> None:
    # 수락 대기 팀원이 남아 있으면 2단계로 넘어갈 수 없다.
    participant = db_session.get(CooperativeMissionParticipant, MEMBER_PARTICIPANT_ID)
    assert participant is not None
    participant.participant_status = ParticipantStatus.PENDING.value
    db_session.commit()

    blocked = client.patch(
        _status_endpoint(),
        json={"currentStep": 2},
        headers=auth_headers(CURRENT_USER_ID),
    )
    assert blocked.status_code == 409
    assert blocked.json() == {"code": "COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS"}

    _soft_delete_participant(db_session, MEMBER_PARTICIPANT_ID)

    response = client.patch(
        _status_endpoint(),
        json={"currentStep": 2},
        headers=auth_headers(CURRENT_USER_ID),
    )
    assert response.status_code == 204


def test_삭제된_방장은_더_이상_방장_권한이_없다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_participant(db_session, HOST_PARTICIPANT_ID)

    response = client.patch(
        _status_endpoint(),
        json={"currentStep": 2},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 403
    assert response.json() == {"code": "COOPERATIVE_MISSION_HOST_ONLY"}


# ---------------------------------------------------------------------
# 진행도 소프트 삭제
# ---------------------------------------------------------------------


def test_삭제된_진행도는_상태_조회에서_404로_응답한다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_progress(db_session)

    response = client.get(_status_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_삭제된_진행도는_홈_조회의_진행중_미션에서_빠진다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_progress(db_session)

    response = client.get(
        HOME_ENDPOINT, params=HOME_PARAMS, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 200
    assert response.json()["progressMission"] == []


def test_삭제된_진행도의_팀_토큰으로는_참여할_수_없다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_progress(db_session)

    response = client.post(
        JOIN_ENDPOINT,
        json={"teamToken": TEAM_TOKEN},
        headers=auth_headers(OUTSIDER_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "INVALID_INVITE_TOKEN"}


def test_삭제된_진행도는_이어하기_대상이_아니다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_progress(db_session)

    response = client.post(START_ENDPOINT, headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 201
    assert response.json()["missionProgressId"] != PROGRESS_ID


def test_삭제된_진행도는_단계를_바꿀_수_없다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _soft_delete_progress(db_session)

    response = client.patch(
        _status_endpoint(),
        json={"currentStep": 2},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


# ---------------------------------------------------------------------
# 역할 진행도 소프트 삭제
# ---------------------------------------------------------------------


def test_삭제된_역할_진행도는_상태_조회에서_빠진다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _add_role_progress(
        db_session, role_progress_id=ROLE_PROGRESS_ID, participant_id=HOST_PARTICIPANT_ID
    )
    _set_step(db_session, 2)

    before = client.get(_status_endpoint(), headers=auth_headers(CURRENT_USER_ID))
    assert before.json()["totalRoleCount"] == 1

    _soft_delete_role_progress(db_session, ROLE_PROGRESS_ID)

    after = client.get(_status_endpoint(), headers=auth_headers(CURRENT_USER_ID))
    assert after.status_code == 200
    assert after.json()["roleProgresses"] == []
    assert after.json()["totalRoleCount"] == 0


def test_역할_진행도가_삭제된_참가자는_역할이_없는_것으로_본다(
    client: TestClient, db_session: Session, room: None
) -> None:
    # 두 참가자 모두 역할을 받아야 3단계로 넘어갈 수 있다.
    _add_role_progress(
        db_session, role_progress_id=ROLE_PROGRESS_ID, participant_id=HOST_PARTICIPANT_ID
    )
    _add_role_progress(
        db_session,
        role_progress_id=ROLE_PROGRESS_ID + 1,
        participant_id=MEMBER_PARTICIPANT_ID,
    )
    _set_step(db_session, 2)

    _soft_delete_role_progress(db_session, ROLE_PROGRESS_ID + 1)

    response = client.patch(
        _status_endpoint(),
        json={"currentStep": 3},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_PARTICIPANT_ROLE_REQUIRED"}


def test_삭제된_역할_진행도는_사진_인증_대상이_아니다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _add_role_progress(
        db_session, role_progress_id=ROLE_PROGRESS_ID, participant_id=HOST_PARTICIPANT_ID
    )
    _set_step(db_session, 3)

    _soft_delete_role_progress(db_session, ROLE_PROGRESS_ID)

    response = client.post(
        _verification_endpoint(),
        files={"itemImage": ("item.png", PNG_BYTES, "image/png")},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_ROLE_PROGRESS_NOT_FOUND"}


def test_삭제된_역할_진행도가_있는_역할_카드는_다시_배정할_수_있다(
    client: TestClient, db_session: Session, room: None
) -> None:
    _add_role_progress(
        db_session, role_progress_id=ROLE_PROGRESS_ID, participant_id=HOST_PARTICIPANT_ID
    )
    _set_step(db_session, 2)

    _soft_delete_role_progress(db_session, ROLE_PROGRESS_ID)

    response = client.put(
        _role_assignment_endpoint(),
        json={"participantId": MEMBER_PARTICIPANT_ID},
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 204

    # 삭제된 행을 되살리지 않고 새 역할 진행도를 만든다.
    db_session.expire_all()
    alive = db_session.scalars(
        select(CooperativeRoleProgress).where(
            CooperativeRoleProgress.deleted_at.is_(None)
        )
    ).all()
    assert len(alive) == 1
    assert alive[0].id != ROLE_PROGRESS_ID
    assert alive[0].participant_id == MEMBER_PARTICIPANT_ID
