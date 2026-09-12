"""방문 장소 판정 모듈 테스트.

기준 문서: app/others/docs/BUSINESS_RULES.md - GPS 및 방문 장소 저장

API 테스트(`test_save_gps.py`)는 저장까지 함께 보므로, 여기서는 DB 없이
**판정 규칙 자체**만 본다. (공통 반경 5km, 경계 포함, 장소별 radius 무시)
"""

import pytest

from app.common.distance import calculate_distance_meter
from app.others.visit_detector import (
    VISIT_RADIUS_METER,
    LocationArea,
    find_visited_location_ids,
)


# 성산일출봉 근처 기준 좌표
LATITUDE = 33.4582
LONGITUDE = 126.9331


def _area(
    location_id: int,
    *,
    latitude: float = LATITUDE,
    longitude: float = LONGITUDE,
) -> LocationArea:
    return LocationArea(id=location_id, latitude=latitude, longitude=longitude)


def _find(*locations: LocationArea) -> list[int]:
    return find_visited_location_ids(
        latitude=LATITUDE, longitude=LONGITUDE, locations=list(locations)
    )


def _longitude_at(distance_meter: int) -> float:
    """기준 좌표에서 동쪽으로 대략 그만큼 떨어진 경도. (같은 위도에서 경도만 이동)"""
    meter_per_degree = calculate_distance_meter(
        LATITUDE, LONGITUDE, LATITUDE, LONGITUDE + 1
    )
    return LONGITUDE + distance_meter / meter_per_degree


def test_공통_판정_반경은_5km다() -> None:
    assert VISIT_RADIUS_METER == 5_000


def test_반경_안의_장소를_반환한다() -> None:
    assert _find(_area(1)) == [1]


def test_반경_밖의_장소는_반환하지_않는다() -> None:
    far = _area(1, longitude=_longitude_at(VISIT_RADIUS_METER + 1_000))

    assert _find(far) == []


def test_장소가_없으면_빈_목록이다() -> None:
    assert _find() == []


def test_좌표가_장소와_정확히_같으면_거리가_0이라_방문이다() -> None:
    assert _find(_area(1)) == [1]


def test_장소별_radius가_작아도_5km_안이면_방문이다() -> None:
    # 예전 규칙(거리 <= LOCATION.radius)이면 300m 반경 장소는 1km 밖에서 빠졌다.
    assert _find(_area(1, longitude=_longitude_at(1_000))) == [1]


def test_5km_경계는_방문으로_본다() -> None:
    # 거리가 반경과 같아지는 지점을 만들어 `거리 <= VISIT_RADIUS_METER` 인지 확인한다.
    on_edge_longitude = _longitude_at(VISIT_RADIUS_METER)
    assert (
        calculate_distance_meter(LATITUDE, LONGITUDE, LATITUDE, on_edge_longitude)
        == VISIT_RADIUS_METER
    )

    on_edge = _area(1, longitude=on_edge_longitude)
    just_outside = _area(2, longitude=_longitude_at(VISIT_RADIUS_METER + 10))

    assert _find(on_edge, just_outside) == [1]


def test_반경_안의_장소를_모두_반환한다() -> None:
    # 가장 가까운 한 곳만 고르지 않는다.
    assert _find(_area(1), _area(2, longitude=_longitude_at(3_000)), _area(3)) == [
        1,
        2,
        3,
    ]


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
    same_spot = LocationArea(id=1, latitude=latitude, longitude=longitude)
    other_side = LocationArea(id=2, latitude=-latitude, longitude=-longitude)

    found = find_visited_location_ids(
        latitude=latitude, longitude=longitude, locations=[same_spot, other_side]
    )

    assert found == [1]
