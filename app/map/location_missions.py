"""장소에 연결된 유형별 세부 미션 조회.

지도 홈 조회(장소 마커의 미션 정보)와 검색 결과 조회(미션 장소 분류)가
같은 정보를 쓰기 때문에 한 곳에 모아 둔다.

장소마다 미션을 다시 조회하면 N+1 이 되므로 항상 장소 id 목록으로 한 번에 가져온다.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.cooperative_mission.models import CooperativeMission
from app.mission.models import Mission
from app.treasure_mission.models import TreasureMission


@dataclass(frozen=True)
class LocationMission:
    """장소에 연결된 유형별 세부 미션."""

    # 공통 MISSION.id 가 아니라 유형별 세부 미션 테이블의 id
    id: int
    # 공통 MISSION.id. 방명록(`GUESTBOOK.mission_id`)이 참조하는 값이다.
    mission_id: int
    mission_title: str


def find_treasure_missions(
    db: Session, location_ids: list[int]
) -> dict[int, LocationMission]:
    """장소 id → 보물찾기 미션을 한 번에 조회한다."""
    statement = (
        select(
            TreasureMission.location_id,
            TreasureMission.id,
            TreasureMission.mission_id,
            Mission.mission_title,
        )
        .join(Mission, Mission.id == TreasureMission.mission_id)
        .where(TreasureMission.location_id.in_(location_ids))
        .order_by(TreasureMission.id)
    )
    return _to_missions_by_location(db, statement, location_ids)


def find_cooperative_missions(
    db: Session, location_ids: list[int]
) -> dict[int, LocationMission]:
    """장소 id → 협동 미션을 한 번에 조회한다."""
    statement = (
        select(
            CooperativeMission.location_id,
            CooperativeMission.id,
            CooperativeMission.mission_id,
            Mission.mission_title,
        )
        .join(Mission, Mission.id == CooperativeMission.mission_id)
        .where(CooperativeMission.location_id.in_(location_ids))
        .order_by(CooperativeMission.id)
    )
    return _to_missions_by_location(db, statement, location_ids)


def _to_missions_by_location(
    db: Session, statement: Select[Any], location_ids: list[int]
) -> dict[int, LocationMission]:
    """조회 결과를 장소 id 기준으로 묶는다.

    한 장소에 같은 유형의 미션은 하나뿐이라는 전제라, 혹시 여러 건이면 id 가 작은 쪽을 쓴다.
    """
    if not location_ids:
        return {}

    missions: dict[int, LocationMission] = {}
    for location_id, mission_id, common_mission_id, mission_title in db.execute(
        statement
    ).all():
        missions.setdefault(
            location_id,
            LocationMission(
                id=mission_id, mission_id=common_mission_id, mission_title=mission_title
            ),
        )
    return missions
