"""문화 미션 도메인 요청/응답 스키마.

필드명은 app/culture_mission/docs/API_SPEC.md 기준(camelCase)이다.
보상 / 다음 장소 스키마는 미션 유형과 무관하게 같은 형태를 쓰므로 공용 모듈(app/common/)의 것을 쓴다.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.common.next_location import NextLocationMissionResponse, NextLocationResponse
from app.common.rewards import GrantedRewardResponse
from app.culture_mission.models import MissionStatus
from app.mission.schemas import MissionType


__all__ = [
    "CultureMissionProgressSaveRequest",
    "CultureMissionProgressSaveResponse",
    "CultureMissionStartResponse",
    "CultureMissionStopResponse",
    "GrantedRewardResponse",
    "MissionStatus",
    "MissionType",
    "NextLocationMissionResponse",
    "NextLocationResponse",
    "QuizDetailResponse",
]


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
    quiz_details: list[QuizDetailResponse]


class CultureMissionProgressSaveRequest(CamelModel):
    """PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress 요청 Body.

    정답 여부는 프론트 판정 결과를 그대로 신뢰한다. (백엔드에서 정답을 재검증하지 않는다)
    """

    quiz_index: int = Field(ge=1, description="사용자가 제출한 퀴즈 번호")
    is_correct: bool = Field(description="사용자가 해당 퀴즈를 맞혔는지 여부")


class CultureMissionProgressSaveResponse(CamelModel):
    """PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress 정상 응답.

    미션이 아직 진행 중이면 `next_location` 과 `reward` 는 `null` 이다.
    완료하면 `next_location` 은 반드시 객체이고, `reward` 에는 이번 요청으로 실제 지급된 보상만 담는다.
    """

    mission_progress_status: MissionStatus
    quiz_count: int
    current_quiz_number: int
    correct_number: int
    next_location: NextLocationResponse | None = None
    reward: GrantedRewardResponse | None = None


class CultureMissionStopResponse(CamelModel):
    """PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress/stop 정상 응답.

    중단은 완료 처리이므로 `mission_progress_status` 는 항상 `COMPLETED` 이고
    `next_location` 과 `reward` 는 항상 객체다. (지급된 보상이 없으면 `reward` 의 항목이 모두 `null`)
    남은 퀴즈와 무관하게 끝내므로 `current_quiz_number` 는 응답에 넣지 않는다.
    """

    mission_progress_status: MissionStatus
    quiz_count: int
    correct_number: int
    next_location: NextLocationResponse
    reward: GrantedRewardResponse
