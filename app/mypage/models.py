"""마이페이지 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- TRAVEL_ENDING_CONTENT

마이페이지 조회는 여러 도메인의 테이블을 읽기만 하므로, 소유 도메인의 모델을
import해서 사용한다. (USER 는 여러 도메인이 공유해 app/user/models.py 에서 한 번만 정의한다)

- USER / USER_TRAVEL_STYLE     → 프로필, 목표 걸음 수, 포인트
- AR_CHARACTER                 → 대표 캐릭터와 도감
- ACQUIRED_AR_CHARACTER        → 캐릭터 획득 여부/시각/획득 미션
- VISITED_LOCATION / LOCATION  → 방문 장소 수, 캐릭터 획득 장소
- MISSION / *_MISSION          → 미션 제목·유형·단계, 캐릭터 보상 설정
- *_MISSION_PROGRESS           → 완료/진행 중인 미션
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantStatus,
)
from app.core.database import Base, BigIntPk
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.map.models import Location, VisitedLocation
from app.mission.models import Mission, MissionStatus, MissionType
from app.treasure_mission.models import (
    AcquiredArCharacter,
    ArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User, UserTravelStyle


__all__ = [
    "AcquiredArCharacter",
    "ArCharacter",
    "CooperativeMission",
    "CooperativeMissionParticipant",
    "CooperativeMissionProgress",
    "CultureMission",
    "CultureMissionProgress",
    "Location",
    "Mission",
    "MissionStatus",
    "MissionType",
    "ParticipantStatus",
    "TravelEndingContent",
    "TreasureMission",
    "TreasureMissionProgress",
    "User",
    "UserTravelStyle",
    "VisitedLocation",
]


class TravelEndingContent(Base):
    """TRAVEL_ENDING_CONTENT - 여행 마무리 엽서.

    엽서에 담을 항목을 선택값으로 나눠 갖지 않고, 완성된 엽서 이미지 URL 하나만 저장한다.
    """

    __tablename__ = "TRAVEL_ENDING_CONTENT"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("USER.id", ondelete="CASCADE"), nullable=False
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
