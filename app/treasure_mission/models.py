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
    JSON,
    BigInteger,
    Boolean,
    DateTime,
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
    __table_args__ = (mysql_table_args("AR 캐릭터 마스터"),)

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    character_name: Mapped[str] = mapped_column(String(50), nullable=False)
    character_description: Mapped[str] = mapped_column(String(200), nullable=False)
    character_story_title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="캐릭터 이야기 제목"
    )
    acquire_condition: Mapped[str] = mapped_column(String(200), nullable=False)
    character_img_url: Mapped[str] = mapped_column(String(500), nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="string[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )


class TreasureMission(Base):
    """TREASURE_MISSION - 보물 찾기 미션.

    자체 `id` 를 PK로 갖고, `mission_id` 로 공통 미션(MISSION)에 속한다.
    (MISSION 1 : N 보물 찾기 미션) 미션이 진행되는 장소는 이 테이블이 가진다.
    보물 좌표(`item_detail`)는 진행도마다 달라지므로 TREASURE_MISSION_PROGRESS 가 가진다.
    """

    __tablename__ = "TREASURE_MISSION"
    __table_args__ = (
        Index("idx_treasure_mission__mission", "mission_id"),
        Index("idx_treasure_mission__location", "location_id"),
        mysql_table_args("보물 찾기 미션"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "MISSION.id", ondelete="CASCADE", name="fk_treasure_mission__mission"
        ),
        nullable=False,
    )
    location_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "LOCATION.id", ondelete="RESTRICT", name="fk_treasure_mission__location"
        ),
        nullable=False,
    )
    item_total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # 미션 보상. {ar_character_id, point, coupon_location, coupon_price}
    reward_detail: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="{ar_character_id, point, coupon_location, coupon_price}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )

    mission: Mapped[Mission] = relationship(lazy="joined")
    location: Mapped[Location] = relationship(lazy="joined")


class TreasureMissionProgress(Base):
    """TREASURE_MISSION_PROGRESS - 보물 찾기 진행도.

    보물 좌표(`item_detail`)는 미션이 아니라 진행도마다 정해지므로 여기에 저장한다.
    """

    __tablename__ = "TREASURE_MISSION_PROGRESS"
    __table_args__ = (
        Index("idx_treasure_progress__user", "user_id", "mission_status"),
        Index("idx_treasure_progress__mission", "treasure_mission_id"),
        mysql_table_args("보물 찾기 진행도"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    treasure_mission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "TREASURE_MISSION.id",
            ondelete="CASCADE",
            name="fk_treasure_progress__mission",
        ),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_treasure_progress__user"),
        nullable=False,
    )
    # 이 진행도에서 찾아야 할 보물 좌표. [{index, mx, my}]
    item_detail: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, comment="[{index, mx, my}] 진행도별 보물 좌표"
    )
    # 찾은 보물 index 목록 (int[])
    current_found_item_idx: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, comment="int[]"
    )
    # 진행 단계. 1 | 2 | 3 (3 = 완료)
    current_step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="진행 단계. 1 | 2 | 3 (3 = 완료)",
    )
    mission_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="IN_PROGRESS | COMPLETED"
    )
    ar_character_reward_granted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="AR 캐릭터 보상 지급 여부",
    )
    point_reward_granted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="포인트 보상 지급 여부",
    )
    coupon_reward_granted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="쿠폰 보상 지급 여부",
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )


class AcquiredArCharacter(Base):
    """ACQUIRED_AR_CHARACTER - 사용자가 미션 보상으로 획득한 AR 캐릭터."""

    __tablename__ = "ACQUIRED_AR_CHARACTER"
    __table_args__ = (
        UniqueConstraint("user_id", "ar_character_id", name="uk_acquired__user_character"),
        Index("idx_acquired__character", "ar_character_id"),
        Index("idx_acquired__mission", "acquired_mission_id"),
        mysql_table_args("획득한 AR 캐릭터"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    ar_character_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("AR_CHARACTER.id", ondelete="CASCADE", name="fk_acquired__character"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_acquired__user"),
        nullable=False,
    )
    acquired_mission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("MISSION.id", ondelete="CASCADE", name="fk_acquired__mission"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )

    ar_character: Mapped[ArCharacter] = relationship(lazy="joined")


class PictureWithCharacter(Base):
    """PICTURE_WITH_CHARACTER - 사용자가 AR 캐릭터와 찍은 사진."""

    __tablename__ = "PICTURE_WITH_CHARACTER"
    __table_args__ = (
        Index("idx_picture__user_saved_at", "user_id", "saved_at"),
        mysql_table_args("AR 캐릭터와 찍은 사진"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_picture__user"),
        nullable=False,
    )
    picture_url: Mapped[str] = mapped_column(String(500), nullable=False)
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
