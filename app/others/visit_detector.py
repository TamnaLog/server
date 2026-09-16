"""방문 장소 판정.

기준 문서: app/others/docs/BUSINESS_RULES.md - GPS 및 방문 장소 저장

좌표 하나와 장소 목록만 받아 **방문한 장소 id 목록**을 돌려준다.
DB·HTTP·트랜잭션을 모르는 순수 함수라, 나중에 판정 규칙이 바뀌어도 이 모듈만 갈아끼우면 된다.
(진입 이벤트, 체류 시간, 위치 정확도, 공간 질의 기반 로직 등으로 교체 예정)

거리는 지도·홈과 같은 기준을 쓰려고 `app/common/distance.py` 의 하버사인 계산을 그대로 쓴다.

TODO: 현재는 장소별 `LOCATION.radius` 를 쓰지 않고 모든 장소에 공통 반경(`VISIT_RADIUS_METER`)
을 적용한다. 명세(BUSINESS_RULES.md)의 "거리 <= radius" 규칙과 다른 임시 규칙이다.
반경 기준이 확정되면 `LocationArea` 에 반경을 다시 담고 `find_visited_location_ids()` 의
비교 대상을 장소별 반경으로 되돌린다. (`app/others/service.py` 도 함께 바꾼다)
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.common.distance import calculate_distance_meter


__all__ = ["VISIT_RADIUS_METER", "LocationArea", "find_visited_location_ids"]


# 모든 장소에 공통으로 적용하는 방문 판정 반경(m).
VISIT_RADIUS_METER = 5_000


@dataclass(frozen=True)
class LocationArea:
    """방문 판정에 필요한 장소 정보.

    ORM 모델을 그대로 받지 않고 필요한 값만 담아서, 판정 로직이 테이블 구조에 묶이지 않게 한다.
    반경은 장소마다 다르지 않고 `VISIT_RADIUS_METER` 하나를 쓰므로 여기에 담지 않는다.
    """

    id: int
    latitude: float
    longitude: float


def find_visited_location_ids(
    *, latitude: float, longitude: float, locations: Iterable[LocationArea]
) -> list[int]:
    """좌표에서 5km 안에 있는 장소 id 목록. 방문한 장소가 없으면 빈 목록.

    - 장소별 반경(`LOCATION.radius`)은 보지 않는다. 모든 장소에 5km 를 똑같이 적용한다.
    - 거리가 반경과 **같은 경계도 방문으로 본다.** (`거리 <= VISIT_RADIUS_METER`)
    - 반경 안에 든 장소를 모두 담는다. 가장 가까운 한 곳만 고르지 않는다.
    - 진입/이탈 상태나 체류 시간은 보지 않는다. 좌표 한 건만으로 판정한다.
    - 입력 순서를 그대로 유지한다.
    """
    return [
        location.id
        for location in locations
        if calculate_distance_meter(
            latitude, longitude, location.latitude, location.longitude
        )
        <= VISIT_RADIUS_METER
    ]
