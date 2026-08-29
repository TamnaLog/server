"""협동 미션 도메인 비즈니스 로직.

기준 문서: app/cooperative_mission/docs/API_SPEC.md,
          app/cooperative_mission/docs/BUSINESS_RULES.md
"""

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common import images, next_location
from app.common.datetimes import now_kst
from app.common.rewards import GrantedRewardResponse
from app.cooperative_mission import photo_verifier, reward_granter
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
    CooperativeMissionLeaveResponse,
    CooperativeMissionProgressSaveRequest,
    CooperativeRoleAssignmentSaveRequest,
    RoleProgressVerificationResponse,
    CooperativeMissionStartResponse,
    CooperativeMissionStatusResponse,
    CurrentParticipantResponse,
    JoinCooperativeMissionRequest,
    JoinCooperativeMissionResponse,
    ParticipantResponse,
    RoleCardResponse,
    RoleProgressResponse,
)
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.services import blob_storage
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
COOPERATIVE_MISSION_ALREADY_COMPLETED = "COOPERATIVE_MISSION_ALREADY_COMPLETED"
COOPERATIVE_MISSION_STEP_NOT_ALLOWED = "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"
COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS = (
    "COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS"
)
COOPERATIVE_PARTICIPANT_ROLE_REQUIRED = "COOPERATIVE_PARTICIPANT_ROLE_REQUIRED"
COOPERATIVE_ROLE_CARD_NOT_FOUND = "COOPERATIVE_ROLE_CARD_NOT_FOUND"
COOPERATIVE_ROLE_PROGRESS_NOT_FOUND = "COOPERATIVE_ROLE_PROGRESS_NOT_FOUND"
COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED = (
    "COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED"
)
COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED = "COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED"

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

# 역할 카드 배정 단계
ROLE_ASSIGN_STEP = 2

# 미션 수행(사진 인증) 단계
MISSION_RUN_STEP = 3

# 역할 카드/역할 진행도를 내려주는 단계 (역할 배정, 미션 수행)
ROLE_STEPS = (ROLE_ASSIGN_STEP, MISSION_RUN_STEP)

# 미션 완료 단계
COMPLETED_STEP = 4

# 역할 사진 인증 Blob 저장 경로의 최상위 prefix. 그 아래를 진행도/역할 진행도로 나눈다.
ROLE_IMAGE_BLOB_PREFIX = "cooperative_mission_role"


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
            CooperativeMissionProgress.deleted_at.is_(None),
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_role == ParticipantRole.HOST.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
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
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
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
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeRoleProgress.deleted_at.is_(None),
        )
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
            CooperativeMissionProgress.deleted_at.is_(None),
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
            CooperativeMissionParticipant.deleted_at.is_(None),
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
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
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
            CooperativeMissionProgress.deleted_at.is_(None),
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
            CooperativeMissionParticipant.deleted_at.is_(None),
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
            CooperativeMissionParticipant.deleted_at.is_(None),
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

    거절은 `REJECTED` 상태를 남기지 않고 `PENDING` 참여자 row 를 소프트 삭제한다.
    (`deleted_at` 을 남기고 조회에서 제외한다. 행을 실제로 지우지는 않는다)
    자리가 하나 비므로 거절당한 사용자도 같은 초대 URL 로 다시 요청할 수 있다.
    이때는 삭제된 row 를 되살리지 않고 참여자 row 를 새로 만든다.

    이미 수락한 팀원을 내보내는 것은 다른 동작이라 여기서 처리하지 않는다. (409)
    """
    progress = _get_in_progress_by_id(db, mission_progress_id)
    _check_host(db, progress.id, current_user_id)
    _check_join_open(progress)

    participant = _get_member_participant(db, progress.id, participant_id)
    _check_not_accepted(participant)

    participant.deleted_at = now_kst()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _check_not_accepted(participant: CooperativeMissionParticipant) -> None:
    """이미 수락된 팀원인지 확인한다. 수락된 팀원은 이 API 로 삭제하지 않는다."""
    if participant.participant_status == ParticipantStatus.ACCEPTED.value:
        raise ConflictError(
            COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED,
            detail=f"참여자 {participant.id} 는 이미 수락된 팀원입니다.",
        )


# ---------------------------------------------------------------------
# 상태 조회 (폴링)
# ---------------------------------------------------------------------


def get_cooperative_mission_status(
    db: Session, current_user_id: int, mission_progress_id: int
) -> CooperativeMissionStatusResponse:
    """협동 미션 상태 조회.

    방장과 팀원이 초대 단계부터 완료까지 폴링하는 API라 단계별로 필요한 값만 채운다.

    - 1단계: 참가자 목록과 내 참여 상태 (수락/거절 결과 확인)
    - 2·3단계: 역할 카드와 역할 진행도, 인증 집계
    - 4단계: 보상과 다음 장소 (참가자/역할 정보는 내려주지 않는다)

    1~3단계 조회는 데이터를 바꾸지 않는다. 4단계는 아직 정산 전이면 보상을 지급한다.
    """
    progress = _get_progress_for_status(db, mission_progress_id)
    participant = _get_my_participant(db, progress.id, current_user_id)

    cooperative_mission = _get_cooperative_mission(db, progress.cooperative_mission_id)
    response = CooperativeMissionStatusResponse(
        mission_progress_id=progress.id,
        mission_id=cooperative_mission.id,
        mission_title=cooperative_mission.mission.mission_title,
        mission_progress_status=MissionStatus(progress.mission_status),
        current_step=progress.current_step,
    )

    if progress.current_step == COMPLETED_STEP:
        return _to_completed_status(db, response, progress, cooperative_mission)

    response.current_participant = CurrentParticipantResponse(
        participant_id=participant.id,
        participant_role=ParticipantRole(participant.participant_role),
        participant_status=ParticipantStatus(participant.participant_status),
    )
    response.participants = _find_participants(db, progress.id)

    if progress.current_step in ROLE_STEPS:
        role_progresses = _find_role_progresses(db, progress.id)
        response.role_cards = _find_role_cards(db)
        response.role_progresses = role_progresses
        response.total_role_count = len(role_progresses)
        response.completed_role_count = sum(
            1
            for role_progress in role_progresses
            if role_progress.progress_status is MissionStatus.COMPLETED
        )

    return response


def _get_progress_for_status(
    db: Session, mission_progress_id: int
) -> CooperativeMissionProgress:
    """상태 조회 대상 진행도를 찾는다.

    완료(4단계) 방도 조회해야 하므로 진행 중인 방으로 제한하지 않는다.
    4단계에서는 보상 정산이 한 번만 일어나도록 행을 잠그고 읽는다.
    (SQLite 는 행 잠금이 없어 무시되고, MySQL 에서만 실제로 걸린다)
    """
    statement = select(CooperativeMissionProgress).where(
        CooperativeMissionProgress.id == mission_progress_id,
        CooperativeMissionProgress.deleted_at.is_(None),
    )
    progress = db.scalars(statement.with_for_update()).first()
    if progress is None:
        raise NotFoundError(
            COOPERATIVE_MISSION_PROGRESS_NOT_FOUND,
            detail=f"협동 미션 진행도 {mission_progress_id} 를 찾을 수 없습니다.",
        )
    return progress


def _get_my_participant(
    db: Session, progress_id: int, current_user_id: int
) -> CooperativeMissionParticipant:
    """현재 사용자의 참가자 row 를 찾는다.

    참여 요청이 거절되면 참가자 row 가 소프트 삭제되고 조회에서 빠지므로,
    거절당한 팀원의 폴링도 여기서 404 가 된다.
    """
    participant = _find_participant(db, progress_id, current_user_id)
    if participant is None:
        raise NotFoundError(
            COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND,
            detail=(
                f"사용자 {current_user_id} 는 진행도 {progress_id} 의 참가자가 아닙니다."
            ),
        )
    return participant


def _to_completed_status(
    db: Session,
    response: CooperativeMissionStatusResponse,
    progress: CooperativeMissionProgress,
    cooperative_mission: CooperativeMission,
) -> CooperativeMissionStatusResponse:
    """완료 화면 응답을 만든다. 참가자/역할 정보 대신 보상과 다음 장소를 채운다."""
    response.reward = reward_granter.settle_cooperative_mission_reward(
        db,
        progress=progress,
        cooperative_mission=cooperative_mission,
        completed_role_count=reward_granter.count_completed_roles(db, progress.id),
    )
    response.next_location = next_location.recommend_next_location_summary(db)
    return response


# ---------------------------------------------------------------------
# 진행도 저장 (단계 변경)
# ---------------------------------------------------------------------


def save_cooperative_mission_progress(
    db: Session,
    current_user_id: int,
    mission_progress_id: int,
    request: CooperativeMissionProgressSaveRequest,
) -> None:
    """방장이 협동 미션을 다음 단계로 넘긴다.

    이 API 는 단계만 바꾼다. 역할 배정/보상/다음 장소는 각각 다른 API 가 담당한다.

    - `1 → 2`: 아직 수락도 거절도 안 된 참여 요청이 남아 있으면 넘길 수 없다.
    - `2 → 3`: 역할을 하나도 못 받은 `ACCEPTED` 참가자가 있으면 넘길 수 없다.
    - `3 → 4`: 인증이 남아 있어도 방장이 끝낼 수 있다. 완료 상태와 완료 시각을 함께 저장한다.
    """
    progress = _get_progress_for_step_change(db, mission_progress_id)
    _check_host(db, progress.id, current_user_id)
    _check_sequential_step(progress, request.current_step)

    if request.current_step == ROLE_ASSIGN_STEP:
        _check_no_pending_participant(db, progress.id)
    elif request.current_step == MISSION_RUN_STEP:
        _check_every_participant_has_role(db, progress.id)

    progress.current_step = request.current_step
    if request.current_step == COMPLETED_STEP:
        progress.mission_status = MissionStatus.COMPLETED.value
        progress.completed_at = now_kst()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _get_progress_for_step_change(
    db: Session, mission_progress_id: int
) -> CooperativeMissionProgress:
    """단계를 바꿀 진행도를 찾는다.

    완료된 방을 "없는 방"으로 감추지 않고 409 로 구분해서 알려준다.
    같은 단계 변경 요청이 동시에 들어와도 한 번만 처리되도록 행을 잠그고 읽는다.
    (SQLite 는 행 잠금이 없어 무시되고, MySQL 에서만 실제로 걸린다)
    """
    statement = (
        select(CooperativeMissionProgress)
        .where(
            CooperativeMissionProgress.id == mission_progress_id,
            CooperativeMissionProgress.deleted_at.is_(None),
        )
        .with_for_update()
    )
    progress = db.scalars(statement).first()
    if progress is None:
        raise NotFoundError(
            COOPERATIVE_MISSION_PROGRESS_NOT_FOUND,
            detail=f"협동 미션 진행도 {mission_progress_id} 를 찾을 수 없습니다.",
        )

    if (
        progress.mission_status == MissionStatus.COMPLETED.value
        or progress.current_step == COMPLETED_STEP
    ):
        raise ConflictError(
            COOPERATIVE_MISSION_ALREADY_COMPLETED,
            detail=f"진행도 {progress.id} 는 이미 완료된 협동 미션입니다.",
        )
    return progress


def _check_sequential_step(
    progress: CooperativeMissionProgress, next_step: int
) -> None:
    """한 단계씩만 올릴 수 있다. 같은 단계/역행/건너뛰기는 모두 막는다."""
    if next_step != progress.current_step + 1:
        raise ConflictError(
            COOPERATIVE_MISSION_STEP_NOT_ALLOWED,
            detail=(
                f"진행도 {progress.id} 의 현재 단계는 {progress.current_step} 이라 "
                f"{next_step} 단계로 바꿀 수 없습니다."
            ),
        )


def _check_no_pending_participant(db: Session, progress_id: int) -> None:
    """수락 대기 중인 참여 요청이 남아 있는지 확인한다. (1 → 2)

    남은 요청을 자동으로 수락하거나 삭제하지 않는다. 방장이 직접 정리해야 한다.
    """
    pending_id = db.scalar(
        select(CooperativeMissionParticipant.id)
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.PENDING.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
        .limit(1)
    )
    if pending_id is not None:
        raise ConflictError(
            COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS,
            detail=f"진행도 {progress_id} 에 아직 처리하지 않은 참여 요청이 있습니다.",
        )


def _check_every_participant_has_role(db: Session, progress_id: int) -> None:
    """`ACCEPTED` 참가자 모두가 역할을 하나 이상 받았는지 확인한다. (2 → 3)

    역할 카드가 남아 있거나 한 참가자가 여러 역할을 맡은 것은 막지 않는다.
    역할 배정 자체의 유효성은 역할 배정 저장 API 가 검증한다.
    """
    statement = (
        select(CooperativeMissionParticipant.id)
        .outerjoin(
            CooperativeRoleProgress,
            (CooperativeRoleProgress.participant_id == CooperativeMissionParticipant.id)
            # 삭제된 역할 진행도는 배정되지 않은 것으로 본다. (ON 절에 둬야 참가자가 남는다)
            & CooperativeRoleProgress.deleted_at.is_(None),
        )
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeRoleProgress.id.is_(None),
        )
        .limit(1)
    )
    participant_id = db.scalar(statement)
    if participant_id is not None:
        raise ConflictError(
            COOPERATIVE_PARTICIPANT_ROLE_REQUIRED,
            detail=f"참가자 {participant_id} 는 아직 역할을 배정받지 않았습니다.",
        )


# ---------------------------------------------------------------------
# 역할 배정 저장
# ---------------------------------------------------------------------


def save_role_assignment(
    db: Session,
    current_user_id: int,
    mission_progress_id: int,
    role_card_id: int,
    request: CooperativeRoleAssignmentSaveRequest,
) -> None:
    """방장이 역할 카드 하나의 담당자를 저장한다. (역할 카드 기준 upsert)

    - 이 방에서 그 역할 카드가 아직 배정되지 않았으면 역할 진행도를 새로 만든다.
    - 이미 배정돼 있으면 새 row 를 만들지 않고 담당 참가자만 바꾼다.
      (`roleProgressId` / 역할 카드 / 인증 정보는 그대로 둔다)
    - 같은 참가자로 다시 요청하면 아무것도 바꾸지 않는다. (멱등)
    """
    progress = _get_progress_for_step_change(db, mission_progress_id)
    _check_host(db, progress.id, current_user_id)
    _check_role_assign_step(progress)
    _get_role_card(db, role_card_id)

    participant = _get_accepted_participant(db, progress.id, request.participant_id)
    role_progress = _find_role_progress_by_role_card(db, progress.id, role_card_id)

    if role_progress is None:
        db.add(
            CooperativeRoleProgress(
                participant_id=participant.id,
                cooperative_role_card_id=role_card_id,
                item_img_url=None,
                progress_status=MissionStatus.IN_PROGRESS.value,
                completed_at=None,
            )
        )
    elif role_progress.participant_id != participant.id:
        # 담당자만 바꾼다. 역할 진행도 id 와 인증 데이터는 유지한다.
        role_progress.participant_id = participant.id
    else:
        # 같은 배정을 다시 요청한 경우라 바꿀 것이 없다.
        return

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _check_role_assign_step(progress: CooperativeMissionProgress) -> None:
    """역할 배정은 2단계에서만 할 수 있다."""
    if progress.current_step != ROLE_ASSIGN_STEP:
        raise ConflictError(
            COOPERATIVE_MISSION_STEP_NOT_ALLOWED,
            detail=(
                f"진행도 {progress.id} 의 현재 단계가 {progress.current_step} 이라 "
                "역할을 배정할 수 없습니다."
            ),
        )


def _get_role_card(db: Session, role_card_id: int) -> CooperativeRoleCard:
    """역할 카드를 조회한다.

    역할 카드는 모든 협동 미션이 함께 쓰는 마스터라 미션으로 더 좁히지 않는다.
    """
    role_card = db.get(CooperativeRoleCard, role_card_id)
    if role_card is None:
        raise NotFoundError(
            COOPERATIVE_ROLE_CARD_NOT_FOUND,
            detail=f"역할 카드 {role_card_id} 를 찾을 수 없습니다.",
        )
    return role_card


def _get_accepted_participant(
    db: Session, progress_id: int, participant_id: int
) -> CooperativeMissionParticipant:
    """역할을 맡을 참가자를 조회한다.

    다른 방의 참가자이거나 아직 수락되지 않은 참가자는 배정 대상이 아니다.
    방장도 역할을 맡을 수 있으므로 역할(`HOST`/`MEMBER`)은 따지지 않는다.
    """
    statement = (
        select(CooperativeMissionParticipant)
        .where(
            CooperativeMissionParticipant.id == participant_id,
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
        .with_for_update()
    )
    participant = db.scalars(statement).first()
    if participant is None:
        raise NotFoundError(
            COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND,
            detail=(
                f"진행도 {progress_id} 에서 역할을 맡을 참가자 {participant_id} 를 "
                "찾을 수 없습니다."
            ),
        )
    return participant


def _find_role_progress_by_role_card(
    db: Session, progress_id: int, role_card_id: int
) -> CooperativeRoleProgress | None:
    """이 방에서 해당 역할 카드에 이미 배정된 역할 진행도를 찾는다.

    역할 진행도는 진행도 id를 직접 갖지 않아 참가자 테이블을 거쳐 방을 좁힌다.
    (역할 카드는 공용 마스터라 카드 id 만으로 찾으면 다른 방의 배정까지 걸린다)
    """
    statement = (
        select(CooperativeRoleProgress)
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.id == CooperativeRoleProgress.participant_id,
        )
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeRoleProgress.cooperative_role_card_id == role_card_id,
            CooperativeRoleProgress.deleted_at.is_(None),
        )
        .order_by(CooperativeRoleProgress.id)
    )
    return db.scalars(statement).first()


# ---------------------------------------------------------------------
# 역할 진행도 저장 (사진 인증)
# ---------------------------------------------------------------------


def verify_role_progress(
    db: Session,
    current_user_id: int,
    mission_progress_id: int,
    role_progress_id: int,
    item_image: BinaryIO,
) -> RoleProgressVerificationResponse:
    """참가자가 자기 역할의 인증 사진을 올린다.

    - 인증에 실패하면 아무것도 바꾸지 않고 `isVerified: false` 만 돌려준다. (오류가 아니다)
    - 성공하면 사진을 Blob 에 올리고 역할 진행도를 `COMPLETED` 로 바꾼다.

    이 API 는 협동 미션의 단계나 완료 상태를 바꾸지 않는다.
    마지막 역할까지 인증돼도 `3 → 4` 는 방장이 진행도 저장 API 로 직접 넘겨야 한다.
    """
    data, image_format = images.read_and_detect(item_image)

    progress = _get_progress_for_verification(db, mission_progress_id)
    role_progress = _get_my_role_progress(
        db, progress.id, role_progress_id, current_user_id
    )
    role_card = _get_role_card(db, role_progress.cooperative_role_card_id)

    is_verified = photo_verifier.verify_role_image(
        image_bytes=data,
        content_type=image_format.content_type,
        role_name=role_card.role_name,
        role_description=role_card.role_description,
        location_to_find=role_card.location_to_find,
    )
    if not is_verified:
        # 판정 실패는 정상 응답이다. 사진을 올리지도, 진행도를 바꾸지도 않는다.
        return RoleProgressVerificationResponse(is_verified=False)

    item_img_url = blob_storage.upload_file(
        data,
        prefix=f"{ROLE_IMAGE_BLOB_PREFIX}/{progress.id}/{role_progress.id}",
        content_type=image_format.content_type,
        extension=image_format.extension,
    )

    try:
        role_progress.item_img_url = item_img_url
        role_progress.progress_status = MissionStatus.COMPLETED.value
        role_progress.completed_at = now_kst()
        db.commit()
    except Exception:
        # DB 가 참조하지 않는 파일이 남지 않도록 올린 사진을 되돌린다.
        db.rollback()
        blob_storage.delete_file(item_img_url)
        raise

    return RoleProgressVerificationResponse(is_verified=True)


def _get_progress_for_verification(
    db: Session, mission_progress_id: int
) -> CooperativeMissionProgress:
    """사진 인증이 가능한 진행도인지 확인한다. (미션 수행 단계에서만 가능)"""
    progress = _get_progress_for_step_change(db, mission_progress_id)
    if progress.current_step != MISSION_RUN_STEP:
        raise ConflictError(
            COOPERATIVE_MISSION_STEP_NOT_ALLOWED,
            detail=(
                f"진행도 {progress.id} 의 현재 단계가 {progress.current_step} 이라 "
                "사진을 인증할 수 없습니다."
            ),
        )
    return progress


def _get_my_role_progress(
    db: Session, progress_id: int, role_progress_id: int, current_user_id: int
) -> CooperativeRoleProgress:
    """인증할 역할 진행도를 찾는다.

    같은 역할에 인증 요청이 동시에 들어와도 한 번만 완료되도록 행을 잠그고 읽는다.
    방장이라도 자기에게 배정된 역할만 인증할 수 있다.
    """
    statement = (
        select(CooperativeRoleProgress, CooperativeMissionParticipant)
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.id == CooperativeRoleProgress.participant_id,
        )
        .where(
            CooperativeRoleProgress.id == role_progress_id,
            CooperativeRoleProgress.deleted_at.is_(None),
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
        .with_for_update(of=CooperativeRoleProgress)
    )
    row = db.execute(statement).first()
    if row is None:
        raise NotFoundError(
            COOPERATIVE_ROLE_PROGRESS_NOT_FOUND,
            detail=(
                f"진행도 {progress_id} 에서 역할 진행도 {role_progress_id} 를 찾을 수 없습니다."
            ),
        )

    role_progress, participant = row
    if (
        participant.user_id != current_user_id
        or participant.participant_status != ParticipantStatus.ACCEPTED.value
    ):
        raise ForbiddenError(
            COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED,
            detail=(
                f"사용자 {current_user_id} 는 역할 진행도 {role_progress_id} 의 담당자가 아닙니다."
            ),
        )

    if role_progress.progress_status == MissionStatus.COMPLETED.value:
        raise ConflictError(
            COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED,
            detail=f"역할 진행도 {role_progress_id} 는 이미 인증을 마쳤습니다.",
        )
    return role_progress


# ---------------------------------------------------------------------
# 협동 미션 나가기
# ---------------------------------------------------------------------


def leave_cooperative_mission(
    db: Session, current_user_id: int, mission_progress_id: int
) -> CooperativeMissionLeaveResponse:
    """현재 사용자가 협동 미션에서 나간다.

    나가는 사람의 역할에 따라 처리가 갈린다.

    - 마지막 `ACCEPTED` 참가자: 방 전체(진행도/참가자/역할 진행도)를 소프트 삭제한다.
    - 방장이고 남은 `ACCEPTED` 팀원이 있음: 본인만 빠지고 다음 팀원이 방장을 승계한다.
    - 그 밖(`MEMBER` 또는 `PENDING`): 본인과 본인의 역할 진행도만 소프트 삭제한다.

    나가기는 미션 완료가 아니므로 보상을 지급하지 않고 단계/완료 상태도 바꾸지 않는다.
    """
    # 완료된 방에서는 나갈 수 없다. (404/409 판정이 단계 변경과 같아 helper 를 함께 쓴다)
    progress = _get_progress_for_step_change(db, mission_progress_id)
    participant = _get_my_participant(db, progress.id, current_user_id)

    # 잠금을 잡은 뒤 다시 세어야 동시에 나가도 방장이 둘이 되거나 사라지지 않는다.
    accepted_participants = _find_accepted_participants(db, progress.id)
    leaving_at = now_kst()

    if _is_last_accepted(participant, accepted_participants):
        _delete_whole_progress(db, progress, leaving_at)
    else:
        _delete_participant(db, participant, leaving_at)
        if participant.participant_role == ParticipantRole.HOST.value:
            _hand_over_host(db, participant, accepted_participants)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return CooperativeMissionLeaveResponse(
        mission_progress_id=progress.id,
        # 나가기는 보상을 지급하지 않으므로 세 항목 모두 비운다.
        reward=GrantedRewardResponse(),
        next_location=next_location.recommend_next_location_summary(db),
    )


def _find_accepted_participants(
    db: Session, progress_id: int
) -> list[CooperativeMissionParticipant]:
    """방에 남아 있는 `ACCEPTED` 참가자를 방장 승계 순서로 정렬해 가져온다.

    먼저 들어온 사람이 앞이고, 참여 시각이 같으면 참가자 id 가 작은 쪽이 앞이다.
    `PENDING` 참가자는 방장 승계 대상이 아니라서 여기서 제외한다.
    """
    statement = (
        select(CooperativeMissionParticipant)
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
        .order_by(
            CooperativeMissionParticipant.joined_at,
            CooperativeMissionParticipant.id,
        )
    )
    return list(db.scalars(statement).all())


def _is_last_accepted(
    participant: CooperativeMissionParticipant,
    accepted_participants: list[CooperativeMissionParticipant],
) -> bool:
    """나가는 사람이 방에 남은 마지막 `ACCEPTED` 참가자인지 본다.

    `PENDING` 참가자는 수를 세지 않는다. 대기 중인 사람만 남아도 방을 유지하지 않는다.
    """
    return (
        participant.participant_status == ParticipantStatus.ACCEPTED.value
        and len(accepted_participants) == 1
    )


def _delete_participant(
    db: Session, participant: CooperativeMissionParticipant, deleted_at: datetime
) -> None:
    """참가자와 그 참가자가 맡은 역할 진행도를 소프트 삭제한다.

    역할 진행도의 `item_img_url` 과 Blob 이미지는 지우지 않고 그대로 둔다.
    """
    participant.deleted_at = deleted_at
    db.execute(
        update(CooperativeRoleProgress)
        .where(
            CooperativeRoleProgress.participant_id == participant.id,
            CooperativeRoleProgress.deleted_at.is_(None),
        )
        .values(deleted_at=deleted_at)
        .execution_options(synchronize_session=False)
    )


def _delete_whole_progress(
    db: Session, progress: CooperativeMissionProgress, deleted_at: datetime
) -> None:
    """방을 통째로 소프트 삭제한다. 남아 있던 `PENDING` 참가자도 함께 정리한다.

    나가기는 완료가 아니라서 `mission_status` / `current_step` / `completed_at` 과
    보상 지급 여부는 건드리지 않는다.
    """
    participant_ids = select(CooperativeMissionParticipant.id).where(
        CooperativeMissionParticipant.cooperative_mission_progress_id == progress.id,
        CooperativeMissionParticipant.deleted_at.is_(None),
    )
    db.execute(
        update(CooperativeRoleProgress)
        .where(
            CooperativeRoleProgress.participant_id.in_(participant_ids),
            CooperativeRoleProgress.deleted_at.is_(None),
        )
        .values(deleted_at=deleted_at)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        update(CooperativeMissionParticipant)
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress.id,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
        .values(deleted_at=deleted_at)
        .execution_options(synchronize_session=False)
    )
    progress.deleted_at = deleted_at


def _hand_over_host(
    db: Session,
    leaving_host: CooperativeMissionParticipant,
    accepted_participants: list[CooperativeMissionParticipant],
) -> None:
    """방장이 나간 자리를 남은 `ACCEPTED` 팀원에게 넘긴다.

    `_find_accepted_participants()` 가 이미 승계 순서로 정렬해 두었으므로 맨 앞을 고른다.
    진행도의 단계/상태/팀 토큰은 그대로 둔다.
    """
    next_host = next(
        (
            candidate
            for candidate in accepted_participants
            if candidate.id != leaving_host.id
        ),
        None,
    )
    if next_host is None:
        # 마지막 참가자 판정을 먼저 하므로 여기까지 오면 데이터가 어긋난 상황이다.
        raise RuntimeError(
            f"진행도 {leaving_host.cooperative_mission_progress_id} 의 방장을 넘길 참가자가 없습니다."
        )

    next_host.participant_role = ParticipantRole.HOST.value
