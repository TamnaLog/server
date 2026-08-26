"""미션 도메인 비즈니스 로직.

기준 문서: app/mission/docs/API_SPEC.md, app/mission/docs/BUSINESS_RULES.md

유형별 세부 미션 모델은 app/mission/models.py 가 아니라 각 소유 도메인에서 직접 import한다.
세 도메인 모두 app/mission/models.py 의 `Mission` 을 import하므로,
반대 방향으로 다시 import하면 순환 참조가 된다.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.common import rewards
from app.cooperative_mission.models import CooperativeMission
from app.core.errors import NotFoundError
from app.culture_mission.models import CultureMission
from app.mission import reward_history
from app.mission.schemas import MissionHomeResponse, MissionStepResponse, MissionType
from app.treasure_mission.models import TreasureMission


MISSION_NOT_FOUND = "MISSION_NOT_FOUND"

# 미션 유형 → 조회할 유형별 세부 미션 모델
# 세부 미션 테이블마다 id 가 중복될 수 있으므로 유형으로 테이블을 먼저 정한다.
_DETAIL_MISSION_MODELS: dict[MissionType, type[CultureMission | CooperativeMission | TreasureMission]] = {
    MissionType.CULTURE: CultureMission,
    MissionType.COOPERATIVE: CooperativeMission,
    MissionType.TREASURE: TreasureMission,
}


def get_mission_home(
    db: Session, mission_type: MissionType, mission_id: int, current_user_id: int
) -> MissionHomeResponse:
    """미션 홈 조회.

    요청받은 유형의 세부 미션만 조회하고, 공통 미션(MISSION)에서 유형/제목/설명/단계를,
    세부 미션에서 보상 정보를 가져와 조합한다.

    보상은 전체가 아니라 아직 한 번도 지급되지 않은 것만 반환한다. 같은 미션을 여러 번
    진행할 수 있으므로 현재 사용자의 해당 미션 진행도 이력 전체를 기준으로 판단한다.
    """
    detail_mission = _get_detail_mission(db, mission_type, mission_id)
    mission = detail_mission.mission

    # 세부 미션이 참조하는 공통 미션의 유형이 요청 유형과 다르면 잘못 연결된 데이터다.
    if mission.mission_type != mission_type.value:
        raise NotFoundError(
            MISSION_NOT_FOUND,
            detail=(
                f"{mission_type.value} 미션 {mission_id} 의 공통 미션 유형이 "
                f"{mission.mission_type} 로 일치하지 않습니다."
            ),
        )

    granted = reward_history.get_granted_rewards(
        db, mission_type=mission_type, mission_id=mission_id, current_user_id=current_user_id
    )

    return MissionHomeResponse(
        id=detail_mission.id,
        mission_type=MissionType(mission.mission_type),
        mission_title=mission.mission_title,
        description=mission.description,
        remaining_reward=rewards.to_remaining_reward(db, detail_mission.reward_detail, granted),
        steps=_to_steps(mission.step_detail),
    )


def _get_detail_mission(
    db: Session, mission_type: MissionType, mission_id: int
) -> CultureMission | CooperativeMission | TreasureMission:
    """요청받은 유형의 세부 미션을 조회한다.

    다른 유형의 테이블은 조회하지 않는다. 같은 id의 다른 유형 미션이 있어도 404다.
    """
    detail_mission = db.get(_DETAIL_MISSION_MODELS[mission_type], mission_id)
    if detail_mission is None:
        raise NotFoundError(
            MISSION_NOT_FOUND,
            detail=f"{mission_type.value} 미션 {mission_id} 을(를) 찾을 수 없습니다.",
        )
    return detail_mission


def _to_steps(step_detail: list[dict[str, Any]] | None) -> list[MissionStepResponse]:
    """공통 미션의 단계 목록을 `step` 오름차순으로 반환한다."""
    steps = sorted(step_detail or [], key=lambda step: step["step"])
    return [
        MissionStepResponse(
            step=step["step"],
            step_title=step["step_title"],
            description=step["description"],
        )
        for step in steps
    ]
