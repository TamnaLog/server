"""홈 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def get_home(db: Session) -> dict[str, Any]:
    """홈 조회."""
    raise NotImplementedError
