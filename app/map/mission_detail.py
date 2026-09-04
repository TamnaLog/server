"""지도 응답의 미션 상세 조합.

지도 모달 조회와 장소 상세 조회가 같은 미션 정보를 내려주므로 조합 규칙을 여기 모은다.
(app/map/docs/BUSINESS_RULES.md - 지도 장소 상세 조회 4. 공통 미션 상세 조합 규칙)

응답 필드는 API 마다 조금씩 다르지만(모달에는 설명이 없고 추천 미션에는 장소 이미지가 붙는다)
완료 이력과 보상 지급 이력을 읽는 규칙은 같다. 그래서 여기서는 공통 값만 만들고
응답 스키마로 바꾸는 일은 각 API 가 한다.

장소를 참조하는 미션은 보물찾기와 협동뿐이다. (문화 미션은 장소를 갖지 않는다)
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.common import rewards
from app.common.rewards import GrantedRewards
from app.cooperative_mission.models import CooperativeMission
from app.map import location_missions
from app.map.schemas import MapRewardDetailResponse
from app.mission import reward_history
from app.mission.completion import is_mission_completed
from app.mission.models import Mission
from app.mission.schemas import MissionType
from app.treasure_mission.models import TreasureMission


@dataclass(frozen=True)
class MissionDetail:
    """지도 응답에 넣을 미션 한 건."""

    # 공통 MISSION.id 가 아니라 유형별 세부 미션 테이블의 id
    mission_id: int
    mission_type: MissionType
    mission_title: str
    description: str | None
    is_completed: bool
    reward_detail: MapRewardDetailResponse
    # 미션이 진행되는 장소. 추천 미션은 각각 다른 장소라 장소명과 이미지를 함께 준다.
    location_title: str
    # 장소의 TourAPI content id. (대표 이미지 조회용)
    location_content_id: int


def find_location_mission(
    db: Session, current_user_id: int, location_id: int
) -> MissionDetail | None:
    """장소에 연결된 미션 하나를 조합한다. 연결된 미션이 없으면 `None`.

    한 장소에 두 유형이 함께 연결된 상태는 데이터 무결성 문제라, 임의로 하나를 고르지 않고
    예외를 올려 500 으로 드러낸다.
    """
    found = {
        MissionType.TREASURE: location_missions.find_treasure_missions(
            db, [location_id]
        ).get(location_id),
        MissionType.COOPERATIVE: location_missions.find_cooperative_missions(
            db, [location_id]
        ).get(location_id),
    }
    matched = [
        (mission_type, location_mission)
        for mission_type, location_mission in found.items()
        if location_mission is not None
    ]
    if not matched:
        return None
    if len(matched) > 1:
        raise RuntimeError(f"장소 {location_id} 에 미션이 여러 유형으로 연결돼 있습니다.")

    mission_type, location_mission = matched[0]
    return build(db, current_user_id, mission_type, location_mission.id)


def build(
    db: Session, current_user_id: int, mission_type: MissionType, mission_id: int
) -> MissionDetail | None:
    """세부 미션 id 로 미션 상세를 조합한다.

    공통 미션이 없거나 유형이 세부 미션과 어긋나는 데이터는 정상 미션으로 보지 않고 `None`.
    조회만 하고 보상을 지급하거나 지급 여부를 바꾸지 않는다.
    """
    detail_mission: TreasureMission | CooperativeMission | None = (
        db.get(TreasureMission, mission_id)
        if mission_type is MissionType.TREASURE
        else db.get(CooperativeMission, mission_id)
    )
    if detail_mission is None:
        return None

    mission = db.get(Mission, detail_mission.mission_id)
    if mission is None or mission.mission_type != mission_type.value:
        return None

    granted = reward_history.get_granted_rewards(
        db, mission_type, detail_mission.id, current_user_id
    )
    return MissionDetail(
        mission_id=detail_mission.id,
        mission_type=mission_type,
        mission_title=mission.mission_title,
        description=mission.description,
        # 완료 여부와 보상 수령 여부는 서로 독립적으로 계산한다.
        is_completed=is_mission_completed(db, current_user_id, mission),
        reward_detail=to_reward_detail(db, detail_mission.reward_detail, granted),
        location_title=detail_mission.location.location_title,
        location_content_id=detail_mission.location.content_id,
    )


def to_reward_detail(
    db: Session, reward_detail: dict[str, Any] | None, granted: GrantedRewards
) -> MapRewardDetailResponse:
    """미션에 설정된 보상 전체와 현재 사용자의 수령 여부를 함께 담는다.

    같은 형식을 여행 마무리 엽서 요소 조회도 쓰므로 조합은 공용 모듈이 한다.
    """
    return rewards.to_full_reward_detail(db, reward_detail, granted)
