"""협동 미션 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- COOPERATIVE_MISSION
- COOPERATIVE_MISSION_PROGRESS
- COOPERATIVE_ROLE_CARD
- COOPERATIVE_MISSION_PARTICIPANT
- COOPERATIVE_ROLE_PROGRESS

MISSION 은 app/mission/models.py, LOCATION 은 app/map/models.py 에서 한 번만 정의하고
여기서는 import해서 사용한다.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPk
from app.map.models import Location
from app.mission.models import Mission, MissionStatus


__all__ = [
    "CooperativeMission",
    "CooperativeMissionParticipant",
    "CooperativeMissionProgress",
    "CooperativeRoleCard",
    "CooperativeRoleProgress",
    "Location",
    "Mission",
    "MissionStatus",
    "ParticipantStatus",
    "ParticipantType",
]


class ParticipantType(str, Enum):
    """참여자 유형."""

    USER = "USER"
    GUEST = "GUEST"


class ParticipantStatus(str, Enum):
    """참여자 상태."""

    ACCEPTED = "ACCEPTED"
    INVITED = "INVITED"


class CooperativeMission(Base):
    """COOPERATIVE_MISSION - 협동 미션.

    자체 `id` 를 PK로 갖고, `mission_id` 로 공통 미션(MISSION)에 속한다. (MISSION 1 : N 협동 미션)
    미션이 진행되는 장소는 이 테이블이 가진다.
    """

    __tablename__ = "COOPERATIVE_MISSION"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("MISSION.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("LOCATION.id", ondelete="RESTRICT"), nullable=False
    )
    role_total_count: Mapped[int] = mapped_column(Integer, nullable=False)
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


class CooperativeMissionProgress(Base):
    """COOPERATIVE_MISSION_PROGRESS - 협동 미션 진행도(방).

    사용자 정보가 직접 없고 COOPERATIVE_MISSION_PARTICIPANT 를 통해 연결된다.
    """

    __tablename__ = "COOPERATIVE_MISSION_PROGRESS"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    cooperative_mission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("COOPERATIVE_MISSION.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_step: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    mission_status: Mapped[str] = mapped_column(String(20), nullable=False)
    team_token: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
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


class CooperativeRoleCard(Base):
    """COOPERATIVE_ROLE_CARD - 협동 미션 역할 카드."""

    __tablename__ = "COOPERATIVE_ROLE_CARD"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    cooperative_mission_progress_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("COOPERATIVE_MISSION_PROGRESS.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_name: Mapped[str] = mapped_column(String(20), nullable=False)
    role_description: Mapped[str] = mapped_column(String(200), nullable=False)
    location_to_find: Mapped[str] = mapped_column(String(200), nullable=False)
    hint: Mapped[str] = mapped_column(String(200), nullable=False)
    picture_guide: Mapped[str] = mapped_column(String(200), nullable=False)
    is_selected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CooperativeMissionParticipant(Base):
    """COOPERATIVE_MISSION_PARTICIPANT - 협동 미션 참여자.

    가입 사용자는 `user_id`, 초대 URL로 들어온 게스트는 `guest_name`/`guest_token` 을 사용한다.
    """

    __tablename__ = "COOPERATIVE_MISSION_PARTICIPANT"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    cooperative_mission_progress_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("COOPERATIVE_MISSION_PROGRESS.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="SET NULL"), nullable=True
    )
    guest_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    guest_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    participant_status: Mapped[str] = mapped_column(String(20), nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CooperativeRoleProgress(Base):
    """COOPERATIVE_ROLE_PROGRESS - 협동 미션 역할 진행도."""

    __tablename__ = "COOPERATIVE_ROLE_PROGRESS"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("COOPERATIVE_MISSION_PARTICIPANT.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cooperative_role_card_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("COOPERATIVE_ROLE_CARD.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    item_img_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    progress_status: Mapped[str] = mapped_column(String(20), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
