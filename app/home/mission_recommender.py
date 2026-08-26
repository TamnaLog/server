"""홈 추천 미션 선정 모듈.

추천 기준이 확정되기 전까지는 DB에 존재하는 미션 중 랜덤으로 선택한다.
추후 기준이 확정되면 이 모듈 내부 로직만 교체하면 된다.
(app/home/docs/BUSINESS_RULES.md - 2. 추천 미션)

추천 대상은 `MISSION`(유형 분류)이 아니라 미션 유형별 테이블의 행이다.
세 유형의 행을 `RecommendableMission` 으로 감싸 같은 형태로 다룬다.
"""

import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.home.models import CooperativeMission, CultureMission, Location, Mission, TreasureMission


# 홈에 노출할 추천 미션 개수
RECOMMEND_COUNT = 3


@dataclass(frozen=True)
class RecommendableMission:
    """추천 후보 미션. 미션 유형별 테이블 한 행을 공통 형태로 감싼 값이다."""

    # 미션 유형별 테이블의 id. 응답의 `missionId` 로 나간다.
    id: int
    # 유형/이름/단계 등 공통 정보
    mission: Mission
    # 미션 장소. 문화 미션은 장소가 없어 `None` 이다.
    location: Location | None


def recommend_missions(db: Session, count: int = RECOMMEND_COUNT) -> list[RecommendableMission]:
    """홈에 노출할 추천 미션을 선정한다. (현재는 랜덤)

    미션이 `count` 보다 적으면 있는 만큼만 반환한다.
    """
    # TODO: 추천 기준 확정 시 사용자 온보딩 정보/위치 기반 추천 로직으로 교체
    candidates = _load_candidates(db)
    if len(candidates) <= count:
        return candidates
    return random.sample(candidates, count)


def _load_candidates(db: Session) -> list[RecommendableMission]:
    """추천 후보가 되는 모든 미션을 유형별 테이블에서 읽어온다."""
    culture = [
        RecommendableMission(id=row.id, mission=row.mission, location=None)
        for row in db.scalars(select(CultureMission)).all()
    ]
    cooperative = [
        RecommendableMission(id=row.id, mission=row.mission, location=row.location)
        for row in db.scalars(select(CooperativeMission)).all()
    ]
    treasure = [
        RecommendableMission(id=row.id, mission=row.mission, location=row.location)
        for row in db.scalars(select(TreasureMission)).all()
    ]
    return [*culture, *cooperative, *treasure]
