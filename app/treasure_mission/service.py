"""보물 찾기 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def save_picture_with_character(db: Session) -> dict[str, Any]:
    """ar 캐릭터와 사진 저장."""
    raise NotImplementedError


def start_treasure_mission(mission_id: int, db: Session) -> dict[str, Any]:
    """보물 찾기 시작/이어하기."""
    raise NotImplementedError


def save_treasure_mission_progress(mission_id: int, db: Session) -> dict[str, Any]:
    """보물 찾기 진행도 저장."""
    raise NotImplementedError


def stop_treasure_mission(mission_id: int, db: Session) -> dict[str, Any]:
    """보물 찾기 중단."""
    raise NotImplementedError
