"""협동 미션 도메인 라우터.

API 명세: app/cooperative_mission/docs/API_SPEC.md

아직 명세가 확정되지 않은 API는 요청/응답 스키마 연결을 TODO로 남겨둔다.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.cooperative_mission import service
from app.cooperative_mission.schemas import CooperativeMissionStartResponse
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


@router.get("/invitations/{invite_token}", summary="초대 url 정보 조회")
def get_invitation(invite_token: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/cooperative-missions/invitations/{inviteToken} - 초대 url 정보 조회."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.get_invitation(invite_token, db)


@router.post("/invitations/{invite_token}/participants", summary="초대 url로 게스트 참여")
def join_as_guest(invite_token: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/cooperative-missions/invitations/{inviteToken}/participants - 초대 url로 게스트 참여."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.join_as_guest(invite_token, db)


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


@router.get("/{mission_progress_id}/progress", summary="협동 미션 상태 조회")
def get_cooperative_mission_status(mission_progress_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/cooperative-missions/{missionProgressId}/progress - 협동 미션 상태 조회."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.get_cooperative_mission_status(mission_progress_id, db)


@router.patch("/{mission_progress_id}/progress", summary="협동 미션 진행도 저장")
def save_cooperative_mission_progress(mission_progress_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/cooperative-missions/{missionProgressId}/progress - 협동 미션 진행도 저장."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.save_cooperative_mission_progress(mission_progress_id, db)


@router.patch("/{mission_progress_id}/progress/stop", summary="협동 미션 중단")
def stop_cooperative_mission(mission_progress_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/cooperative-missions/{missionProgressId}/progress/stop - 협동 미션 중단."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.stop_cooperative_mission(mission_progress_id, db)


@router.post("/{mission_progress_id}/role-progress/{role_progress_id}", summary="협동 미션 역할 진행도 저장")
def save_role_progress(mission_progress_id: int, role_progress_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/cooperative-missions/{missionProgressId}/role-progress/{roleProgressId} - 협동 미션 역할 진행도 저장."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.save_role_progress(mission_progress_id, role_progress_id, db)
