"""DELETE /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/me
- 협동 미션 나가기 테스트.

기준 문서: app/cooperative_mission/docs/API_SPEC_2.md,
          app/cooperative_mission/docs/BUSINESS_RULES_2.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import next_location
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
LOCATION_ID = 1

PROGRESS_ID = 10
TEAM_TOKEN = "mock-team-token-10"

# 현재 사용자(1)가 방장이다.
HOST_PARTICIPANT_ID = 1
MEMBER_USER_ID = 2
MEMBER_PARTICIPANT_ID = 2
LATE_MEMBER_USER_ID = 3
LATE_MEMBER_PARTICIPANT_ID = 3
PENDING_USER_ID = 4
PENDING_PARTICIPANT_ID = 4
OUTSIDER_USER_ID = 5

ROLE_CARD_ID = 1
HOST_ROLE_PROGRESS_ID = 100
MEMBER_ROLE_PROGRESS_ID = 101

AR_CHARACTER_ID = 5
REWARD_POINT = 200
INITIAL_USER_POINT = 30

REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": REWARD_POINT,
    "coupon_location": "협재 바다뷰 카페",
    "coupon_price": 4000,
}

HOST_JOINED_AT = datetime(2026, 8, 20, 10, 0, 0)
MEMBER_JOINED_AT = datetime(2026, 8, 20, 11, 0, 0)
LATE_MEMBER_JOINED_AT = datetime(2026, 8, 20, 12, 0, 0)


def _endpoint(progress_id: object = PROGRESS_ID) -> str:
    return f"/api/v1/cooperative-missions/{progress_id}/participants/me"


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """장소 이미지 조회(TourAPI)를 막아 외부 네트워크를 타지 않게 한다."""
    monkeypatch.setattr(next_location, "get_location_image_url", lambda content_id: None)


@pytest.fixture
def leave_data(db_session: Session) -> None:
    """방장(현재 사용자) + 수락된 팀원 1명이 있는 2단계 방."""
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
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name="협재 파도지기",
                character_description="팀의 사진 미션을 응원하는 캐릭터입니다.",
                character_story_title="이야기 제목",
                acquire_condition="협동 미션을 완료하면 만날 수 있어요.",
                character_img_url="https://example.com/characters/wave.png",
                hashtags=["#협동"],
            ),
            CooperativeRoleCard(
                id=ROLE_CARD_ID,
                role_name="사진 담당",
                role_description="풍경 사진을 찍어요.",
                location_to_find=["과수원"],
            ),
        ]
    )
    for user_id, nickname in (
        (CURRENT_USER_ID, "나민"),
        (MEMBER_USER_ID, "이서연"),
        (LATE_MEMBER_USER_ID, "김민우"),
        (PENDING_USER_ID, "박도윤"),
        (OUTSIDER_USER_ID, "최하늘"),
    ):
        db_session.add(
            User(
                id=user_id,
                access_token_hash=access_token_hash(user_id),
                nickname=nickname,
                point=INITIAL_USER_POINT,
            )
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
                joined_at=HOST_JOINED_AT,
            ),
            CooperativeMissionParticipant(
                id=MEMBER_PARTICIPANT_ID,
                cooperative_mission_progress_id=PROGRESS_ID,
                user_id=MEMBER_USER_ID,
                participant_status=ParticipantStatus.ACCEPTED.value,
                participant_role=ParticipantRole.MEMBER.value,
                joined_at=MEMBER_JOINED_AT,
            ),
        ]
    )
    db_session.commit()


def _add_participant(
    db_session: Session,
    *,
    participant_id: int,
    user_id: int,
    participant_status: ParticipantStatus = ParticipantStatus.ACCEPTED,
    participant_role: ParticipantRole = ParticipantRole.MEMBER,
    joined_at: datetime | None = LATE_MEMBER_JOINED_AT,
) -> None:
    db_session.add(
        CooperativeMissionParticipant(
            id=participant_id,
            cooperative_mission_progress_id=PROGRESS_ID,
            user_id=user_id,
            participant_status=participant_status.value,
            participant_role=participant_role.value,
            joined_at=joined_at,
        )
    )
    db_session.commit()


def _add_role_progress(
    db_session: Session,
    *,
    role_progress_id: int,
    participant_id: int,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
    item_img_url: str | None = None,
) -> None:
    db_session.add(
        CooperativeRoleProgress(
            id=role_progress_id,
            participant_id=participant_id,
            cooperative_role_card_id=ROLE_CARD_ID,
            item_img_url=item_img_url,
            progress_status=status.value,
            completed_at=datetime(2026, 8, 21, 9, 0, 0)
            if status is MissionStatus.COMPLETED
            else None,
        )
    )
    db_session.commit()


def _participant(db_session: Session, participant_id: int) -> CooperativeMissionParticipant:
    db_session.expire_all()
    participant = db_session.get(CooperativeMissionParticipant, participant_id)
    assert participant is not None
    return participant


def _progress(db_session: Session) -> CooperativeMissionProgress:
    db_session.expire_all()
    progress = db_session.get(CooperativeMissionProgress, PROGRESS_ID)
    assert progress is not None
    return progress


def _alive_participant_ids(db_session: Session) -> list[int]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(CooperativeMissionParticipant.id)
            .where(
                CooperativeMissionParticipant.cooperative_mission_progress_id == PROGRESS_ID,
                CooperativeMissionParticipant.deleted_at.is_(None),
            )
            .order_by(CooperativeMissionParticipant.id)
        ).all()
    )


def _alive_role_progress_ids(db_session: Session) -> list[int]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(CooperativeRoleProgress.id)
            .where(CooperativeRoleProgress.deleted_at.is_(None))
            .order_by(CooperativeRoleProgress.id)
        ).all()
    )


# ---------------------------------------------------------------------
# 정상 응답
# ---------------------------------------------------------------------


def test_나가기에_성공하면_200과_진행도_id를_반환한다(
    client: TestClient, leave_data: None
) -> None:
    response = client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert response.status_code == 200
    assert response.json()["missionProgressId"] == PROGRESS_ID


def test_보상은_지급하지_않고_세_항목을_모두_null로_반환한다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    response = client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert response.status_code == 200
    # 키는 유지하고 값만 비운다. (프론트가 완료 화면과 같은 구조로 처리한다)
    assert response.json()["reward"] == {
        "arCharacter": None,
        "point": None,
        "coupon": None,
    }

    # 실제 지급도 없어야 한다.
    db_session.expire_all()
    user = db_session.get(User, MEMBER_USER_ID)
    assert user is not None
    assert user.point == INITIAL_USER_POINT
    assert db_session.scalars(select(AcquiredArCharacter)).all() == []

    progress = _progress(db_session)
    assert progress.ar_character_reward_granted is False
    assert progress.point_reward_granted is False
    assert progress.coupon_reward_granted is False


def test_다음_장소를_추천해_함께_반환한다(
    client: TestClient, leave_data: None
) -> None:
    response = client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert response.status_code == 200
    next_location_response = response.json()["nextLocation"]
    assert next_location_response is not None
    # 목업에 장소가 하나뿐이라 그 장소가 추천된다.
    assert next_location_response["id"] == LOCATION_ID
    assert next_location_response["locationTitle"] == "종화네 과수원"


def test_추천할_장소가_없으면_nextLocation이_null이다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    # 추천은 LOCATION 중 하나를 고르므로 장소가 하나도 없어야 null 이 된다.
    db_session.execute(Location.__table__.delete())
    db_session.commit()

    response = client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert response.status_code == 200
    assert response.json()["nextLocation"] is None


# ---------------------------------------------------------------------
# 일반 팀원 / 대기 참가자 나가기 (BUSINESS_RULES_2 4.)
# ---------------------------------------------------------------------


def test_일반_팀원이_나가면_본인만_소프트_삭제된다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert _alive_participant_ids(db_session) == [HOST_PARTICIPANT_ID]

    # 행은 남기고 deleted_at 만 채운다. 상태 값은 건드리지 않는다.
    left = _participant(db_session, MEMBER_PARTICIPANT_ID)
    assert left.deleted_at is not None
    assert left.participant_status == ParticipantStatus.ACCEPTED.value
    assert left.participant_role == ParticipantRole.MEMBER.value


def test_일반_팀원이_나가면_그_팀원의_역할_진행도도_소프트_삭제된다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    _add_role_progress(
        db_session,
        role_progress_id=HOST_ROLE_PROGRESS_ID,
        participant_id=HOST_PARTICIPANT_ID,
    )
    _add_role_progress(
        db_session,
        role_progress_id=MEMBER_ROLE_PROGRESS_ID,
        participant_id=MEMBER_PARTICIPANT_ID,
    )

    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    # 나간 팀원의 역할만 빠지고 방장 역할은 그대로다.
    assert _alive_role_progress_ids(db_session) == [HOST_ROLE_PROGRESS_ID]
    db_session.expire_all()
    deleted = db_session.get(CooperativeRoleProgress, MEMBER_ROLE_PROGRESS_ID)
    assert deleted is not None
    assert deleted.deleted_at is not None


def test_일반_팀원이_나가도_단계와_상태는_그대로다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    progress = _progress(db_session)
    assert progress.current_step == 2
    assert progress.mission_status == MissionStatus.IN_PROGRESS.value
    assert progress.completed_at is None
    assert progress.deleted_at is None
    assert progress.team_token == TEAM_TOKEN


def test_대기_중인_참가자도_나가기로_참여_요청을_취소할_수_있다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    _add_participant(
        db_session,
        participant_id=PENDING_PARTICIPANT_ID,
        user_id=PENDING_USER_ID,
        participant_status=ParticipantStatus.PENDING,
        joined_at=None,
    )

    response = client.delete(_endpoint(), headers=auth_headers(PENDING_USER_ID))

    assert response.status_code == 200
    assert _alive_participant_ids(db_session) == [
        HOST_PARTICIPANT_ID,
        MEMBER_PARTICIPANT_ID,
    ]
    assert _participant(db_session, PENDING_PARTICIPANT_ID).deleted_at is not None


def test_대기_참가자가_나가도_방장만_남은_방은_유지된다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    # 수락된 참가자가 방장 한 명뿐인 방에 대기 참가자를 붙인다.
    member = _participant(db_session, MEMBER_PARTICIPANT_ID)
    db_session.delete(member)
    db_session.commit()
    _add_participant(
        db_session,
        participant_id=PENDING_PARTICIPANT_ID,
        user_id=PENDING_USER_ID,
        participant_status=ParticipantStatus.PENDING,
        joined_at=None,
    )

    response = client.delete(_endpoint(), headers=auth_headers(PENDING_USER_ID))

    assert response.status_code == 200
    # 마지막 참가자 판정은 ACCEPTED 만 센다. 대기 참가자가 나갔다고 방을 지우면 안 된다.
    assert _progress(db_session).deleted_at is None
    assert _alive_participant_ids(db_session) == [HOST_PARTICIPANT_ID]
    assert (
        _participant(db_session, HOST_PARTICIPANT_ID).participant_role
        == ParticipantRole.HOST.value
    )


def test_역할_사진의_Blob_URL은_지우지_않는다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    item_img_url = "https://example.com/blob/role/1.png"
    _add_role_progress(
        db_session,
        role_progress_id=MEMBER_ROLE_PROGRESS_ID,
        participant_id=MEMBER_PARTICIPANT_ID,
        status=MissionStatus.COMPLETED,
        item_img_url=item_img_url,
    )

    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    db_session.expire_all()
    role_progress = db_session.get(CooperativeRoleProgress, MEMBER_ROLE_PROGRESS_ID)
    assert role_progress is not None
    assert role_progress.deleted_at is not None
    # 이력 확인을 위해 사진 정보는 그대로 둔다.
    assert role_progress.item_img_url == item_img_url
    assert role_progress.progress_status == MissionStatus.COMPLETED.value


# ---------------------------------------------------------------------
# 방장 나가기와 승계 (BUSINESS_RULES_2 5.)
# ---------------------------------------------------------------------


def test_방장이_나가면_남은_팀원이_방장을_승계한다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    response = client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 200
    assert _alive_participant_ids(db_session) == [MEMBER_PARTICIPANT_ID]

    new_host = _participant(db_session, MEMBER_PARTICIPANT_ID)
    assert new_host.participant_role == ParticipantRole.HOST.value
    # 승계는 역할만 바꾼다. 참여 시각은 그대로다.
    assert new_host.joined_at == MEMBER_JOINED_AT

    left_host = _participant(db_session, HOST_PARTICIPANT_ID)
    assert left_host.deleted_at is not None


def test_방장을_승계해도_진행도는_그대로_유지된다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    progress = _progress(db_session)
    assert progress.deleted_at is None
    assert progress.current_step == 2
    assert progress.mission_status == MissionStatus.IN_PROGRESS.value
    assert progress.team_token == TEAM_TOKEN


def test_방장의_역할_진행도도_함께_소프트_삭제된다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    _add_role_progress(
        db_session,
        role_progress_id=HOST_ROLE_PROGRESS_ID,
        participant_id=HOST_PARTICIPANT_ID,
    )
    _add_role_progress(
        db_session,
        role_progress_id=MEMBER_ROLE_PROGRESS_ID,
        participant_id=MEMBER_PARTICIPANT_ID,
    )

    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert _alive_role_progress_ids(db_session) == [MEMBER_ROLE_PROGRESS_ID]


def test_승계는_먼저_참여한_ACCEPTED_팀원을_고른다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    # 나중에 들어온 팀원을 추가한다. 승계는 먼저 들어온 2번이어야 한다.
    _add_participant(
        db_session,
        participant_id=LATE_MEMBER_PARTICIPANT_ID,
        user_id=LATE_MEMBER_USER_ID,
        joined_at=LATE_MEMBER_JOINED_AT,
    )

    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert (
        _participant(db_session, MEMBER_PARTICIPANT_ID).participant_role
        == ParticipantRole.HOST.value
    )
    assert (
        _participant(db_session, LATE_MEMBER_PARTICIPANT_ID).participant_role
        == ParticipantRole.MEMBER.value
    )


def test_참여_시각이_같으면_참가자_id가_작은_쪽이_승계한다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    _add_participant(
        db_session,
        participant_id=LATE_MEMBER_PARTICIPANT_ID,
        user_id=LATE_MEMBER_USER_ID,
        joined_at=MEMBER_JOINED_AT,
    )

    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert (
        _participant(db_session, MEMBER_PARTICIPANT_ID).participant_role
        == ParticipantRole.HOST.value
    )


def test_PENDING_참가자는_방장을_승계하지_않는다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    # 수락된 팀원을 지우고 대기 참가자만 남긴다.
    member = _participant(db_session, MEMBER_PARTICIPANT_ID)
    db_session.delete(member)
    db_session.commit()
    _add_participant(
        db_session,
        participant_id=PENDING_PARTICIPANT_ID,
        user_id=PENDING_USER_ID,
        participant_status=ParticipantStatus.PENDING,
        joined_at=None,
    )

    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    # 승계 대상이 없으므로 방 전체가 삭제되고 대기 참가자도 함께 정리된다.
    assert _progress(db_session).deleted_at is not None
    assert _alive_participant_ids(db_session) == []
    assert _participant(db_session, PENDING_PARTICIPANT_ID).deleted_at is not None


# ---------------------------------------------------------------------
# 마지막 참가자 나가기 (BUSINESS_RULES_2 6.)
# ---------------------------------------------------------------------


def test_마지막_ACCEPTED_참가자가_나가면_방_전체가_소프트_삭제된다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    # 팀원이 먼저 나가고 방장 혼자 남은 상태를 만든다.
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    response = client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 200
    assert _progress(db_session).deleted_at is not None
    assert _alive_participant_ids(db_session) == []


def test_방_전체를_삭제해도_완료_처리하지_않는다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))
    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    progress = _progress(db_session)
    assert progress.mission_status == MissionStatus.IN_PROGRESS.value
    assert progress.current_step == 2
    assert progress.completed_at is None
    assert progress.point_reward_granted is False


def test_방_전체_삭제_시_남은_역할_진행도도_모두_소프트_삭제된다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    _add_role_progress(
        db_session,
        role_progress_id=HOST_ROLE_PROGRESS_ID,
        participant_id=HOST_PARTICIPANT_ID,
    )
    _add_participant(
        db_session,
        participant_id=PENDING_PARTICIPANT_ID,
        user_id=PENDING_USER_ID,
        participant_status=ParticipantStatus.PENDING,
        joined_at=None,
    )
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert _alive_role_progress_ids(db_session) == []
    # 남아 있던 PENDING 참가자도 함께 정리된다.
    assert _participant(db_session, PENDING_PARTICIPANT_ID).deleted_at is not None


def test_삭제된_방은_상태_조회에서_404가_된다(
    client: TestClient, leave_data: None
) -> None:
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))
    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    response = client.get(
        f"/api/v1/cooperative-missions/{PROGRESS_ID}/progress",
        headers=auth_headers(CURRENT_USER_ID),
    )

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


# ---------------------------------------------------------------------
# 3단계에서 나가기 (BUSINESS_RULES_2 7.)
# ---------------------------------------------------------------------


def test_3단계에서_나가도_단계를_되돌리지_않는다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    progress = _progress(db_session)
    progress.current_step = 3
    db_session.commit()
    _add_role_progress(
        db_session,
        role_progress_id=MEMBER_ROLE_PROGRESS_ID,
        participant_id=MEMBER_PARTICIPANT_ID,
        status=MissionStatus.COMPLETED,
        item_img_url="https://example.com/blob/role/1.png",
    )

    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert _progress(db_session).current_step == 3
    # 인증까지 마친 역할이어도 삭제되어 집계에서 빠진다.
    assert _alive_role_progress_ids(db_session) == []


def test_3단계에서_나간_역할은_집계에서_빠진다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    progress = _progress(db_session)
    progress.current_step = 3
    db_session.commit()
    _add_role_progress(
        db_session,
        role_progress_id=HOST_ROLE_PROGRESS_ID,
        participant_id=HOST_PARTICIPANT_ID,
    )
    _add_role_progress(
        db_session,
        role_progress_id=MEMBER_ROLE_PROGRESS_ID,
        participant_id=MEMBER_PARTICIPANT_ID,
        status=MissionStatus.COMPLETED,
    )

    before = client.get(
        f"/api/v1/cooperative-missions/{PROGRESS_ID}/progress",
        headers=auth_headers(CURRENT_USER_ID),
    )
    assert before.json()["totalRoleCount"] == 2
    assert before.json()["completedRoleCount"] == 1

    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    after = client.get(
        f"/api/v1/cooperative-missions/{PROGRESS_ID}/progress",
        headers=auth_headers(CURRENT_USER_ID),
    )
    assert after.json()["totalRoleCount"] == 1
    assert after.json()["completedRoleCount"] == 0


# ---------------------------------------------------------------------
# 404 / 409
# ---------------------------------------------------------------------


def test_진행도가_없으면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, leave_data: None
) -> None:
    response = client.delete(_endpoint(999), headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_이미_삭제된_방이면_404_PROGRESS_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))
    client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    response = client.delete(_endpoint(), headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"}


def test_방의_참가자가_아니면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    response = client.delete(_endpoint(), headers=auth_headers(OUTSIDER_USER_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}
    # 아무도 나가지 않아야 한다.
    assert _alive_participant_ids(db_session) == [
        HOST_PARTICIPANT_ID,
        MEMBER_PARTICIPANT_ID,
    ]


def test_이미_나간_사용자가_다시_요청하면_404_PARTICIPANT_NOT_FOUND로_응답한다(
    client: TestClient, leave_data: None
) -> None:
    client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    response = client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"}


@pytest.mark.parametrize(
    ("mission_status", "current_step"),
    [
        pytest.param(MissionStatus.COMPLETED, 4, id="완료_상태이고_4단계"),
        pytest.param(MissionStatus.IN_PROGRESS, 4, id="4단계"),
        pytest.param(MissionStatus.COMPLETED, 3, id="완료_상태"),
    ],
)
def test_이미_완료된_방이면_409로_응답하고_아무도_나가지_않는다(
    client: TestClient,
    db_session: Session,
    leave_data: None,
    mission_status: MissionStatus,
    current_step: int,
) -> None:
    progress = _progress(db_session)
    progress.mission_status = mission_status.value
    progress.current_step = current_step
    db_session.commit()

    response = client.delete(_endpoint(), headers=auth_headers(MEMBER_USER_ID))

    assert response.status_code == 409
    assert response.json() == {"code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"}
    assert _alive_participant_ids(db_session) == [
        HOST_PARTICIPANT_ID,
        MEMBER_PARTICIPANT_ID,
    ]
    assert _progress(db_session).deleted_at is None


# ---------------------------------------------------------------------
# 400 / 401
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "progress_id",
    [
        pytest.param("abc", id="정수가_아님"),
        pytest.param(0, id="0"),
        pytest.param(-1, id="음수"),
    ],
)
def test_path_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, leave_data: None, progress_id: object
) -> None:
    response = client.delete(
        _endpoint(progress_id), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _alive_participant_ids(db_session) == [
        HOST_PARTICIPANT_ID,
        MEMBER_PARTICIPANT_ID,
    ]


def test_토큰의_사용자가_없으면_401로_응답하고_아무도_나가지_않는다(
    client: TestClient, db_session: Session, leave_data: None
) -> None:
    response = client.delete(_endpoint(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _alive_participant_ids(db_session) == [
        HOST_PARTICIPANT_ID,
        MEMBER_PARTICIPANT_ID,
    ]
