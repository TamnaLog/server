"""온보딩 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.onboarding import service


router = APIRouter(prefix="/api/v1/users", tags=["onboarding"])


@router.patch("/me", summary="사용자 온보딩 정보 저장")
def save_onboarding_info(db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/users/me - 사용자 온보딩 정보 저장."""
    # TODO: 요청/응답 스키마 연결 (app/onboarding/schemas.py)
    return service.save_onboarding_info(db)
