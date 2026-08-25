"""홈 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.home import service


router = APIRouter(prefix="/api/v1/users/me", tags=["home"])


@router.get("/home", summary="홈 조회")
def get_home(db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/users/me/home - 홈 조회."""
    # TODO: 요청/응답 스키마 연결 (app/home/schemas.py)
    return service.get_home(db)
