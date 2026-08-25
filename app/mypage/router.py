"""마이페이지 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.mypage import service


router = APIRouter(prefix="/api/v1/users/me", tags=["mypage"])


@router.get("/mypage", summary="마이페이지 조회")
def get_mypage(db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/users/me/mypage - 마이페이지 조회."""
    # TODO: 요청/응답 스키마 연결 (app/mypage/schemas.py)
    return service.get_mypage(db)


@router.post("/profile", summary="사용자 정보 변경")
def update_user_info(db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/users/me/profile - 사용자 정보 변경."""
    # TODO: 요청/응답 스키마 연결 (app/mypage/schemas.py)
    return service.update_user_info(db)


# TODO: POST (엔드포인트 미정) - 여행 마무리 엽서 저장
#       노션 명세에 엔드포인트가 아직 비어 있음 (확정되면 라우트 추가)
