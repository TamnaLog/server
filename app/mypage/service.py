"""마이페이지 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def get_mypage(db: Session) -> dict[str, Any]:
    """마이페이지 조회."""
    raise NotImplementedError


def update_user_info(db: Session) -> dict[str, Any]:
    """사용자 정보 변경."""
    raise NotImplementedError
