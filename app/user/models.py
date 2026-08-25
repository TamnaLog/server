"""사용자 공통 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- USER
- USER_SETTING
- USER_TRAVEL_STYLE
- STEP_COUNT

여러 도메인이 함께 쓰는 사용자 테이블은 여기서 한 번만 정의하고,
각 도메인 models.py에서 import해서 사용한다.
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.treasure_mission.models import ArCharacter


class UserTravelStyle(Base):
    """USER_TRAVEL_STYLE - 여행 유형 마스터."""

    __tablename__ = "USER_TRAVEL_STYLE"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_type: Mapped[str] = mapped_column(String(20), nullable=False)
    type_description: Mapped[str] = mapped_column(String(200), nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class User(Base):
    """USER - 사용자."""

    __tablename__ = "USER"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expectation: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    transportation: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    travel_style: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    user_travel_style_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("USER_TRAVEL_STYLE.id", ondelete="SET NULL"), nullable=True
    )
    ar_character_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("AR_CHARACTER.id", ondelete="SET NULL"), nullable=True
    )
    nickname: Mapped[str | None] = mapped_column(String(20), nullable=True)
    point: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user_travel_style: Mapped[UserTravelStyle | None] = relationship(lazy="joined")
    ar_character: Mapped[ArCharacter | None] = relationship(lazy="joined")
