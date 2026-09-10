"""기타 도메인 라우터.

API 명세: app/others/docs/API_SPEC.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.others import service
from app.others.schemas import (
    GpsSaveRequest,
    StepCountSaveRequest,
    StepCountSaveResponse,
)


router = APIRouter(prefix="/api/v1/users/me", tags=["others"])


@router.put(
    "/step-counts",
    summary="걸음 수 저장",
    status_code=status.HTTP_200_OK,
    response_model=StepCountSaveResponse,
)
def save_step_count(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    request: StepCountSaveRequest,
) -> StepCountSaveResponse:
    """PUT /api/v1/users/me/step-counts - 걸음 수 저장."""
    return service.save_step_count(
        db=db, current_user_id=current_user_id, request=request
    )


@router.post(
    "/gps",
    summary="GPS 및 방문 장소 저장",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def save_gps(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    request: GpsSaveRequest,
) -> Response:
    """POST /api/v1/users/me/gps - GPS 및 방문 장소 저장."""
    service.save_gps(db=db, current_user_id=current_user_id, request=request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
