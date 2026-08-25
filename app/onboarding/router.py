"""온보딩 도메인 라우터.

API 명세: app/onboarding/docs/API_SPEC.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.onboarding import service
from app.onboarding.schemas import OnboardingSaveRequest, OnboardingSaveResponse


router = APIRouter(prefix="/api/v1/users", tags=["onboarding"])


@router.patch(
    "/me",
    summary="사용자 온보딩 정보 저장",
    status_code=status.HTTP_201_CREATED,
    response_model=OnboardingSaveResponse,
    response_model_by_alias=True,
)
def save_onboarding_info(
    request: OnboardingSaveRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
) -> OnboardingSaveResponse:
    """PATCH /api/v1/users/me - 사용자 온보딩 정보 저장."""
    return service.save_onboarding_info(
        db=db, current_user_id=current_user_id, request=request
    )
