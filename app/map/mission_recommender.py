"""장소 상세의 "근처에서 할 수 있는 미션" 추천 모듈.

추천 기준이 확정되기 전까지는 현재 사용자가 아직 완료하지 않은 미션 중
랜덤으로 최대 3개를 고른다. 기준이 정해지면 이 모듈 안만 바꾸면 된다.
(app/map/docs/BUSINESS_RULES.md - 지도 장소 상세 조회 5. 임시 추천 미션)

이 모듈은 "어떤 미션을 보여줄지" 고르는 일만 한다.
제목·설명·완료 여부·보상 같은 응답 값은 `app/map/mission_detail.py` 가 조합한다.

추천 대상은 장소를 가진 보물찾기와 협동 미션이다.
문화 미션은 장소를 참조하지 않아 후보가 아니고, 지금 보고 있는 장소의 미션도 후보에 넣는다.
"""

import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import mission_completion
from app.cooperative_mission.models import CooperativeMission
from app.mission.schemas import MissionType
from app.treasure_mission.models import TreasureMission


# 장소 상세에 노출할 추천 미션 개수
RECOMMEND_COUNT = 3


@dataclass(frozen=True)
class RecommendedMission:
    """추천된 미션. 유형별 세부 미션 한 행을 가리키는 값이다."""

    # 공통 MISSION.id 가 아니라 유형별 세부 미션 테이블의 id
    id: int
    mission_type: MissionType


def recommend_nearby_missions(
    db: Session, current_user_id: int, count: int = RECOMMEND_COUNT
) -> list[RecommendedMission]:
    """현재 사용자가 완료하지 않은 미션 중 최대 `count` 개를 무작위로 고른다.

    후보가 `count` 보다 적으면 있는 만큼만, 하나도 없으면 빈 배열을 반환한다.
    같은 미션이 두 번 나오지 않는다.
    """
    # TODO: 추천 기준 확정 시 사용자 위치/취향 기반 추천 로직으로 교체
    candidates = _load_candidates(db, current_user_id)
    if len(candidates) > count:
        candidates = random.sample(candidates, count)

    return candidates


def _load_candidates(db: Session, current_user_id: int) -> list[RecommendedMission]:
    """완료하지 않은 추천 후보를 모은다."""
    treasure = _load_missions(db, TreasureMission, MissionType.TREASURE)
    cooperative = _load_missions(db, CooperativeMission, MissionType.COOPERATIVE)

    completed_treasure_ids = mission_completion.find_completed_treasure_mission_ids(
        db, current_user_id, [candidate.id for candidate in treasure]
    )
    completed_cooperative_ids = mission_completion.find_completed_cooperative_mission_ids(
        db, current_user_id, [candidate.id for candidate in cooperative]
    )

    return [
        *(
            candidate
            for candidate in treasure
            if candidate.id not in completed_treasure_ids
        ),
        *(
            candidate
            for candidate in cooperative
            if candidate.id not in completed_cooperative_ids
        ),
    ]


def _load_missions(
    db: Session,
    mission_model: type[CooperativeMission] | type[TreasureMission],
    mission_type: MissionType,
) -> list[RecommendedMission]:
    """유형별 세부 미션 id 를 읽어온다."""
    statement = select(mission_model.id).order_by(mission_model.id)
    return [
        RecommendedMission(id=mission_id, mission_type=mission_type)
        for mission_id in db.scalars(statement).all()
    ]
