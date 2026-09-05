"""보물 찾기 도메인 요청/응답 스키마.

필드명은 app/treasure_mission/docs/API_SPEC.md 기준(camelCase)이다.
보물 표시/인식 반경은 프론트가 관리하므로 응답에 포함하지 않는다.
"""

from datetime import datetime

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.common.next_location import NextLocationResponse
from app.common.rewards import FullRewardDetailResponse, GrantedRewardResponse
from app.mission.models import MissionStatus, MissionType


__all__ = [
    "CompletedTreasureMissionResponse",
    "GrantedRewardResponse",
    "MissionStatus",
    "MissionType",
    "NearbyTreasureMissionResponse",
    "NextLocationResponse",
    "ReceivedCouponResponse",
    "TreasureItemResponse",
    "TreasureLocationResponse",
    "TreasureMissionCompletionResponse",
    "TreasureMissionLocationResponse",
    "TreasureMissionProgressSaveRequest",
    "TreasureMissionProgressSaveResponse",
    "TreasureMissionStartResponse",
    "TreasureMissionStopResponse",
]


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TreasureLocationResponse(CamelModel):
    """보물 좌표. 진행도 `item_detail` 의 `my`(위도) / `mx`(경도) 다."""

    lat: float
    lng: float


class TreasureMissionLocationResponse(CamelModel):
    """보물찾기 미션이 진행되는 장소.

    `location_description` 은 TourAPI `detailCommon2.overview` 를 정리한 설명의 첫 문장이다.
    조회에 실패하거나 `overview` 가 없으면 `null` 이다.
    """

    location_id: int
    location_title: str
    location_address: str
    location_description: str | None = None
    lat: float
    lng: float


class TreasureItemResponse(CamelModel):
    """보물 하나. `is_found` 는 `current_found_item_idx` 포함 여부다."""

    treasure_index: int
    location: TreasureLocationResponse
    is_found: bool


class TreasureMissionStartResponse(CamelModel):
    """POST /api/v1/treasure-missions/{treasureMissionId}/progress 정상 응답.

    진행도를 새로 만들었으면 `201`, 기존 진행도를 이어서 하면 `200` 으로 응답한다.
    """

    treasure_mission_progress_id: int
    mission_progress_status: MissionStatus
    location: TreasureMissionLocationResponse
    treasure_count: int
    treasure_items: list[TreasureItemResponse]


class TreasureMissionProgressSaveRequest(CamelModel):
    """PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress 요청 Body.

    보물 발견 여부는 프론트 판정 결과를 그대로 신뢰한다.
    (백엔드에서 사용자 좌표와 보물 좌표의 거리를 다시 검증하지 않는다)
    """

    treasure_index: int = Field(ge=1, description="사용자가 찾은 보물 번호")


class TreasureMissionProgressSaveResponse(CamelModel):
    """PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress 정상 응답.

    미션이 아직 진행 중이면 `next_location` 은 `null` 이고, 완료하면 반드시 객체다.
    `reward` 는 진행 상태와 무관하게 객체이며 이번 요청으로 실제 지급된 항목만 채운다.
    """

    mission_progress_status: MissionStatus
    treasure_count: int
    found_treasure_indexes: list[int]
    next_location: NextLocationResponse | None = None
    reward: GrantedRewardResponse


class TreasureMissionStopResponse(CamelModel):
    """PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress/stop 정상 응답.

    중단은 완료 처리이므로 `mission_progress_status` 는 항상 `COMPLETED` 이고
    `next_location` 은 항상 객체다.
    보상은 보물을 찾을 때마다 이미 지급되므로 중단 응답에는 보상 정보를 넣지 않는다.
    """

    mission_progress_status: MissionStatus
    treasure_count: int
    found_treasure_indexes: list[int]
    next_location: NextLocationResponse


class PictureWithCharacterSaveRequest(CamelModel):
    """POST /api/v1/treasure-missions/pictures-with-character 요청 Body.

    `multipart/form-data` 로 받는다. 사진 형식/크기 검증은 파일 내용을 봐야 하므로
    스키마가 아니라 service 에서 처리한다.
    """

    picture: UploadFile
    taken_at: str


# ---------------------------------------------------------------------
# 완료한 보물찾기 추천 화면
# ---------------------------------------------------------------------


class CompletedTreasureMissionResponse(CamelModel):
    """완료한 보물찾기 정보.

    `completed_at` 은 현재 사용자의 **가장 최근** 완료 진행도의 완료 시각이다.
    캐릭터 보상이 없거나 연결된 캐릭터를 찾을 수 없으면 이미지가 `null` 이다.
    """

    mission_id: int
    mission_type: MissionType
    completed_at: datetime
    ar_character_image_url: str | None = None


class NearbyTreasureMissionResponse(CamelModel):
    """추천할 근처 보물찾기 한 건.

    `mission_id` 는 공통 `MISSION.id` 가 아니라 `TREASURE_MISSION.id` 다.
    난이도는 이 화면에서 쓰지 않으므로 반환하지 않는다.
    """

    mission_id: int
    mission_type: MissionType
    location_id: int
    mission_title: str
    representative_image_url: str | None = None
    distance_meter: int
    duration_minutes: int
    # 미션에 설정된 전체 보상 + 보상별 수령 여부. 지도 미션 상세와 같은 형식이다.
    reward_detail: FullRewardDetailResponse


class ReceivedCouponResponse(CamelModel):
    """현재 사용자가 지금까지 받은 쿠폰 한 건.

    쿠폰 사용처 이름과 이름이 같은 장소를 찾아 장소 정보를 붙인다.
    일치하는 장소가 없으면 장소 관련 세 값이 모두 `null` 이고,
    장소는 찾았지만 대표 이미지를 얻지 못하면 이미지만 `null` 이다.
    """

    coupon_location: str
    coupon_price: int
    location_id: int | None = None
    location_address: str | None = None
    location_image_url: str | None = None


class TreasureMissionCompletionResponse(CamelModel):
    """GET /api/v1/missions/{missionType}/{missionId}/completion 정상 응답.

    두 목록은 결과가 없어도 키를 생략하지 않고 빈 배열로 내려준다.
    """

    completed_mission: CompletedTreasureMissionResponse
    nearby_treasure_missions: list[NearbyTreasureMissionResponse]
    received_coupons: list[ReceivedCouponResponse]
