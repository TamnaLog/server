"""문화 미션 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- CULTURE_MISSION
- CULTURE_MISSION_PROGRESS

MISSION 은 app/mission/models.py 에서 한 번만 정의하고 여기서는 import해서 사용한다.
문화 미션은 장소를 갖지 않는다. (장소는 협동/보물 찾기 미션만 가진다)
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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import (
    Base,
    BigIntPk,
    CurrentTimestampOnUpdate,
    mysql_table_args,
)
from app.mission.models import Mission, MissionStatus


__all__ = ["CultureMission", "CultureMissionProgress", "Mission", "MissionStatus"]


class CultureMission(Base):
    """CULTURE_MISSION - 문화 미션.

    자체 `id` 를 PK로 갖고, `mission_id` 로 공통 미션(MISSION)에 속한다. (MISSION 1 : N 문화 미션)
    """

    __tablename__ = "CULTURE_MISSION"
    __table_args__ = (
        Index("idx_culture_mission__mission", "mission_id"),
        mysql_table_args("문화 미션"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    mission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("MISSION.id", ondelete="CASCADE", name="fk_culture_mission__mission"),
        nullable=False,
    )
    quiz_total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # [{quiz_index, img_url, question, options, answer, hint, explanation}]
    quiz_detail: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        comment="[{quiz_index, img_url, question, options, answer, hint, explanation}]",
    )
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


class CultureMissionProgress(Base):
    """CULTURE_MISSION_PROGRESS - 문화 미션 진행도."""

    __tablename__ = "CULTURE_MISSION_PROGRESS"
    __table_args__ = (
        Index("idx_culture_progress__user", "user_id", "mission_status"),
        Index("idx_culture_progress__mission", "culture_mission_id"),
        mysql_table_args("문화 미션 진행도"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    culture_mission_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "CULTURE_MISSION.id", ondelete="CASCADE", name="fk_culture_progress__mission"
        ),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_culture_progress__user"),
        nullable=False,
    )
    mission_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="IN_PROGRESS | COMPLETED"
    )
    current_quiz_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    correct_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
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
