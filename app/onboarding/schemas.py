"""온보딩 도메인 요청/응답 스키마.

필드명은 app/onboarding/docs/API_SPEC.md 기준(camelCase)이다.
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Category(str, Enum):
    """여행 기대 항목."""

    PHOTO = "PHOTO"
    LOCAL = "LOCAL"
    NATURE = "NATURE"
    CULTURE = "CULTURE"
    CAFE = "CAFE"
    WALKING = "WALKING"


class Transportation(str, Enum):
    """주 이동 수단."""

    WALK = "WALK"
    BUS = "BUS"
    CAR = "CAR"
    BICYCLE = "BICYCLE"


class TravelStyle(str, Enum):
    """자투리 시간 여행 방식."""

    RIGHT_HERE = "RIGHT_HERE"
    NEAR_AROUND = "NEAR_AROUND"
    NEAR_DESTINATION = "NEAR_DESTINATION"


class OnboardingSaveRequest(BaseModel):
    """PATCH /api/v1/users/me 요청 Body.

    **나중에 할게요**를 선택한 경우 빈 객체 `{}` 로 전달된다.
    """

    model_config = ConfigDict(populate_by_name=True)

    categories: list[Category] = []
    transportation: list[Transportation] = []
    travel_style: Annotated[list[TravelStyle], Field(alias="travelStyle")] = []

    @property
    def is_skipped(self) -> bool:
        """**나중에 할게요** 선택 여부."""
        return not (self.categories or self.transportation or self.travel_style)


class ArCharacterResponse(CamelModel):
    """사용자에게 배정된 AR 캐릭터 정보."""

    id: int
    name: str
    image_url: str


class UserTravelStyleResponse(CamelModel):
    """사용자에게 배정된 여행 유형 정보."""

    id: int
    user_type: str
    type_description: str
    hashtags: list[str]


class UserResponse(CamelModel):
    """생성된 사용자 정보."""

    id: int
    ar_character: ArCharacterResponse
    user_travel_style: UserTravelStyleResponse | None = None


class OnboardingSaveResponse(CamelModel):
    """PATCH /api/v1/users/me 정상 응답."""

    user: UserResponse
