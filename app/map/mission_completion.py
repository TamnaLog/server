"""사용자별 미션 완료 판정.

지도 홈 조회(`isCompleted`)와 장소 상세의 추천 미션(완료한 미션 제외)이
같은 기준으로 판단해야 해서 한 곳에 모아 둔다.

- 보물찾기: 현재 사용자의 `COMPLETED` 진행도가 하나라도 있으면 완료
- 협동 미션: 현재 사용자의 삭제되지 않은 `ACCEPTED` 참가자와
  삭제되지 않은 `COMPLETED` 진행도가 연결되어 있으면 완료

여러 번 진행한 이력이 있어도 완료가 하나라도 있으면 완료로 본다.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cooperative_mission.models import (
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantStatus,
)
from app.mission.models import MissionStatus
from app.treasure_mission.models import TreasureMissionProgress


def find_completed_treasure_mission_ids(
    db: Session, current_user_id: int, treasure_mission_ids: list[int]
) -> set[int]:
    """현재 사용자가 완료한 보물찾기 미션 id 를 한 번에 조회한다."""
    if not treasure_mission_ids:
        return set()

    statement = select(TreasureMissionProgress.treasure_mission_id).where(
        TreasureMissionProgress.treasure_mission_id.in_(treasure_mission_ids),
        TreasureMissionProgress.user_id == current_user_id,
        TreasureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
    )
    return set(db.scalars(statement).all())


def find_completed_cooperative_mission_ids(
    db: Session, current_user_id: int, cooperative_mission_ids: list[int]
) -> set[int]:
    """현재 사용자가 완료한 협동 미션 id 를 한 번에 조회한다.

    협동 미션 진행도에는 사용자가 없어서 참가자를 거쳐 현재 사용자와 연결한다.
    나간 참가자와 삭제된 방은 완료 이력으로 보지 않는다.
    """
    if not cooperative_mission_ids:
        return set()

    statement = (
        select(CooperativeMissionProgress.cooperative_mission_id)
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.cooperative_mission_progress_id
            == CooperativeMissionProgress.id,
        )
        .where(
            CooperativeMissionProgress.cooperative_mission_id.in_(cooperative_mission_ids),
            CooperativeMissionProgress.mission_status == MissionStatus.COMPLETED.value,
            CooperativeMissionProgress.deleted_at.is_(None),
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
    )
    return set(db.scalars(statement).all())
