"""협동 미션 보상 지급.

협동 미션은 개인이 아니라 **팀 단위**로 보상을 정산한다.
완료된 역할 수로 보상 등급을 정하고, 그 등급의 보상을 완료 시점의 `ACCEPTED` 참가자 **전원**에게
같은 등급으로 한 번만 지급한다.
(app/cooperative_mission/docs/BUSINESS_RULES_2.md - 13. 완료 역할 수에 따른 보상 / 14. 보상 정산)

| 완료 역할 수 | 지급 보상 |
| --- | --- |
| 0 | 없음 |
| 1~2 | AR 캐릭터 |
| 3~4 | AR 캐릭터, 포인트 |
| 5~6 | AR 캐릭터, 포인트, 쿠폰 |

| 보상 | 저장 위치 |
| --- | --- |
| AR 캐릭터 | `ACQUIRED_AR_CHARACTER` 에 참가자별 획득 기록 추가 |
| 포인트 | 참가자별 `USER.point` 에 누적 |
| 쿠폰 | 별도 보관 테이블이 없어 진행도의 지급 여부만 기록하고 응답으로 내려준다 |

정산이 끝나면 등급에 들지 못해 **소멸한 보상까지 포함해** 진행도의 지급 여부 세 개를 모두 `TRUE` 로
바꾼다. 이후 폴링은 추가 지급 없이 같은 등급의 보상 정보만 다시 조합해서 응답한다.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.rewards import (
    GrantedRewardResponse,
    RewardItem,
    to_ar_character,
    to_coupon,
)
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    CooperativeRoleProgress,
    MissionStatus,
    ParticipantStatus,
)
from app.treasure_mission.models import AcquiredArCharacter
from app.user.models import User


# 완료 역할 수 → 지급 보상 등급. (완료 역할이 0개면 아무 보상도 없다)
REWARD_GRADES: tuple[tuple[int, tuple[RewardItem, ...]], ...] = (
    (1, (RewardItem.AR_CHARACTER,)),
    (3, (RewardItem.AR_CHARACTER, RewardItem.POINT)),
    (5, (RewardItem.AR_CHARACTER, RewardItem.POINT, RewardItem.COUPON)),
)


def settle_cooperative_mission_reward(
    db: Session,
    progress: CooperativeMissionProgress,
    cooperative_mission: CooperativeMission,
    completed_role_count: int,
) -> GrantedRewardResponse:
    """완료한 협동 미션의 보상을 정산하고 이 사용자에게 보여줄 보상 정보를 반환한다.

    아직 정산 전이면 `ACCEPTED` 참가자 전원에게 지급하고 지급 여부를 마감한다.
    이미 정산이 끝났으면 아무것도 바꾸지 않고 같은 등급의 보상 정보만 조합한다.
    (커밋은 이 함수에서 한 번만 한다. 실패하면 참가자 전원의 지급을 함께 되돌린다)
    """
    reward = cooperative_mission.reward_detail or {}
    grade = _reward_grade(completed_role_count)

    if not _is_settled(progress):
        try:
            _grant_to_participants(db, progress.id, cooperative_mission, reward, grade)
            _close_reward_grant(progress)
            db.commit()
        except Exception:
            # 일부 참가자만 받은 상태로 지급 여부가 마감되면 안 된다.
            db.rollback()
            raise

    return _to_reward_response(db, reward, grade)


def _reward_grade(completed_role_count: int) -> tuple[RewardItem, ...]:
    """완료 역할 수에 해당하는 보상 등급을 구한다."""
    grade: tuple[RewardItem, ...] = ()
    for minimum_count, items in REWARD_GRADES:
        if completed_role_count >= minimum_count:
            grade = items
    return grade


def _is_settled(progress: CooperativeMissionProgress) -> bool:
    """이미 정산이 끝났는지. 세 지급 여부가 모두 `TRUE` 면 마감된 것으로 본다."""
    return (
        progress.ar_character_reward_granted
        and progress.point_reward_granted
        and progress.coupon_reward_granted
    )


def _close_reward_grant(progress: CooperativeMissionProgress) -> None:
    """지급 여부를 마감한다. 등급에 들지 못해 소멸한 보상도 함께 `TRUE` 로 바꾼다."""
    progress.ar_character_reward_granted = True
    progress.point_reward_granted = True
    progress.coupon_reward_granted = True


def _grant_to_participants(
    db: Session,
    progress_id: int,
    cooperative_mission: CooperativeMission,
    reward: dict[str, Any],
    grade: tuple[RewardItem, ...],
) -> None:
    """완료 시점의 `ACCEPTED` 참가자 전원에게 같은 등급의 보상을 지급한다."""
    if not grade:
        return

    user_ids = db.scalars(
        select(CooperativeMissionParticipant.user_id).where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
    ).all()

    for user_id in user_ids:
        if RewardItem.AR_CHARACTER in grade:
            _grant_ar_character(db, user_id, cooperative_mission, reward)
        if RewardItem.POINT in grade:
            _grant_point(db, user_id, reward)
        # 쿠폰은 저장할 테이블이 없어 진행도의 지급 여부로만 남긴다.


def _grant_ar_character(
    db: Session, user_id: int, cooperative_mission: CooperativeMission, reward: dict[str, Any]
) -> None:
    """AR 캐릭터 획득 기록을 남긴다.

    `(user_id, ar_character_id)` 가 UNIQUE 라 이미 가지고 있으면 기록을 추가하지 않는다.
    획득 기록에는 협동 미션 id가 아니라 공통 `MISSION.id` 를 남긴다.
    """
    ar_character_id = reward.get("ar_character_id")
    if not ar_character_id or to_ar_character(db, ar_character_id) is None:
        return

    already_acquired = db.scalar(
        select(AcquiredArCharacter.id)
        .where(
            AcquiredArCharacter.user_id == user_id,
            AcquiredArCharacter.ar_character_id == ar_character_id,
        )
        .limit(1)
    )
    if already_acquired is not None:
        return

    db.add(
        AcquiredArCharacter(
            ar_character_id=ar_character_id,
            user_id=user_id,
            acquired_mission_id=cooperative_mission.mission_id,
        )
    )


def _grant_point(db: Session, user_id: int, reward: dict[str, Any]) -> None:
    """포인트를 참가자에게 누적한다."""
    point = reward.get("point") or 0
    if point <= 0:
        return

    user = db.get(User, user_id)
    if user is None:
        # 사용자 데이터가 없으면 누적할 곳이 없다.
        return

    user.point += point


def _to_reward_response(
    db: Session, reward: dict[str, Any], grade: tuple[RewardItem, ...]
) -> GrantedRewardResponse:
    """등급에 든 보상만 채운 응답을 만든다. `reward_detail` 에 없는 보상은 `null` 이다."""
    point = reward.get("point") or 0
    return GrantedRewardResponse(
        ar_character=(
            to_ar_character(db, reward.get("ar_character_id"))
            if RewardItem.AR_CHARACTER in grade
            else None
        ),
        point=point if RewardItem.POINT in grade and point > 0 else None,
        coupon=to_coupon(reward) if RewardItem.COUPON in grade else None,
    )


def count_completed_roles(db: Session, progress_id: int) -> int:
    """이 방에서 인증까지 끝난 역할 진행도 수를 센다."""
    statement = (
        select(CooperativeRoleProgress.id)
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.id == CooperativeRoleProgress.participant_id,
        )
        .where(
            CooperativeMissionParticipant.cooperative_mission_progress_id == progress_id,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeRoleProgress.progress_status == MissionStatus.COMPLETED.value,
            CooperativeRoleProgress.deleted_at.is_(None),
        )
    )
    return len(db.scalars(statement).all())
