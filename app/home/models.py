"""홈 도메인 SQLAlchemy 모델.

홈 조회는 여러 도메인의 테이블을 함께 읽기만 한다.
홈이 소유한 테이블은 없으므로 각 소유 도메인의 모델을 import해서 사용한다.

미션 구조상, 실제 미션 한 건은 미션 유형별 테이블의 행이다.
`MISSION` 은 유형/이름/설명/단계 같은 공통 정보만 갖는 분류 테이블이고,
장소와 보상은 유형별 테이블이 각자 가진다. (문화 미션은 장소가 없다)

- USER / AR_CHARACTER             → 캐릭터 이미지
- MISSION                         → 미션 공통 정보(유형/이름/단계)
- CULTURE_MISSION                 → 문화 미션 + 문화 미션 단계 정보(`quiz_total_count`)
- COOPERATIVE_MISSION             → 협동 미션 + 장소
- TREASURE_MISSION                → 보물 찾기 미션 + 장소
- LOCATION                        → 미션 장소 좌표
- *_MISSION_PROGRESS              → 진행 중인 미션
- COOPERATIVE_MISSION_PARTICIPANT → 협동 미션에서 현재 사용자 찾기
- GUESTBOOK / ROAD_GUESTBOOK      → 쌓인 방명록 개수
"""

from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.guestbook.models import Guestbook, RoadGuestbook
from app.map.models import Location
from app.mission.models import Mission, MissionStatus, MissionType
from app.treasure_mission.models import ArCharacter, TreasureMission, TreasureMissionProgress
from app.user.models import User


__all__ = [
    "ArCharacter",
    "CooperativeMission",
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
    "TreasureMission",
    "TreasureMissionProgress",
    "User",
]
