"""온보딩 결과 → 여행 유형 / AR 캐릭터 배정 모듈.

기획의 매칭 기준이 확정되기 전까지는 DB에 존재하는 값 중 랜덤으로 배정한다.
추후 매칭 기준이 확정되면 이 모듈 내부 로직만 교체하면 된다.
"""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.onboarding.models import ArCharacter, UserTravelStyle
from app.onboarding.schemas import OnboardingSaveRequest


# **나중에 할게요**를 선택한 사용자에게 배정하는 기본 캐릭터
DEFAULT_AR_CHARACTER_NAME = "돌멍이"


def assign_travel_style(db: Session, request: OnboardingSaveRequest) -> UserTravelStyle:
    """온보딩 결과에 맞는 여행 유형을 배정한다. (현재는 랜덤)"""
    # TODO: 매칭 기준 확정 시 request 값 기반 매칭 로직으로 교체
    travel_styles = db.scalars(select(UserTravelStyle)).all()
    if not travel_styles:
        raise RuntimeError("배정할 여행 유형 데이터가 없습니다.")
    return random.choice(travel_styles)


def assign_ar_character(db: Session, request: OnboardingSaveRequest) -> ArCharacter:
    """온보딩 결과에 맞는 AR 캐릭터를 배정한다. (현재는 랜덤)"""
    # TODO: 매칭 기준 확정 시 request 값 기반 매칭 로직으로 교체
    characters = db.scalars(select(ArCharacter)).all()
    if not characters:
        raise RuntimeError("배정할 AR 캐릭터 데이터가 없습니다.")
    return random.choice(characters)


def get_default_ar_character(db: Session) -> ArCharacter:
    """**나중에 할게요**를 선택한 사용자에게 배정할 기본 캐릭터를 반환한다."""
    character = db.scalars(
        select(ArCharacter).where(ArCharacter.character_name == DEFAULT_AR_CHARACTER_NAME)
    ).first()
    if character is None:
        raise RuntimeError(f"기본 AR 캐릭터({DEFAULT_AR_CHARACTER_NAME}) 데이터가 없습니다.")
    return character
