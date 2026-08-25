"""홈 추천 미션 선정 모듈.

추천 기준이 확정되기 전까지는 DB에 존재하는 미션 중 랜덤으로 선택한다.
추후 기준이 확정되면 이 모듈 내부 로직만 교체하면 된다.
(app/home/docs/BUSINESS_RULES.md - 2. 추천 미션)
"""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.home.models import Mission


# 홈에 노출할 추천 미션 개수
RECOMMEND_COUNT = 3


def recommend_missions(db: Session, count: int = RECOMMEND_COUNT) -> list[Mission]:
    """홈에 노출할 추천 미션을 선정한다. (현재는 랜덤)

    미션이 `count` 보다 적으면 있는 만큼만 반환한다.
    """
    # TODO: 추천 기준 확정 시 사용자 온보딩 정보/위치 기반 추천 로직으로 교체
    missions = list(db.scalars(select(Mission)).all())
    if len(missions) <= count:
        return missions
    return random.sample(missions, count)
