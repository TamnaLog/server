"""지도 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.map import service


router = APIRouter(prefix="/api/v1/map", tags=["map"])


@router.get("", summary="지도 홈 조회")
def get_map_home(db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/map - 지도 홈 조회."""
    # TODO: 요청/응답 스키마 연결 (app/map/schemas.py)
    return service.get_map_home(db)


@router.get("/modals", summary="지도 모달 조회")
def get_map_modals(db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/map/modals - 지도 모달 조회."""
    # TODO: 요청/응답 스키마 연결 (app/map/schemas.py)
    return service.get_map_modals(db)


@router.get("/search", summary="지도 검색 결과 조회")
def search_map(db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/map/search - 지도 검색 결과 조회."""
    # TODO: 요청/응답 스키마 연결 (app/map/schemas.py)
    return service.search_map(db)


@router.get("/locations/{location_id}", summary="지도 장소 상세 조회")
def get_map_location(location_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """GET /api/v1/map/locations/{locationId} - 지도 장소 상세 조회."""
    # TODO: 요청/응답 스키마 연결 (app/map/schemas.py)
    return service.get_map_location(location_id, db)
