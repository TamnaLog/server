"""제주시청 주변 심사용 방명록 데이터를 생성한다.

장소 방명록 15건은 LOCATION 테이블에서 제주시청과 가까운 순서로 고른다.
길바닥 방명록 15건은 제주시청 반경 안에 좌표를 분산해 생성한다.
일부 방명록에는 TourAPI detailImage2 원본 이미지를 내려받아 Azure Blob의
``guestbooke_test/`` 경로에 올린 URL을 저장한다.

기본 실행은 .env의 공통/TourAPI/Blob 설정과 .env.azure.database의 DB 설정을
사용한다. 로컬 DB를 사용할 때는 --local을 붙인다.

    python scripts/seed_jeju_cityhall_guestbooks.py --dry-run
    python scripts/seed_jeju_cityhall_guestbooks.py --user-ids 1,2,3
    python scripts/seed_jeju_cityhall_guestbooks.py --local --user-ids 1

같은 문구의 활성 방명록이 이미 있으면 중복 생성하지 않는다. DB 저장이 실패하면
이번 실행에서 업로드한 Blob도 삭제한다.
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import pymysql
from azure.storage.blob import BlobServiceClient, ContentSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AZURE_ENV_FILE = PROJECT_ROOT / ".env.azure.database"

# 제주시청 본관(제주시 광양9길 10) 부근. 필요하면 CLI 옵션으로 덮어쓸 수 있다.
JEJU_CITY_HALL_LATITUDE = 33.49957
JEJU_CITY_HALL_LONGITUDE = 126.53120
GENERAL_COUNT = 15
ROAD_COUNT = 15
MAX_AUTHORS = 10
TOUR_API_TIMEOUT_SECONDS = 15.0
IMAGE_DOWNLOAD_MAX_BYTES = 15 * 1024 * 1024
BLOB_PREFIX = "guestbooke_test"
EXPECTED_BLOB_CONTAINER = "jamkkanjeju"

WEATHERS = ("SUNNY", "CLOUDY", "WINDY", "RAINY")
COLORS = (
    "#FFD8A8",
    "#B2F2BB",
    "#A5D8FF",
    "#D0BFFF",
    "#FFEC99",
    "#FFC9C9",
    "#C3FAE8",
    "#E9ECEF",
)

FOOD_WRITINGS = (
    "간이 세지 않고 재료 맛이 또렷해서 여행 중 먹은 한 끼 중 가장 기억에 남았다.",
    "따뜻할 때 먹으니 향이 훨씬 좋았다. 기다린 시간이 아깝지 않은 든든한 한 끼였다.",
    "제주 재료의 신선함이 느껴졌고 양도 넉넉했다. 다음에는 다른 메뉴도 먹어 보고 싶다.",
    "현지인 손님이 많은 이유를 알 것 같다. 자극적이지 않아 끝까지 맛있게 먹었다.",
    "메인 메뉴도 좋았지만 곁들임 반찬까지 정갈했다. 근처에 오면 다시 들를 곳이다.",
)
SHOPPING_WRITINGS = (
    "제주다운 소품이 많아 구경하는 재미가 있었다. 부담 없이 선물 고르기 좋은 곳이다.",
    "진열이 깔끔하고 제품 설명도 친절했다. 여행을 기억할 작은 기념품을 골랐다.",
    "흔한 기념품보다 개성 있는 물건이 많았다. 천천히 둘러보다 마음에 드는 걸 찾았다.",
)
CULTURE_WRITINGS = (
    "전시를 따라 천천히 걷다 보니 제주의 이야기가 더 가깝게 느껴졌다. 조용히 머물기 좋았다.",
    "공간은 아담하지만 볼거리가 알찼다. 설명을 읽으며 둘러보니 시간이 금방 지나갔다.",
    "제주의 분위기를 차분하게 느낄 수 있었다. 비 오는 날 다시 찾아와도 좋을 것 같다.",
)
ATTRACTION_WRITINGS = (
    "도심 가까이에 이런 풍경이 있다는 게 반가웠다. 천천히 걸으며 쉬어 가기 좋았다.",
    "사진보다 실제 풍경이 더 좋았다. 바람을 맞으며 한 바퀴 걷고 나니 기분이 맑아졌다.",
    "잠깐 들렀다가 예상보다 오래 머물렀다. 제주 여행의 여유를 제대로 느낀 곳이다.",
    "동선이 편하고 주변 풍경도 좋아 가볍게 둘러보기 좋았다. 다음에는 해 질 무렵 오고 싶다.",
    "사람이 붐비지 않아 천천히 볼 수 있었다. 소소하지만 오래 기억에 남을 장소다.",
)
ROAD_WRITINGS = (
    "시청 근처 골목을 걷다가 귤나무 너머로 햇빛이 내려앉는 순간이 예뻐서 잠시 멈췄다.",
    "큰길에서 한 블록 들어왔을 뿐인데 갑자기 조용해졌다. 제주에서의 느린 오후가 좋다.",
    "바람은 조금 셌지만 골목 끝으로 보이는 파란 하늘이 시원해서 한참 걷고 싶었다.",
    "돌담 옆 작은 화분들이 정겹다. 목적지 없이 걷다가 만난 풍경이라 더 기억에 남는다.",
    "횡단보도를 기다리는데 구름 사이로 햇빛이 나왔다. 평범한 길도 여행 중에는 특별하다.",
    "따뜻한 빵 냄새를 따라 걷다 보니 처음 보는 골목에 들어왔다. 이런 우연이 여행의 재미다.",
    "가로수 그늘 아래 잠깐 쉬었다. 차 소리 사이로 새소리가 들려 의외로 마음이 편안했다.",
    "비가 막 그친 뒤라 아스팔트가 반짝였다. 젖은 돌담 색이 유난히 선명해 보였다.",
    "시장 쪽으로 걷는 길에 사람들의 제주 사투리가 들렸다. 비로소 여행지에 온 기분이 났다.",
    "해가 기울면서 건물 사이로 주황빛이 번졌다. 별일 없는 순간인데도 사진처럼 남았다.",
    "조용한 주택가를 천천히 걸었다. 담장 너머 꽃향기 덕분에 발걸음이 자꾸 느려졌다.",
    "버스를 한 대 보내고 조금 더 걸었다. 선선한 바람이 불어 걷기를 잘했다는 생각이 들었다.",
    "골목 모퉁이에서 귀여운 고양이를 만났다. 눈을 마주친 짧은 순간이 오늘 여행의 하이라이트다.",
    "멀리 한라산 윤곽이 희미하게 보였다. 도심 한가운데서 만난 제주다운 장면이었다.",
    "카페를 나와 숙소까지 걷는 길, 낮보다 조용한 제주시의 저녁 분위기가 마음에 들었다.",
)
ROAD_ALIASES = (
    "제주시청 앞 산책길",
    "광양사거리 골목",
    "시청 뒤편 돌담길",
    "광양로 가로수길",
    "이도이동 작은 골목",
    "시청 근처 버스정류장",
    "광양9길 모퉁이",
    "제주시청 동쪽 골목",
    "시민회관 가는 길",
    "시청 남쪽 산책로",
    "이도이동 주택가",
    "광양사거리 횡단보도",
    "시청 북쪽 골목",
    "제주시청 야경길",
    "광양로 카페 골목",
)


@dataclass(frozen=True)
class Location:
    id: int
    content_id: int
    title: str
    category: str
    longitude: float
    latitude: float
    distance_m: float


@dataclass(frozen=True)
class ImageUpload:
    url: str
    blob_name: str


def load_environment(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
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


def connect_database(config: dict[str, str]) -> pymysql.Connection:
    ssl_enabled = config.get("MYSQL_SSL_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    return pymysql.connect(
        host=required(config, "MYSQL_HOST"),
        port=int(config.get("MYSQL_PORT", "3306")),
        user=required(config, "MYSQL_USER"),
        password=required(config, "MYSQL_PASSWORD"),
        database=required(config, "MYSQL_DATABASE"),
        charset="utf8mb4",
        autocommit=False,
        ssl={"check_hostname": True} if ssl_enabled else None,
    )


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(a))


def nearest_locations(
    connection: pymysql.Connection, latitude: float, longitude: float
) -> list[Location]:
    # 전체 LOCATION을 읽어 Python에서 Haversine 거리로 정렬한다. 제주 LOCATION 규모에서는
    # 충분히 작고, MySQL 버전별 공간 함수 차이도 피할 수 있다.
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT `id`, `content_id`, `location_title`, `location_category`, `mx`, `my`
            FROM `LOCATION`
            """
        )
        rows = cursor.fetchall()

    locations = [
        Location(
            id=int(row[0]),
            content_id=int(row[1]),
            title=str(row[2]),
            category=str(row[3]),
            longitude=float(row[4]),
            latitude=float(row[5]),
            distance_m=haversine_m(latitude, longitude, float(row[5]), float(row[4])),
        )
        for row in rows
    ]
    locations.sort(key=lambda item: (item.distance_m, item.id))
    if len(locations) < GENERAL_COUNT:
        raise RuntimeError(
            f"LOCATION이 {GENERAL_COUNT}개보다 적습니다. 먼저 scripts/insert_location.py를 실행하세요."
        )
    return locations[:GENERAL_COUNT]


def resolve_user_ids(
    connection: pymysql.Connection, requested_ids: list[int] | None
) -> list[int]:
    with connection.cursor() as cursor:
        if requested_ids:
            placeholders = ", ".join(["%s"] * len(requested_ids))
            cursor.execute(
                f"SELECT `id` FROM `USER` WHERE `id` IN ({placeholders}) ORDER BY `id`",
                requested_ids,
            )
        else:
            cursor.execute("SELECT `id` FROM `USER` ORDER BY `id` LIMIT %s", (MAX_AUTHORS,))
        existing = [int(row[0]) for row in cursor.fetchall()]

    if requested_ids and set(existing) != set(requested_ids):
        missing = sorted(set(requested_ids) - set(existing))
        raise ValueError(f"존재하지 않는 USER id입니다: {missing}")
    if not existing:
        raise RuntimeError("방명록 작성자로 사용할 USER가 없습니다.")
    return existing


def writing_for(location: Location, index: int) -> str:
    category = location.category
    if "음식" in category:
        pool = FOOD_WRITINGS
    elif "쇼핑" in category:
        pool = SHOPPING_WRITINGS
    elif "문화" in category or "공연" in category or "전시" in category:
        pool = CULTURE_WRITINGS
    else:
        pool = ATTRACTION_WRITINGS
    review = pool[index % len(pool)]
    return f"{location.title}, {review}"


def temperature_for(weather: str, rng: random.Random) -> float:
    ranges = {
        "SUNNY": (22.0, 29.5),
        "CLOUDY": (19.0, 26.0),
        "WINDY": (18.0, 25.0),
        "RAINY": (18.0, 24.0),
    }
    low, high = ranges[weather]
    return round(rng.uniform(low, high), 1)


def random_point(
    latitude: float, longitude: float, rng: random.Random, index: int
) -> tuple[float, float]:
    # 90~650m 사이에 고르게 퍼뜨리고 각도를 섞어 핀이 겹치지 않게 한다.
    distance_m = rng.uniform(90.0, 650.0)
    bearing = math.radians((index * 137.508 + rng.uniform(-18.0, 18.0)) % 360)
    north_m = math.cos(bearing) * distance_m
    east_m = math.sin(bearing) * distance_m
    point_lat = latitude + north_m / 111_320.0
    point_lon = longitude + east_m / (111_320.0 * math.cos(math.radians(latitude)))
    return round(point_lat, 7), round(point_lon, 7)


def fetch_detail_image_url(
    client: httpx.Client, config: dict[str, str], content_id: int
) -> str | None:
    response = client.get(
        "/detailImage2",
        params={
            "serviceKey": required(config, "KTO_SERVICE_KEY"),
            "MobileOS": config.get("KTO_MOBILE_OS", "ETC"),
            "MobileApp": config.get("KTO_MOBILE_APP", "jamkkanjeju"),
            "_type": "json",
            "contentId": str(content_id),
            "imageYN": "Y",
            "numOfRows": "20",
            "pageNo": "1",
        },
    )
    response.raise_for_status()
    body = response.json().get("response", {}).get("body", {})
    items = body.get("items") or {}
    items = items.get("item") or []
    if isinstance(items, dict):
        items = [items]
    for item in items:
        url = item.get("originimgurl") if isinstance(item, dict) else None
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
    return None


def download_image(client: httpx.Client, url: str) -> tuple[bytes, str, str]:
    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if not content_type.startswith("image/"):
            raise ValueError(f"이미지가 아닌 TourAPI 파일입니다: {content_type or 'unknown'}")
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > IMAGE_DOWNLOAD_MAX_BYTES:
                raise ValueError("TourAPI 이미지가 15MB를 초과합니다.")
            chunks.append(chunk)

    suffix = Path(urlparse(str(response.url)).path).suffix.lower()
    if not suffix or len(suffix) > 6:
        suffix = mimetypes.guess_extension(content_type) or ".jpg"
    return b"".join(chunks), content_type, suffix


def upload_image(
    container: Any,
    *,
    data: bytes,
    content_type: str,
    suffix: str,
    content_id: int,
    kind: str,
) -> ImageUpload:
    # 실행을 반복해도 Blob 이름이 충돌하지 않도록 시각과 난수를 함께 쓴다.
    nonce = os.urandom(6).hex()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    blob_name = f"{BLOB_PREFIX}/{kind}_{content_id}_{stamp}_{nonce}{suffix}"
    blob = container.get_blob_client(blob_name)
    blob.upload_blob(
        data,
        overwrite=False,
        content_settings=ContentSettings(content_type=content_type),
    )
    return ImageUpload(url=blob.url, blob_name=blob_name)


def existing_writings(connection: pymysql.Connection) -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT `content_writing` FROM `GUESTBOOK`
            WHERE `deleted_at` IS NULL AND `content_writing` IS NOT NULL
            UNION
            SELECT `content_writing` FROM `ROAD_GUESTBOOK`
            WHERE `deleted_at` IS NULL AND `content_writing` IS NOT NULL
            """
        )
        return {str(row[0]) for row in cursor.fetchall()}


def insert_general(
    connection: pymysql.Connection,
    *,
    location: Location,
    user_id: int,
    writing: str,
    image_url: str | None,
    weather: str,
    temperature: float,
    color: str,
    visited_at: date,
    saved_at: datetime,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO `GUESTBOOK`
                (`user_id`, `location_id`, `visited_at`, `content_img_url`,
                 `content_writing`, `content_audio_url`, `audio_title`,
                 `content_weather`, `content_temperature_celsius`,
                 `content_color_code`, `saved_at`, `mission_id`)
            VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s, %s, %s, %s, NULL)
            """,
            (
                user_id,
                location.id,
                visited_at,
                json.dumps([image_url], ensure_ascii=False) if image_url else None,
                writing,
                weather,
                temperature,
                color,
                saved_at,
            ),
        )


def insert_road(
    connection: pymysql.Connection,
    *,
    user_id: int,
    alias: str,
    latitude: float,
    longitude: float,
    writing: str,
    image_url: str | None,
    weather: str,
    temperature: float,
    color: str,
    visited_at: date,
    saved_at: datetime,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO `ROAD_GUESTBOOK`
                (`user_id`, `location_id`, `location_alias`, `visited_at`,
                 `content_img_url`, `content_writing`, `content_audio_url`,
                 `audio_title`, `content_weather`,
                 `content_temperature_celsius`, `content_color_code`, `mx`, `my`,
                 `saved_at`)
            VALUES (%s, NULL, %s, %s, %s, %s, NULL, NULL, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                alias,
                visited_at,
                json.dumps([image_url], ensure_ascii=False) if image_url else None,
                writing,
                weather,
                temperature,
                color,
                longitude,
                latitude,
                saved_at,
            ),
        )


def parse_user_ids(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    values = [int(value.strip()) for value in raw.split(",") if value.strip()]
    if not values or any(value < 1 for value in values):
        raise argparse.ArgumentTypeError("--user-ids는 1 이상의 정수를 쉼표로 구분해야 합니다.")
    return list(dict.fromkeys(values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="제주시청 주변 심사용 방명록 30건 생성")
    parser.add_argument("--local", action="store_true", help=".env의 로컬 DB 사용")
    parser.add_argument("--dry-run", action="store_true", help="DB/Blob 변경 없이 대상만 출력")
    parser.add_argument("--seed", type=int, default=20260917, help="랜덤 시드")
    parser.add_argument("--user-ids", help="작성자로 사용할 USER id 목록(예: 1,2,3)")
    parser.add_argument("--latitude", type=float, default=JEJU_CITY_HALL_LATITUDE)
    parser.add_argument("--longitude", type=float, default=JEJU_CITY_HALL_LONGITUDE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not -90 <= args.latitude <= 90 or not -180 <= args.longitude <= 180:
        raise ValueError("위도/경도 범위가 올바르지 않습니다.")

    common_config = load_environment(PROJECT_ROOT / ".env")
    config = dict(common_config)
    if not args.local:
        config.update(load_environment(AZURE_ENV_FILE))

        host = required(config, "MYSQL_HOST")
        if not host.endswith(".mysql.database.azure.com"):
            raise ValueError(f"Azure MySQL 호스트가 아닙니다: {host}")
        if config.get("MYSQL_SSL_ENABLED", "").lower() not in {"1", "true", "yes"}:
            raise ValueError("Azure DB 구간은 MYSQL_SSL_ENABLED=true여야 합니다.")

    connection = connect_database(config)
    uploaded: list[ImageUpload] = []
    try:
        locations = nearest_locations(connection, args.latitude, args.longitude)
        user_ids = resolve_user_ids(connection, parse_user_ids(args.user_ids))
        existing = existing_writings(connection)
        print(f"기준 좌표: {args.latitude:.6f}, {args.longitude:.6f}")
        print(f"작성자 USER id: {user_ids}")
        for index, location in enumerate(locations, start=1):
            print(
                f"  {index:02d}. {location.title} / {location.category} / "
                f"{location.distance_m:.0f}m / contentId={location.content_id}"
            )

        if args.dry_run:
            print("dry-run 완료: DB와 Blob은 변경하지 않았습니다.")
            return

        connection_string = required(config, "AZURE_STORAGE_CONNECTION_STRING")
        container_name = required(config, "AZURE_STORAGE_CONTAINER")
        if container_name != EXPECTED_BLOB_CONTAINER:
            raise ValueError(
                f"심사용 이미지는 {EXPECTED_BLOB_CONTAINER!r} 컨테이너에 올려야 합니다. "
                f"현재 설정: {container_name!r}"
            )
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container = blob_service.get_container_client(container_name)

        rng = random.Random(args.seed)
        today = date.today()
        general_inserted = 0
        road_inserted = 0

        with httpx.Client(
            base_url=required(config, "KTO_BASE_URL").rstrip("/"),
            timeout=TOUR_API_TIMEOUT_SECONDS,
            headers={"User-Agent": "jamkkanjeju-guestbook-seeder/1.0"},
        ) as tour_client, httpx.Client(timeout=TOUR_API_TIMEOUT_SECONDS) as image_client:
            # 장소형은 짝수 인덱스(8건)에만 이미지를 시도한다.
            general_image_urls: dict[int, str] = {}
            for index, location in enumerate(locations):
                if index % 2 != 0 or writing_for(location, index) in existing:
                    continue
                try:
                    source_url = fetch_detail_image_url(
                        tour_client, config, location.content_id
                    )
                    if source_url:
                        data, content_type, suffix = download_image(image_client, source_url)
                        upload = upload_image(
                            container,
                            data=data,
                            content_type=content_type,
                            suffix=suffix,
                            content_id=location.content_id,
                            kind="general",
                        )
                        uploaded.append(upload)
                        general_image_urls[location.id] = upload.url
                except (httpx.HTTPError, ValueError) as error:
                    print(f"이미지 건너뜀({location.title}): {error}")

            # 길바닥형은 가까운 장소의 상세 이미지를 5건만 재사용하지 않고 별도로 업로드한다.
            road_image_urls: dict[int, str] = {}
            for road_index in (1, 4, 7, 10, 13):
                if ROAD_WRITINGS[road_index] in existing:
                    continue
                location = locations[road_index]
                try:
                    source_url = fetch_detail_image_url(
                        tour_client, config, location.content_id
                    )
                    if source_url:
                        data, content_type, suffix = download_image(image_client, source_url)
                        upload = upload_image(
                            container,
                            data=data,
                            content_type=content_type,
                            suffix=suffix,
                            content_id=location.content_id,
                            kind="road",
                        )
                        uploaded.append(upload)
                        road_image_urls[road_index] = upload.url
                except (httpx.HTTPError, ValueError) as error:
                    print(f"길바닥 이미지 건너뜀({location.title} 근처): {error}")

        for index, location in enumerate(locations):
            writing = writing_for(location, index)
            if writing in existing:
                print(f"중복 장소 방명록 건너뜀: {location.title}")
                continue
            weather = rng.choice(WEATHERS)
            days_ago = rng.randint(1, 20)
            visited = today - timedelta(days=days_ago)
            saved = datetime.combine(
                visited, time(hour=rng.randint(9, 20), minute=rng.randint(0, 59))
            )
            insert_general(
                connection,
                location=location,
                user_id=user_ids[index % len(user_ids)],
                writing=writing,
                image_url=general_image_urls.get(location.id),
                weather=weather,
                temperature=temperature_for(weather, rng),
                color=rng.choice(COLORS),
                visited_at=visited,
                saved_at=saved,
            )
            general_inserted += 1

        for index in range(ROAD_COUNT):
            writing = ROAD_WRITINGS[index]
            if writing in existing:
                print(f"중복 길바닥 방명록 건너뜀: {ROAD_ALIASES[index]}")
                continue
            weather = rng.choice(WEATHERS)
            latitude, longitude = random_point(
                args.latitude, args.longitude, rng, index
            )
            days_ago = rng.randint(0, 20)
            visited = today - timedelta(days=days_ago)
            saved = datetime.combine(
                visited, time(hour=rng.randint(8, 21), minute=rng.randint(0, 59))
            )
            insert_road(
                connection,
                user_id=user_ids[(index + GENERAL_COUNT) % len(user_ids)],
                alias=ROAD_ALIASES[index],
                latitude=latitude,
                longitude=longitude,
                writing=writing,
                image_url=road_image_urls.get(index),
                weather=weather,
                temperature=temperature_for(weather, rng),
                color=rng.choice(COLORS),
                visited_at=visited,
                saved_at=saved,
            )
            road_inserted += 1

        connection.commit()
        print(
            f"완료: 장소 방명록 {general_inserted}건, 길바닥 방명록 {road_inserted}건, "
            f"Blob 이미지 {len(uploaded)}개"
        )
    except Exception:
        connection.rollback()
        # DB가 실패했을 때 이번 실행의 고아 Blob만 정리한다.
        if uploaded:
            try:
                for item in uploaded:
                    container.get_blob_client(item.blob_name).delete_blob()
            except Exception as cleanup_error:  # noqa: BLE001
                print(f"경고: 실패 후 Blob 정리 중 오류: {cleanup_error}")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
