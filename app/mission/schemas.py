"""미션 도메인 요청/응답 스키마.

필드명은 app/mission/docs/API_SPEC.md 기준(camelCase)이다.
보상 스키마는 세 미션 유형이 같은 형태를 쓰므로 공용 모듈(app/common/rewards.py)의 것을 쓴다.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.common.rewards import ArCharacterResponse, CouponResponse, RemainingRewardResponse


__all__ = [
    "ArCharacterResponse",
    "CouponResponse",
    "MissionHomeResponse",
    "MissionStepResponse",
    "MissionType",
    "RemainingRewardResponse",
]


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MissionType(str, Enum):
    """미션 유형. 조회할 유형별 세부 미션 테이블을 결정한다."""

    CULTURE = "CULTURE"
    COOPERATIVE = "COOPERATIVE"
    TREASURE = "TREASURE"


class MissionStepResponse(CamelModel):
    """미션 단계 하나."""

    step: int
    step_title: str
    description: str


class MissionHomeResponse(CamelModel):
    """GET /api/v1/missions/{missionType}/{missionId} 정상 응답.

    `id` 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션의 id다.
    """

    id: int
    mission_type: MissionType
    mission_title: str
    description: str
    remaining_reward: RemainingRewardResponse
    steps: list[MissionStepResponse]
