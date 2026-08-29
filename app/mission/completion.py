"""미션 완료 이력 판정.

"이 사용자가 이 미션을 완료한 적이 있는가"는 미션 유형마다 진행도 테이블과 사용자 연결이 달라서
호출하는 쪽(방명록 등)이 JOIN 구조를 알 필요가 없도록 여기로 모은다.
(app/guestbook/docs/BUSINESS_RULES.md - B.5 일반 방명록 미션 처리)

| `missionType` | 완료 이력 |
| --- | --- |
| `CULTURE` | `CULTURE_MISSION_PROGRESS.user_id` 로 직접 연결 |
| `TREASURE` | `TREASURE_MISSION_PROGRESS.user_id` 로 직접 연결 |
| `COOPERATIVE` | `COOPERATIVE_MISSION_PARTICIPANT` 를 거쳐 연결 (수락된 참가자만) |

완료 여부는 보상 지급 여부가 아니라 `mission_status = COMPLETED` 이력으로 판단한다.
여러 번 도전한 미션은 완료 이력이 하나라도 있으면 완료로 본다.
"""

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.mission.models import Mission, MissionStatus, MissionType
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress


def is_mission_completed(db: Session, current_user_id: int, mission: Mission) -> bool:
    """현재 사용자가 이 공통 미션을 완료한 적이 있는지."""
    statement = _completed_progress_query(mission, current_user_id)
    if statement is None:
        return False

    return db.scalar(statement.limit(1)) is not None


def _completed_progress_query(
    mission: Mission, current_user_id: int
) -> Select[tuple[int]] | None:
    """미션 유형에 맞는 완료 이력 조회 쿼리를 만든다. 모르는 유형이면 `None`."""
    if mission.mission_type == MissionType.CULTURE.value:
        return (
            select(CultureMissionProgress.id)
            .join(
                CultureMission,
                CultureMission.id == CultureMissionProgress.culture_mission_id,
            )
            .where(
                CultureMission.mission_id == mission.id,
                CultureMissionProgress.user_id == current_user_id,
                CultureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
            )
        )

    if mission.mission_type == MissionType.TREASURE.value:
        return (
            select(TreasureMissionProgress.id)
            .join(
                TreasureMission,
                TreasureMission.id == TreasureMissionProgress.treasure_mission_id,
            )
            .where(
                TreasureMission.mission_id == mission.id,
                TreasureMissionProgress.user_id == current_user_id,
                TreasureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
            )
        )

    if mission.mission_type == MissionType.COOPERATIVE.value:
        # 협동 미션 진행도는 사용자 정보를 직접 갖지 않고 참여자 테이블로 연결된다.
        return (
            select(CooperativeMissionProgress.id)
            .join(
                CooperativeMission,
                CooperativeMission.id
                == CooperativeMissionProgress.cooperative_mission_id,
            )
            .join(
                CooperativeMissionParticipant,
                CooperativeMissionParticipant.cooperative_mission_progress_id
                == CooperativeMissionProgress.id,
            )
            .where(
                CooperativeMission.mission_id == mission.id,
                CooperativeMissionProgress.mission_status
                == MissionStatus.COMPLETED.value,
                CooperativeMissionProgress.deleted_at.is_(None),
                CooperativeMissionParticipant.user_id == current_user_id,
                CooperativeMissionParticipant.participant_status
                == ParticipantStatus.ACCEPTED.value,
                CooperativeMissionParticipant.deleted_at.is_(None),
            )
        )

    return None
