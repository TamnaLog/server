"""미션 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- MISSION

MISSION 과 미션 진행 상태 값은 문화/협동/보물 찾기 도메인이 함께 쓰므로
여기서 한 번만 정의하고 다른 도메인은 import해서 사용한다.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.map.models import Location


class MissionType(str, Enum):
    """미션 유형."""

    CULTURE = "CULTURE"
    COOPERATIVE = "COOPERATIVE"
    TREASURE = "TREASURE"


class MissionStatus(str, Enum):
    """미션 진행 상태."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class Mission(Base):
    """MISSION - 미션 공통."""

    __tablename__ = "MISSION"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mission_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mission_title: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    location_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("LOCATION.id", ondelete="SET NULL"), nullable=True
    )
    # {ar_character_id, point, coupon_location, coupon_price}
    reward_detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # [{step, step_title, description}]
    step_detail: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    location: Mapped[Location | None] = relationship(lazy="joined")

    @property
    def total_step(self) -> int:
        """공통 미션 단계 수. `step_detail` 항목 개수로 판단한다.

        보물 찾기 / 협동 미션이 사용한다.
        문화 미션은 대신 `CULTURE_MISSION.quiz_total_count` 를 단계 수로 쓴다.
        """
        return len(self.step_detail or [])
