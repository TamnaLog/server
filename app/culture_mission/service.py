"""문화 미션 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def start_culture_mission(mission_id: int, db: Session) -> dict[str, Any]:
    """문화 미션 시작/이어하기."""
    raise NotImplementedError


def save_culture_mission_progress(mission_id: int, db: Session) -> dict[str, Any]:
    """문화 미션 진행도 저장."""
    raise NotImplementedError


def stop_culture_mission(mission_id: int, db: Session) -> dict[str, Any]:
    """문화 미션 중단."""
    raise NotImplementedError
