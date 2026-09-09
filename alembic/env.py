"""Alembic 마이그레이션 실행 환경.

접속 대상 DB는 다음 순서로 정한다.
1. `alembic -x db_url=...` 로 직접 넘긴 URL
2. `ALEMBIC_ENV_FILE` 환경변수가 가리키는 env 파일 (예: 개발용 `.env.azure.database`)
3. 기본값: 프로젝트 `.env` 를 읽는 `app.core.config.get_settings()`

`target_metadata` 는 `app.core.models` 를 import 해서 모든 도메인 모델이
`Base.metadata` 에 등록된 상태로 잡는다. (import 안 된 모델은 조용히 누락된다)
"""

import os
from logging.config import fileConfig
from pathlib import Path
from typing import Any

from alembic import context
from sqlalchemy import Connection, create_engine, pool, text

from app.core.config import Settings, get_settings
from app.core.database import Base
import app.core.models  # noqa: F401  # 전체 도메인 모델 등록


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _is_autogenerate() -> bool:
    """스키마를 비교해 변경점을 뽑아내는 명령인지. (`revision --autogenerate`, `check`)"""
    cmd_opts = getattr(config, "cmd_opts", None)
    if cmd_opts is None:
        return False
    if getattr(cmd_opts, "autogenerate", False):
        return True
    cmd = getattr(cmd_opts, "cmd", None)
    if cmd is None:
        return False
    return bool(cmd[0].__name__ == "check")


def _read_env_file(path: Path) -> dict[str, Any]:
    """env 파일에서 `Settings` 필드에 해당하는 값만 읽는다."""
    values: dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        field = key.strip().lower()
        if field in Settings.model_fields:
            values[field] = value.strip()
    return values


def _resolve_settings() -> Settings:
    """접속 정보를 담은 Settings 를 만든다."""
    env_file = os.getenv("ALEMBIC_ENV_FILE")
    if not env_file:
        return get_settings()

    # pydantic-settings 는 env 파일보다 프로세스 환경변수를 먼저 본다.
    # 컨테이너에는 docker compose 의 `env_file: .env` 값이 이미 환경변수로 들어와 있어서
    # `_env_file=` 로만 지정하면 무시되고 엉뚱한 DB 에 붙는다.
    # 그래서 파일 값을 직접 읽어 생성자 인자로 넘겨 확실히 우선하게 한다.
    path = Path(env_file)
    if not path.is_file():
        raise RuntimeError(f"ALEMBIC_ENV_FILE 이 가리키는 파일이 없다: {env_file}")
    return Settings(**_read_env_file(path))


def _resolve_url_and_connect_args() -> tuple[str, dict[str, Any]]:
    x_args = context.get_x_argument(as_dictionary=True)
    if "db_url" in x_args:
        return x_args["db_url"], {}

    settings = _resolve_settings()
    connect_args: dict[str, Any] = dict(settings.database_connect_args)

    # SSL CA 경로는 컨테이너(Linux) 기준이라 Windows 호스트에서 직접 실행하면 없다.
    # CA 검증을 조용히 끄면 안 되므로 원인을 알려주고 멈춘다.
    ssl_options = connect_args.get("ssl")
    if isinstance(ssl_options, dict):
        ca_path = ssl_options.get("ca")
        if isinstance(ca_path, str) and not Path(ca_path).exists():
            raise RuntimeError(
                f"MYSQL_SSL_ENABLED=true 인데 CA 파일이 없다: {ca_path} / "
                "SSL 이 필요한 DB(Azure MySQL)에는 컨테이너 안에서 실행한다. 예) "
                "docker compose -f docker-compose.dev.yml run --rm "
                "-e ALEMBIC_ENV_FILE=.env.azure.database api alembic upgrade head"
            )

    return settings.database_url, connect_args


def _guard_case_insensitive_server(connection: Connection) -> None:
    """테이블명을 소문자로 저장하는 서버에서는 autogenerate 를 막는다.

    모델과 `scripts/sql/01-schema.sql` 은 테이블명을 대문자(`USER`)로 쓰는데,
    Azure MySQL 은 `lower_case_table_names=1` 이라 소문자(`user`)로 저장한다.
    이 상태로 autogenerate 를 돌리면 alembic 이 소문자 테이블 25개를 전부
    "삭제된 테이블"로, 대문자 테이블 25개를 "추가된 테이블"로 인식해서
    **모든 데이터를 지우는 마이그레이션**을 만들어낸다.

    비교가 필요한 작업은 대소문자를 그대로 두는 로컬 MySQL 에서 하고,
    이런 서버에는 만들어진 마이그레이션을 `upgrade` 로 적용만 한다.
    """
    if connection.dialect.name != "mysql":
        return

    row = connection.execute(
        text("SHOW VARIABLES LIKE 'lower_case_table_names'")
    ).first()
    if row is None or str(row[1]) == "0":
        return

    raise RuntimeError(
        "이 서버는 lower_case_table_names="
        f"{row[1]} 이라 테이블명을 소문자로 저장한다. "
        "여기서 autogenerate 를 돌리면 테이블 전체를 삭제/재생성하는 "
        "마이그레이션이 만들어진다. "
        "마이그레이션은 로컬 MySQL(lower_case_table_names=0)에서 만들고, "
        "이 서버에는 `alembic upgrade` 로 적용만 한다."
    )


def run_migrations_offline() -> None:
    """DB 접속 없이 SQL 스크립트만 출력하는 모드."""
    url, _ = _resolve_url_and_connect_args()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """실제 DB에 접속해서 마이그레이션을 실행하는 모드."""
    url, connect_args = _resolve_url_and_connect_args()
    connectable = create_engine(url, connect_args=connect_args, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        if _is_autogenerate():
            _guard_case_insensitive_server(connection)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
