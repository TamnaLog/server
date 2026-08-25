"""협동 미션 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def get_invitation(invite_token: str, db: Session) -> dict[str, Any]:
    """초대 url 정보 조회."""
    raise NotImplementedError


def join_as_guest(invite_token: str, db: Session) -> dict[str, Any]:
    """초대 url로 게스트 참여."""
    raise NotImplementedError


def start_cooperative_mission(mission_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 시작하기/이어하기."""
    raise NotImplementedError


def get_cooperative_mission_status(mission_progress_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 상태 조회."""
    raise NotImplementedError


def save_cooperative_mission_progress(mission_progress_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 진행도 저장."""
    raise NotImplementedError


def stop_cooperative_mission(mission_progress_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 중단."""
    raise NotImplementedError


def save_role_progress(mission_progress_id: int, role_progress_id: int, db: Session) -> dict[str, Any]:
    """협동 미션 역할 진행도 저장."""
    raise NotImplementedError
