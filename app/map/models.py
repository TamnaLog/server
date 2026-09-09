"""지도 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- LOCATION
- VISITED_LOCATION
- GPS

LOCATION 은 미션/방명록 등 여러 도메인이 함께 쓰므로 여기서 한 번만 정의하고
다른 도메인은 import해서 사용한다.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import (
    Base,
    BigIntPk,
    CurrentTimestampOnUpdate,
    mysql_table_args,
)


class Location(Base):
    """LOCATION - 장소."""

    __tablename__ = "LOCATION"
    __table_args__ = (
        UniqueConstraint("content_id", name="uk_location__content_id"),
        Index("idx_location__coord", "mx", "my"),
        mysql_table_args("장소"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="TourAPI contentId"
    )
    location_title: Mapped[str] = mapped_column(String(100), nullable=False)
    location_address: Mapped[str] = mapped_column(String(255), nullable=False)
    location_category: Mapped[str] = mapped_column(String(20), nullable=False)
    # 장소 인증 반경(m)
    radius: Mapped[int] = mapped_column(Integer, nullable=False, comment="인증 반경(m)")
    # mx = 경도(longitude), my = 위도(latitude)
    mx: Mapped[float] = mapped_column(Double, nullable=False, comment="경도(longitude)")
    my: Mapped[float] = mapped_column(Double, nullable=False, comment="위도(latitude)")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )


class VisitedLocation(Base):
    """VISITED_LOCATION - 사용자가 방문한 장소."""

    __tablename__ = "VISITED_LOCATION"
    __table_args__ = (
        Index("idx_visited_location__user", "user_id", "visited_at"),
        Index("idx_visited_location__location", "location_id"),
        mysql_table_args("방문한 장소"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_visited_location__user"),
        nullable=False,
    )
    location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "LOCATION.id", ondelete="CASCADE", name="fk_visited_location__location"
        ),
        nullable=False,
    )
    visited_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )

    location: Mapped[Location] = relationship(lazy="joined")


class Gps(Base):
    """GPS - 사용자 위치 기록."""

    __tablename__ = "GPS"
    __table_args__ = (
        Index("idx_gps__user_saved_at", "user_id", "saved_at"),
        mysql_table_args("사용자 위치 기록"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_gps__user"),
        nullable=False,
    )
    # mx = 경도(longitude), my = 위도(latitude)
    mx: Mapped[float] = mapped_column(Double, nullable=False, comment="경도(longitude)")
    my: Mapped[float] = mapped_column(Double, nullable=False, comment="위도(latitude)")
    saved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )
