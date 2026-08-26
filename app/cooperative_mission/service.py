"""협동 미션 도메인 비즈니스 로직.

기준 문서: app/cooperative_mission/docs/API_SPEC.md,
          app/cooperative_mission/docs/BUSINESS_RULES.md
"""

import secrets
from dataclasses import dataclass
from typing import Any

from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from app.cooperative_mission.schemas import (
    CooperativeMissionStartResponse,
    ParticipantResponse,
    RoleCardResponse,
    RoleProgressResponse,
)
from app.core.errors import NotFoundError
from app.user.models import User


COOPERATIVE_MISSION_NOT_FOUND = "COOPERATIVE_MISSION_NOT_FOUND"

# 신규 진행도 초기값
FIRST_STEP = 1

# 팀 토큰 바이트 수. token_urlsafe(32) 는 약 43자라 VARCHAR(100) 안에 들어간다.
TEAM_TOKEN_BYTES = 32

# team_token UNIQUE 충돌 시 재시도 횟수
MAX_TEAM_TOKEN_ATTEMPTS = 5


@dataclass(frozen=True)
class StartCooperativeMissionResult:
    """협동 미션 시작/이어하기 결과.

    응답 구조는 같지만 상태 코드가 달라서(신규 201 / 이어하기 200)
    진행도를 새로 만들었는지를 라우터에 함께 전달한다.
    """

    response: CooperativeMissionStartResponse
    is_created: bool


def start_cooperative_mission(
    db: Session, current_user_id: int, cooperative_mission_id: int
) -> StartCooperativeMissionResult:
    """협동 미션 시작하기/이어하기.

    - 현재 사용자가 `HOST` 인 `IN_PROGRESS` 진행도가 있으면 그 방을 그대로 반환한다.
    - 없으면 진행도와 방장 참여자를 함께 만든다. (완료된 방만 있으면 새 도전으로 본다)
    - 다른 방에 `MEMBER` 로 참여 중인 기록은 이어하기 대상이 아니다.
    """
    _get_cooperative_mission(db, cooperative_mission_id)

    progress = _find_hosting_progress(db, current_user_id, cooperative_mission_id)
    is_created = progress is None
    if progress is None:
        try:
            progress = _create_progress_with_host(db, current_user_id, cooperative_mission_id)
            db.commit()
        except Exception:
            # 방장 없는 진행도나 진행도 없는 참여자가 남지 않도록 함께 되돌린다.
            db.rollback()
            raise
        db.refresh(progress)

    return StartCooperativeMissionResult(
        response=CooperativeMissionStartResponse(
            mission_progress_id=progress.id,
            mission_progress_status=MissionStatus(progress.mission_status),
            current_step=progress.current_step,
            team_token=progress.team_token,
            participants=_find_participants(db, progress.id),
            role_cards=_find_role_cards(db),
            role_progresses=_find_role_progresses(db, progress.id),
        ),
        is_created=is_created,
    )


def _get_cooperative_mission(db: Session, cooperative_mission_id: int) -> CooperativeMission:
    """협동 미션을 조회한다. 없으면 진행도를 만들지 않고 404."""
    cooperative_mission = db.get(CooperativeMission, cooperative_mission_id)
    if cooperative_mission is None:
        raise NotFoundError(
            COOPERATIVE_MISSION_NOT_FOUND,
            detail=f"협동 미션 {cooperative_mission_id} 을(를) 찾을 수 없습니다.",
        )
    return cooperative_mission


def _find_hosting_progress(
    db: Session, current_user_id: int, cooperative_mission_id: int
) -> CooperativeMissionProgress | None:
    """현재 사용자가 방장인 진행 중 방을 찾는다.

    `MEMBER` 로 참여 중인 방과 이미 완료된 방은 이어하기 대상이 아니다.
    같은 조건의 방은 하나만 있어야 하지만, 여러 건이어도 결과가 흔들리지 않게 가장 먼저 만든 방을 쓴다.
    """
    statement = (
        select(CooperativeMissionProgress)
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.cooperative_mission_progress_id
            == CooperativeMissionProgress.id,
        )
        .where(
            CooperativeMissionProgress.cooperative_mission_id == cooperative_mission_id,
            CooperativeMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_role == ParticipantRole.HOST.value,
        )
        .order_by(CooperativeMissionProgress.id)
    )
    return db.scalars(statement).first()


def _create_progress_with_host(
    db: Session, current_user_id: int, cooperative_mission_id: int
) -> CooperativeMissionProgress:
    """진행도와 방장 참여자를 함께 만든다. (커밋은 호출한 쪽에서 한 번만)

    팀 토큰이 겹쳐 저장에 실패하면 트랜잭션을 되돌리고 새 토큰으로 처음부터 다시 시도한다.
    (SAVEPOINT 는 테스트 DB인 SQLite 에서 신뢰할 수 없어 쓰지 않는다)
    """
    for _ in range(MAX_TEAM_TOKEN_ATTEMPTS):
        progress = CooperativeMissionProgress(
            cooperative_mission_id=cooperative_mission_id,
            current_step=FIRST_STEP,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token=secrets.token_urlsafe(TEAM_TOKEN_BYTES),
            completed_at=None,
        )
        db.add(progress)
        try:
            # 참여자에 넣을 진행도 id 를 얻기 위해 먼저 flush 한다.
            db.flush()
        except IntegrityError:
            # 토큰은 로그에 남기지 않는다. (알면 방 참여 요청 화면에 접근할 수 있다)
            db.rollback()
            continue

        db.add(
            CooperativeMissionParticipant(
                cooperative_mission_progress_id=progress.id,
                user_id=current_user_id,
                participant_status=ParticipantStatus.ACCEPTED.value,
                participant_role=ParticipantRole.HOST.value,
                joined_at=now_kst(),
            )
        )
        return progress

    raise RuntimeError(f"팀 토큰 생성에 {MAX_TEAM_TOKEN_ATTEMPTS}번 연속 실패했습니다.")


def _find_participants(db: Session, progress_id: int) -> list[ParticipantResponse]:
    """참여자 목록을 만든다. 방장을 먼저 두고 나머지는 참여한 순서대로 정렬한다."""
    statement = (
        select(CooperativeMissionParticipant, User.nickname)
        .join(User, User.id == CooperativeMissionParticipant.user_id)
        .where(CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id)
        .order_by(
            case(
                (
                    CooperativeMissionParticipant.participant_role
                    == ParticipantRole.HOST.value,
                    0,
                ),
                else_=1,
            ),
            CooperativeMissionParticipant.created_at,
            CooperativeMissionParticipant.id,
        )
    )
    return [
        ParticipantResponse(
            participant_id=participant.id,
            name=nickname or "",
            participant_role=ParticipantRole(participant.participant_role),
            participant_status=ParticipantStatus(participant.participant_status),
        )
        for participant, nickname in db.execute(statement).all()
    ]


def _find_role_cards(db: Session) -> list[RoleCardResponse]:
    """공통 역할 카드 전체를 id 오름차순으로 반환한다."""
    role_cards = db.scalars(
        select(CooperativeRoleCard).order_by(CooperativeRoleCard.id)
    ).all()
    if not role_cards:
        # 응답을 만들 수 없는 데이터 문제라 공통 500 으로 처리한다.
        raise RuntimeError("협동 미션 역할 카드 마스터 데이터가 없습니다.")

    return [
        RoleCardResponse(
            role_card_id=role_card.id,
            role_name=role_card.role_name,
            role_description=role_card.role_description,
            location_to_find=role_card.location_to_find,
        )
        for role_card in role_cards
    ]


def _find_role_progresses(db: Session, progress_id: int) -> list[RoleProgressResponse]:
    """이 방의 참여자에게 배정된 역할 진행도를 반환한다. 아직 없으면 빈 배열."""
    statement = (
        select(CooperativeRoleProgress, User.nickname, CooperativeRoleCard.role_name)
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.id == CooperativeRoleProgress.participant_id,
        )
        .join(User, User.id == CooperativeMissionParticipant.user_id)
        .join(
            CooperativeRoleCard,
            CooperativeRoleCard.id == CooperativeRoleProgress.cooperative_role_card_id,
        )
        .where(CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id)
        .order_by(CooperativeRoleProgress.id)
    )
    return [
        RoleProgressResponse(
            role_progress_id=role_progress.id,
            participant_id=role_progress.participant_id,
            participant_name=nickname or "",
            role_card_id=role_progress.cooperative_role_card_id,
            role_name=role_name,
            progress_status=MissionStatus(role_progress.progress_status),
            item_img_url=role_progress.item_img_url,
        )
        for role_progress, nickname, role_name in db.execute(statement).all()
    ]


# ---------------------------------------------------------------------
# 미구현 API
# ---------------------------------------------------------------------


def get_invitation(invite_token: str, db: Session) -> dict[str, Any]:
    """초대 url 정보 조회."""
    raise NotImplementedError


def join_as_guest(invite_token: str, db: Session) -> dict[str, Any]:
    """초대 url로 게스트 참여."""
    raise NotImplementedError


def get_cooperative_mission_status(mission_progress_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 상태 조회."""
    raise NotImplementedError


def save_cooperative_mission_progress(mission_progress_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 진행도 저장."""
    raise NotImplementedError


def stop_cooperative_mission(mission_progress_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 중단."""
    raise NotImplementedError


def save_role_progress(
    mission_progress_id: int, role_progress_id: int, db: Session
) -> dict[str, Any]:
    """협동 미션 역할 진행도 저장."""
    raise NotImplementedError
