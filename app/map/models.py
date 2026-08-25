"""지도 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- LOCATION
- VISITED_LOCATION
- GPS

LOCATION 은 미션/방명록 등 여러 도메인이 함께 쓰므로 여기서 한 번만 정의하고
다른 도메인은 import해서 사용한다.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Location(Base):
    """LOCATION - 장소."""

    __tablename__ = "LOCATION"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    location_title: Mapped[str] = mapped_column(String(20), nullable=False)
    location_address: Mapped[str] = mapped_column(String(100), nullable=False)
    location_category: Mapped[str] = mapped_column(String(20), nullable=False)
    # 장소 인증 반경(m)
    radius: Mapped[int] = mapped_column(Integer, nullable=False)
    # mx = 경도(longitude), my = 위도(latitude)
    mx: Mapped[float] = mapped_column(Float, nullable=False)
    my: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class VisitedLocation(Base):
    """VISITED_LOCATION - 사용자가 방문한 장소."""

    __tablename__ = "VISITED_LOCATION"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("LOCATION.id", ondelete="CASCADE"), nullable=False
    )
    visited_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    location: Mapped[Location] = relationship(lazy="joined")


class Gps(Base):
    """GPS - 사용자 위치 기록."""

    __tablename__ = "GPS"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    # mx = 경도(longitude), my = 위도(latitude)
    mx: Mapped[float] = mapped_column(Float, nullable=False)
    my: Mapped[float] = mapped_column(Float, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
