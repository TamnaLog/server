"""미션 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- MISSION

MISSION 은 미션의 공통 정보(유형/이름/설명/단계)만 가진다.
장소와 보상은 미션 유형별 테이블(CULTURE/COOPERATIVE/TREASURE_MISSION)이 각자 가진다.

MISSION 과 미션 진행 상태 값은 문화/협동/보물 찾기 도메인이 함께 쓰므로
여기서 한 번만 정의하고 다른 도메인은 import해서 사용한다.

반대로 유형별 세부 미션 모델은 여기서 import하지 않는다.
세 도메인이 모두 이 모듈을 import하므로 순환 참조가 되기 때문이다.
미션 도메인에서 세부 미션이 필요하면 app/mission/service.py 처럼 각 소유 도메인에서 직접 import한다.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import (
    Base,
    BigIntPk,
    CurrentTimestampOnUpdate,
    mysql_table_args,
)


class MissionType(str, Enum):
    """미션 유형."""

    CULTURE = "CULTURE"
    COOPERATIVE = "COOPERATIVE"
    TREASURE = "TREASURE"


class MissionStatus(str, Enum):
    """미션 진행 상태."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class Mission(Base):
    """MISSION - 미션 공통."""

    __tablename__ = "MISSION"
    __table_args__ = (
        Index("idx_mission__type", "mission_type"),
        mysql_table_args("미션 공통"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    mission_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="CULTURE | COOPERATIVE | TREASURE"
    )
    mission_title: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    # [{step, step_title, description}]
    step_detail: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, comment="[{step, step_title, description}]"
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

    @property
    def total_step(self) -> int:
        """공통 미션 단계 수. `step_detail` 항목 개수로 판단한다.

        보물 찾기 / 협동 미션이 사용한다.
        문화 미션은 대신 `CULTURE_MISSION.quiz_total_count` 를 단계 수로 쓴다.
        """
        return len(self.step_detail or [])
