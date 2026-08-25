"""사용자 위치 ↔ 미션 장소 사이의 거리 / 예상 소요 시간 계산.

- 거리는 두 좌표 사이의 직선거리(하버사인)를 미터 단위로 계산한다.
- 예상 소요 시간은 직선거리에 비례해 분 단위로 계산한다.
  계산 기준은 100m 를 1분 20초(80초)에 걷는 것으로 가정한다.
(app/home/docs/BUSINESS_RULES.md - 3. 거리 및 예상 소요 시간)
"""

from math import asin, cos, radians, sin, sqrt


# 지구 반지름(m)
EARTH_RADIUS_METER = 6_371_000

# 100m 를 이동하는 데 걸리는 시간(초)
SECONDS_PER_100_METER = 80


def calculate_distance_meter(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """두 좌표 사이의 직선거리를 미터 단위로 반환한다."""
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
    return round(2 * EARTH_RADIUS_METER * asin(sqrt(a)))


def calculate_duration_minutes(distance_meter: int) -> int:
    """직선거리를 기준으로 예상 소요 시간을 분 단위로 반환한다."""
    seconds = distance_meter / 100 * SECONDS_PER_100_METER
    return round(seconds / 60)
