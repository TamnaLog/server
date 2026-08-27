"""협동 미션 도메인 요청/응답 스키마.

필드명은 app/cooperative_mission/docs/API_SPEC.md 기준(camelCase)이다.
"""

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.common.next_location import NextLocationSummaryResponse
from app.common.rewards import GrantedRewardResponse
from app.cooperative_mission.models import (
    MissionStatus,
    ParticipantRole,
    ParticipantStatus,
)


__all__ = [
    "CooperativeMissionProgressSaveRequest",
    "CooperativeRoleAssignmentSaveRequest",
    "RoleProgressVerificationRequest",
    "RoleProgressVerificationResponse",
    "CooperativeMissionStartResponse",
    "CooperativeMissionStatusResponse",
    "CurrentParticipantResponse",
    "GrantedRewardResponse",
    "JoinCooperativeMissionRequest",
    "JoinCooperativeMissionResponse",
    "MissionStatus",
    "NextLocationSummaryResponse",
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


class CurrentParticipantResponse(CamelModel):
    """Bearer 토큰으로 식별한 현재 사용자의 참가자 정보.

    프론트가 자기 참가자 id/역할/상태를 보내지 않고 이 값으로 화면을 정한다.
    """

    participant_id: int
    participant_role: ParticipantRole
    participant_status: ParticipantStatus


class CooperativeMissionStatusResponse(CamelModel):
    """GET /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress 정상 응답.

    프론트가 폴링하는 API라 단계별로 필요한 값만 채우고 나머지는 키를 지우지 않고 `null` 로 둔다.

    | 필드 | 1단계 | 2·3단계 | 4단계 |
    | --- | --- | --- | --- |
    | `current_participant` / `participants` | 값 | 값 | `null` |
    | `role_cards` | `null` | 값 | `null` |
    | `role_progresses` / 역할 집계 | `null` | 값(없으면 빈 배열/0) | `null` |
    | `reward` / `next_location` | `null` | `null` | 값 |
    """

    mission_progress_id: int
    mission_id: int
    mission_title: str
    mission_progress_status: MissionStatus
    current_step: int
    current_participant: CurrentParticipantResponse | None = None
    participants: list[ParticipantResponse] | None = None
    role_cards: list[RoleCardResponse] | None = None
    role_progresses: list[RoleProgressResponse] | None = None
    completed_role_count: int | None = None
    total_role_count: int | None = None
    reward: GrantedRewardResponse | None = None
    next_location: NextLocationSummaryResponse | None = None


class CooperativeMissionProgressSaveRequest(CamelModel):
    """PATCH /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress 요청 Body.

    다음 단계 하나만 받는다. 1단계로 되돌리는 요청은 없으므로 `2 | 3 | 4` 만 허용한다.
    """

    current_step: int = Field(ge=2, le=4, description="변경할 다음 단계. 2 | 3 | 4")


class CooperativeRoleAssignmentSaveRequest(CamelModel):
    """PUT /api/v1/cooperative-missions/{progressId}/role-assignments/{roleCardId} 요청 Body.

    배정 단위는 Path 의 역할 카드이고, Body 로는 그 카드를 맡을 참가자만 받는다.
    """

    participant_id: int = Field(
        ge=1, description="역할 카드를 배정할 ACCEPTED 참가자 id"
    )


class RoleProgressVerificationRequest(CamelModel):
    """POST .../role-progresses/{roleProgressId}/verification 요청 Body.

    `multipart/form-data` 로 받는다. 사진 형식/크기 검증은 파일 내용을 봐야 하므로
    스키마가 아니라 service 에서 처리한다.
    참가자와 역할 카드는 요청으로 받지 않고 역할 진행도 관계로 조회한다.
    """

    item_image: UploadFile


class RoleProgressVerificationResponse(CamelModel):
    """POST .../role-progresses/{roleProgressId}/verification 정상 응답.

    인증 실패는 오류가 아니라 판정 결과이므로 `200` 으로 `is_verified: false` 를 반환한다.
    갱신된 역할 상태는 상태 조회 API 폴링으로 확인한다.
    """

    is_verified: bool


class JoinCooperativeMissionRequest(CamelModel):
    """POST /api/v1/cooperative-missions/join-requests 요청 Body.

    참여할 사람은 Body 가 아니라 공통 `Authorization: Bearer` 액세스 토큰으로 식별한다.
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
