"""방명록 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.guestbook import service


router = APIRouter(prefix="/api/v1/guestbooks", tags=["guestbook"])


@router.post("", summary="방명록 저장")
def create_guestbook(db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/guestbooks - 방명록 저장."""
    # TODO: 요청/응답 스키마 연결 (app/guestbook/schemas.py)
    return service.create_guestbook(db)


@router.get("", summary="방명록 조회")
def get_guestbooks(db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/guestbooks - 방명록 조회."""
    # TODO: 요청/응답 스키마 연결 (app/guestbook/schemas.py)
    return service.get_guestbooks(db)
