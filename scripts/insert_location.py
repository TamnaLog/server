"""한국관광공사 TourAPI 장소를 Azure MySQL LOCATION에 저장한다.

처리 순서:
1. 한국관광공사 TourAPI에서 제주 관광지·문화시설·행사/공연/축제를 전부 조회한다.
2. contentId 오름차순으로 정렬하고 모든 데이터를 검증한다.
3. LOCATION에 인증 반경 100m로 장소를 저장한다.

별도 옵션 없이 실행하면 .env의 TourAPI 설정과 .env.azure.database의
Azure MySQL 설정을 사용한다. 스키마 및 목 데이터 SQL은 실행하지 않는다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pymysql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AZURE_ENV_FILE = PROJECT_ROOT / ".env.azure.database"

JEJU_AREA_CODE = "39"
LOCATION_RADIUS_METER = 100
TOUR_API_ROWS_PER_PAGE = 1000
TOUR_API_TIMEOUT_SECONDS = 30.0
LOCATION_TITLE_MAX_LENGTH = 100
LOCATION_ADDRESS_MAX_LENGTH = 255

CONTENT_TYPES = {
    "12": "관광지",
    "14": "문화시설",
    "15": "행사·공연·축제",
}


@dataclass(frozen=True)
class LocationRow:
    content_id: int
    title: str
    address: str
    category: str
    radius: int
    longitude: float
    latitude: float


def load_environment(path: Path) -> dict[str, str]:
    """env 파일을 읽고, 동일한 OS 환경변수가 있으면 OS 값을 우선한다."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")

    for name in tuple(values):
        if name in os.environ:
            values[name] = os.environ[name]
    return values


def required(config: dict[str, str], name: str) -> str:
    value = config.get(name, "").strip()
    if not value:
        raise ValueError(f"필수 환경변수가 없습니다: {name}")
    return value


def fetch_locations(config: dict[str, str]) -> list[LocationRow]:
    """대상 콘텐츠 유형을 모두 조회하고 contentId 오름차순으로 반환한다."""
    base_url = required(config, "KTO_BASE_URL").rstrip("/")
    common_params = {
        "serviceKey": required(config, "KTO_SERVICE_KEY"),
        "MobileOS": config.get("KTO_MOBILE_OS", "ETC"),
        "MobileApp": config.get("KTO_MOBILE_APP", "jamkkanjeju"),
        "_type": "json",
        "areaCode": JEJU_AREA_CODE,
        "numOfRows": TOUR_API_ROWS_PER_PAGE,
    }

    by_content_id: dict[int, LocationRow] = {}
    with httpx.Client(base_url=base_url, timeout=TOUR_API_TIMEOUT_SECONDS) as client:
        for content_type_id, category in CONTENT_TYPES.items():
            for item in _fetch_content_type(client, common_params, content_type_id):
                row = _to_location(item, category)
                before = by_content_id.get(row.content_id)
                if before is not None and before != row:
                    raise ValueError(f"중복 contentId의 데이터가 서로 다릅니다: {row.content_id}")
                by_content_id[row.content_id] = row

    return sorted(by_content_id.values(), key=lambda row: row.content_id)


def _fetch_content_type(
    client: httpx.Client, common_params: dict[str, Any], content_type_id: str
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_no = 1
    total_count: int | None = None

    while total_count is None or len(items) < total_count:
        response = client.get(
            "/areaBasedList2",
            params={
                **common_params,
                "contentTypeId": content_type_id,
                "pageNo": page_no,
            },
        )
        response.raise_for_status()
        payload = response.json().get("response", {})
        header = payload.get("header", {})
        if header.get("resultCode") != "0000":
            raise RuntimeError(
                f"TourAPI 오류(contentTypeId={content_type_id}): "
                f"{header.get('resultCode')} {header.get('resultMsg')}"
            )

        body = payload.get("body", {})
        total_count = int(body.get("totalCount") or 0)
        page_items = body.get("items") or {}
        page_items = page_items.get("item") or []
        if isinstance(page_items, dict):
            page_items = [page_items]
        if not isinstance(page_items, list):
            raise ValueError(f"TourAPI items 형식이 올바르지 않습니다: {content_type_id}")

        items.extend(item for item in page_items if isinstance(item, dict))
        if not page_items:
            break
        page_no += 1

    if len(items) != total_count:
        raise RuntimeError(
            f"TourAPI 전체 건수와 조회 건수가 다릅니다: "
            f"contentTypeId={content_type_id}, total={total_count}, fetched={len(items)}"
        )
    return items


def _to_location(item: dict[str, Any], category: str) -> LocationRow:
    content_id = _required_int(item, "contentid")
    title = _required_text(item, "title", content_id)
    address = " ".join(
        value.strip()
        for value in (str(item.get("addr1") or ""), str(item.get("addr2") or ""))
        if value.strip()
    )
    if not address:
        raise ValueError(f"주소가 없는 TourAPI 콘텐츠입니다: {content_id}")
    if len(title) > LOCATION_TITLE_MAX_LENGTH:
        raise ValueError(f"장소명이 {LOCATION_TITLE_MAX_LENGTH}자를 초과합니다: {content_id}")
    if len(address) > LOCATION_ADDRESS_MAX_LENGTH:
        raise ValueError(f"주소가 {LOCATION_ADDRESS_MAX_LENGTH}자를 초과합니다: {content_id}")

    return LocationRow(
        content_id=content_id,
        title=title,
        address=address,
        category=category,
        radius=LOCATION_RADIUS_METER,
        longitude=_required_float(item, "mapx", content_id),
        latitude=_required_float(item, "mapy", content_id),
    )


def _required_text(item: dict[str, Any], name: str, content_id: int) -> str:
    value = str(item.get(name) or "").strip()
    if not value:
        raise ValueError(f"{name} 값이 없습니다: {content_id}")
    return value


def _required_int(item: dict[str, Any], name: str) -> int:
    try:
        return int(str(item.get(name)).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 값이 올바르지 않습니다: {item.get(name)!r}") from exc


def _required_float(item: dict[str, Any], name: str, content_id: int) -> float:
    try:
        return float(str(item.get(name)).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 값이 올바르지 않습니다: {content_id}") from exc


def connect_database(config: dict[str, str]) -> pymysql.Connection:
    ssl_enabled = config.get("MYSQL_SSL_ENABLED", "true").lower() in {"1", "true", "yes"}
    return pymysql.connect(
        host=required(config, "MYSQL_HOST"),
        port=int(config.get("MYSQL_PORT", "3306")),
        user=required(config, "MYSQL_USER"),
        password=required(config, "MYSQL_PASSWORD"),
        database=required(config, "MYSQL_DATABASE"),
        charset="utf8mb4",
        autocommit=True,
        ssl={"check_hostname": True} if ssl_enabled else None,
    )


def insert_locations(
    connection: pymysql.Connection, locations: list[LocationRow]
) -> None:
    query = """
        INSERT INTO `LOCATION`
            (`content_id`, `location_title`, `location_address`,
             `location_category`, `radius`, `mx`, `my`)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `location_title` = VALUES(`location_title`),
            `location_address` = VALUES(`location_address`),
            `location_category` = VALUES(`location_category`),
            `radius` = VALUES(`radius`),
            `mx` = VALUES(`mx`),
            `my` = VALUES(`my`)
    """
    values = [
        (
            row.content_id,
            row.title,
            row.address,
            row.category,
            row.radius,
            row.longitude,
            row.latitude,
        )
        for row in locations
    ]
    with connection.cursor() as cursor:
        cursor.executemany(query, values)


def verify_locations(connection: pymysql.Connection, locations: list[LocationRow]) -> None:
    content_ids = [row.content_id for row in locations]
    placeholders = ", ".join(["%s"] * len(content_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) FROM `LOCATION` WHERE `content_id` IN ({placeholders})",
            content_ids,
        )
        actual_count = int(cursor.fetchone()[0])
        if actual_count != len(locations):
            raise RuntimeError(
                f"LOCATION 저장 건수가 다릅니다: expected={len(locations)}, actual={actual_count}"
            )


def main() -> None:
    # 공통 API 설정은 .env에서 읽고, 대상 DB 설정은 전달받은 env 파일로
    # 덮어쓴다. 이를 통해 TourAPI 키와 Azure 접속 정보를 별도 파일로 관리한다.
    config = load_environment(PROJECT_ROOT / ".env")
    config.update(load_environment(AZURE_ENV_FILE))
    locations = fetch_locations(config)
    counts = {
        category: sum(row.category == category for row in locations)
        for category in CONTENT_TYPES.values()
    }

    print(f"대상 DB: {required(config, 'MYSQL_HOST')} / {required(config, 'MYSQL_DATABASE')}")
    print(f"TourAPI 장소: 총 {len(locations)}건, {counts}")
    print(f"저장 반경: {LOCATION_RADIUS_METER}m")

    host = required(config, "MYSQL_HOST")
    if not host.endswith(".mysql.database.azure.com"):
        raise ValueError(f"Azure MySQL 호스트가 아닙니다: {host}")
    if config.get("MYSQL_SSL_ENABLED", "").lower() not in {"1", "true", "yes"}:
        raise ValueError("Azure DB 구축은 MYSQL_SSL_ENABLED=true여야 합니다.")

    connection = connect_database(config)
    try:
        insert_locations(connection, locations)
        verify_locations(connection, locations)
    finally:
        connection.close()

    print("LOCATION 저장 완료")


if __name__ == "__main__":
    main()
