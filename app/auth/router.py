"""인증 도메인 라우터.

API 명세: app/auth/docs/API_SPEC.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.schemas import AnonymousUserResponse
from app.core.database import get_db


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/anonymous",
    summary="익명 사용자 발급",
    status_code=status.HTTP_201_CREATED,
    response_model=AnonymousUserResponse,
    response_model_by_alias=True,
)
def issue_anonymous_user(db: Annotated[Session, Depends(get_db)]) -> AnonymousUserResponse:
    """POST /api/v1/auth/anonymous - 익명 사용자 발급.

    아직 토큰이 없는 상태에서 호출하므로 `Authorization` 헤더를 요구하지 않는다.
    """
    return service.issue_anonymous_user(db=db)
