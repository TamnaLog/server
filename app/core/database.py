from collections.abc import Generator
from typing import Any

from sqlalchemy import BigInteger, Engine, Integer, create_engine, event, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.sql.expression import ColumnElement

from app.core.config import get_settings


# 자동 증가 기본키 타입.
# 운영 DB(MySQL)에서는 ERD/DDL 대로 BIGINT 를 쓰지만, 테스트용 SQLite 는
# `INTEGER PRIMARY KEY` 에만 자동 증가(ROWID)를 적용하고 BIGINT 는 NULL 로 둔다.
# 그래서 SQLite 에서만 INTEGER 로 바꿔 id 없이 INSERT 할 수 있게 한다.
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


class CurrentTimestampOnUpdate(ColumnElement):
    """`DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` 서버 기본값.

    `updated_at` 은 DDL(scripts/sql/01-schema.sql)에서 MySQL 이 직접 값을 갱신하도록
    `ON UPDATE CURRENT_TIMESTAMP` 를 붙인다. 그런데 테스트용 SQLite 에는 이 문법이 없어서
    같은 문자열을 그대로 쓰면 `create_all()` 이 깨진다.
    그래서 dialect 별로 다르게 렌더링해 MySQL 에만 `ON UPDATE` 를 붙인다.
    """

    inherit_cache = True


@compiles(CurrentTimestampOnUpdate)
def _render_current_timestamp_on_update(
    element: CurrentTimestampOnUpdate, compiler: Any, **kw: Any
) -> str:
    """MySQL 이 아닌 dialect(테스트용 SQLite)에서는 기본값만 남긴다."""
    return "CURRENT_TIMESTAMP"


@compiles(CurrentTimestampOnUpdate, "mysql")
def _render_current_timestamp_on_update_mysql(
    element: CurrentTimestampOnUpdate, compiler: Any, **kw: Any
) -> str:
    return "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"


def mysql_table_args(comment: str) -> dict[str, str]:
    """MySQL 테이블 옵션. scripts/sql/01-schema.sql 의 ENGINE/CHARSET/COLLATE 와 맞춘다.

    모델과 DDL 이 어긋나면 alembic autogenerate 가 매번 가짜 diff 를 만들기 때문에
    테이블 코멘트까지 여기서 같이 지정한다.
    """
    return {
        "comment": comment,
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci",
    }


# MySQL 연결 세션의 타임존. `created_at`/`updated_at` 의 서버 기본값
# `CURRENT_TIMESTAMP` 는 연결 세션의 `time_zone` 을 따르므로, 서버(컨테이너)가 UTC 로
# 동작해도 이 값을 KST 로 맞춰두면 DB 에 한국시간으로 저장된다.
# KST 는 서머타임이 없어 고정 오프셋으로 지정해도 정확하다. (app/common/datetimes.py 와 같은 기준)
MYSQL_SESSION_TIME_ZONE = "+09:00"


def _set_kst_session_time_zone(dbapi_connection: Any, connection_record: Any) -> None:
    """새로 맺은 MySQL 연결의 세션 타임존을 KST 로 설정한다."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET time_zone = %s", (MYSQL_SESSION_TIME_ZONE,))
    finally:
        cursor.close()


def use_kst_session_time_zone(target_engine: Engine) -> None:
    """엔진이 새로 연결을 열 때마다 세션 타임존을 KST 로 맞춘다.

    커넥션 풀에서 연결을 새로 만들 때(재연결 포함)마다 실행된다.
    MySQL 전용 구문이라 테스트용 SQLite 엔진에는 걸지 않는다.
    """
    if target_engine.dialect.name != "mysql":
        return
    event.listen(target_engine, "connect", _set_kst_session_time_zone)


settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args=settings.database_connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)
use_kst_session_time_zone(engine)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_database() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
