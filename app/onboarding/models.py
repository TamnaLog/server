"""온보딩 도메인 SQLAlchemy 모델.

docs/erd.md 기준으로 이 도메인이 담당하는 테이블:
- USER
- USER_TRAVEL_STYLE
- USER_SETTING

세 테이블 모두 여러 도메인이 공유하므로 app/user/models.py 에서
한 번만 정의하고 여기서는 import해서 사용한다.
"""

from app.treasure_mission.models import ArCharacter
from app.user.models import User, UserSetting, UserTravelStyle


__all__ = ["ArCharacter", "User", "UserSetting", "UserTravelStyle"]
