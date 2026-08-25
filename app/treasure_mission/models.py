"""보물 찾기 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- TREASURE_MISSION
- TREASURE_MISSION_PROGRESS
- AR_CHARACTER
- ACQUIRED_AR_CHARACTER
- PICTURE_WITH_CHARACTER
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ArCharacter(Base):
    """AR_CHARACTER - AR 캐릭터 마스터."""

    __tablename__ = "AR_CHARACTER"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
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


# TODO: TREASURE_MISSION / TREASURE_MISSION_PROGRESS /
#       ACQUIRED_AR_CHARACTER / PICTURE_WITH_CHARACTER 모델 정의
