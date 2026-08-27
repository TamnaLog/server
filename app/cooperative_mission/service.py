"""협동 미션 도메인 비즈니스 로직.

기준 문서: app/cooperative_mission/docs/API_SPEC.md,
          app/cooperative_mission/docs/BUSINESS_RULES.md
"""

import secrets
from dataclasses import dataclass
from typing import Any

from sqlalchemy import case, func, select
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
    JoinCooperativeMissionRequest,
    JoinCooperativeMissionResponse,
    ParticipantResponse,
    RoleCardResponse,
    RoleProgressResponse,
)
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.user.models import User


COOPERATIVE_MISSION_NOT_FOUND = "COOPERATIVE_MISSION_NOT_FOUND"
INVALID_INVITE_TOKEN = "INVALID_INVITE_TOKEN"
COOPERATIVE_MISSION_FULL = "COOPERATIVE_MISSION_FULL"
COOPERATIVE_MISSION_JOIN_CLOSED = "COOPERATIVE_MISSION_JOIN_CLOSED"
COOPERATIVE_MISSION_PROGRESS_NOT_FOUND = "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND = "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
COOPERATIVE_MISSION_HOST_ONLY = "COOPERATIVE_MISSION_HOST_ONLY"
COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED = (
    "COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED"
)

# 신규 진행도 초기값
FIRST_STEP = 1

# 팀 토큰 바이트 수. token_urlsafe(32) 는 약 43자라 VARCHAR(100) 안에 들어간다.
TEAM_TOKEN_BYTES = 32

# team_token UNIQUE 충돌 시 재시도 횟수
MAX_TEAM_TOKEN_ATTEMPTS = 5

# 방장을 포함한 최대 참여 인원
COOPERATIVE_MISSION_MAX_PARTICIPANTS = 6

# 새 팀원을 받을 수 있는 단계 (초대 단계)
JOIN_OPEN_STEP = 1


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
# URL로 참여 요청
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class JoinCooperativeMissionResult:
    """참여 요청 결과.

    응답 구조는 같지만 상태 코드가 달라서(신규 201 / 기존 참여자 200)
    참여자를 새로 만들었는지를 라우터에 함께 전달한다.
    """

    response: JoinCooperativeMissionResponse
    is_created: bool


def join_cooperative_mission(
    db: Session, current_user_id: int, request: JoinCooperativeMissionRequest
) -> JoinCooperativeMissionResult:
    """초대 URL(팀 토큰)로 협동 미션 방에 참여를 요청한다.

    - 이미 참여자면(수락 전이든 후든) 새로 만들지 않고 기존 정보를 돌려준다.
    - 새로 요청하는 경우에만 참여 가능 단계와 최대 인원을 확인한다.
    """
    progress = _get_progress_by_team_token(db, request.team_token)

    # 기존 참여자 확인을 단계/인원 검증보다 먼저 한다.
    # 방장이나 이미 요청한 사람이 같은 링크를 다시 열어도 409 가 나면 안 되기 때문이다.
    participant = _find_participant(db, progress.id, current_user_id)
    is_created = participant is None
    if participant is None:
        _check_join_open(progress)
        _check_not_full(db, progress.id)
        participant = _create_member_participant(db, progress.id, current_user_id)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(participant)

    return JoinCooperativeMissionResult(
        response=JoinCooperativeMissionResponse(
            mission_progress_id=progress.id,
            participant_id=participant.id,
            participant_status=ParticipantStatus(participant.participant_status),
        ),
        is_created=is_created,
    )


def _get_progress_by_team_token(db: Session, team_token: str) -> CooperativeMissionProgress:
    """팀 토큰으로 진행 중인 방을 찾는다. 없거나 이미 끝난 방이면 유효하지 않은 초대다.

    동시에 여러 참여 요청이 들어와도 인원 계산이 어긋나지 않도록 진행도 행을 잠근다.
    (SQLite 는 행 잠금이 없어 무시되고, MySQL 에서만 실제로 걸린다)
    """
    statement = (
        select(CooperativeMissionProgress)
        .where(
            CooperativeMissionProgress.team_token == team_token,
            CooperativeMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
        .with_for_update()
    )
    progress = db.scalars(statement).first()
    if progress is None:
        # 토큰 원문은 로그에 남기지 않는다.
        raise NotFoundError(
            INVALID_INVITE_TOKEN, detail="진행 중인 협동 미션 방을 찾을 수 없습니다."
        )
    return progress


def _find_participant(
    db: Session, progress_id: int, current_user_id: int
) -> CooperativeMissionParticipant | None:
    """이 방에 현재 사용자의 참여자 데이터가 이미 있는지 찾는다."""
    statement = (
        select(CooperativeMissionParticipant)
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.user_id == current_user_id,
        )
        .order_by(CooperativeMissionParticipant.id)
    )
    return db.scalars(statement).first()


def _check_join_open(progress: CooperativeMissionProgress) -> None:
    """새 팀원을 받을 수 있는 단계인지 확인한다. (초대 단계에서만 가능)"""
    if progress.current_step != JOIN_OPEN_STEP:
        raise ConflictError(
            COOPERATIVE_MISSION_JOIN_CLOSED,
            detail=(
                f"진행도 {progress.id} 의 현재 단계가 {progress.current_step} 이라 "
                "새 참여 요청을 받을 수 없습니다."
            ),
        )


def _check_not_full(db: Session, progress_id: int) -> None:
    """최대 인원을 넘지 않는지 확인한다. 수락 전(PENDING) 참여자도 인원에 포함한다."""
    participant_count = db.scalar(
        select(func.count())
        .select_from(CooperativeMissionParticipant)
        .where(CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id)
    )
    if (participant_count or 0) >= COOPERATIVE_MISSION_MAX_PARTICIPANTS:
        raise ConflictError(
            COOPERATIVE_MISSION_FULL,
            detail=(
                f"진행도 {progress_id} 의 참여자가 이미 "
                f"{COOPERATIVE_MISSION_MAX_PARTICIPANTS}명입니다."
            ),
        )


def _create_member_participant(
    db: Session, progress_id: int, current_user_id: int
) -> CooperativeMissionParticipant:
    """수락 대기 상태의 팀원을 만든다. 수락 시각(`joined_at`)은 아직 없다."""
    participant = CooperativeMissionParticipant(
        cooperative_mission_progress_id=progress_id,
        user_id=current_user_id,
        participant_status=ParticipantStatus.PENDING.value,
        participant_role=ParticipantRole.MEMBER.value,
        joined_at=None,
    )
    db.add(participant)
    return participant


# ---------------------------------------------------------------------
# 참여 요청 수락
# ---------------------------------------------------------------------


def accept_join_request(
    db: Session, current_user_id: int, mission_progress_id: int, participant_id: int
) -> None:
    """방장이 참여 요청을 수락한다.

    - `PENDING` 팀원을 `ACCEPTED` 로 바꾸고 수락 시각을 남긴다.
    - 이미 `ACCEPTED` 인 팀원에 대한 재요청은 아무것도 바꾸지 않는다. (멱등)

    수락은 기존 참여자 row 의 상태만 바꾸므로 최대 인원을 다시 확인하지 않는다.
    (URL 로 참여 요청할 때 `PENDING` 도 인원에 포함했다)
    """
    progress = _get_in_progress_by_id(db, mission_progress_id)
    _check_host(db, progress.id, current_user_id)
    _check_join_open(progress)

    participant = _get_member_participant(db, progress.id, participant_id)
    if participant.participant_status == ParticipantStatus.ACCEPTED.value:
        # 이미 수락된 팀원이면 수락 시각을 덮어쓰지 않는다.
        return

    participant.participant_status = ParticipantStatus.ACCEPTED.value
    participant.joined_at = now_kst()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _get_in_progress_by_id(db: Session, mission_progress_id: int) -> CooperativeMissionProgress:
    """진행 중인 협동 미션 방을 조회한다.

    없는 방과 이미 끝난 방을 구분하지 않고 404 로 처리한다.
    수락과 단계 변경이 동시에 들어와도 어긋나지 않도록 진행도 행을 잠근다.
    (SQLite 는 행 잠금이 없어 무시되고, MySQL 에서만 실제로 걸린다)
    """
    statement = (
        select(CooperativeMissionProgress)
        .where(
            CooperativeMissionProgress.id == mission_progress_id,
            CooperativeMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
        .with_for_update()
    )
    progress = db.scalars(statement).first()
    if progress is None:
        raise NotFoundError(
            COOPERATIVE_MISSION_PROGRESS_NOT_FOUND,
            detail=f"진행 중인 협동 미션 진행도 {mission_progress_id} 를 찾을 수 없습니다.",
        )
    return progress


def _check_host(db: Session, progress_id: int, current_user_id: int) -> None:
    """현재 사용자가 이 방의 방장인지 확인한다.

    방장 여부는 요청 값이 아니라 토큰으로 식별한 사용자의 참여자 row 로만 판단한다.
    """
    statement = (
        select(CooperativeMissionParticipant.id)
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_role == ParticipantRole.HOST.value,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
        )
        .limit(1)
    )
    if db.scalar(statement) is None:
        raise ForbiddenError(
            COOPERATIVE_MISSION_HOST_ONLY,
            detail=f"사용자 {current_user_id} 는 진행도 {progress_id} 의 방장이 아닙니다.",
        )


def _get_member_participant(
    db: Session, progress_id: int, participant_id: int
) -> CooperativeMissionParticipant:
    """수락 대상 팀원을 조회한다.

    다른 방의 참여자이거나 방장이면 대상이 아니므로 404 로 처리한다.
    수락 재요청/거절과 동시에 들어와도 어긋나지 않도록 참여자 행을 잠근다.
    """
    statement = (
        select(CooperativeMissionParticipant)
        .where(
            CooperativeMissionParticipant.id == participant_id,
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.participant_role == ParticipantRole.MEMBER.value,
        )
        .with_for_update()
    )
    participant = db.scalars(statement).first()
    if participant is None:
        raise NotFoundError(
            COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND,
            detail=(
                f"진행도 {progress_id} 에서 수락할 팀원 {participant_id} 를 찾을 수 없습니다."
            ),
        )
    return participant


# ---------------------------------------------------------------------
# 참여 요청 거절
# ---------------------------------------------------------------------


def reject_join_request(
    db: Session, current_user_id: int, mission_progress_id: int, participant_id: int
) -> None:
    """방장이 참여 요청을 거절한다.

    거절은 `REJECTED` 상태를 남기지 않고 `PENDING` 참여자 row 를 지운다.
    자리가 하나 비므로 거절당한 사용자도 같은 초대 URL 로 다시 요청할 수 있다.

    이미 수락한 팀원을 내보내는 것은 다른 동작이라 여기서 처리하지 않는다. (409)
    """
    progress = _get_in_progress_by_id(db, mission_progress_id)
    _check_host(db, progress.id, current_user_id)
    _check_join_open(progress)

    participant = _get_member_participant(db, progress.id, participant_id)
    _check_not_accepted(participant)

    db.delete(participant)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _check_not_accepted(participant: CooperativeMissionParticipant) -> None:
    """이미 수락된 팀원인지 확인한다. 수락된 팀원은 이 API 로 지우지 않는다."""
    if participant.participant_status == ParticipantStatus.ACCEPTED.value:
        raise ConflictError(
            COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED,
            detail=f"참여자 {participant.id} 는 이미 수락된 팀원입니다.",
        )


# ---------------------------------------------------------------------
# 미구현 API
# ---------------------------------------------------------------------


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
