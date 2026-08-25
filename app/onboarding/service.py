"""온보딩 도메인 비즈니스 로직."""

from typing import Any

from sqlalchemy.orm import Session


def save_onboarding_info(db: Session) -> dict[str, Any]:
    """사용자 온보딩 정보 저장."""
    raise NotImplementedError
