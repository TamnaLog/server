"""협동 미션 도메인 요청/응답 스키마.

필드명은 app/cooperative_mission/docs/API_SPEC.md 기준(camelCase)이다.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.cooperative_mission.models import (
    MissionStatus,
    ParticipantRole,
    ParticipantStatus,
)


__all__ = [
    "CooperativeMissionStartResponse",
    "JoinCooperativeMissionRequest",
    "JoinCooperativeMissionResponse",
    "MissionStatus",
    "ParticipantResponse",
    "ParticipantRole",
    "ParticipantStatus",
    "RoleCardResponse",
    "RoleProgressResponse",
]


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ParticipantResponse(CamelModel):
    """협동 미션 참여자 한 명. 아직 수락 전인 참여 요청(`PENDING`)도 포함한다."""

    participant_id: int
    name: str
    participant_role: ParticipantRole
    participant_status: ParticipantStatus


class RoleCardResponse(CamelModel):
    """역할 카드 하나.

    역할 카드는 특정 미션에 속하지 않고 모든 협동 미션이 공통으로 쓰는 마스터 데이터다.
    """

    role_card_id: int
    role_name: str
    role_description: str
    location_to_find: list[str]


class RoleProgressResponse(CamelModel):
    """참여자에게 배정된 역할과 그 진행 상태."""

    role_progress_id: int
    participant_id: int
    participant_name: str
    role_card_id: int
    role_name: str
    progress_status: MissionStatus
    item_img_url: str | None = None


class CooperativeMissionStartResponse(CamelModel):
    """POST /api/v1/cooperative-missions/{cooperativeMissionId}/progress 정상 응답.

    진행도를 새로 만들었으면 `201`, 기존 진행도를 이어서 하면 `200` 으로 응답한다.
    시작하기와 이어하기의 응답 구조는 같고, 아직 없는 목록은 빈 배열로 내려간다.
    """

    mission_progress_id: int
    mission_progress_status: MissionStatus
    current_step: int
    team_token: str
    participants: list[ParticipantResponse]
    role_cards: list[RoleCardResponse]
    role_progresses: list[RoleProgressResponse]


class JoinCooperativeMissionRequest(CamelModel):
    """POST /api/v1/cooperative-missions/join-requests 요청 Body.

    참여할 사람은 Body 가 아니라 공통 `X-Test-User-Id` 헤더로 식별한다.
    """

    team_token: str = Field(min_length=1, description="초대 URL 에서 추출한 팀 토큰")


class JoinCooperativeMissionResponse(CamelModel):
    """POST /api/v1/cooperative-missions/join-requests 정상 응답.

    새 참여 요청을 만들었으면 `201`, 이미 참여자였으면 `200` 으로 응답한다.
    프론트는 `mission_progress_id` 로 자신의 참여 상태를 폴링한다.
    """

    mission_progress_id: int
    participant_id: int
    participant_status: ParticipantStatus
