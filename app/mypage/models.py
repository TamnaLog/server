"""마이페이지 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- USER
- TRAVEL_ENDING_CONTENT

USER 는 여러 도메인이 공유하므로 app/user/models.py 에서 한 번만 정의하고
여기서는 import해서 사용한다.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigIntPk
from app.user.models import User


__all__ = ["TravelEndingContent", "User"]


class TravelEndingContent(Base):
    """TRAVEL_ENDING_CONTENT - 여행 마무리 엽서.

    `visited_place` / `missions` / `pictures` 는 엽서에 어떤 항목을 담을지 선택한 값이다.
    """

    __tablename__ = "TRAVEL_ENDING_CONTENT"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    travel_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    visited_place: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    missions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    pictures: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
