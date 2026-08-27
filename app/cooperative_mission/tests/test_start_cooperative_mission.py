"""POST /api/v1/cooperative-missions/{cooperativeMissionId}/progress
- 협동 미션 시작하기/이어하기 테스트.

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
    CooperativeRoleCard,
    CooperativeRoleProgress,
    MissionStatus,
    ParticipantRole,
    ParticipantStatus,
)
from app.map.models import Location
from app.mission.models import Mission
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash


COOPERATIVE_TYPE_ID = 1
COOPERATIVE_MISSION_ID = 11
OTHER_COOPERATIVE_MISSION_ID = 12
LOCATION_ID = 1

OTHER_USER_ID = 2
THIRD_USER_ID = 3

CURRENT_USER_NICKNAME = "몽글몽글파도"
OTHER_USER_NICKNAME = "한라봉주스"

ROLE_CARD_COUNT = 6


def _endpoint(cooperative_mission_id: object) -> str:
    return f"/api/v1/cooperative-missions/{cooperative_mission_id}/progress"


@pytest.fixture
def cooperative_data(db_session: Session) -> None:
    """협동 미션 / 역할 카드 / 사용자 목업 데이터."""
    db_session.add_all(
        [
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="일행과 역할을 나눠 귤나무를 완성해보세요!",
                step_detail=[{"step": 1, "step_title": "일행 초대하기", "description": "설명"}],
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
                nickname=CURRENT_USER_NICKNAME,
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname=OTHER_USER_NICKNAME,
                point=0,
            ),
            User(
                id=THIRD_USER_ID,
                access_token_hash=access_token_hash(THIRD_USER_ID),
                nickname="오름러버",
                point=0,
            ),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=LOCATION_ID,
                reward_detail={},
            ),
            CooperativeMission(
                id=OTHER_COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=LOCATION_ID,
                reward_detail={},
            ),
        ]
    )
    # 역할 카드는 특정 미션에 속하지 않는 공통 마스터 데이터다.
    db_session.add_all(
        [
            CooperativeRoleCard(
                id=index,
                role_name=f"역할{index}",
                role_description=f"역할{index} 설명입니다.",
                location_to_find=[f"장소{index}-1", f"장소{index}-2"],
            )
            for index in range(1, ROLE_CARD_COUNT + 1)
        ]
    )
    db_session.commit()


def _add_progress(
    db_session: Session,
    *,
    progress_id: int,
    cooperative_mission_id: int = COOPERATIVE_MISSION_ID,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
    current_step: int = 1,
    team_token: str | None = None,
) -> CooperativeMissionProgress:
    progress = CooperativeMissionProgress(
        id=progress_id,
        cooperative_mission_id=cooperative_mission_id,
        current_step=current_step,
        mission_status=status.value,
        team_token=team_token or f"team-token-{progress_id}",
        completed_at=(
            datetime(2026, 8, 20, 12, 0, 0) if status is MissionStatus.COMPLETED else None
        ),
    )
    db_session.add(progress)
    db_session.commit()
    return progress


def _add_participant(
    db_session: Session,
    *,
    participant_id: int,
    progress_id: int,
    user_id: int,
    role: ParticipantRole,
    status: ParticipantStatus = ParticipantStatus.ACCEPTED,
) -> None:
    db_session.add(
        CooperativeMissionParticipant(
            id=participant_id,
            cooperative_mission_progress_id=progress_id,
            user_id=user_id,
            participant_status=status.value,
            participant_role=role.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
    )
    db_session.commit()


def _progresses(db_session: Session) -> list[CooperativeMissionProgress]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(CooperativeMissionProgress).order_by(CooperativeMissionProgress.id)
        ).all()
    )


def _participants(db_session: Session) -> list[CooperativeMissionParticipant]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(CooperativeMissionParticipant).order_by(CooperativeMissionParticipant.id)
        ).all()
    )


# ---------------------------------------------------------------------
# 신규 생성 (BUSINESS_RULES 3.)
# ---------------------------------------------------------------------


def test_처음_시작하면_201로_응답하고_명세의_필드를_모두_반환한다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "missionProgressId",
        "missionProgressStatus",
        "currentStep",
        "teamToken",
        "participants",
        "roleCards",
        "roleProgresses",
    }
    assert body["missionProgressStatus"] == "IN_PROGRESS"
    assert body["currentStep"] == 1
    # 역할을 아직 배정하지 않았으므로 null 이 아니라 빈 배열이다.
    assert body["roleProgresses"] == []


def test_진행도와_방장_참여자를_함께_생성한다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    body = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()

    progresses = _progresses(db_session)
    assert len(progresses) == 1
    progress = progresses[0]
    assert progress.id == body["missionProgressId"]
    assert progress.cooperative_mission_id == COOPERATIVE_MISSION_ID
    assert progress.current_step == 1
    assert progress.mission_status == MissionStatus.IN_PROGRESS.value
    assert progress.completed_at is None
    # 보상은 이 API가 다루지 않는다.
    assert progress.ar_character_reward_granted is False
    assert progress.point_reward_granted is False
    assert progress.coupon_reward_granted is False

    participants = _participants(db_session)
    assert len(participants) == 1
    host = participants[0]
    assert host.cooperative_mission_progress_id == progress.id
    assert host.user_id == CURRENT_USER_ID
    assert host.participant_role == ParticipantRole.HOST.value
    assert host.participant_status == ParticipantStatus.ACCEPTED.value
    assert host.joined_at is not None


def test_신규_응답의_참여자는_방장_한_명이다(
    client: TestClient, cooperative_data: None
) -> None:
    body = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()

    assert body["participants"] == [
        {
            "participantId": body["participants"][0]["participantId"],
            "name": CURRENT_USER_NICKNAME,
            "participantRole": "HOST",
            "participantStatus": "ACCEPTED",
        }
    ]


def test_저장된_팀_토큰을_그대로_반환한다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    # 초대 URL 조합은 프론트 책임이라 백엔드는 토큰만 내려준다.
    body = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()

    progress = _progresses(db_session)[0]
    assert body["teamToken"] == progress.team_token
    # 완성된 URL 을 만들거나 저장하지 않는다.
    assert "http" not in body["teamToken"]
    assert "/cooperative-missions/invite" not in body["teamToken"]


def test_팀_토큰은_방마다_다르게_생성된다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    client.post(_endpoint(COOPERATIVE_MISSION_ID))
    client.post(_endpoint(OTHER_COOPERATIVE_MISSION_ID))

    tokens = {progress.team_token for progress in _progresses(db_session)}
    assert len(tokens) == 2


# ---------------------------------------------------------------------
# 이어하기 (BUSINESS_RULES 4.)
# ---------------------------------------------------------------------


def test_방장으로_진행_중인_방이_있으면_200으로_이어서_반환한다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    progress = _add_progress(db_session, progress_id=1, current_step=3)
    _add_participant(
        db_session, participant_id=1, progress_id=1, user_id=CURRENT_USER_ID, role=ParticipantRole.HOST
    )

    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 200
    body = response.json()
    assert body["missionProgressId"] == 1
    assert body["currentStep"] == 3
    # 새 진행도나 참여자를 만들지 않는다.
    assert len(_progresses(db_session)) == 1
    assert len(_participants(db_session)) == 1
    # 팀 토큰도 그대로라 기존 초대 링크가 계속 유효하다.
    assert body["teamToken"] == progress.team_token


def test_시작_API를_두_번_호출해도_방은_하나만_생긴다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    first = client.post(_endpoint(COOPERATIVE_MISSION_ID))
    second = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["missionProgressId"] == second.json()["missionProgressId"]
    assert first.json()["teamToken"] == second.json()["teamToken"]
    assert len(_progresses(db_session)) == 1
    assert len(_participants(db_session)) == 1


def test_참여자는_방장을_먼저_두고_참여한_순서로_반환한다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    _add_progress(db_session, progress_id=1)
    # 방장을 일부러 마지막 id로 넣어 정렬이 id 순이 아님을 드러낸다.
    _add_participant(
        db_session,
        participant_id=1,
        progress_id=1,
        user_id=OTHER_USER_ID,
        role=ParticipantRole.MEMBER,
    )
    _add_participant(
        db_session,
        participant_id=2,
        progress_id=1,
        user_id=THIRD_USER_ID,
        role=ParticipantRole.MEMBER,
        status=ParticipantStatus.PENDING,
    )
    _add_participant(
        db_session,
        participant_id=3,
        progress_id=1,
        user_id=CURRENT_USER_ID,
        role=ParticipantRole.HOST,
    )

    body = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()

    assert [participant["participantId"] for participant in body["participants"]] == [3, 1, 2]
    assert body["participants"][0]["participantRole"] == "HOST"
    # 아직 수락하지 않은 참여 요청도 포함한다.
    assert body["participants"][2]["participantStatus"] == "PENDING"


def test_역할_진행도가_있으면_참여자와_역할_카드_정보를_함께_반환한다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    _add_progress(db_session, progress_id=1, current_step=3)
    _add_participant(
        db_session, participant_id=1, progress_id=1, user_id=CURRENT_USER_ID, role=ParticipantRole.HOST
    )
    _add_participant(
        db_session,
        participant_id=2,
        progress_id=1,
        user_id=OTHER_USER_ID,
        role=ParticipantRole.MEMBER,
    )
    db_session.add_all(
        [
            CooperativeRoleProgress(
                id=31,
                participant_id=1,
                cooperative_role_card_id=1,
                item_img_url="https://example.com/role/31.jpg",
                progress_status=MissionStatus.COMPLETED.value,
                completed_at=datetime(2026, 8, 20, 13, 0, 0),
            ),
            CooperativeRoleProgress(
                id=32,
                participant_id=2,
                cooperative_role_card_id=2,
                item_img_url=None,
                progress_status=MissionStatus.IN_PROGRESS.value,
            ),
        ]
    )
    db_session.commit()

    body = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()

    assert body["roleProgresses"] == [
        {
            "roleProgressId": 31,
            "participantId": 1,
            "participantName": CURRENT_USER_NICKNAME,
            "roleCardId": 1,
            "roleName": "역할1",
            "progressStatus": "COMPLETED",
            "itemImgUrl": "https://example.com/role/31.jpg",
        },
        {
            "roleProgressId": 32,
            "participantId": 2,
            "participantName": OTHER_USER_NICKNAME,
            "roleCardId": 2,
            "roleName": "역할2",
            "progressStatus": "IN_PROGRESS",
            "itemImgUrl": None,
        },
    ]


def test_다른_방의_역할_진행도는_포함하지_않는다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    _add_progress(db_session, progress_id=1)
    _add_participant(
        db_session, participant_id=1, progress_id=1, user_id=CURRENT_USER_ID, role=ParticipantRole.HOST
    )
    # 다른 방(진행도 2)의 참여자와 역할 진행도
    _add_progress(db_session, progress_id=2, cooperative_mission_id=OTHER_COOPERATIVE_MISSION_ID)
    _add_participant(
        db_session, participant_id=2, progress_id=2, user_id=OTHER_USER_ID, role=ParticipantRole.HOST
    )
    db_session.add(
        CooperativeRoleProgress(
            id=41,
            participant_id=2,
            cooperative_role_card_id=1,
            progress_status=MissionStatus.IN_PROGRESS.value,
        )
    )
    db_session.commit()

    body = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()

    assert body["roleProgresses"] == []


# ---------------------------------------------------------------------
# 이어하기 대상 판별 (BUSINESS_RULES 2.)
# ---------------------------------------------------------------------


def test_완료된_방만_있으면_새_방을_만든다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    _add_progress(db_session, progress_id=1, status=MissionStatus.COMPLETED, current_step=4)
    _add_participant(
        db_session, participant_id=1, progress_id=1, user_id=CURRENT_USER_ID, role=ParticipantRole.HOST
    )

    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 201
    assert response.json()["currentStep"] == 1
    progresses = _progresses(db_session)
    assert len(progresses) == 2
    # 기존 완료 기록은 그대로 남는다.
    assert progresses[0].mission_status == MissionStatus.COMPLETED.value


def test_다른_방에_MEMBER로_참여_중이면_이어하기_대상이_아니다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    _add_progress(db_session, progress_id=1)
    _add_participant(
        db_session,
        participant_id=1,
        progress_id=1,
        user_id=CURRENT_USER_ID,
        role=ParticipantRole.MEMBER,
    )

    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 201
    assert response.json()["missionProgressId"] != 1
    assert len(_progresses(db_session)) == 2


def test_다른_협동_미션의_진행_중인_방은_이어하기_대상이_아니다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    _add_progress(db_session, progress_id=1, cooperative_mission_id=OTHER_COOPERATIVE_MISSION_ID)
    _add_participant(
        db_session, participant_id=1, progress_id=1, user_id=CURRENT_USER_ID, role=ParticipantRole.HOST
    )

    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 201
    assert response.json()["missionProgressId"] != 1


def test_다른_사용자가_방장인_방은_이어하기_대상이_아니다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    _add_progress(db_session, progress_id=1)
    _add_participant(
        db_session, participant_id=1, progress_id=1, user_id=OTHER_USER_ID, role=ParticipantRole.HOST
    )

    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 201
    assert response.json()["missionProgressId"] != 1


# ---------------------------------------------------------------------
# 역할 카드 (BUSINESS_RULES 5.)
# ---------------------------------------------------------------------


def test_역할_카드는_공통_마스터_전체를_id_순서로_반환한다(
    client: TestClient, cooperative_data: None
) -> None:
    body = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()

    role_cards = body["roleCards"]
    assert len(role_cards) == ROLE_CARD_COUNT
    assert [card["roleCardId"] for card in role_cards] == list(range(1, ROLE_CARD_COUNT + 1))
    assert role_cards[0] == {
        "roleCardId": 1,
        "roleName": "역할1",
        "roleDescription": "역할1 설명입니다.",
        "locationToFind": ["장소1-1", "장소1-2"],
    }


def test_역할_카드는_미션과_무관하게_같은_목록을_반환한다(
    client: TestClient, cooperative_data: None
) -> None:
    first = client.post(_endpoint(COOPERATIVE_MISSION_ID)).json()
    second = client.post(_endpoint(OTHER_COOPERATIVE_MISSION_ID)).json()

    assert first["roleCards"] == second["roleCards"]


def test_진행도_생성이_역할_카드를_복사하지_않는다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    client.post(_endpoint(COOPERATIVE_MISSION_ID))

    db_session.expire_all()
    role_cards = db_session.scalars(select(CooperativeRoleCard)).all()
    assert len(role_cards) == ROLE_CARD_COUNT


def test_역할_카드_마스터가_없으면_500으로_응답하고_방을_만들지_않는다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    db_session.query(CooperativeRoleCard).delete()
    db_session.commit()

    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}


# ---------------------------------------------------------------------
# 오류
# ---------------------------------------------------------------------


def test_협동_미션이_없으면_404로_응답하고_방을_만들지_않는다(
    client: TestClient, db_session: Session, cooperative_data: None
) -> None:
    response = client.post(_endpoint(999))

    assert response.status_code == 404
    assert response.json() == {"code": "COOPERATIVE_MISSION_NOT_FOUND"}
    assert _progresses(db_session) == []
    assert _participants(db_session) == []


def test_방장_참여자_저장이_실패하면_진행도도_저장되지_않는다(
    client: TestClient,
    db_session: Session,
    cooperative_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 진행도만 남고 방장이 없는 방이 생기면 안 된다.
    def boom(self: Session) -> None:
        raise RuntimeError("커밋 실패")

    monkeypatch.setattr(Session, "commit", boom)

    response = client.post(_endpoint(COOPERATIVE_MISSION_ID))

    assert response.status_code == 500
    assert _progresses(db_session) == []
    assert _participants(db_session) == []


@pytest.mark.parametrize(
    "cooperative_mission_id",
    [
        pytest.param("abc", id="정수가_아닌_id"),
        pytest.param(0, id="0인_id"),
        pytest.param(-1, id="음수_id"),
    ],
)
def test_잘못된_id면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, cooperative_data: None, cooperative_mission_id: object
) -> None:
    response = client.post(_endpoint(cooperative_mission_id))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
