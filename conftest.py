"""공통 테스트 픽스처.

DB는 SQLite 인메모리를 사용하고, `get_db` 의존성만 교체해서
실제 라우터/서비스/모델을 그대로 태운다.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import models as all_models  # noqa: F401  (전체 테이블 메타데이터 등록)
from app.core.database import Base, get_db
from app.core.security import TOKEN_TYPE, hash_access_token
from app.main import app


# 테스트에서 기본으로 사용하는 사용자 id
CURRENT_USER_ID = 1


def access_token(user_id: int) -> str:
    """테스트용 액세스 토큰 원문.

    실제 발급 토큰은 난수라서 테스트에서 미리 알 수 없다.
    사용자마다 값이 다르기만 하면 되므로 id로 만든 고정값을 쓴다.
    목업 데이터(scripts/sql/02-data-mock.sql)도 같은 규칙을 쓴다.
    """
    return f"test-user-{user_id}-token"


def access_token_hash(user_id: int) -> str:
    """테스트용 `USER.access_token_hash` 값.

    실제 인증과 같은 방식으로 해시해야 `auth_headers()`로 로그인이 된다.
    """
    return hash_access_token(access_token(user_id))


def auth_headers(user_id: int) -> dict[str, str]:
    """해당 사용자로 요청할 때 쓸 인증 헤더."""
    return {"Authorization": f"{TOKEN_TYPE} {access_token(user_id)}"}


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    """테스트용 SQLite 인메모리 엔진."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(test_engine)
        test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """테스트 데이터 준비/검증용 세션."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    """`get_db`가 테스트 DB를 바라보도록 교체한 API 클라이언트."""

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # 500 에러 응답 형식을 검증하기 위해 예외를 다시 발생시키지 않는다.
    # 인증 헤더는 기본 사용자로 넣어 두고, 필요한 테스트만 직접 덮어쓴다.
    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=auth_headers(CURRENT_USER_ID),
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
