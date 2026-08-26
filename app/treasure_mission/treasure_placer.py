"""보물 좌표 생성.

진행도를 새로 만들 때 한 번만 좌표를 정하고, 이어하기에서는 다시 생성하지 않는다.
(app/treasure_mission/docs/BUSINESS_RULES.md - 5. 보물 좌표 생성)

생성 규칙:

1. 미션 장소를 원의 중심으로 두고 반경은 `TREASURE_APPEAR_RADIUS_METER` 를 쓴다.
2. 장소 → 사용자 방향 벡터에 수직인 직선으로 원을 반으로 나눈다.
3. 사용자가 있는 쪽 반원 안에서 `item_total_count` 개의 좌표를 무작위로 고른다.

즉 후보 좌표 `P` 는 장소 `L`, 사용자 `U` 에 대해 아래 두 조건을 만족한다.

    distance(L, P) <= TREASURE_APPEAR_RADIUS_METER
    dot(P - L, U - L) >= 0

위경도를 그대로 평면 좌표로 쓰면 위도에 따라 경도 간격이 달라져 실제 거리가 틀어진다.
그래서 장소를 원점으로 하는 **미터 단위 평면 좌표**로 바꿔 점을 만든 뒤 다시 위경도로 되돌린다.
(반경이 100m 수준이라 이 근사로 충분하다)

사용자와 장소가 사실상 같은 지점이면 방향을 정할 수 없으므로 원 전체에서 생성한다.
"""

import random
from math import atan2, cos, hypot, pi, radians, sin

from app.common.distance import EARTH_RADIUS_METER
from app.map.models import Location
from app.treasure_mission.constants import TREASURE_APPEAR_RADIUS_METER


# 위도 1도에 해당하는 거리(m). 경도는 위도에 따라 cos(위도)만큼 좁아진다.
METER_PER_DEGREE = pi * EARTH_RADIUS_METER / 180

# 이 거리보다 가까우면 장소와 사용자가 같은 지점이라고 보고 방향을 정하지 않는다.
SAME_POINT_TOLERANCE_METER = 0.5


def place_treasures(
    location: Location, latitude: float, longitude: float, treasure_count: int
) -> list[dict[str, float | int]]:
    """진행도에 저장할 보물 좌표(`item_detail`)를 만든다.

    `index` 는 1부터 시작하고, `mx` 는 경도, `my` 는 위도다.
    """
    center_lat, center_lng = location.my, location.mx
    user_x, user_y = _to_local_meter(center_lat, center_lng, latitude, longitude)

    return [
        _to_item(index, center_lat, center_lng, *_pick_point(user_x, user_y))
        for index in range(1, treasure_count + 1)
    ]


def _pick_point(user_x: float, user_y: float) -> tuple[float, float]:
    """장소를 원점으로 하는 평면에서 보물 하나의 좌표(m)를 고른다."""
    # sqrt 를 쓰지 않으면 중심 쪽에 점이 몰린다. (원 면적이 반지름의 제곱에 비례)
    distance = TREASURE_APPEAR_RADIUS_METER * (random.random() ** 0.5)

    if hypot(user_x, user_y) < SAME_POINT_TOLERANCE_METER:
        # 사용자와 장소가 같은 지점이면 방향을 정할 수 없으므로 원 전체에서 고른다.
        angle = random.uniform(-pi, pi)
    else:
        # 사용자 방향 ±90도 = 사용자가 있는 쪽 반원
        angle = atan2(user_y, user_x) + random.uniform(-pi / 2, pi / 2)

    return distance * cos(angle), distance * sin(angle)


def _to_local_meter(
    center_lat: float, center_lng: float, latitude: float, longitude: float
) -> tuple[float, float]:
    """위경도를 장소 중심 기준의 평면 좌표(m)로 바꾼다. (x=동쪽, y=북쪽)"""
    x = (longitude - center_lng) * METER_PER_DEGREE * cos(radians(center_lat))
    y = (latitude - center_lat) * METER_PER_DEGREE
    return x, y


def _to_item(
    index: int, center_lat: float, center_lng: float, x: float, y: float
) -> dict[str, float | int]:
    """평면 좌표(m)를 다시 위경도로 바꿔 `item_detail` 한 건으로 만든다."""
    latitude = center_lat + y / METER_PER_DEGREE
    longitude = center_lng + x / (METER_PER_DEGREE * cos(radians(center_lat)))
    return {"index": index, "mx": longitude, "my": latitude}
