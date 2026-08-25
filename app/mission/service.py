"""미션 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def get_mission_home(mission_id: int, db: Session) -> dict[str, Any]:
    """미션 홈 조회."""
    raise NotImplementedError
