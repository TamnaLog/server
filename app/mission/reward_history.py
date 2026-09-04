"""미션 보상 지급 이력 조회.

미션 홈 조회는 "아직 한 번도 지급되지 않은 보상"만 반환한다. (BUSINESS_RULES.md 4~5장)
같은 미션을 여러 번 진행할 수 있으므로 가장 최근 진행도 하나가 아니라
해당 미션의 **모든 진행도 이력**을 기준으로 판단한다.

유형마다 진행도 테이블과 사용자 연결 방식이 달라서 조회 기준을 이 모듈에 모아 둔다.

| `missionType` | 진행도 테이블 | 사용자 연결 |
| --- | --- | --- |
| `CULTURE` | `CULTURE_MISSION_PROGRESS` | `user_id` |
| `TREASURE` | `TREASURE_MISSION_PROGRESS` | `user_id` |
| `COOPERATIVE` | `COOPERATIVE_MISSION_PROGRESS` | `COOPERATIVE_MISSION_PARTICIPANT.user_id` (수락된 참가자만) |
"""

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.common.rewards import GrantedRewards
from app.cooperative_mission.models import (
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMissionProgress
from app.mission.schemas import MissionType
from app.treasure_mission.models import TreasureMissionProgress


def get_granted_rewards(
    db: Session, mission_type: MissionType, mission_id: int, current_user_id: int
) -> GrantedRewards:
    """해당 미션에서 현재 사용자에게 한 번이라도 지급된 보상을 조회한다.

    진행도 이력이 하나도 없으면 세 보상 모두 아직 지급되지 않은 것으로 본다.
    """
    granted = get_granted_rewards_map(db, mission_type, [mission_id], current_user_id)
    return granted.get(mission_id, GrantedRewards())


def get_granted_rewards_map(
    db: Session,
    mission_type: MissionType,
    mission_ids: Sequence[int],
    current_user_id: int,
) -> dict[int, GrantedRewards]:
    """여러 미션의 보상 지급 이력을 한 번에 조회한다. `세부 미션 id → 지급 이력`.

    미션마다 따로 조회하지 않아야 하는 목록 응답에서 쓴다. (N+1 방지)
    진행도 이력이 없는 미션은 결과에 들어가지 않는다. (= 세 보상 모두 미지급)
    """
    if not mission_ids:
        return {}

    granted: dict[int, GrantedRewards] = {}
    rows = db.execute(_granted_flags_query(mission_type, mission_ids, current_user_id)).all()
    for row in rows:
        before = granted.get(row.mission_id, GrantedRewards())
        granted[row.mission_id] = GrantedRewards(
            # 같은 미션의 진행도가 여러 건이면 보상별로 OR 한다.
            ar_character=before.ar_character or row.ar_character_reward_granted,
            point=before.point or row.point_reward_granted,
            coupon=before.coupon or row.coupon_reward_granted,
        )
    return granted


def _granted_flags_query(
    mission_type: MissionType, mission_ids: Sequence[int], current_user_id: int
) -> Select[tuple[int, bool, bool, bool]]:
    """유형별 진행도 테이블에서 세부 미션 id 와 보상 지급 여부 컬럼만 조회하는 쿼리를 만든다."""
    if mission_type is MissionType.CULTURE:
        return select(
            CultureMissionProgress.culture_mission_id.label("mission_id"),
            CultureMissionProgress.ar_character_reward_granted,
            CultureMissionProgress.point_reward_granted,
            CultureMissionProgress.coupon_reward_granted,
        ).where(
            CultureMissionProgress.culture_mission_id.in_(mission_ids),
            CultureMissionProgress.user_id == current_user_id,
        )

    if mission_type is MissionType.TREASURE:
        return select(
            TreasureMissionProgress.treasure_mission_id.label("mission_id"),
            TreasureMissionProgress.ar_character_reward_granted,
            TreasureMissionProgress.point_reward_granted,
            TreasureMissionProgress.coupon_reward_granted,
        ).where(
            TreasureMissionProgress.treasure_mission_id.in_(mission_ids),
            TreasureMissionProgress.user_id == current_user_id,
        )

    # 협동 미션 진행도는 사용자 정보를 직접 갖지 않고 참여자 테이블로 연결된다.
    return (
        select(
            CooperativeMissionProgress.cooperative_mission_id.label("mission_id"),
            CooperativeMissionProgress.ar_character_reward_granted,
            CooperativeMissionProgress.point_reward_granted,
            CooperativeMissionProgress.coupon_reward_granted,
        )
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.cooperative_mission_progress_id
            == CooperativeMissionProgress.id,
        )
        .where(
            CooperativeMissionProgress.cooperative_mission_id.in_(mission_ids),
            CooperativeMissionProgress.deleted_at.is_(None),
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
    )
