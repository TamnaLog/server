"""방명록 도메인 요청/응답 스키마.

필드명은 app/guestbook/docs/API_SPEC.md 기준(camelCase)이다.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Self

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.mission.models import MissionType


__all__ = [
    "GeneralGuestbookResponse",
    "GuestbookCreateRequest",
    "GuestbookCreateResponse",
    "GuestbookLikeRequest",
    "GuestbookLikeResponse",
    "GuestbookListQuery",
    "GuestbookListResponse",
    "GuestbookScope",
    "GuestbookLocationResponse",
    "GuestbookMissionResponse",
    "GuestbookType",
    "RoadGuestbookResponse",
    "GuestbookWriteAvailabilityResponse",
    "VisitedLocationResponse",
    "VisitedLocationSummaryResponse",
    "WriteAvailabilityQuery",
]


# 섭씨 기온 허용 범위. DB 컬럼이 DECIMAL(4,1) 이라 소수 첫째 자리까지만 받는다.
# 범위를 벗어나거나 정밀도가 더 크면 임의로 반올림하지 않고 공통 400 으로 막는다.
MIN_TEMPERATURE_CELSIUS = Decimal("-999.9")
MAX_TEMPERATURE_CELSIUS = Decimal("999.9")


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WriteAvailabilityQuery(CamelModel):
    """GET /api/v1/guestbooks/write-availability 요청 Query.

    작성자는 Query 가 아니라 공통 `Authorization: Bearer` 액세스 토큰으로 식별한다.
    """

    location_id: int = Field(ge=1, description="방명록 작성 가능 여부를 확인할 장소 id")


class VisitedLocationResponse(CamelModel):
    """가장 최근 방문 기록으로 만든 장소 정보."""

    location_id: int
    location_name: str
    visited_at: datetime


class GuestbookWriteAvailabilityResponse(CamelModel):
    """GET /api/v1/guestbooks/write-availability 정상 응답.

    방문 기록이 없으면 `visited_location` 을 부분적으로 만들지 않고 `null` 로 둔다.
    두 경우 모두 키는 생략하지 않는다.
    """

    can_write: bool
    visited_location: VisitedLocationResponse | None = None


class GuestbookType(str, Enum):
    """방명록 유형. 유형에 따라 저장 테이블과 조건부 필드가 달라진다."""

    # 등록된 LOCATION 에 작성하는 일반 방명록
    GENERAL = "GENERAL"
    # 장소에 귀속되지 않고 지도 좌표에 작성하는 길바닥 방명록
    ROAD = "ROAD"


class GuestbookCreateRequest(CamelModel):
    """POST /api/v1/guestbooks 요청 Body.

    `multipart/form-data` 로 받는다. 파일 형식/크기 검증은 파일 내용을 봐야 하므로
    스키마가 아니라 service 에서 처리하고, 여기서는 **유형별 조건부 필드**만 검증한다.
    작성자는 요청이 아니라 공통 `Authorization: Bearer` 액세스 토큰으로 식별한다.
    """

    guestbook_type: GuestbookType
    location_id: int | None = Field(default=None, ge=1)
    location_alias: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    visited_at: date
    content_writing: str | None = Field(default=None, max_length=500)
    content_weather: str | None = Field(default=None, max_length=20)
    # 오디오 제목(`audioTitle`)은 요청으로 받지 않는다. 서버가 첨부 오디오로 생성한다.
    content_temperature_celsius: Decimal | None = Field(
        default=None,
        ge=MIN_TEMPERATURE_CELSIUS,
        le=MAX_TEMPERATURE_CELSIUS,
        decimal_places=1,
        description="섭씨 기온. -999.9~999.9, 소수 첫째 자리까지",
    )
    content_color_code: str | None = Field(default=None, max_length=20)
    mission_id: int | None = Field(default=None, ge=1)
    image_files: list[UploadFile] | None = None
    audio_files: list[UploadFile] | None = None

    @model_validator(mode="after")
    def _check_type_fields(self) -> Self:
        """유형별 필수/미사용 필드를 한곳에서 검증한다. (어기면 공통 400)"""
        if self.guestbook_type is GuestbookType.GENERAL:
            if self.location_id is None:
                raise ValueError("GENERAL 방명록은 locationId 가 필요합니다.")
            if (
                self.location_alias is not None
                or self.latitude is not None
                or self.longitude is not None
            ):
                raise ValueError(
                    "GENERAL 방명록은 locationAlias / latitude / longitude 를 사용하지 않습니다."
                )
            return self

        if self.location_alias is None or self.latitude is None or self.longitude is None:
            raise ValueError(
                "ROAD 방명록은 locationAlias / latitude / longitude 가 모두 필요합니다."
            )
        if self.location_id is not None or self.mission_id is not None:
            raise ValueError("ROAD 방명록은 locationId / missionId 를 사용하지 않습니다.")
        return self


class GuestbookCreateResponse(CamelModel):
    """POST /api/v1/guestbooks 정상 응답.

    일반/길바닥을 한 모델로 내려주는 1-depth 구조라, 유형에서 쓰지 않는 필드도
    키를 생략하지 않고 `null` 로 둔다. 파일이 없으면 URL 목록도 빈 배열이 아니라 `null` 이다.
    """

    guestbook_id: int
    guestbook_type: GuestbookType
    location_id: int | None = None
    location_alias: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    visited_at: date
    content_image_urls: list[str] | None = None
    content_writing: str | None = None
    content_audio_urls: list[str] | None = None
    audio_title: str | None = None
    content_weather: str | None = None
    # 응답에서는 JSON 숫자로 나가야 해서 Decimal 이 아니라 float 로 담는다.
    content_temperature_celsius: float | None = None
    content_color_code: str | None = None
    mission_id: int | None = None
    saved_at: datetime


class GuestbookLocationResponse(CamelModel):
    """일반 방명록이 작성된 장소. `LOCATION` 은 my=위도 / mx=경도로 저장한다."""

    id: int
    location_title: str
    location_address: str
    location_category: str
    latitude: float
    longitude: float


class GuestbookMissionResponse(CamelModel):
    """방명록에 연결된 공통 미션. 작성 시 저장한 `mission_id` 만 기준으로 한다."""

    id: int
    mission_type: MissionType
    mission_title: str


class GeneralGuestbookResponse(CamelModel):
    """일반 방명록 한 건. 콘텐츠는 저장값을 그대로 돌려준다.

    `content_image_urls` / `content_audio_urls` 는 DB 가 `NULL` 이면 `null`,
    빈 배열이면 `[]` 로 구분해서 내려준다.
    `is_liked` 는 현재 사용자의 좋아요 여부, `like_count` 는 사용자 구분 없는 전체 개수다.
    둘 다 취소된(소프트 삭제된) 좋아요는 세지 않는다.
    """

    id: int
    user_id: int
    character_img_url: str | None = None
    user_nickname: str | None = None
    location: GuestbookLocationResponse
    visited_at: date
    content_image_urls: list[str] | None = None
    content_writing: str | None = None
    content_audio_urls: list[str] | None = None
    audio_title: str | None = None
    content_weather: str | None = None
    content_temperature_celsius: float | None = None
    content_color_code: str | None = None
    is_liked: bool = False
    like_count: int = 0
    saved_at: datetime
    mission: GuestbookMissionResponse | None = None


class RoadGuestbookResponse(CamelModel):
    """길바닥 방명록 한 건. 장소/미션을 붙이지 않고 저장된 좌표와 별칭만 쓴다.

    좋아요는 일반 방명록과 규칙이 같고 테이블만 `ROAD_GUESTBOOK_LIKE` 로 다르다.
    """

    id: int
    user_id: int
    character_img_url: str | None = None
    user_nickname: str | None = None
    location_alias: str
    latitude: float
    longitude: float
    visited_at: date
    content_image_urls: list[str] | None = None
    content_writing: str | None = None
    content_audio_urls: list[str] | None = None
    audio_title: str | None = None
    content_weather: str | None = None
    content_temperature_celsius: float | None = None
    content_color_code: str | None = None
    is_liked: bool = False
    like_count: int = 0
    saved_at: datetime


class GuestbookScope(str, Enum):
    """방명록 조회 범위."""

    # 작성자를 가리지 않고 전부
    ALL = "ALL"
    # 현재 사용자가 쓴 것만
    MINE = "MINE"


class GuestbookListQuery(CamelModel):
    """GET /api/v1/guestbooks 요청 Query.

    조회 범위만 받고 페이지네이션 관련 Query 는 받지 않는다.
    `scope` 를 생략하면 전체 조회(`ALL`)다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    scope: GuestbookScope = Field(
        default=GuestbookScope.ALL, description="조회 범위. 생략하면 ALL"
    )


class VisitedLocationSummaryResponse(CamelModel):
    """현재 사용자가 방문한 장소. 목록에는 id 와 장소명만 담는다.

    작성 가능 여부 조회의 `VisitedLocationResponse` 와 달리 방문 시각은 응답에 넣지 않는다.
    (정렬에만 쓴다)
    """

    id: int
    location_title: str


class GuestbookListResponse(CamelModel):
    """GET /api/v1/guestbooks 정상 응답.

    유형은 항목 필드가 아니라 최상위 배열 이름으로 구분한다.
    결과가 없어도 세 배열 키를 모두 포함하고 빈 배열로 내려준다.
    `visited_locations` 는 방명록 유무와 상관없이 항상 함께 내려준다.
    """

    visited_locations: list[VisitedLocationSummaryResponse]
    general_guestbooks: list[GeneralGuestbookResponse]
    road_guestbooks: list[RoadGuestbookResponse]


# ---------------------------------------------------------------------
# 방명록 좋아요
# ---------------------------------------------------------------------


class GuestbookLikeRequest(CamelModel):
    """PUT /api/v1/guestbooks/{guestbookId}/like 요청 Body.

    `is_liked` 는 현재 상태를 뒤집으라는 뜻이 아니라 **요청 후 적용될 최종 상태**다.
    그래서 같은 요청을 여러 번 보내도 결과가 같다. (멱등)
    두 방명록 테이블은 id 가 겹칠 수 있어서 `guestbook_type` 없이는 대상을 정할 수 없다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    guestbook_type: GuestbookType = Field(description="대상 방명록 유형")
    is_liked: bool = Field(description="요청 완료 후 적용할 최종 좋아요 상태")


class GuestbookLikeResponse(CamelModel):
    """PUT /api/v1/guestbooks/{guestbookId}/like 정상 응답.

    `like_count` 는 요청을 반영한 뒤의 활성 좋아요 수다. (취소된 좋아요는 세지 않는다)
    """

    guestbook_id: int
    guestbook_type: GuestbookType
    is_liked: bool
    like_count: int = 0
