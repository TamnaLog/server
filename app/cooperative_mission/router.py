"""협동 미션 도메인 라우터.

API 명세: app/cooperative_mission/docs/API_SPEC.md

아직 명세가 확정되지 않은 API는 요청/응답 스키마 연결을 TODO로 남겨둔다.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, File, Path, Response, status
from sqlalchemy.orm import Session

from app.cooperative_mission import service
from app.cooperative_mission.schemas import (
    CooperativeMissionLeaveResponse,
    CooperativeMissionProgressSaveRequest,
    CooperativeRoleAssignmentSaveRequest,
    RoleProgressVerificationRequest,
    RoleProgressVerificationResponse,
    CooperativeMissionStartResponse,
    CooperativeMissionStatusResponse,
    JoinCooperativeMissionRequest,
    JoinCooperativeMissionResponse,
)
from app.core.database import get_db
from app.core.deps import get_current_user_id


router = APIRouter(prefix="/api/v1/cooperative-missions", tags=["cooperative-mission"])


def _error_response(description: str, code: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                "example": {"code": code},
            }
        },
    }


@router.post(
    "/join-requests",
    summary="URL로 참여 요청",
    # 새 참여 요청을 만든 경우가 기본이고, 이미 참여자면 200으로 바꾼다.
    status_code=status.HTTP_201_CREATED,
    response_model=JoinCooperativeMissionResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_200_OK: {
            "description": "이미 참여 요청했거나 수락된 사용자인 경우",
            "model": JoinCooperativeMissionResponse,
        },
        status.HTTP_404_NOT_FOUND: _error_response(
            "진행 중인 협동 미션 방을 찾을 수 없음", service.INVALID_INVITE_TOKEN
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "최대 인원 도달 또는 참여를 받을 수 없는 단계",
            f"{service.COOPERATIVE_MISSION_FULL} | {service.COOPERATIVE_MISSION_JOIN_CLOSED}",
        ),
    },
)
def join_cooperative_mission(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    request: Annotated[JoinCooperativeMissionRequest, Body()],
) -> JoinCooperativeMissionResponse:
    """POST /api/v1/cooperative-missions/join-requests - URL로 참여 요청."""
    result = service.join_cooperative_mission(
        db=db, current_user_id=current_user_id, request=request
    )
    if not result.is_created:
        response.status_code = status.HTTP_200_OK
    return result.response


@router.post(
    "/{cooperative_mission_id}/progress",
    summary="협동 미션 시작하기/이어하기",
    # 진행도를 새로 만든 경우가 기본이고, 이어서 하는 경우에만 200으로 바꾼다.
    status_code=status.HTTP_201_CREATED,
    response_model=CooperativeMissionStartResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_200_OK: {
            "description": "이미 진행 중인 협동 미션을 이어서 하는 경우",
            "model": CooperativeMissionStartResponse,
        },
        status.HTTP_404_NOT_FOUND: _error_response(
            "협동 미션을 찾을 수 없음", service.COOPERATIVE_MISSION_NOT_FOUND
        ),
    },
)
def start_cooperative_mission(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    cooperative_mission_id: Annotated[
        int, Path(ge=1, description="진행도를 생성하거나 조회할 COOPERATIVE_MISSION.id")
    ],
) -> CooperativeMissionStartResponse:
    """POST /api/v1/cooperative-missions/{cooperativeMissionId}/progress - 협동 미션 시작하기/이어하기."""
    result = service.start_cooperative_mission(
        db=db,
        current_user_id=current_user_id,
        cooperative_mission_id=cooperative_mission_id,
    )
    if not result.is_created:
        response.status_code = status.HTTP_200_OK
    return result.response


@router.patch(
    "/{mission_progress_id}/participants/{participant_id}/accept",
    summary="참여 요청 수락",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_403_FORBIDDEN: _error_response(
            "현재 사용자가 방장이 아님", service.COOPERATIVE_MISSION_HOST_ONLY
        ),
        status.HTTP_404_NOT_FOUND: _error_response(
            "진행 중인 협동 미션 방 또는 수락할 팀원을 찾을 수 없음",
            f"{service.COOPERATIVE_MISSION_PROGRESS_NOT_FOUND} | "
            f"{service.COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND}",
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "참여 요청을 수락할 수 있는 초대 단계를 지남",
            service.COOPERATIVE_MISSION_JOIN_CLOSED,
        ),
    },
)
def accept_join_request(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_progress_id: Annotated[
        int, Path(ge=1, description="참여 요청이 속한 COOPERATIVE_MISSION_PROGRESS.id")
    ],
    participant_id: Annotated[
        int, Path(ge=1, description="수락할 COOPERATIVE_MISSION_PARTICIPANT.id")
    ],
) -> Response:
    """PATCH /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/{participantId}/accept."""
    service.accept_join_request(
        db=db,
        current_user_id=current_user_id,
        mission_progress_id=mission_progress_id,
        participant_id=participant_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# `/participants/me` 는 아래 `/participants/{participant_id}` 보다 먼저 등록해야 한다.
# 순서가 바뀌면 "me" 가 participant_id 로 먼저 매칭돼 400 이 된다.
@router.delete(
    "/{mission_progress_id}/participants/me",
    summary="협동 미션 나가기",
    status_code=status.HTTP_200_OK,
    response_model=CooperativeMissionLeaveResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "협동 미션 방 또는 현재 사용자의 참가자 데이터를 찾을 수 없음",
            f"{service.COOPERATIVE_MISSION_PROGRESS_NOT_FOUND} | "
            f"{service.COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND}",
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "이미 완료된 협동 미션", service.COOPERATIVE_MISSION_ALREADY_COMPLETED
        ),
    },
)
def leave_cooperative_mission(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_progress_id: Annotated[
        int, Path(ge=1, description="나갈 COOPERATIVE_MISSION_PROGRESS.id")
    ],
) -> CooperativeMissionLeaveResponse:
    """DELETE /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/me."""
    return service.leave_cooperative_mission(
        db=db,
        current_user_id=current_user_id,
        mission_progress_id=mission_progress_id,
    )


@router.delete(
    "/{mission_progress_id}/participants/{participant_id}",
    summary="참여 요청 거절",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_403_FORBIDDEN: _error_response(
            "현재 사용자가 방장이 아님", service.COOPERATIVE_MISSION_HOST_ONLY
        ),
        status.HTTP_404_NOT_FOUND: _error_response(
            "진행 중인 협동 미션 방 또는 거절할 참여 요청을 찾을 수 없음",
            f"{service.COOPERATIVE_MISSION_PROGRESS_NOT_FOUND} | "
            f"{service.COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND}",
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "초대 단계를 지났거나 이미 수락된 팀원",
            f"{service.COOPERATIVE_MISSION_JOIN_CLOSED} | "
            f"{service.COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED}",
        ),
    },
)
def reject_join_request(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_progress_id: Annotated[
        int, Path(ge=1, description="참여 요청이 속한 COOPERATIVE_MISSION_PROGRESS.id")
    ],
    participant_id: Annotated[
        int, Path(ge=1, description="거절할 COOPERATIVE_MISSION_PARTICIPANT.id")
    ],
) -> Response:
    """DELETE /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/{participantId}."""
    service.reject_join_request(
        db=db,
        current_user_id=current_user_id,
        mission_progress_id=mission_progress_id,
        participant_id=participant_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{mission_progress_id}/progress",
    summary="협동 미션 상태 조회",
    status_code=status.HTTP_200_OK,
    response_model=CooperativeMissionStatusResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "협동 미션 방이 없거나 현재 사용자가 그 방의 참가자가 아님",
            f"{service.COOPERATIVE_MISSION_PROGRESS_NOT_FOUND} | "
            f"{service.COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND}",
        ),
    },
)
def get_cooperative_mission_status(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_progress_id: Annotated[
        int, Path(ge=1, description="조회할 COOPERATIVE_MISSION_PROGRESS.id")
    ],
) -> CooperativeMissionStatusResponse:
    """GET /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress - 협동 미션 상태 조회."""
    return service.get_cooperative_mission_status(
        db=db,
        current_user_id=current_user_id,
        mission_progress_id=mission_progress_id,
    )


@router.patch(
    "/{mission_progress_id}/progress",
    summary="협동 미션 진행도 저장",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_403_FORBIDDEN: _error_response(
            "현재 사용자가 방장이 아님", service.COOPERATIVE_MISSION_HOST_ONLY
        ),
        status.HTTP_404_NOT_FOUND: _error_response(
            "협동 미션 진행도를 찾을 수 없음",
            service.COOPERATIVE_MISSION_PROGRESS_NOT_FOUND,
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "이미 완료됐거나 순차 단계 변경 조건을 만족하지 못함",
            f"{service.COOPERATIVE_MISSION_ALREADY_COMPLETED} | "
            f"{service.COOPERATIVE_MISSION_STEP_NOT_ALLOWED} | "
            f"{service.COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS} | "
            f"{service.COOPERATIVE_PARTICIPANT_ROLE_REQUIRED}",
        ),
    },
)
def save_cooperative_mission_progress(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_progress_id: Annotated[
        int, Path(ge=1, description="단계를 변경할 COOPERATIVE_MISSION_PROGRESS.id")
    ],
    request: Annotated[CooperativeMissionProgressSaveRequest, Body()],
) -> Response:
    """PATCH /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress - 협동 미션 진행도 저장."""
    service.save_cooperative_mission_progress(
        db=db,
        current_user_id=current_user_id,
        mission_progress_id=mission_progress_id,
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{mission_progress_id}/progress/stop", summary="협동 미션 중단")
def stop_cooperative_mission(mission_progress_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/cooperative-missions/{missionProgressId}/progress/stop - 협동 미션 중단."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.stop_cooperative_mission(mission_progress_id, db)


@router.put(
    "/{mission_progress_id}/role-assignments/{role_card_id}",
    summary="협동 미션 역할 배정 저장",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        status.HTTP_403_FORBIDDEN: _error_response(
            "현재 사용자가 방장이 아님", service.COOPERATIVE_MISSION_HOST_ONLY
        ),
        status.HTTP_404_NOT_FOUND: _error_response(
            "협동 미션 방, 역할 카드 또는 배정할 참가자를 찾을 수 없음",
            f"{service.COOPERATIVE_MISSION_PROGRESS_NOT_FOUND} | "
            f"{service.COOPERATIVE_ROLE_CARD_NOT_FOUND} | "
            f"{service.COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND}",
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "이미 완료됐거나 역할 배정 단계가 아님",
            f"{service.COOPERATIVE_MISSION_ALREADY_COMPLETED} | "
            f"{service.COOPERATIVE_MISSION_STEP_NOT_ALLOWED}",
        ),
    },
)
def save_role_assignment(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_progress_id: Annotated[
        int, Path(ge=1, description="역할을 배정할 COOPERATIVE_MISSION_PROGRESS.id")
    ],
    role_card_id: Annotated[
        int, Path(ge=1, description="담당자를 배정/변경할 COOPERATIVE_ROLE_CARD.id")
    ],
    request: Annotated[CooperativeRoleAssignmentSaveRequest, Body()],
) -> Response:
    """PUT /api/v1/cooperative-missions/{cooperativeMissionProgressId}/role-assignments/{roleCardId}."""
    service.save_role_assignment(
        db=db,
        current_user_id=current_user_id,
        mission_progress_id=mission_progress_id,
        role_card_id=role_card_id,
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{mission_progress_id}/role-progresses/{role_progress_id}/verification",
    summary="협동 미션 역할 진행도 저장",
    status_code=status.HTTP_200_OK,
    response_model=RoleProgressVerificationResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_403_FORBIDDEN: _error_response(
            "현재 사용자가 이 역할의 담당자가 아님",
            service.COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED,
        ),
        status.HTTP_404_NOT_FOUND: _error_response(
            "협동 미션 방 또는 역할 진행도를 찾을 수 없음",
            f"{service.COOPERATIVE_MISSION_PROGRESS_NOT_FOUND} | "
            f"{service.COOPERATIVE_ROLE_PROGRESS_NOT_FOUND}",
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "이미 완료됐거나 미션 수행 단계가 아니거나 이미 인증한 역할",
            f"{service.COOPERATIVE_MISSION_ALREADY_COMPLETED} | "
            f"{service.COOPERATIVE_MISSION_STEP_NOT_ALLOWED} | "
            f"{service.COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED}",
        ),
    },
)
def verify_role_progress(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_progress_id: Annotated[
        int, Path(ge=1, description="역할 진행도가 속한 COOPERATIVE_MISSION_PROGRESS.id")
    ],
    role_progress_id: Annotated[
        int, Path(ge=1, description="사진을 인증할 COOPERATIVE_ROLE_PROGRESS.id")
    ],
    # File() 로 선언해야 Swagger 문서에도 multipart/form-data 로 나온다.
    request: Annotated[RoleProgressVerificationRequest, File()],
) -> RoleProgressVerificationResponse:
    """POST /api/v1/cooperative-missions/{progressId}/role-progresses/{roleProgressId}/verification."""
    # UploadFile.file 은 동기 파일 객체라, DB 세션과 같은 동기 흐름에서 그대로 읽을 수 있다.
    return service.verify_role_progress(
        db=db,
        current_user_id=current_user_id,
        mission_progress_id=mission_progress_id,
        role_progress_id=role_progress_id,
        item_image=request.item_image.file,
    )
