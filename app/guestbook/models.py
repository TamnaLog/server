"""방명록 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- GUESTBOOK
- GUESTBOOK_LIKE
- ROAD_GUESTBOOK
- ROAD_GUESTBOOK_LIKE

LOCATION / MISSION 은 각 소유 도메인에서 정의한 모델을 import해서 사용한다.
네 테이블 모두 `deleted_at` 으로 소프트 삭제를 표현하므로 조회 시 항상 제외한다.
좋아요는 유형별로 테이블이 나뉘고, 두 방명록 테이블의 id 는 서로 겹칠 수 있어서
좋아요를 찾을 때는 항상 유형을 함께 정해야 한다.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigIntPk
from app.map.models import Location
from app.mission.models import Mission


__all__ = [
    "Guestbook",
    "GuestbookLike",
    "Location",
    "Mission",
    "RoadGuestbook",
    "RoadGuestbookLike",
]


class Guestbook(Base):
    """GUESTBOOK - 등록된 장소에 남기는 방명록."""

    __tablename__ = "GUESTBOOK"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
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
    audio_title: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_weather: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 섭씨 기온. 소수 첫째 자리까지 저장한다. (예: -3.5, 28.4)
    content_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 1), nullable=True
    )
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


class GuestbookLike(Base):
    """GUESTBOOK_LIKE - 장소 방명록 좋아요.

    한 사용자는 한 방명록에 좋아요를 한 행으로만 갖는다. (`guestbook_id` + `user_id` 유니크)
    취소는 행 삭제가 아니라 `deleted_at` 소프트 삭제이므로, 좋아요 개수를 셀 때는
    `deleted_at IS NULL` 인 행만 센다.
    """

    __tablename__ = "GUESTBOOK_LIKE"
    __table_args__ = (
        UniqueConstraint(
            "guestbook_id", "user_id", name="uk_guestbook_like__guestbook_user"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    guestbook_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("GUESTBOOK.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RoadGuestbook(Base):
    """ROAD_GUESTBOOK - 등록된 장소가 아닌 길 위에 남기는 방명록."""

    __tablename__ = "ROAD_GUESTBOOK"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
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
    audio_title: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_weather: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 섭씨 기온. 소수 첫째 자리까지 저장한다. (예: -3.5, 28.4)
    content_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 1), nullable=True
    )
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


class RoadGuestbookLike(Base):
    """ROAD_GUESTBOOK_LIKE - 길 위의 방명록 좋아요.

    `GuestbookLike` 와 같은 규칙이고 참조하는 방명록 테이블만 다르다.
    (`road_guestbook_id` + `user_id` 유니크, 취소는 `deleted_at` 소프트 삭제)
    """

    __tablename__ = "ROAD_GUESTBOOK_LIKE"
    __table_args__ = (
        UniqueConstraint(
            "road_guestbook_id", "user_id", name="uk_road_guestbook_like__guestbook_user"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    road_guestbook_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ROAD_GUESTBOOK.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
