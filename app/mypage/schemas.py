"""마이페이지 도메인 요청/응답 스키마.

필드명은 app/mypage/docs/API_SPEC.md 기준(camelCase)이다.
"""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from pydantic.alias_generators import to_camel

from app.mission.models import MissionType
from app.onboarding.schemas import Category, Transportation, TravelStyle


__all__ = [
    "AcquiredMissionResponse",
    "ArCharacterCollectionResponse",
    "DailyStepResponse",
    "MyPageResponse",
    "ProfileResponse",
    "ProgressMissionResponse",
    "SelectedArCharacterResponse",
    "SummaryResponse",
    "TravelStyleResponse",
    "UserProfileUpdateRequest",
]

# 목표 걸음 수 허용 범위
MIN_TARGET_STEP_COUNT = 1
MAX_TARGET_STEP_COUNT = 100_000

# 닉네임 길이 (앞뒤 공백을 지운 뒤 기준)
MIN_NICKNAME_LENGTH = 1
MAX_NICKNAME_LENGTH = 20


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TravelStyleResponse(CamelModel):
    """온보딩에서 진단된 여행 유형."""

    user_type: str
    hashtags: list[str]


class SelectedArCharacterResponse(CamelModel):
    """마이페이지 상단에 노출할 대표 AR 캐릭터.

    배정만 되고 아직 획득하지 않은 캐릭터도 대표 캐릭터가 될 수 있다.
    (그래서 도감의 `is_acquired` 와 별개로 판단한다)
    """

    id: int
    name: str
    image_url: str


class ProfileResponse(CamelModel):
    """사용자 프로필. 값이 없으면 부분적으로 만들지 않고 통째로 `null` 로 둔다."""

    nickname: str | None = None
    travel_style: TravelStyleResponse | None = None
    selected_ar_character: SelectedArCharacterResponse | None = None


class DailyStepResponse(CamelModel):
    """하루 목표 걸음 수. 기록이 아니라 사용자 설정값(`USER.target_step`)이다."""

    target_step_count: int


class SummaryResponse(CamelModel):
    """마이페이지 요약 수치."""

    visited_location_count: int = 0
    completed_mission_count: int = 0
    point: int = 0


class ProgressMissionResponse(CamelModel):
    """진행 중인 미션 한 건.

    `mission_id` 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션 id 다.
    진행 수의 의미는 유형마다 다르다. (퀴즈 번호 / 찾은 보물 수 / 현재 단계)
    """

    mission_id: int
    mission_type: MissionType
    mission_title: str
    current_count: int
    total_count: int


class AcquiredMissionResponse(CamelModel):
    """캐릭터를 획득할 수 있는 미션. `id` 는 유형별 세부 미션 id 다."""

    id: int
    mission_type: MissionType
    mission_title: str


class ArCharacterCollectionResponse(CamelModel):
    """도감에 보여줄 AR 캐릭터 한 건.

    획득 여부와 관계없이 이름·이미지·이야기·해시태그·획득 조건을 모두 준다.
    실루엣 처리는 프론트가 `is_acquired` 로 판단한다.
    """

    id: int
    name: str
    image_url: str
    is_acquired: bool = False
    acquired_at: date | None = None
    acquired_location: str | None = None
    story_title: str
    story_content: str
    hashtags: list[str]
    acquire_condition: str
    acquired_missions: list[AcquiredMissionResponse]


class MyPageResponse(CamelModel):
    """GET /api/v1/users/me/mypage 정상 응답.

    목록은 결과가 없어도 키를 생략하지 않고 빈 배열로 내려준다.
    """

    profile: ProfileResponse
    daily_step: DailyStepResponse
    summary: SummaryResponse
    progress_missions: list[ProgressMissionResponse]
    ar_characters: list[ArCharacterCollectionResponse]


# ---------------------------------------------------------------------
# 사용자 정보 변경
# ---------------------------------------------------------------------


class UserProfileUpdateRequest(CamelModel):
    """PUT /api/v1/users/me/profile 요청 Body.

    부분 갱신이 아니라 **프로필 전체를 교체**한다. 그래서 다섯 필드가 모두 필수이고,
    하나라도 빠지면 공통 400 이다. (기본값을 두지 않는 이유)

    선택 항목 enum 은 온보딩과 같은 값이라 `app/onboarding/schemas.py` 의 것을 그대로 쓴다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        # 닉네임은 앞뒤 공백을 지운 값으로 저장하고 길이도 그 값 기준으로 본다.
        # (`str_strip_whitespace` 가 먼저 적용돼서 공백만 보내면 min_length 에 걸린다)
        str_strip_whitespace=True,
    )

    nickname: str = Field(
        min_length=MIN_NICKNAME_LENGTH,
        max_length=MAX_NICKNAME_LENGTH,
        description="앞뒤 공백을 지운 뒤 1~20자. 다른 사용자와 중복돼도 된다.",
    )
    categories: list[Category] = Field(description="여행 기대 항목. 빈 배열 허용")
    transportation: list[Transportation] = Field(description="주 이동 수단. 빈 배열 허용")
    travel_style: list[TravelStyle] = Field(description="자투리 시간 여행 방식. 빈 배열 허용")
    # bool 과 소수를 정수로 바꿔 받지 않도록 StrictInt 를 쓴다. (`True` → 1 방지)
    target_step_count: StrictInt = Field(
        ge=MIN_TARGET_STEP_COUNT,
        le=MAX_TARGET_STEP_COUNT,
        description="하루 목표 걸음 수. 1~100000 정수",
    )

    @model_validator(mode="after")
    def _check_no_duplicates(self) -> Self:
        """같은 항목을 두 번 고른 요청은 받지 않는다. (어기면 공통 400)"""
        for field_name, values in (
            ("categories", self.categories),
            ("transportation", self.transportation),
            ("travelStyle", self.travel_style),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} 에 중복된 값이 있습니다.")
        return self
