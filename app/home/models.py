"""홈 도메인 SQLAlchemy 모델.

홈 조회는 여러 도메인의 테이블을 함께 읽기만 한다.
홈이 소유한 테이블은 없으므로 각 소유 도메인의 모델을 import해서 사용한다.

- USER / AR_CHARACTER            → 캐릭터 이미지
- MISSION / LOCATION             → 추천 미션, 미션 장소, 공통 단계 정보(`step_detail`)
- CULTURE_MISSION                → 문화 미션 단계 정보(`quiz_total_count`)
- CULTURE_MISSION_PROGRESS       → 진행 중인 문화 미션
- TREASURE_MISSION_PROGRESS      → 진행 중인 보물 찾기 미션
- COOPERATIVE_MISSION_PROGRESS   → 진행 중인 협동 미션
- COOPERATIVE_MISSION_PARTICIPANT → 협동 미션에서 현재 사용자 찾기
- GUESTBOOK / ROAD_GUESTBOOK     → 쌓인 방명록 개수
"""

from app.cooperative_mission.models import (
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.guestbook.models import Guestbook, RoadGuestbook
from app.map.models import Location
from app.mission.models import Mission, MissionStatus, MissionType
from app.treasure_mission.models import ArCharacter, TreasureMissionProgress
from app.user.models import User


__all__ = [
    "ArCharacter",
    "CooperativeMissionParticipant",
    "CooperativeMissionProgress",
    "CultureMission",
    "CultureMissionProgress",
    "Guestbook",
    "Location",
    "Mission",
    "MissionStatus",
    "MissionType",
    "RoadGuestbook",
    "TreasureMissionProgress",
    "User",
]
