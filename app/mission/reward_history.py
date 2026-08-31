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
    rows = db.execute(_granted_flags_query(mission_type, mission_id, current_user_id)).all()
    return GrantedRewards(
        ar_character=any(row.ar_character_reward_granted for row in rows),
        point=any(row.point_reward_granted for row in rows),
        coupon=any(row.coupon_reward_granted for row in rows),
    )


def _granted_flags_query(
    mission_type: MissionType, mission_id: int, current_user_id: int
) -> Select[tuple[bool, bool, bool]]:
    """유형별 진행도 테이블에서 보상 지급 여부 컬럼만 조회하는 쿼리를 만든다."""
    if mission_type is MissionType.CULTURE:
        return select(
            CultureMissionProgress.ar_character_reward_granted,
            CultureMissionProgress.point_reward_granted,
            CultureMissionProgress.coupon_reward_granted,
        ).where(
            CultureMissionProgress.culture_mission_id == mission_id,
            CultureMissionProgress.user_id == current_user_id,
        )

    if mission_type is MissionType.TREASURE:
        return select(
            TreasureMissionProgress.ar_character_reward_granted,
            TreasureMissionProgress.point_reward_granted,
            TreasureMissionProgress.coupon_reward_granted,
        ).where(
            TreasureMissionProgress.treasure_mission_id == mission_id,
            TreasureMissionProgress.user_id == current_user_id,
        )

    # 협동 미션 진행도는 사용자 정보를 직접 갖지 않고 참여자 테이블로 연결된다.
    return (
        select(
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
            CooperativeMissionProgress.cooperative_mission_id == mission_id,
            CooperativeMissionProgress.deleted_at.is_(None),
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
    )
