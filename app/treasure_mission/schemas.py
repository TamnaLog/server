"""보물 찾기 도메인 요청/응답 스키마.

필드명은 app/treasure_mission/docs/API_SPEC.md 기준(camelCase)이다.
보물 표시/인식 반경은 프론트가 관리하므로 응답에 포함하지 않는다.
"""

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.common.next_location import NextLocationResponse
from app.common.rewards import GrantedRewardResponse
from app.mission.models import MissionStatus


__all__ = [
    "GrantedRewardResponse",
    "MissionStatus",
    "NextLocationResponse",
    "TreasureItemResponse",
    "TreasureLocationResponse",
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
    """보물찾기 미션이 진행되는 장소."""

    location_title: str
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
