"""방문 장소 판정.

기준 문서: app/others/docs/BUSINESS_RULES.md - GPS 및 방문 장소 저장

좌표 하나와 장소 목록만 받아 **방문한 장소 id 목록**을 돌려준다.
DB·HTTP·트랜잭션을 모르는 순수 함수라, 나중에 판정 규칙이 바뀌어도 이 모듈만 갈아끼우면 된다.
(진입 이벤트, 체류 시간, 위치 정확도, 공간 질의 기반 로직 등으로 교체 예정)

거리는 지도·홈과 같은 기준을 쓰려고 `app/common/distance.py` 의 하버사인 계산을 그대로 쓴다.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.common.distance import calculate_distance_meter


__all__ = ["LocationArea", "find_visited_location_ids"]


@dataclass(frozen=True)
class LocationArea:
    """방문 판정에 필요한 장소 정보.

    ORM 모델을 그대로 받지 않고 필요한 값만 담아서, 판정 로직이 테이블 구조에 묶이지 않게 한다.
    """

    id: int
    latitude: float
    longitude: float
    radius_meter: int


def find_visited_location_ids(
    *, latitude: float, longitude: float, locations: Iterable[LocationArea]
) -> list[int]:
    """좌표가 반경 안에 들어오는 장소 id 목록. 방문한 장소가 없으면 빈 목록.

    - 거리가 반경과 **같은 경계도 방문으로 본다.** (`거리 <= radius`)
    - 반경이 겹치면 걸린 장소를 모두 담는다. 가장 가까운 한 곳만 고르지 않는다.
    - 진입/이탈 상태나 체류 시간은 보지 않는다. 좌표 한 건만으로 판정한다.
    - 입력 순서를 그대로 유지한다.
    """
    return [
        location.id
        for location in locations
        if calculate_distance_meter(
            latitude, longitude, location.latitude, location.longitude
        )
        <= location.radius_meter
    ]
