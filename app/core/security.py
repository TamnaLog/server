"""액세스 토큰 생성 / 해시 유틸.

인증 인프라라서 core에 두고, `app/auth`(발급)와 `app/core/deps.py`(식별)가 함께 쓴다.

- DB에는 토큰 원문을 저장하지 않고 SHA-256 해시(`USER.access_token_hash`)만 저장한다.
- 해시는 복호화하지 않고, 요청으로 받은 토큰 원문을 같은 방식으로 해시해서 비교한다.
"""

import hashlib
import secrets


# 인증 헤더에 사용하는 토큰 타입. `Authorization: Bearer {accessToken}`
TOKEN_TYPE = "Bearer"

# 액세스 토큰 원문의 난수 바이트 수. urlsafe base64로 바뀌면서 약 43자가 된다.
ACCESS_TOKEN_BYTES = 32


def generate_access_token() -> str:
    """예측하기 어려운 액세스 토큰 원문을 만든다.

    토큰 원문에는 사용자 id나 개인정보를 넣지 않는다.
    """
    return secrets.token_urlsafe(ACCESS_TOKEN_BYTES)


def hash_access_token(access_token: str) -> str:
    """액세스 토큰 원문을 `USER.access_token_hash`에 저장할 SHA-256 hex(64자)로 바꾼다."""
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()
