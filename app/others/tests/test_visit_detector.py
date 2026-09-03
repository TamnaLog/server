"""방문 장소 판정 모듈 테스트.

기준 문서: app/others/docs/BUSINESS_RULES.md - GPS 및 방문 장소 저장

API 테스트(`test_save_gps.py`)는 저장까지 함께 보므로, 여기서는 DB 없이
**판정 규칙 자체**만 본다. (경계 포함, 반경 중첩, 반경별 차이)
"""

import pytest

from app.common.distance import calculate_distance_meter
from app.others.visit_detector import LocationArea, find_visited_location_ids


# 성산일출봉 근처 기준 좌표
LATITUDE = 33.4582
LONGITUDE = 126.9331


def _area(
    location_id: int,
    *,
    latitude: float = LATITUDE,
    longitude: float = LONGITUDE,
    radius_meter: int = 300,
) -> LocationArea:
    return LocationArea(
        id=location_id,
        latitude=latitude,
        longitude=longitude,
        radius_meter=radius_meter,
    )


def _find(*locations: LocationArea) -> list[int]:
    return find_visited_location_ids(
        latitude=LATITUDE, longitude=LONGITUDE, locations=list(locations)
    )


def test_반경_안의_장소를_반환한다() -> None:
    assert _find(_area(1)) == [1]


def test_반경_밖의_장소는_반환하지_않는다() -> None:
    # 같은 위도에서 경도만 크게 벌려 반경(300m) 밖으로 보낸다.
    far = _area(1, longitude=LONGITUDE + 0.05)

    assert _find(far) == []


def test_장소가_없으면_빈_목록이다() -> None:
    assert _find() == []


def test_좌표가_장소와_정확히_같으면_거리가_0이라_방문이다() -> None:
    assert _find(_area(1, radius_meter=1)) == [1]


def test_반경_경계는_방문으로_본다() -> None:
    # 거리가 반경과 같아지는 지점을 만들어 `거리 <= radius` 인지 확인한다.
    edge_longitude = LONGITUDE + 0.003
    distance = calculate_distance_meter(
        LATITUDE, LONGITUDE, LATITUDE, edge_longitude
    )

    on_edge = _area(1, longitude=edge_longitude, radius_meter=distance)
    just_outside = _area(2, longitude=edge_longitude, radius_meter=distance - 1)

    assert _find(on_edge, just_outside) == [1]


def test_반경이_겹치면_모두_반환한다() -> None:
    # 가장 가까운 한 곳만 고르지 않는다.
    assert _find(_area(1), _area(2), _area(3)) == [1, 2, 3]


def test_반경이_다르면_결과가_갈린다() -> None:
    near_longitude = LONGITUDE + 0.002
    distance = calculate_distance_meter(
        LATITUDE, LONGITUDE, LATITUDE, near_longitude
    )

    wide = _area(1, longitude=near_longitude, radius_meter=distance + 50)
    narrow = _area(2, longitude=near_longitude, radius_meter=distance - 50)

    assert _find(wide, narrow) == [1]


def test_입력_순서를_그대로_유지한다() -> None:
    assert _find(_area(30), _area(10), _area(20)) == [30, 10, 20]


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        pytest.param(-33.4582, 126.9331, id="남반구"),
        pytest.param(33.4582, -126.9331, id="서반구"),
    ],
)
def test_부호가_반대인_좌표도_같은_규칙으로_판정한다(
    latitude: float, longitude: float
) -> None:
    same_spot = LocationArea(
        id=1, latitude=latitude, longitude=longitude, radius_meter=10
    )
    other_side = LocationArea(
        id=2, latitude=-latitude, longitude=-longitude, radius_meter=10
    )

    found = find_visited_location_ids(
        latitude=latitude, longitude=longitude, locations=[same_spot, other_side]
    )

    assert found == [1]
