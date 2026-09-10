"""기타 도메인 SQLAlchemy 모델.

이 도메인이 소유한 테이블은 없다. 소유 도메인의 모델을 import해서 사용한다.

- STEP_COUNT (app/user)                     → 사용자별 측정 시각당 누적 걸음 수 한 행
- GPS (app/map)                             → 사용자 위치 기록
- LOCATION (app/map)                        → 방문 판정 대상 장소와 반경
- VISITED_LOCATION (app/map)                → 판정된 방문 기록
- USER (app/user)                           → 기록의 소유자, 목표 걸음 수
- AR_CHARACTER (app/treasure_mission)       → 목표 달성 보상으로 추첨하는 캐릭터
- ACQUIRED_AR_CHARACTER (app/treasure_mission) → 추첨된 캐릭터의 획득 기록
"""

from app.map.models import Gps, Location, VisitedLocation
from app.treasure_mission.models import AcquiredArCharacter, ArCharacter
from app.user.models import StepCount, User


__all__ = [
    "AcquiredArCharacter",
    "ArCharacter",
    "Gps",
    "Location",
    "StepCount",
    "User",
    "VisitedLocation",
]
