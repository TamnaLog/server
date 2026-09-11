"""홈 추천 미션 선정 모듈.

홈에는 문화 / 협동 / 보물 찾기 미션을 한 건씩 추천한다.
(app/home/docs/BUSINESS_RULES.md - 2. 추천 미션)

- 문화 미션: 장소가 없어 거리로 비교할 수 없으므로 무작위로 한 건 고른다.
- 협동 / 보물 찾기 미션: 현재 사용자가 완료한 이력이 없는 미션 중
  장소가 사용자 위치에서 가장 가까운 한 건을 고른다.

해당 유형의 추천 후보가 하나도 없으면 그 유형은 빼고 반환한다.
(협동/보물 찾기는 모든 미션을 이미 완료한 경우가 여기에 해당한다)

추천 대상은 `MISSION`(유형 분류)이 아니라 미션 유형별 테이블의 행이다.
세 유형의 행을 `RecommendableMission` 으로 감싸 같은 형태로 다룬다.
"""

import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import distance, mission_completion
from app.home.models import CooperativeMission, CultureMission, Location, Mission, TreasureMission


@dataclass(frozen=True)
class RecommendableMission:
    """추천 후보 미션. 미션 유형별 테이블 한 행을 공통 형태로 감싼 값이다."""

    # 미션 유형별 테이블의 id. 응답의 `missionId` 로 나간다.
    id: int
    # 유형/이름/단계 등 공통 정보
    mission: Mission
    # 미션 장소. 문화 미션은 장소가 없어 `None` 이다.
    location: Location | None


def recommend_missions(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> list[RecommendableMission]:
    """홈에 노출할 추천 미션을 유형별로 한 건씩 선정한다.

    후보가 없는 유형은 결과에서 빠지므로 최대 3건, 최소 0건을 반환한다.
    """
    candidates = [
        _pick_random_culture(db),
        _pick_nearest_cooperative(db, current_user_id, latitude, longitude),
        _pick_nearest_treasure(db, current_user_id, latitude, longitude),
    ]
    return [candidate for candidate in candidates if candidate is not None]


def _pick_random_culture(db: Session) -> RecommendableMission | None:
    """문화 미션 중 한 건을 무작위로 고른다. 문화 미션이 없으면 `None`."""
    rows = db.scalars(select(CultureMission)).all()
    if not rows:
        return None

    row = random.choice(list(rows))
    return RecommendableMission(id=row.id, mission=row.mission, location=None)


def _pick_nearest_cooperative(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> RecommendableMission | None:
    """완료 이력이 없는 협동 미션 중 장소가 가장 가까운 한 건을 고른다."""
    rows = list(db.scalars(select(CooperativeMission)).all())
    completed_ids = mission_completion.find_completed_cooperative_mission_ids(
        db, current_user_id, [row.id for row in rows]
    )
    return _pick_nearest(
        [row for row in rows if row.id not in completed_ids], latitude, longitude
    )


def _pick_nearest_treasure(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> RecommendableMission | None:
    """완료 이력이 없는 보물 찾기 미션 중 장소가 가장 가까운 한 건을 고른다."""
    rows = list(db.scalars(select(TreasureMission)).all())
    completed_ids = mission_completion.find_completed_treasure_mission_ids(
        db, current_user_id, [row.id for row in rows]
    )
    return _pick_nearest(
        [row for row in rows if row.id not in completed_ids], latitude, longitude
    )


def _pick_nearest(
    rows: list[CooperativeMission] | list[TreasureMission],
    latitude: float,
    longitude: float,
) -> RecommendableMission | None:
    """장소를 가진 미션 중 사용자 위치에서 직선거리가 가장 짧은 한 건을 고른다.

    후보가 하나도 없으면 `None`. 거리가 같으면 미션 id 가 작은 쪽을 고른다.
    """
    if not rows:
        return None

    row = min(
        rows,
        key=lambda candidate: (
            distance.calculate_distance_meter(
                latitude, longitude, candidate.location.my, candidate.location.mx
            ),
            candidate.id,
        ),
    )
    return RecommendableMission(id=row.id, mission=row.mission, location=row.location)
