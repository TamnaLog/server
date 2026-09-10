"""기타 도메인 요청/응답 스키마.

필드명은 app/others/docs/API_SPEC.md 기준(camelCase)이다.
"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


__all__ = [
    "GpsSaveRequest",
    "StepCountSaveRequest",
    "StepCountSaveResponse",
]


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StepCountSaveRequest(CamelModel):
    """PUT /api/v1/users/me/step-counts 요청 Body.

    프론트가 특정 시점의 누적 걸음 수를 보낸다. 목표 달성 여부도 프론트가 판정해서 보내고,
    서버는 이 값을 저장하거나 걸음 수로 다시 검증하지 않는다.
    작성자는 요청이 아니라 공통 `Authorization: Bearer` 액세스 토큰으로 식별한다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    recorded_at: datetime = Field(description="걸음 수를 측정한 시각. KST 기준")
    steps_count: int = Field(ge=0, description="해당 시점의 누적 걸음 수")
    is_goal_achieved: bool = Field(description="프론트가 판단한 목표 걸음 수 달성 여부")

    @model_validator(mode="after")
    def _check_naive(self) -> Self:
        """offset 이 붙은 시각은 받지 않는다. (어기면 공통 400)

        시간 값은 프로젝트 정책대로 offset 없는 KST 로 주고받고 DB 에도 그대로 저장한다.
        offset 이 붙은 값을 그대로 저장하면 KST 인지 아닌지 구분할 수 없다.
        """
        if self.recorded_at.tzinfo is not None:
            raise ValueError("recordedAt 은 offset 없는 KST 시각이어야 합니다.")
        return self


class StepCountSaveResponse(CamelModel):
    """PUT /api/v1/users/me/step-counts 정상 응답.

    목표를 달성하지 못했으면 캐릭터를 추첨하지 않으므로 캐릭터 두 값은 `null` 이다.
    목표 걸음 수는 기록이 아니라 사용자 설정값(`USER.target_step`)이다.
    """

    character_name: str | None = None
    character_image_url: str | None = None
    target_step: int


class GpsSaveRequest(CamelModel):
    """POST /api/v1/users/me/gps 요청 Body.

    프론트가 일정 간격으로 측정한 좌표를 보낸다.
    작성자는 요청이 아니라 공통 `Authorization: Bearer` 액세스 토큰으로 식별한다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    recorded_at: datetime = Field(description="좌표를 측정한 시각. KST 기준")
    latitude: float = Field(ge=-90, le=90, description="사용자 위도")
    longitude: float = Field(ge=-180, le=180, description="사용자 경도")

    @model_validator(mode="after")
    def _check_naive(self) -> Self:
        """offset 이 붙은 시각은 받지 않는다. (어기면 공통 400)

        시간 값은 프로젝트 정책대로 offset 없는 KST 로 주고받고 DB 에도 그대로 저장한다.
        offset 이 붙은 값을 그대로 저장하면 KST 인지 아닌지 구분할 수 없다.
        """
        if self.recorded_at.tzinfo is not None:
            raise ValueError("recordedAt 은 offset 없는 KST 시각이어야 합니다.")
        return self
