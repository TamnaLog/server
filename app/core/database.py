from collections.abc import Generator
from typing import Any

from sqlalchemy import BigInteger, Integer, create_engine, text
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


settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args=settings.database_connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)

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
