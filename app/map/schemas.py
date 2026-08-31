"""지도 도메인 요청/응답 스키마.

필드명은 app/map/docs/BUSINESS_RULES.md 기준(camelCase)이다.
"""

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.mission.schemas import MissionType


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MapContentsQuery(CamelModel):
    """GET /api/v1/map/contents 요청 Query.

    지도 화면의 네 꼭짓점 좌표와 클러스터링 여부를 받는다.
    지도를 회전하면 네 꼭짓점이 위도·경도 축과 나란하지 않으므로 꼭짓점을 모두 받는다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    left_top_latitude: float = Field(ge=-90, le=90, description="지도 화면 좌상단 위도")
    left_top_longitude: float = Field(ge=-180, le=180, description="지도 화면 좌상단 경도")
    right_top_latitude: float = Field(ge=-90, le=90, description="지도 화면 우상단 위도")
    right_top_longitude: float = Field(ge=-180, le=180, description="지도 화면 우상단 경도")
    left_bottom_latitude: float = Field(ge=-90, le=90, description="지도 화면 좌하단 위도")
    left_bottom_longitude: float = Field(
        ge=-180, le=180, description="지도 화면 좌하단 경도"
    )
    right_bottom_latitude: float = Field(ge=-90, le=90, description="지도 화면 우하단 위도")
    right_bottom_longitude: float = Field(
        ge=-180, le=180, description="지도 화면 우하단 경도"
    )
    user_latitude: float = Field(
        ge=-90, le=90, description="현재 사용자 위치의 위도. 장소까지의 거리 계산에 쓴다."
    )
    user_longitude: float = Field(
        ge=-180, le=180, description="현재 사용자 위치의 경도. 장소까지의 거리 계산에 쓴다."
    )
    is_clustered: bool = Field(
        description="true 이면 좌표만, false 이면 상세 정보를 반환한다."
    )


class MapPointResponse(CamelModel):
    """지도에 찍을 좌표."""

    latitude: float
    longitude: float


class ClusteredLocationResponse(MapPointResponse):
    """클러스터링 상태에서 내려주는 장소.

    클러스터 구성과 표시 개수 계산은 프론트가 하므로 식별자와 좌표만 준다.
    다만 프론트가 마커 모양을 정할 수 있게 연결된 미션의 id/유형은 함께 준다.

    `id` 는 `LOCATION.id`, `mission_id` 는 유형별 세부 미션 id 라 서로 다른 값이다.
    한 장소에는 미션이 최대 하나라 두 필드는 항상 한 쌍으로 나가고, 없으면 둘 다 `null` 이다.
    """

    id: int
    mission_id: int | None = None
    mission_type: MissionType | None = None


class ClusteredRoadGuestbookResponse(MapPointResponse):
    """클러스터링 상태에서 내려주는 길바닥 방명록. 식별자와 좌표만 준다."""

    id: int


class MapMissionResponse(CamelModel):
    """지도 장소에 연결된 미션 정보.

    `id` 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션 테이블의 id다.
    `has_written_guestbook` 은 미션을 완료한 경우에만 조회하므로 미완료면 `null` 이다.
    """

    id: int
    mission_title: str
    is_completed: bool
    has_written_guestbook: bool | None = None


class MapLocationResponse(MapPointResponse):
    """지도에 표시할 장소 상세 정보.

    한 장소에는 보물찾기 **또는** 협동 미션이 최대 하나만 있다고 본다.
    그래서 두 미션 필드 중 많아야 하나만 값이 있고 나머지는 `null` 이다.
    문화 미션은 장소를 참조하지 않아 지도에 나오지 않는다.
    """

    id: int
    location_title: str
    distance_meter: int
    duration_minutes: int
    treasure_mission: MapMissionResponse | None = None
    cooperative_mission: MapMissionResponse | None = None
    guestbooks_count: int = 0
    representative_image_url: str | None = None


class MapRoadGuestbookResponse(MapPointResponse):
    """지도에 표시할 길바닥 방명록 상세 정보."""

    id: int
    location_alias: str
    representative_guestbook_image_url: str | None = None


class MapContentsResponse(CamelModel):
    """GET /api/v1/map/contents 정상 응답. (`isClustered = false`)

    조회 결과가 없어도 오류가 아니라 빈 배열이다.
    """

    locations: list[MapLocationResponse]
    road_guestbooks: list[MapRoadGuestbookResponse]


class ClusteredMapContentsResponse(CamelModel):
    """GET /api/v1/map/contents 정상 응답. (`isClustered = true`)

    대량 전송을 줄이려고 클러스터링에 필요한 값만 내려준다.
    장소명·거리·미션 제목/완료 여부·방명록 개수·이미지는 조회하지도, 응답에 넣지도 않는다.
    """

    locations: list[ClusteredLocationResponse]
    road_guestbooks: list[ClusteredRoadGuestbookResponse]


# ---------------------------------------------------------------------
# 지도 모달 조회
# ---------------------------------------------------------------------


class MapModalTargetType(str, Enum):
    """지도 모달 조회 대상. 미션 자체는 조회 대상이 아니다."""

    LOCATION = "LOCATION"
    ROAD_GUESTBOOK = "ROAD_GUESTBOOK"


class MapModalQuery(CamelModel):
    """GET /api/v1/map/modals 요청 Query."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    target_type: MapModalTargetType = Field(description="조회 대상 유형")
    target_id: int = Field(
        ge=1, description="LOCATION 이면 LOCATION.id, ROAD_GUESTBOOK 이면 ROAD_GUESTBOOK.id"
    )
    user_latitude: float = Field(ge=-90, le=90, description="현재 사용자 위치의 위도")
    user_longitude: float = Field(ge=-180, le=180, description="현재 사용자 위치의 경도")


class LocationModalGuestbookResponse(CamelModel):
    """장소 모달에 함께 보여줄 방명록 한 건."""

    id: int
    representative_image_url: str | None = None
    user_nickname: str
    mission_title: str | None = None
    # 작성일은 `created_at`/`saved_at` 이 아니라 방문일(`visited_at`) 기준이다.
    visited_at: date
    content_writing: str | None = None


class LocationModalResponse(CamelModel):
    """`targetType = LOCATION` 모달 응답.

    `guestbooks_count` 는 아래 목록의 길이가 아니라 그 장소의 전체 방명록 개수다.
    """

    id: int
    location_title: str
    location_category: str
    distance_meter: int
    duration_minutes: int
    guestbooks_count: int = 0
    guestbooks: list[LocationModalGuestbookResponse]


class RoadGuestbookModalResponse(CamelModel):
    """`targetType = ROAD_GUESTBOOK` 모달 응답.

    저장된 콘텐츠는 값과 순서를 그대로 내려주고, 없으면 키를 지우지 않고 `null` 로 둔다.
    """

    id: int
    user_nickname: str
    location_alias: str
    distance_meter: int
    duration_minutes: int
    visited_at: date
    content_image_urls: list[str] | None = None
    content_writing: str | None = None
    content_audio_urls: list[str] | None = None
    content_weather: str | None = None
    content_color_code: str | None = None


# ---------------------------------------------------------------------
# 지도 장소 상세 조회
# ---------------------------------------------------------------------


class NearbyMissionResponse(CamelModel):
    """근처에서 할 수 있는 추천 미션.

    `id` 는 공통 `MISSION.id` 가 아니라 `mission_type` 에 해당하는 세부 미션 테이블의 id다.
    """

    id: int
    mission_type: MissionType
    mission_title: str


class LocationMissionResponse(CamelModel):
    """이 장소에 직접 연결된 미션. 제목 없이 유형과 id 만 내려준다."""

    id: int
    mission_type: MissionType


class LocationGuestbookResponse(CamelModel):
    """장소 상세에 보여줄 방명록 한 건."""

    id: int
    mission_title: str | None = None
    representative_image_url: str | None = None
    user_nickname: str
    # 작성일은 `created_at`/`saved_at` 이 아니라 방문일(`visited_at`) 기준이다.
    visited_at: date
    content_writing: str | None = None


class LocationDetailResponse(CamelModel):
    """GET /api/v1/map/locations/{locationId} 정상 응답.

    장소명·분류·거리·예상 시간은 모달 조회에서 이미 내려줬으므로 여기서 다시 주지 않는다.
    """

    location_address: str
    location_description: str | None = None
    nearby_missions: list[NearbyMissionResponse]
    guestbooks: list[LocationGuestbookResponse]
    location_mission: LocationMissionResponse | None = None


# ---------------------------------------------------------------------
# 지도 검색 결과 조회
# ---------------------------------------------------------------------


class MapSearchQuery(CamelModel):
    """GET /api/v1/map/search 요청 Query.

    `keyword` 는 앞뒤 공백을 지운 뒤 한 글자 이상이어야 한다.
    (`str_strip_whitespace` 가 먼저 적용돼서 공백만 보내면 `min_length` 에 걸린다)
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    keyword: str = Field(min_length=1, description="장소 이름에서 찾을 검색어")
    user_latitude: float = Field(ge=-90, le=90, description="현재 사용자 위치의 위도")
    user_longitude: float = Field(ge=-180, le=180, description="현재 사용자 위치의 경도")


class RecommendedLocationResponse(CamelModel):
    """검색된 장소 중 연결된 미션이 없는 장소."""

    location_id: int
    location_title: str
    location_category: str
    representative_image_url: str | None = None
    distance_meter: int


class MissionLocationResponse(CamelModel):
    """검색된 장소 중 보물찾기 또는 협동 미션이 연결된 장소.

    `mission_id` 는 공통 `MISSION.id` 가 아니라 `mission_type` 에 해당하는 세부 미션 id다.
    """

    location_id: int
    mission_id: int
    mission_type: MissionType
    location_title: str
    mission_title: str
    representative_image_url: str | None = None
    distance_meter: int


class MapSearchResponse(CamelModel):
    """GET /api/v1/map/search 정상 응답.

    검색 결과가 없어도 키를 생략하지 않고 빈 배열을 내려준다.
    """

    recommended_locations: list[RecommendedLocationResponse]
    mission_locations: list[MissionLocationResponse]
