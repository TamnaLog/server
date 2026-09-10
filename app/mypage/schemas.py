"""마이페이지 도메인 요청/응답 스키마.

필드명은 app/mypage/docs/API_SPEC.md 기준(camelCase)이다.
"""

import json
from datetime import date, datetime
from json import JSONDecodeError
from typing import Self

from fastapi import UploadFile
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from app.common.rewards import FullRewardDetailResponse
from app.mission.models import MissionType
from app.mypage.constants import MAX_TRAVEL_ENDING_SELECTION_COUNT
from app.onboarding.schemas import Category, Transportation, TravelStyle


__all__ = [
    "AcquiredMissionResponse",
    "TravelEndingCompletedMissionResponse",
    "TravelEndingContentCreateRequest",
    "TravelEndingContentCreateResponse",
    "TravelEndingMissionRequest",
    "TravelEndingElementsResponse",
    "TravelEndingVisitedLocationResponse",
    "ArCharacterCollectionResponse",
    "DailyStepResponse",
    "MyPageResponse",
    "ProfileResponse",
    "ProgressMissionResponse",
    "SelectedArCharacterResponse",
    "SummaryResponse",
    "TravelStyleResponse",
    "UserInfoResponse",
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
    character_color: str | None = None


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

    획득 여부와 관계없이 이름·이미지·색상·이야기·해시태그·획득 조건을 모두 준다.
    실루엣 처리는 프론트가 `is_acquired` 로 판단한다.
    """

    id: int
    name: str
    image_url: str
    character_color: str | None = None
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
# 사용자 정보 조회
# ---------------------------------------------------------------------


class UserInfoResponse(CamelModel):
    """GET /api/v1/users/me 정상 응답. (프로필 수정 화면에 채울 현재 값)

    마이페이지 전체 조회의 `ProfileResponse` 와 필요한 값이 달라 따로 둔다.

    선택 배열 세 개는 저장값을 그대로 내려준다. `null`(설정 전)과 `[]`(아무것도 선택 안 함)을
    구분해야 해서 기본값을 두지 않고, 정렬/중복 제거/enum 변환도 하지 않는다.
    (그래서 타입도 enum 이 아니라 `list[str]` 이다)
    """

    user_type: str | None = None
    ar_character_image_url: str | None = None
    nickname: str | None = None
    categories: list[str] | None = Field(
        default=None,
        description="여행 기대 항목. PHOTO | LOCAL | NATURE | CULTURE | CAFE | WALKING",
    )
    transportation: list[str] | None = Field(
        default=None, description="주 이동 수단. WALK | BUS | CAR | BICYCLE"
    )
    travel_style: list[str] | None = Field(
        default=None,
        description="자투리 시간 여행 방식. RIGHT_HERE | NEAR_AROUND | NEAR_DESTINATION",
    )
    target_step_count: int


# ---------------------------------------------------------------------
# 여행 마무리 엽서 요소 조회
# ---------------------------------------------------------------------


class TravelEndingVisitedLocationResponse(CamelModel):
    """엽서에 넣을 수 있는 방문 장소 한 곳. `id` 는 `LOCATION.id` 다."""

    id: int
    location_title: str


class TravelEndingCompletedMissionResponse(CamelModel):
    """엽서에 넣을 수 있는 완료 미션 한 건.

    `mission_id` 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션 id 다.
    `completed_at` 은 같은 미션을 여러 번 완료했으면 가장 최근 완료 시각이다.
    장소를 갖지 않는 문화 미션은 `completed_location` 이 `null` 이다.
    """

    mission_id: int
    mission_type: MissionType
    mission_title: str
    completed_location: str | None = None
    completed_at: datetime
    # 미션에 설정된 전체 보상 + 보상별 수령 여부. 지도 미션 상세와 같은 형식이다.
    reward_detail: FullRewardDetailResponse


class TravelEndingElementsResponse(CamelModel):
    """GET /api/v1/users/me/travel-ending-elements 정상 응답.

    두 count 는 별도 집계가 아니라 각 목록의 길이와 항상 같다.
    사진 목록과 사진 개수는 이 API 가 다루지 않는다.
    """

    point: int
    visited_location_count: int
    visited_locations: list[TravelEndingVisitedLocationResponse]
    completed_mission_count: int
    completed_missions: list[TravelEndingCompletedMissionResponse]


# ---------------------------------------------------------------------
# 여행 마무리 엽서 저장
# ---------------------------------------------------------------------


class TravelEndingMissionRequest(CamelModel):
    """엽서에 넣을 완료 미션 한 건. `mission_id` 는 유형별 세부 미션 id 다."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    mission_type: MissionType
    # bool 을 정수로 바꿔 받지 않도록 StrictInt 를 쓴다. (`True` → 1 방지)
    mission_id: StrictInt = Field(ge=1)


class TravelEndingContentCreateRequest(CamelModel):
    """POST /api/v1/users/me/travel-ending-contents 요청 Body.

    `multipart/form-data` 로 받는다. `visitedLocationIds` 와 `missions` 는 배열 전체를
    **JSON 문자열 한 필드**로 받고, `photos` 는 같은 필드명을 파일마다 반복해서 받는다.

    여기서는 JSON 역직렬화와 개수·중복·형식 검증까지만 한다. (어기면 공통 400)
    실제로 현재 사용자의 방문 장소·완료 미션인지는 DB 를 봐야 해서 service 가 확인한다.
    사진 내용 검증(형식·크기)도 파일을 읽어야 하므로 service 가 한다.
    """

    visited_location_ids: list[StrictInt] = Field(
        min_length=1,
        max_length=MAX_TRAVEL_ENDING_SELECTION_COUNT,
        description=(
            "엽서에 넣을 LOCATION.id 배열을 JSON 문자열로 전달. "
            f"1~{MAX_TRAVEL_ENDING_SELECTION_COUNT}개이며 중복 불가"
        ),
    )
    missions: list[TravelEndingMissionRequest] = Field(
        min_length=1,
        max_length=MAX_TRAVEL_ENDING_SELECTION_COUNT,
        description=(
            "엽서에 넣을 완료 미션 배열을 JSON 문자열로 전달. "
            f"1~{MAX_TRAVEL_ENDING_SELECTION_COUNT}개이며 같은 (유형, 미션 id) 중복 불가"
        ),
    )
    photos: list[UploadFile] = Field(
        min_length=1,
        max_length=MAX_TRAVEL_ENDING_SELECTION_COUNT,
        description=(
            f"엽서에 넣을 사용자 사진. 같은 필드명을 반복해 1~"
            f"{MAX_TRAVEL_ENDING_SELECTION_COUNT}개 전송 (JPEG / PNG / WebP, 파일당 최대 10MB)"
        ),
    )
    travel_note: str | None = Field(
        default=None, description="엽서에 넣을 여행 한 줄. 생략 가능하며 글자 수 제한 없음"
    )

    @field_validator("visited_location_ids", "missions", mode="before")
    @classmethod
    def _parse_json_array(cls, value: object) -> object:
        """multipart 로 온 JSON 문자열을 배열로 바꾼다.

        배열 필드는 FastAPI 가 같은 이름의 form 값을 모아 주므로, 값이 하나뿐인 문자열
        목록(`["[15, 22]"]`)으로 들어온다. 그 안의 JSON 문자열을 배열로 바꾼다.
        JSON 문법이 잘못됐거나 배열이 아니면 여기서 걸러 공통 400 이 된다.
        (이미 배열이면 그대로 둔다. 테스트나 JSON 요청에서 그대로 넘길 수 있다)
        """
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
            value = value[0]

        if not isinstance(value, str):
            return value

        try:
            parsed = json.loads(value)
        except JSONDecodeError as error:
            raise ValueError(f"JSON 배열 문자열이 아닙니다: {error.msg}") from error

        if not isinstance(parsed, list):
            raise ValueError("JSON 배열이 아닙니다.")
        return parsed

    @model_validator(mode="after")
    def _check_no_duplicates(self) -> Self:
        """같은 장소나 같은 미션을 두 번 고른 요청은 받지 않는다. (어기면 공통 400)"""
        if len(set(self.visited_location_ids)) != len(self.visited_location_ids):
            raise ValueError("visitedLocationIds 에 중복된 장소가 있습니다.")

        mission_keys = {
            (mission.mission_type, mission.mission_id) for mission in self.missions
        }
        if len(mission_keys) != len(self.missions):
            raise ValueError("missions 에 중복된 미션이 있습니다.")
        return self


class TravelEndingContentCreateResponse(CamelModel):
    """POST /api/v1/users/me/travel-ending-contents 정상 응답.

    `remaining_point` 는 따로 계산한 값이 아니라 포인트를 차감해 커밋한 `USER.point` 다.
    """

    id: int
    image_url: str
    remaining_point: int


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
