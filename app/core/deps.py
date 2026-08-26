"""공통 FastAPI 의존성.

로그인 기능이 아직 없어서 현재 사용자는 요청 헤더로 정한다.
프론트는 앱 시작 시 사용자 번호를 입력받아 메모리에 두고, 모든 요청에 아래 헤더를 넣는다.

```text
X-Test-User-Id: 2
```

로그인을 구현하면 이 모듈의 헤더 처리만 토큰 인증으로 바꾸면 되고,
`get_current_user_id()` 를 쓰는 라우터는 그대로 둘 수 있다.
"""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import TEST_USER_ID_HEADER, UNAUTHORIZED_USER, UnauthorizedError
from app.user.models import User


# 테스트/로컬에서 기본으로 사용하는 사용자 id
CURRENT_USER_ID = 1


def get_current_user_id(
    db: Annotated[Session, Depends(get_db)],
    x_test_user_id: Annotated[
        int,
        Header(
            alias=TEST_USER_ID_HEADER,
            ge=1,
            description="현재 사용자 id. 로그인 구현 전까지 프론트가 직접 넣는다.",
        ),
    ],
) -> int:
    """현재 로그인한 사용자 id를 반환한다.

    헤더로 받은 id의 사용자가 실제로 존재하는지 확인한다.
    없는 사용자로 요청하면 이후 로직이 엉뚱한 데이터를 만들 수 있어 401로 막는다.
    """
    if db.get(User, x_test_user_id) is None:
        raise UnauthorizedError(
            UNAUTHORIZED_USER,
            detail=f"{TEST_USER_ID_HEADER}={x_test_user_id} 사용자를 찾을 수 없습니다.",
        )
    return x_test_user_id
