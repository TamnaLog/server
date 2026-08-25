"""홈 도메인 요청/응답 스키마.

필드명은 app/home/docs/API_SPEC.md 기준(camelCase)이다.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MissionType(str, Enum):
    """미션 유형."""

    CULTURE = "CULTURE"
    TREASURE = "TREASURE"
    COOPERATIVE = "COOPERATIVE"


class LocationPoint(CamelModel):
    """미션 장소 좌표."""

    lat: float
    lng: float


class RecommendedMission(CamelModel):
    """홈에 노출할 추천 미션.

    장소가 없는 미션이면 장소 관련 필드는 모두 `null` 이다.
    """

    mission_id: int
    mission_type: MissionType
    mission_title: str
    location_title: str | None = None
    location: LocationPoint | None = None
    distance_meter: int | None = None
    duration_minutes: int | None = None


class ProgressMission(CamelModel):
    """사용자가 진행 중인 미션.

    추천 미션과 달리 `location` 좌표는 내려주지 않고 단계 정보를 함께 내려준다.
    단계 정보의 출처는 미션 유형마다 다르다. (BUSINESS_RULES 5. 단계 정보)

    - 문화 미션: 퀴즈 진행도(`quiz_total_count` / `current_quiz_index`)
    - 보물 찾기 / 협동 미션: 공통 단계 정보(`step_detail` 개수 / 진행도의 `current_step`)
    """

    mission_id: int
    mission_type: MissionType
    mission_title: str
    location_title: str | None = None
    distance_meter: int | None = None
    duration_minutes: int | None = None
    total_step: int
    current_step: int


class HomeResponse(CamelModel):
    """GET /api/v1/users/me/home 정상 응답."""

    mission_recommend: list[RecommendedMission]
    progress_mission: list[ProgressMission]
    guestbook_count: int
    character_img_url: str | None = None
