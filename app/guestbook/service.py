"""방명록 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def create_guestbook(db: Session) -> dict[str, Any]:
    """방명록 저장."""
    raise NotImplementedError


def get_guestbooks(db: Session) -> dict[str, Any]:
    """방명록 조회."""
    raise NotImplementedError
