"""기타 도메인 SQLAlchemy 모델.

이 도메인이 소유한 테이블은 없다. 소유 도메인의 모델을 import해서 사용한다.

- STEP_COUNT (app/user)      → 사용자별 날짜당 하루 누적 걸음 수 한 행
- GPS (app/map)              → 사용자 위치 기록
- LOCATION (app/map)         → 방문 판정 대상 장소와 반경
- VISITED_LOCATION (app/map) → 판정된 방문 기록
- USER (app/user)            → 기록의 소유자
"""

from app.map.models import Gps, Location, VisitedLocation
from app.user.models import StepCount, User


__all__ = ["Gps", "Location", "StepCount", "User", "VisitedLocation"]
