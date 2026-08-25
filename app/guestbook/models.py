"""방명록 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- GUESTBOOK
- ROAD_GUESTBOOK

LOCATION / MISSION 은 각 소유 도메인에서 정의한 모델을 import해서 사용한다.
두 방명록 모두 `deleted_at` 으로 소프트 삭제를 표현하므로 조회 시 항상 제외한다.
"""

from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.map.models import Location
from app.mission.models import Mission


__all__ = ["Guestbook", "Location", "Mission", "RoadGuestbook"]


class Guestbook(Base):
    """GUESTBOOK - 등록된 장소에 남기는 방명록."""

    __tablename__ = "GUESTBOOK"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("LOCATION.id", ondelete="CASCADE"), nullable=False
    )
    visited_at: Mapped[date] = mapped_column(Date, nullable=False)
    content_img_url: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    content_writing: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_audio_url: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    content_weather: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content_color_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    mission_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("MISSION.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RoadGuestbook(Base):
    """ROAD_GUESTBOOK - 등록된 장소가 아닌 길 위에 남기는 방명록."""

    __tablename__ = "ROAD_GUESTBOOK"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("LOCATION.id", ondelete="SET NULL"), nullable=True
    )
    location_alias: Mapped[str] = mapped_column(String(100), nullable=False)
    visited_at: Mapped[date] = mapped_column(Date, nullable=False)
    content_img_url: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    content_writing: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_audio_url: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    content_weather: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content_color_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
