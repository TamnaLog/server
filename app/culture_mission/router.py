"""문화 미션 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.culture_mission import service


router = APIRouter(prefix="/api/v1/culture-missions", tags=["culture-mission"])


@router.post("/{mission_id}/progress", summary="문화 미션 시작/이어하기")
def start_culture_mission(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/culture-missions/{missionId}/progress - 문화 미션 시작/이어하기."""
    # TODO: 요청/응답 스키마 연결 (app/culture_mission/schemas.py)
    return service.start_culture_mission(mission_id, db)


@router.patch("/{mission_id}/progress", summary="문화 미션 진행도 저장")
def save_culture_mission_progress(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/culture-missions/{missionId}/progress - 문화 미션 진행도 저장."""
    # TODO: 요청/응답 스키마 연결 (app/culture_mission/schemas.py)
    return service.save_culture_mission_progress(mission_id, db)


@router.patch("/{mission_id}/progress/stop", summary="문화 미션 중단")
def stop_culture_mission(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/culture-missions/{missionId}/progress/stop - 문화 미션 중단."""
    # TODO: 요청/응답 스키마 연결 (app/culture_mission/schemas.py)
    return service.stop_culture_mission(mission_id, db)
