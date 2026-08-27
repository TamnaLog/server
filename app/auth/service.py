"""인증 도메인 비즈니스 로직.

비즈니스 룰: app/auth/docs/BUSINESS_RULES.md
"""

import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import AnonymousUserResponse
from app.core.security import TOKEN_TYPE, generate_access_token, hash_access_token
from app.user.models import User, UserSetting


# 익명 사용자에게 배정할 닉네임 후보. UNIQUE 제약이 없어 중복 배정을 허용한다.
ANONYMOUS_NICKNAMES = (
    "몽글몽글파도",
    "한라봉주스",
    "오름러버",
    "돌담산책",
    "귤빛노을",
)

# 토큰 해시가 UNIQUE 제약에 걸렸을 때 새 토큰으로 다시 시도하는 횟수
MAX_TOKEN_ATTEMPTS = 5


def issue_anonymous_user(*, db: Session) -> AnonymousUserResponse:
    """새로운 익명 사용자와 액세스 토큰을 발급한다.

    호출할 때마다 항상 새 사용자를 만든다. 기존 사용자를 찾아 재사용하지 않는다.
    사용자와 사용자 설정은 한 트랜잭션으로 저장한다.
    """
    for _ in range(MAX_TOKEN_ATTEMPTS):
        access_token = generate_access_token()
        try:
            _create_anonymous_user(db=db, access_token=access_token)
        except IntegrityError:
            # 토큰 해시 UNIQUE 충돌. 이 토큰은 버리고 새 토큰으로 다시 만든다.
            db.rollback()
            continue
        return AnonymousUserResponse(access_token=access_token, token_type=TOKEN_TYPE)

    # 여기까지 오면 난수 토큰이 계속 충돌한 상황이라 정상 응답을 만들 수 없다.
    raise RuntimeError(f"액세스 토큰을 {MAX_TOKEN_ATTEMPTS}번 시도했지만 저장하지 못했습니다.")


def _create_anonymous_user(*, db: Session, access_token: str) -> None:
    """익명 사용자와 기본 사용자 설정을 만들고 커밋한다."""
    user = User(
        nickname=secrets.choice(ANONYMOUS_NICKNAMES),
        point=0,
        access_token_hash=hash_access_token(access_token),
    )
    db.add(user)
    # USER_SETTING.user_id 를 채우려면 사용자 id가 먼저 필요하다.
    db.flush()

    db.add(
        UserSetting(
            user_id=user.id,
            push_notification=True,
            near_mission_notification=True,
        )
    )
    db.commit()
