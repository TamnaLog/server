from collections.abc import Generator

from sqlalchemy import BigInteger, Integer, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


# 자동 증가 기본키 타입.
# 운영 DB(MySQL)에서는 ERD/DDL 대로 BIGINT 를 쓰지만, 테스트용 SQLite 는
# `INTEGER PRIMARY KEY` 에만 자동 증가(ROWID)를 적용하고 BIGINT 는 NULL 로 둔다.
# 그래서 SQLite 에서만 INTEGER 로 바꿔 id 없이 INSERT 할 수 있게 한다.
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


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
