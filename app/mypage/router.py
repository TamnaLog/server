"""마이페이지 도메인 라우터.

API 명세: app/mypage/docs/API_SPEC.md

여행 마무리 엽서 저장은 아직 명세가 확정되지 않아 TODO 로 남겨둔다.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.mypage import service
from app.mypage.schemas import (
    MyPageResponse,
    TravelEndingContentCreateRequest,
    TravelEndingContentCreateResponse,
    TravelEndingElementsResponse,
    UserInfoResponse,
    UserProfileUpdateRequest,
)


router = APIRouter(prefix="/api/v1/users/me", tags=["mypage"])


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
    "/mypage",
    summary="마이페이지 조회",
    status_code=status.HTTP_200_OK,
    response_model=MyPageResponse,
    response_model_by_alias=True,
)
def get_mypage(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
) -> MyPageResponse:
    """GET /api/v1/users/me/mypage - 마이페이지 조회."""
    return service.get_mypage(db=db, current_user_id=current_user_id)


@router.get(
    "",
    summary="사용자 정보 조회",
    status_code=status.HTTP_200_OK,
    response_model=UserInfoResponse,
    response_model_by_alias=True,
)
def get_user_info(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
) -> UserInfoResponse:
    """GET /api/v1/users/me - 사용자 정보 조회. (프로필 수정 화면 진입용)"""
    return service.get_user_info(db=db, current_user_id=current_user_id)


@router.put(
    "/profile",
    summary="사용자 정보 변경",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def update_user_info(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    request: UserProfileUpdateRequest,
) -> Response:
    """PUT /api/v1/users/me/profile - 사용자 정보 변경."""
    service.update_user_info(
        db=db, current_user_id=current_user_id, request=request
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/travel-ending-elements",
    summary="여행 마무리 엽서 요소 조회",
    status_code=status.HTTP_200_OK,
    response_model=TravelEndingElementsResponse,
    response_model_by_alias=True,
)
def get_travel_ending_elements(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
) -> TravelEndingElementsResponse:
    """GET /api/v1/users/me/travel-ending-elements - 여행 마무리 엽서 요소 조회."""
    return service.get_travel_ending_elements(db=db, current_user_id=current_user_id)


@router.post(
    "/travel-ending-contents",
    summary="여행 마무리 엽서 저장",
    status_code=status.HTTP_201_CREATED,
    response_model=TravelEndingContentCreateResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_409_CONFLICT: _error_response(
            "엽서를 만들 포인트가 부족함", service.INSUFFICIENT_POINT
        ),
    },
)
def create_travel_ending_content(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    # File() 로 선언해야 Swagger 문서에도 multipart/form-data 로 나온다.
    request: Annotated[TravelEndingContentCreateRequest, File()],
) -> TravelEndingContentCreateResponse:
    """POST /api/v1/users/me/travel-ending-contents - 여행 마무리 엽서 저장."""
    return service.create_travel_ending_content(
        db=db, current_user_id=current_user_id, request=request
    )
