"""지도 조회 영역(화면에 보이는 사각형) 판정.

지도를 회전하면 화면 네 꼭짓점이 위도·경도 축과 나란하지 않다.
그래서 "위도 범위 AND 경도 범위" 만으로는 화면 밖 데이터까지 걸린다.
실제 네 꼭짓점이 만드는 사각형 안에 있는지까지 확인해야 한다.

조회 영역 계산 규칙은 나중에 바뀔 수 있어(DB 공간 함수 사용 등) 서비스와 분리해 둔다.
"""

from dataclasses import dataclass


# 좌표 비교 오차 허용치. 경계선 위의 점을 부동소수점 오차로 놓치지 않기 위해 쓴다.
EPSILON = 1e-12


@dataclass(frozen=True)
class Point:
    """위도·경도 한 쌍. (`latitude` = `my`, `longitude` = `mx`)"""

    latitude: float
    longitude: float


@dataclass(frozen=True)
class Viewport:
    """지도 화면 네 꼭짓점이 만드는 조회 영역.

    꼭짓점은 `좌상단 → 우상단 → 우하단 → 좌하단` 순서로 이어 사각형을 만든다.
    """

    left_top: Point
    right_top: Point
    right_bottom: Point
    left_bottom: Point

    @property
    def corners(self) -> tuple[Point, Point, Point, Point]:
        """사각형을 이루는 순서대로의 꼭짓점."""
        return (self.left_top, self.right_top, self.right_bottom, self.left_bottom)

    @property
    def min_latitude(self) -> float:
        return min(corner.latitude for corner in self.corners)

    @property
    def max_latitude(self) -> float:
        return max(corner.latitude for corner in self.corners)

    @property
    def min_longitude(self) -> float:
        return min(corner.longitude for corner in self.corners)

    @property
    def max_longitude(self) -> float:
        return max(corner.longitude for corner in self.corners)

    def is_valid(self) -> bool:
        """넓이가 있는 영역인지 확인한다.

        네 점이 한 점에 모여 있거나 한 직선 위에 있으면 화면 영역이 될 수 없다.
        """
        return abs(_signed_area(self.corners)) > EPSILON

    def contains(self, latitude: float, longitude: float) -> bool:
        """좌표가 조회 영역 안(경계선 포함)에 있는지 확인한다."""
        point = Point(latitude=latitude, longitude=longitude)
        if _is_on_edge(point, self.corners):
            return True
        return _is_inside(point, self.corners)


def _signed_area(corners: tuple[Point, ...]) -> float:
    """신발끈 공식으로 다각형의 부호 있는 넓이를 구한다. (넓이가 0이면 찌그러진 도형)"""
    total = 0.0
    for current, following in _edges(corners):
        total += current.longitude * following.latitude
        total -= following.longitude * current.latitude
    return total / 2


def _edges(corners: tuple[Point, ...]) -> list[tuple[Point, Point]]:
    """다각형의 변 목록. 마지막 꼭짓점은 첫 꼭짓점과 이어진다."""
    return [
        (corners[index], corners[(index + 1) % len(corners)])
        for index in range(len(corners))
    ]


def _is_on_edge(point: Point, corners: tuple[Point, ...]) -> bool:
    """점이 경계선 위에 있는지 확인한다. 경계선 위의 점도 영역 안으로 본다."""
    return any(_is_on_segment(point, start, end) for start, end in _edges(corners))


def _is_on_segment(point: Point, start: Point, end: Point) -> bool:
    """점이 선분 위에 있는지 확인한다."""
    cross = (end.longitude - start.longitude) * (point.latitude - start.latitude) - (
        end.latitude - start.latitude
    ) * (point.longitude - start.longitude)
    if abs(cross) > EPSILON:
        # 선분을 지나는 직선 위에 없다.
        return False

    # 직선 위에 있어도 선분 바깥일 수 있어 두 끝점 사이인지 확인한다.
    return (
        min(start.longitude, end.longitude) - EPSILON
        <= point.longitude
        <= max(start.longitude, end.longitude) + EPSILON
        and min(start.latitude, end.latitude) - EPSILON
        <= point.latitude
        <= max(start.latitude, end.latitude) + EPSILON
    )


def _is_inside(point: Point, corners: tuple[Point, ...]) -> bool:
    """점에서 한쪽으로 반직선을 그어 변과 만나는 횟수로 내부인지 판정한다.

    홀수 번 만나면 내부, 짝수 번이면 외부다. (ray casting)
    회전해서 기울어진 사각형에도 그대로 쓸 수 있다.
    """
    is_inside = False
    for start, end in _edges(corners):
        crosses_latitude = (start.latitude > point.latitude) != (end.latitude > point.latitude)
        if not crosses_latitude:
            continue

        # 변이 point 의 위도에 닿는 지점의 경도
        crossing_longitude = start.longitude + (point.latitude - start.latitude) * (
            end.longitude - start.longitude
        ) / (end.latitude - start.latitude)
        if point.longitude < crossing_longitude:
            is_inside = not is_inside
    return is_inside
