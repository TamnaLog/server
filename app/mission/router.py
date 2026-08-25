"""미션 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.mission import service


router = APIRouter(prefix="/api/v1/missions", tags=["mission"])


@router.get("/{mission_id}", summary="미션 홈 조회")
def get_mission_home(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/missions/{missionId} - 미션 홈 조회."""
    # TODO: 요청/응답 스키마 연결 (app/mission/schemas.py)
    return service.get_mission_home(mission_id, db)
