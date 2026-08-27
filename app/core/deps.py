"""공통 FastAPI 의존성.

현재 사용자는 `Authorization` 헤더의 Bearer 액세스 토큰으로 식별한다.

```text
Authorization: Bearer {accessToken}
```

토큰 원문은 `POST /api/v1/auth/anonymous`(익명 사용자 발급)에서 한 번만 내려준다.
DB에는 원문 대신 SHA-256 해시(`USER.access_token_hash`)만 저장하므로,
요청으로 받은 토큰 원문을 같은 방식으로 해시해서 사용자를 찾는다.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import (
    OPENAPI_SECURITY_SCHEME_NAME,
    UNAUTHORIZED_USER,
    UnauthorizedError,
)
from app.core.security import hash_access_token
from app.user.models import User


# 헤더가 없거나 Bearer가 아니면 여기서 막지 않고 아래에서 401 UNAUTHORIZED_USER 로 처리한다.
# (FastAPI 기본 동작은 403이라 공통 에러 형식과 맞지 않는다.)
bearer_scheme = HTTPBearer(
    scheme_name=OPENAPI_SECURITY_SCHEME_NAME,
    description="익명 사용자 발급 API에서 받은 액세스 토큰 원문",
    auto_error=False,
)


def get_current_user_id(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int:
    """현재 사용자 id를 반환한다.

    토큰이 없거나 일치하는 사용자가 없으면 401로 막는다.
    토큰 원문과 해시는 에러 메시지에 넣지 않는다.
    """
    if credentials is None:
        raise UnauthorizedError(UNAUTHORIZED_USER, detail="Bearer 액세스 토큰이 없습니다.")

    user_id = db.scalar(
        select(User.id).where(
            User.access_token_hash == hash_access_token(credentials.credentials)
        )
    )
    if user_id is None:
        raise UnauthorizedError(UNAUTHORIZED_USER, detail="토큰에 해당하는 사용자가 없습니다.")
    return user_id
