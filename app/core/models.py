"""전체 ORM 모델 등록 모듈.

SQLAlchemy는 모델 클래스가 **import된 시점**에만 `Base.metadata`에 테이블을 등록한다.
그래서 어느 도메인도 import하지 않는 모델은 `Base.metadata`에서 빠지고,
테스트의 `create_all()`이나 메타데이터를 쓰는 도구에서 해당 테이블만 조용히 누락된다.

이 모듈은 도메인별 models 모듈을 한 곳에서 모두 import해서 그 누락을 막는다.
**새 도메인 모델을 추가하면 여기에도 import를 추가한다.**

docs/erd.md의 25개 테이블이 모두 등록되는지는
`app/core/tests/test_models_registry.py`에서 검증한다.
"""

from app.cooperative_mission import models as cooperative_mission_models
from app.culture_mission import models as culture_mission_models
from app.guestbook import models as guestbook_models
from app.map import models as map_models
from app.mission import models as mission_models
from app.mypage import models as mypage_models
from app.others import models as others_models
from app.treasure_mission import models as treasure_mission_models
from app.user import models as user_models


__all__ = [
    "cooperative_mission_models",
    "culture_mission_models",
    "guestbook_models",
    "map_models",
    "mission_models",
    "mypage_models",
    "others_models",
    "treasure_mission_models",
    "user_models",
]
