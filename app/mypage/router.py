"""마이페이지 도메인 라우터.

API 명세: app/mypage/docs/API_SPEC.md

여행 마무리 엽서 저장은 아직 명세가 확정되지 않아 TODO 로 남겨둔다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.mypage import service
from app.mypage.schemas import MyPageResponse, UserProfileUpdateRequest


router = APIRouter(prefix="/api/v1/users/me", tags=["mypage"])


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


# TODO: POST (엔드포인트 미정) - 여행 마무리 엽서 저장
#       노션 명세에 엔드포인트가 아직 비어 있음 (확정되면 라우트 추가)
