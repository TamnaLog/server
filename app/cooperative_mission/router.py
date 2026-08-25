"""협동 미션 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.cooperative_mission import service


router = APIRouter(prefix="/api/v1/cooperative-missions", tags=["cooperative-mission"])


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


@router.post("/{mission_id}/progress", summary="협동 미션 시작하기/이어하기")
def start_cooperative_mission(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/cooperative-missions/{missionId}/progress - 협동 미션 시작하기/이어하기."""
    # TODO: 요청/응답 스키마 연결 (app/cooperative_mission/schemas.py)
    return service.start_cooperative_mission(mission_id, db)


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
