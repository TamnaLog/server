"""지도 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def get_map_home(db: Session) -> dict[str, Any]:
    """지도 홈 조회."""
    raise NotImplementedError


def get_map_modals(db: Session) -> dict[str, Any]:
    """지도 모달 조회."""
    raise NotImplementedError


def search_map(db: Session) -> dict[str, Any]:
    """지도 검색 결과 조회."""
    raise NotImplementedError


def get_map_location(location_id: int, db: Session) -> dict[str, Any]:
    """지도 장소 상세 조회."""
    raise NotImplementedError
