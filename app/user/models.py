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

from sqlalchemy import (
    CHAR,
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
from app.treasure_mission.models import ArCharacter


# 하루 목표 걸음 수 기본값. 익명 사용자 발급 시 이 값으로 시작한다.
DEFAULT_TARGET_STEP = 10000


class UserTravelStyle(Base):
    """USER_TRAVEL_STYLE - 여행 유형 마스터."""

    __tablename__ = "USER_TRAVEL_STYLE"
    __table_args__ = (mysql_table_args("여행 유형 마스터"),)

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="여행 유형명"
    )
    type_description: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="유형 설명"
    )
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


class User(Base):
    """USER - 사용자."""

    __tablename__ = "USER"
    __table_args__ = (
        UniqueConstraint("access_token_hash", name="uk_user__access_token_hash"),
        Index("idx_user__travel_style", "user_travel_style_id"),
        Index("idx_user__ar_character", "ar_character_id"),
        mysql_table_args("사용자"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    expectation: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="string[] 여행 기대 항목"
    )
    transportation: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="string[] 이동수단"
    )
    travel_style: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="string[] 자투리 시간 여행 방식"
    )
    user_travel_style_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "USER_TRAVEL_STYLE.id",
            ondelete="SET NULL",
            name="fk_user__travel_style",
        ),
        nullable=True,
        comment="진단된 여행 유형",
    )
    ar_character_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("AR_CHARACTER.id", ondelete="SET NULL", name="fk_user__ar_character"),
        nullable=True,
        comment="배정된 AR 캐릭터",
    )
    nickname: Mapped[str | None] = mapped_column(String(20), nullable=True)
    point: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # 하루 목표 걸음 수. 기록(STEP_COUNT)이 아니라 사용자 설정값이라 여기에 둔다.
    target_step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_TARGET_STEP,
        server_default=str(DEFAULT_TARGET_STEP),
        comment="하루 목표 걸음 수",
    )
    # 액세스 토큰 해시(SHA-256 hex 64자). 토큰 원문은 저장하지 않는다.
    access_token_hash: Mapped[str] = mapped_column(
        CHAR(64), nullable=False, comment="액세스 토큰 해시(SHA-256 hex)"
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

    user_travel_style: Mapped[UserTravelStyle | None] = relationship(lazy="joined")
    ar_character: Mapped[ArCharacter | None] = relationship(lazy="joined")


class UserSetting(Base):
    """USER_SETTING - 사용자 알림 설정. 사용자 1명당 1행."""

    __tablename__ = "USER_SETTING"
    __table_args__ = (
        UniqueConstraint("user_id", name="uk_user_setting__user"),
        mysql_table_args("사용자 알림 설정"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_user_setting__user"),
        nullable=False,
    )
    push_notification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    near_mission_notification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
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


class StepCount(Base):
    """STEP_COUNT - 걸음 수 기록.

    목표 걸음 수(`target_step`)는 기록마다 다른 값이 아니라 사용자 설정값이라
    `USER` 가 가진다.

    `saved_at` 은 서버가 저장한 시각이 아니라 **프론트가 걸음 수를 측정한 시각**이다.
    같은 시각으로 다시 보내면 행을 추가하지 않고 갱신하려고
    `(user_id, saved_at)` 에 유니크 제약을 건다.
    """

    __tablename__ = "STEP_COUNT"
    __table_args__ = (
        UniqueConstraint("user_id", "saved_at", name="uk_step_count__user_saved_at"),
        mysql_table_args("걸음 수 기록"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("USER.id", ondelete="CASCADE", name="fk_step_count__user"),
        nullable=False,
    )
    saved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    steps_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=CurrentTimestampOnUpdate(),
        onupdate=func.now(),
    )
