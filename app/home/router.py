"""홈 도메인 라우터.

API 명세: app/home/docs/API_SPEC.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.home import service
from app.home.schemas import HomeResponse


router = APIRouter(prefix="/api/v1/users/me", tags=["home"])


@router.get(
    "/home",
    summary="홈 조회",
    status_code=status.HTTP_200_OK,
    response_model=HomeResponse,
    response_model_by_alias=True,
)
def get_home(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    latitude: Annotated[
        float, Query(ge=-90, le=90, description="현재 위치 또는 사용자가 선택한 위치의 위도")
    ],
    longitude: Annotated[
        float, Query(ge=-180, le=180, description="현재 위치 또는 사용자가 선택한 위치의 경도")
    ],
) -> HomeResponse:
    """GET /api/v1/users/me/home - 홈 조회."""
    return service.get_home(
        db=db, current_user_id=current_user_id, latitude=latitude, longitude=longitude
    )
