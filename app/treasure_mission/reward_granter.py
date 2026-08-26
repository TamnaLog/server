"""보물찾기 미션 보상 지급.

보물 하나를 새로 찾을 때마다 **지급 가능한 보상 항목을 최대 하나** 지급한다.
완료 시점에 모아서 주지 않고 각 보물 발견 요청에서 즉시 지급한다.
(app/treasure_mission/docs/BUSINESS_RULES.md - 4~6)

| 보상 | 저장 위치 |
| --- | --- |
| AR 캐릭터 | `ACQUIRED_AR_CHARACTER` 에 획득 기록 추가 |
| 포인트 | `USER.point` 에 누적 |
| 쿠폰 | 별도 보관 테이블이 없어 진행도의 지급 여부만 기록하고 응답으로 내려준다 |

지급 규칙:

- 지급 순서는 AR 캐릭터 → 포인트 → 쿠폰이다.
  (후보 계산은 미션 유형과 무관하므로 `app/common/rewards.py` 의 `remaining_reward_items()` 를 쓴다)
- 같은 사용자/보물찾기 미션의 **모든 진행도 이력**에서 이미 지급된 항목과
  `reward_detail` 에 없는 항목은 후보에서 빠진다. (재도전해도 같은 보상을 다시 주지 않는다)
- 실제로 지급한 항목만 현재 진행도의 지급 여부 컬럼을 `true` 로 바꾼다.

커밋은 하지 않는다. 보물 발견 저장과 보상 지급이 한 트랜잭션으로 묶이도록
호출한 service 에서 한 번만 커밋한다.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.rewards import (
    ArCharacterResponse,
    CouponResponse,
    GrantedRewardResponse,
    RewardItem,
    remaining_reward_items,
    to_ar_character,
    to_coupon,
)
from app.mission.schemas import MissionType
from app.mission import reward_history
from app.treasure_mission.models import (
    AcquiredArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User


def grant_next_treasure_reward(
    db: Session, progress: TreasureMissionProgress, treasure_mission: TreasureMission
) -> GrantedRewardResponse:
    """보물 하나를 찾은 대가로 남은 보상 중 우선순위가 가장 높은 하나를 지급한다.

    지급할 보상이 남아 있지 않으면 항목이 모두 `null` 인 응답을 반환한다.
    """
    reward = treasure_mission.reward_detail or {}
    granted_before = reward_history.get_granted_rewards(
        db,
        mission_type=MissionType.TREASURE,
        mission_id=progress.treasure_mission_id,
        current_user_id=progress.user_id,
    )

    candidates = remaining_reward_items(db, reward, granted_before)
    if not candidates:
        return GrantedRewardResponse()

    next_item = candidates[0]
    if next_item is RewardItem.AR_CHARACTER:
        return GrantedRewardResponse(
            ar_character=_grant_ar_character(db, progress, treasure_mission, reward)
        )
    if next_item is RewardItem.POINT:
        return GrantedRewardResponse(point=_grant_point(db, progress, reward))
    return GrantedRewardResponse(coupon=_grant_coupon(progress, reward))


def _grant_ar_character(
    db: Session,
    progress: TreasureMissionProgress,
    treasure_mission: TreasureMission,
    reward: dict[str, Any],
) -> ArCharacterResponse | None:
    """AR 캐릭터 획득 기록을 남긴다.

    같은 캐릭터를 여러 미션 보상으로 줄 수 있고 `(user_id, ar_character_id)` 가 UNIQUE 라,
    이미 가지고 있으면 기록만 추가하지 않고 이번 미션의 보상 지급 자체는 성립한 것으로 본다.
    획득 기록에는 보물찾기 미션 id가 아니라 공통 `MISSION.id` 를 남긴다.
    """
    ar_character_id = reward["ar_character_id"]
    already_acquired = db.scalar(
        select(AcquiredArCharacter.id)
        .where(
            AcquiredArCharacter.user_id == progress.user_id,
            AcquiredArCharacter.ar_character_id == ar_character_id,
        )
        .limit(1)
    )
    if already_acquired is None:
        db.add(
            AcquiredArCharacter(
                ar_character_id=ar_character_id,
                user_id=progress.user_id,
                acquired_mission_id=treasure_mission.mission_id,
            )
        )

    progress.ar_character_reward_granted = True
    return to_ar_character(db, ar_character_id)


def _grant_point(
    db: Session, progress: TreasureMissionProgress, reward: dict[str, Any]
) -> int | None:
    """포인트를 사용자에게 누적한다. 실제로 더한 값을 반환한다."""
    user = db.get(User, progress.user_id)
    if user is None:
        # 사용자 데이터가 없으면 누적할 곳이 없으므로 지급하지 않은 것으로 둔다.
        return None

    point = reward["point"]
    user.point += point
    progress.point_reward_granted = True
    return point


def _grant_coupon(
    progress: TreasureMissionProgress, reward: dict[str, Any]
) -> CouponResponse | None:
    """쿠폰은 저장할 테이블이 없어 진행도에 지급 여부만 기록한다."""
    progress.coupon_reward_granted = True
    return to_coupon(reward)
