"""ORM 모델 ↔ ERD/DDL 일치 테스트.

모델을 API 구현 중에 하나씩 추가하다 보면 ERD에는 있는데 ORM에는 없는 테이블,
DDL에는 있는데 모델에는 없는 컬럼이 조용히 생긴다.
이 테스트는 `scripts/sql/01-schema.sql`(ERD를 그대로 옮긴 DDL)을 기준으로
`Base.metadata`가 빠짐없이 같은 모양인지 확인한다.
"""

import re
from pathlib import Path

import pytest

from app.core import models as all_models  # noqa: F401  (전체 테이블 메타데이터 등록)
from app.core.database import Base


SCHEMA_SQL = Path(__file__).resolve().parents[3] / "scripts" / "sql" / "01-schema.sql"

# DDL의 CREATE TABLE 블록에서 컬럼 정의가 아닌 줄(제약조건/인덱스)을 걸러내기 위한 키워드
_NON_COLUMN_KEYWORDS = ("PRIMARY KEY", "UNIQUE KEY", "KEY ", "CONSTRAINT", "FOREIGN KEY")


def _parse_schema_sql() -> dict[str, set[str]]:
    """DDL에서 `{테이블명: {컬럼명}}` 을 뽑아낸다."""
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    tables: dict[str, set[str]] = {}

    for match in re.finditer(
        r"CREATE TABLE `(?P<table>\w+)` \((?P<body>.*?)\n\) ENGINE", sql, re.DOTALL
    ):
        columns = set()
        for line in match.group("body").splitlines():
            stripped = line.strip()
            if not stripped.startswith("`"):
                continue
            if any(keyword in stripped for keyword in _NON_COLUMN_KEYWORDS):
                continue
            columns.add(stripped.split("`")[1])
        tables[match.group("table")] = columns

    return tables


@pytest.fixture(scope="module")
def schema_tables() -> dict[str, set[str]]:
    tables = _parse_schema_sql()
    # 파싱이 깨지면 이후 비교가 전부 무의미해지므로 먼저 확인한다.
    assert len(tables) >= 20, f"DDL 파싱 결과가 비정상입니다: {sorted(tables)}"
    return tables


def test_DDL의_모든_테이블에_대응하는_ORM_모델이_있다(
    schema_tables: dict[str, set[str]],
) -> None:
    missing = set(schema_tables) - set(Base.metadata.tables)

    assert not missing, f"ORM 모델이 없는 테이블: {sorted(missing)}"


def test_DDL에_없는_테이블이_ORM에_정의되어_있지_않다(
    schema_tables: dict[str, set[str]],
) -> None:
    extra = set(Base.metadata.tables) - set(schema_tables)

    assert not extra, f"DDL에 없는 ORM 테이블: {sorted(extra)}"


def test_모든_모델의_컬럼이_DDL과_일치한다(schema_tables: dict[str, set[str]]) -> None:
    mismatched: dict[str, dict[str, list[str]]] = {}

    for table_name, table in Base.metadata.tables.items():
        expected = schema_tables.get(table_name)
        if expected is None:
            continue

        actual = {column.name for column in table.columns}
        if actual == expected:
            continue

        mismatched[table_name] = {
            "모델에만_있음": sorted(actual - expected),
            "DDL에만_있음": sorted(expected - actual),
        }

    assert not mismatched, f"DDL과 다른 모델: {mismatched}"
