"""문화 미션 도메인 요청/응답 스키마.

필드명은 app/culture_mission/docs/API_SPEC.md 기준(camelCase)이다.
보상 스키마는 세 미션 유형이 같은 형태를 쓰므로 공용 모듈(app/common/rewards.py)의 것을 쓴다.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.common.rewards import RewardDetailResponse


__all__ = ["CultureMissionStartResponse", "QuizDetailResponse", "RewardDetailResponse"]


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class QuizDetailResponse(CamelModel):
    """문화 미션 문제 하나.

    정답은 주관식/객관식 모두 문자열이다. 주관식 문제는 `options` 가 `null` 이다.
    """

    quiz_index: int
    img_url: str | None = None
    question: str
    options: list[str] | None = None
    answer: str
    hint: str
    explanation: str


class CultureMissionStartResponse(CamelModel):
    """POST /api/v1/culture-missions/{cultureMissionId}/progress 정상 응답.

    진행도를 새로 만들었으면 `201`, 기존 진행도를 이어서 하면 `200` 으로 응답한다.
    """

    culture_mission_progress_id: int
    quiz_count: int
    current_quiz_number: int
    is_rewarded: bool
    quiz_details: list[QuizDetailResponse]
    reward_detail: RewardDetailResponse
