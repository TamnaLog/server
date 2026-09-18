"""방명록 도메인 라우터.

API 명세: app/guestbook/docs/API_SPEC.md

아직 명세가 확정되지 않은 API는 요청/응답 스키마 연결을 TODO로 남겨둔다.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.guestbook import service
from app.guestbook.schemas import (
    GuestbookCreateRequest,
    GuestbookCreateResponse,
    GuestbookLikeRequest,
    GuestbookLikeResponse,
    GuestbookListQuery,
    GuestbookListResponse,
    GuestbookWriteAvailabilityResponse,
    WriteAvailabilityQuery,
)


router = APIRouter(prefix="/api/v1/guestbooks", tags=["guestbook"])


def _error_response(description: str, code: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                "example": {"code": code},
            }
        },
    }


@router.get(
    "/write-availability",
    summary="방명록 작성 가능 여부 조회",
    status_code=status.HTTP_200_OK,
    response_model=GuestbookWriteAvailabilityResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "장소를 찾을 수 없음", service.LOCATION_NOT_FOUND
        ),
    },
)
def get_write_availability(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    query: Annotated[WriteAvailabilityQuery, Query()],
) -> GuestbookWriteAvailabilityResponse:
    """GET /api/v1/guestbooks/write-availability - 방명록 작성 가능 여부 조회."""
    return service.get_write_availability(
        db=db, current_user_id=current_user_id, query=query
    )


@router.post(
    "",
    summary="방명록 작성",
    status_code=status.HTTP_201_CREATED,
    response_model=GuestbookCreateResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "장소 또는 미션을 찾을 수 없음",
            f"{service.LOCATION_NOT_FOUND} | {service.MISSION_NOT_FOUND}",
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "현재 사용자의 방문 이력이 없는 장소", service.LOCATION_NOT_VISITED
        ),
    },
)
def create_guestbook(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    # File() 로 선언해야 Swagger 문서에도 multipart/form-data 로 나온다.
    request: Annotated[GuestbookCreateRequest, File()],
) -> GuestbookCreateResponse:
    """POST /api/v1/guestbooks - 방명록 작성."""
    return service.create_guestbook(
        db=db, current_user_id=current_user_id, request=request
    )


@router.get(
    "",
    summary="방명록 조회",
    status_code=status.HTTP_200_OK,
    response_model=GuestbookListResponse,
    response_model_by_alias=True,
)
def get_guestbooks(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    query: Annotated[GuestbookListQuery, Query()],
) -> GuestbookListResponse:
    """GET /api/v1/guestbooks - 방명록 조회."""
    return service.get_guestbooks(
        db=db, current_user_id=current_user_id, query=query
    )


@router.put(
    "/{guestbook_id}/like",
    summary="방명록 좋아요",
    status_code=status.HTTP_200_OK,
    response_model=GuestbookLikeResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "방명록을 찾을 수 없거나 삭제된 방명록", service.GUESTBOOK_NOT_FOUND
        ),
    },
)
def set_guestbook_like(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    guestbook_id: Annotated[int, Path(ge=1, description="좋아요 상태를 바꿀 방명록 id")],
    request: GuestbookLikeRequest,
) -> GuestbookLikeResponse:
    """PUT /api/v1/guestbooks/{guestbookId}/like - 방명록 좋아요."""
    return service.set_guestbook_like(
        db=db,
        current_user_id=current_user_id,
        guestbook_id=guestbook_id,
        request=request,
    )
