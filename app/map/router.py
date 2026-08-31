"""지도 도메인 라우터.

API 명세: app/map/docs/API_SPEC.md, app/map/docs/BUSINESS_RULES.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.map import service
from app.map.schemas import (
    ClusteredMapContentsResponse,
    LocationDetailQuery,
    LocationDetailResponse,
    LocationModalResponse,
    MapContentsQuery,
    MapContentsResponse,
    MapModalQuery,
    MapSearchQuery,
    MapSearchResponse,
    RoadGuestbookModalResponse,
)


router = APIRouter(prefix="/api/v1/map", tags=["map"])


@router.get(
    "/contents",
    summary="지도 홈 조회",
    status_code=status.HTTP_200_OK,
    response_model=MapContentsResponse | ClusteredMapContentsResponse,
    response_model_by_alias=True,
)
def get_map_contents(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    query: Annotated[MapContentsQuery, Query()],
) -> MapContentsResponse | ClusteredMapContentsResponse:
    """GET /api/v1/map/contents - 지도 홈 조회.

    `isClustered` 에 따라 응답 형태가 다르다.
    `true` 면 좌표만, `false` 면 마커에 필요한 상세 정보까지 내려준다.
    미션 완료 여부와 미션 방명록 작성 여부는 토큰으로 식별한 현재 사용자 기준이다.
    """
    return service.get_map_contents(
        db=db, current_user_id=current_user_id, query=query
    )


@router.get(
    "/modals",
    summary="지도 모달 조회",
    status_code=status.HTTP_200_OK,
    response_model=LocationModalResponse | RoadGuestbookModalResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "조회 대상을 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {"code": service.MAP_MODAL_TARGET_NOT_FOUND}
                }
            },
        },
    },
)
def get_map_modal(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    query: Annotated[MapModalQuery, Query()],
) -> LocationModalResponse | RoadGuestbookModalResponse:
    """GET /api/v1/map/modals - 지도 모달 조회.

    `targetType` 에 따라 응답 형태가 다르다.
    `LOCATION` 이면 장소 정보와 미션·최신 방명록, `ROAD_GUESTBOOK` 이면 방명록 상세를 내려준다.
    미션의 완료/보상 수령 여부는 토큰으로 식별한 현재 사용자 기준이다.
    """
    return service.get_map_modal(db=db, current_user_id=current_user_id, query=query)


@router.get(
    "/search",
    summary="지도 검색 결과 조회",
    status_code=status.HTTP_200_OK,
    response_model=MapSearchResponse,
    response_model_by_alias=True,
    # 검색 결과 자체는 사용자별로 갈리지 않지만 로그인한 사용자만 호출할 수 있다.
    # 서비스에서 쓰지 않으므로 인자로 받지 않고 의존성으로만 검증한다.
    dependencies=[Depends(get_current_user_id)],
)
def search_map(
    db: Annotated[Session, Depends(get_db)],
    query: Annotated[MapSearchQuery, Query()],
) -> MapSearchResponse:
    """GET /api/v1/map/search - 지도 검색 결과 조회.

    장소 이름에 검색어가 포함된 장소를 미션 없는 장소와 미션 있는 장소로 나눠 내려준다.
    """
    return service.search_map(db=db, query=query)


@router.get(
    "/locations/{location_id}",
    summary="지도 장소 상세 조회",
    status_code=status.HTTP_200_OK,
    response_model=LocationDetailResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "장소를 찾을 수 없음",
            "content": {
                "application/json": {"example": {"code": service.LOCATION_NOT_FOUND}}
            },
        },
    },
)
def get_location_detail(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    location_id: Annotated[int, Path(ge=1, description="상세 조회할 LOCATION.id")],
    query: Annotated[LocationDetailQuery, Query()],
) -> LocationDetailResponse:
    """GET /api/v1/map/locations/{locationId} - 지도 장소 상세 조회.

    거리와 예상 이동 시간은 모달 응답을 재사용하지 않고 요청 좌표로 다시 계산한다.
    추천 미션은 토큰으로 식별한 현재 사용자가 완료하지 않은 미션 중에서 고른다.
    """
    return service.get_location_detail(
        db=db, current_user_id=current_user_id, location_id=location_id, query=query
    )
