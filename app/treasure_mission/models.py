"""보물 찾기 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- TREASURE_MISSION
- TREASURE_MISSION_PROGRESS
- AR_CHARACTER
- ACQUIRED_AR_CHARACTER
- PICTURE_WITH_CHARACTER

AR_CHARACTER 는 온보딩/홈/마이페이지가 함께 쓰므로 여기서 한 번만 정의하고
다른 도메인은 import해서 사용한다.
MISSION / LOCATION 은 각 소유 도메인에서 import해서 사용한다.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPk
from app.map.models import Location
from app.mission.models import Mission, MissionStatus


__all__ = [
    "AcquiredArCharacter",
    "ArCharacter",
    "Location",
    "Mission",
    "MissionStatus",
    "PictureWithCharacter",
    "TreasureMission",
    "TreasureMissionProgress",
]


class ArCharacter(Base):
    """AR_CHARACTER - AR 캐릭터 마스터."""

    __tablename__ = "AR_CHARACTER"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    character_name: Mapped[str] = mapped_column(String(50), nullable=False)
    character_description: Mapped[str] = mapped_column(String(200), nullable=False)
    acquire_condition: Mapped[str] = mapped_column(String(200), nullable=False)
    character_img_url: Mapped[str] = mapped_column(String(500), nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TreasureMission(Base):
    """TREASURE_MISSION - 보물 찾기 미션.

    자체 `id` 를 PK로 갖고, `mission_id` 로 공통 미션(MISSION)에 속한다.
    (MISSION 1 : N 보물 찾기 미션) 미션이 진행되는 장소는 이 테이블이 가진다.
    """

    __tablename__ = "TREASURE_MISSION"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("MISSION.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("LOCATION.id", ondelete="RESTRICT"), nullable=False
    )
    item_total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # [{index, mx, my, radius}]
    item_detail: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # 미션 보상. {ar_character_id, point, coupon_location, coupon_price}
    reward_detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    mission: Mapped[Mission] = relationship(lazy="joined")
    location: Mapped[Location] = relationship(lazy="joined")


class TreasureMissionProgress(Base):
    """TREASURE_MISSION_PROGRESS - 보물 찾기 진행도."""

    __tablename__ = "TREASURE_MISSION_PROGRESS"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    treasure_mission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("TREASURE_MISSION.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    # 찾은 보물 index 목록 (int[])
    current_found_item_idx: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    # 진행 단계. 1 | 2 | 3 (3 = 완료)
    current_step: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    mission_status: Mapped[str] = mapped_column(String(20), nullable=False)
    ar_character_reward_granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    point_reward_granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    coupon_reward_granted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AcquiredArCharacter(Base):
    """ACQUIRED_AR_CHARACTER - 사용자가 미션 보상으로 획득한 AR 캐릭터."""

    __tablename__ = "ACQUIRED_AR_CHARACTER"
    __table_args__ = (UniqueConstraint("user_id", "ar_character_id"),)

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    ar_character_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("AR_CHARACTER.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    acquired_mission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("MISSION.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    ar_character: Mapped[ArCharacter] = relationship(lazy="joined")


class PictureWithCharacter(Base):
    """PICTURE_WITH_CHARACTER - 사용자가 AR 캐릭터와 찍은 사진."""

    __tablename__ = "PICTURE_WITH_CHARACTER"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    picture_url: Mapped[str] = mapped_column(String(500), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
