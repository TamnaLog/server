"""온보딩 결과 → 여행 유형 / AR 캐릭터 배정 모듈.

기획의 매칭 기준이 확정되기 전까지 여행 유형은 DB에 존재하는 값 중 랜덤으로,
AR 캐릭터는 온보딩 전용 캐릭터(id 7~12) 중 랜덤으로 배정한다.
추후 매칭 기준이 확정되면 이 모듈 내부 로직만 교체하면 된다.
"""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.onboarding.models import ArCharacter, UserTravelStyle
from app.onboarding.schemas import OnboardingSaveRequest


ONBOARDING_AR_CHARACTER_IDS = tuple(range(7, 13))


def assign_travel_style(db: Session, request: OnboardingSaveRequest) -> UserTravelStyle:
    """온보딩 결과에 맞는 여행 유형을 배정한다. (현재는 랜덤)"""
    # TODO: 매칭 기준 확정 시 request 값 기반 매칭 로직으로 교체
    travel_styles = db.scalars(select(UserTravelStyle)).all()
    if not travel_styles:
        raise RuntimeError("배정할 여행 유형 데이터가 없습니다.")
    return random.choice(travel_styles)


def assign_ar_character(db: Session, request: OnboardingSaveRequest) -> ArCharacter:
    """온보딩 전용 AR 캐릭터(id 7~12) 중 하나를 랜덤으로 배정한다."""
    # TODO: 매칭 기준 확정 시 request 값 기반 매칭 로직으로 교체
    characters = db.scalars(
        select(ArCharacter).where(ArCharacter.id.in_(ONBOARDING_AR_CHARACTER_IDS))
    ).all()
    if not characters:
        raise RuntimeError("배정할 온보딩 AR 캐릭터(id 7~12) 데이터가 없습니다.")
    return random.choice(characters)
