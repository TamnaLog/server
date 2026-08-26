"""미션 보상 지급 모듈.

미션을 완료했을 때 `reward_detail` 의 보상을 실제 데이터에 반영한다.
보상 형태는 미션 유형과 무관하게 같으므로 공용 모듈에 한 번만 두고 각 도메인에서 import해서 쓴다.

| 보상 | 저장 위치 |
| --- | --- |
| 포인트 | `USER.point` 에 누적 |
| AR 캐릭터 | `ACQUIRED_AR_CHARACTER` 에 획득 기록 추가 |
| 쿠폰 | 저장할 테이블이 없어 기록하지 않는다 |

이 모듈은 **"지금 지급한다"만 책임진다.** 재도전처럼 이미 보상을 받은 사용자에게
다시 지급하면 안 되는 판단은 각 도메인의 진행 이력(`COMPLETED` 진행도 존재 여부)으로
호출하는 쪽에서 결정한다.

커밋은 하지 않는다. 미션 완료 처리와 보상 지급이 한 트랜잭션으로 묶이도록
호출한 service 에서 한 번만 커밋한다.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.treasure_mission.models import AcquiredArCharacter, ArCharacter
from app.user.models import User


@dataclass(frozen=True)
class GrantedReward:
    """실제로 지급된 보상. 지급하지 않은 항목은 0 / None 이다."""

    point: int = 0
    ar_character_id: int | None = None


def grant_mission_reward(
    db: Session, user_id: int, mission_id: int, reward_detail: dict[str, Any] | None
) -> GrantedReward:
    """미션 보상을 사용자 데이터에 반영한다.

    `mission_id` 는 유형별 세부 미션 id가 아니라 획득 기록에 남길 공통 `MISSION.id` 다.
    """
    reward = reward_detail or {}
    return GrantedReward(
        point=_grant_point(db, user_id, reward.get("point") or 0),
        ar_character_id=_grant_ar_character(db, user_id, mission_id, reward.get("ar_character_id")),
    )


def _grant_point(db: Session, user_id: int, point: int) -> int:
    """포인트를 사용자에게 누적한다. 실제로 더한 값을 반환한다."""
    if point <= 0:
        return 0

    user = db.get(User, user_id)
    if user is None:
        return 0

    user.point += point
    return point


def _grant_ar_character(
    db: Session, user_id: int, mission_id: int, ar_character_id: int | None
) -> int | None:
    """AR 캐릭터 획득 기록을 남긴다. 실제로 기록한 캐릭터 id를 반환한다.

    같은 캐릭터를 여러 미션에서 보상으로 줄 수 있고 `(user_id, ar_character_id)` 가 UNIQUE 라,
    이미 가지고 있으면 기록을 추가하지 않는다.
    """
    if not ar_character_id:
        return None

    if db.get(ArCharacter, ar_character_id) is None:
        # 보상에 적힌 캐릭터가 삭제된 경우. 미션 완료 자체를 실패시키지 않는다.
        return None

    already_acquired = db.scalar(
        select(AcquiredArCharacter.id)
        .where(
            AcquiredArCharacter.user_id == user_id,
            AcquiredArCharacter.ar_character_id == ar_character_id,
        )
        .limit(1)
    )
    if already_acquired is not None:
        return None

    db.add(
        AcquiredArCharacter(
            ar_character_id=ar_character_id,
            user_id=user_id,
            acquired_mission_id=mission_id,
        )
    )
    return ar_character_id
