"""문화 미션 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- CULTURE_MISSION
- CULTURE_MISSION_PROGRESS

MISSION 은 app/mission/models.py 에서 한 번만 정의하고 여기서는 import해서 사용한다.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.mission.models import Mission, MissionStatus


__all__ = ["CultureMission", "CultureMissionProgress", "Mission", "MissionStatus"]


class CultureMission(Base):
    """CULTURE_MISSION - 문화 미션. `mission_id` 가 MISSION 과 1:1로 이어진다."""

    __tablename__ = "CULTURE_MISSION"

    mission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("MISSION.id", ondelete="CASCADE"), primary_key=True
    )
    quiz_total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # [{quiz_index, img_url, question, options, answer, hint, explanation}]
    quiz_detail: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CultureMissionProgress(Base):
    """CULTURE_MISSION_PROGRESS - 문화 미션 진행도."""

    __tablename__ = "CULTURE_MISSION_PROGRESS"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    culture_mission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("CULTURE_MISSION.mission_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    mission_status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_quiz_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    correct_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
