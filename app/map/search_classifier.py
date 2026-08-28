"""지도 검색 결과 분류 모듈.

검색으로 찾은 장소를 "추천 장소"와 "참여 가능한 미션 장소" 두 갈래로 나눈다.
(app/map/docs/BUSINESS_RULES.md - 지도 검색 결과 조회 3. 검색 로직 분리)

검색과 분류를 분리해 두는 이유는 **분류 기준이 바뀔 예정이기 때문**이다.
지금은 "미션이 연결돼 있느냐"만 보고 조건에 맞는 장소를 전부 내려주지만,
추천 정책이 정해지면 이 모듈 안의 선별 기준만 갈아끼우면 된다.
서비스(`app/map/service.py`)는 이 모듈을 호출만 하므로 손대지 않아도 된다.

이 모듈은 DB를 조회하지 않는다. 이미 조회된 장소와 미션 정보를 받아 고르고 정렬만 한다.
(검색 자체와 미션 일괄 조회는 서비스에서 이미 끝난 상태로 들어온다)
"""

from typing import TypeVar

from app.common import distance
from app.map.location_missions import LocationMission
from app.map.models import Location
from app.map.schemas import MissionLocationResponse, RecommendedLocationResponse
from app.mission.schemas import MissionType
from app.services.kto import get_location_image_url


# 두 응답은 정렬 기준(거리, 장소 id)을 똑같이 갖는다.
SearchedLocationT = TypeVar(
    "SearchedLocationT", RecommendedLocationResponse, MissionLocationResponse
)


def build_recommended_locations(
    locations: list[Location],
    treasure_missions: dict[int, LocationMission],
    cooperative_missions: dict[int, LocationMission],
    user_latitude: float,
    user_longitude: float,
) -> list[RecommendedLocationResponse]:
    """검색 결과에서 추천 장소를 고른다.

    현재 기준: 보물찾기도 협동 미션도 연결되지 않은 장소를 전부 담는다.
    """
    recommended = [
        _to_recommended_location(location, user_latitude, user_longitude)
        for location in locations
        if _is_recommendable(location, treasure_missions, cooperative_missions)
    ]
    return _sort_by_distance(recommended)


def _is_recommendable(
    location: Location,
    treasure_missions: dict[int, LocationMission],
    cooperative_missions: dict[int, LocationMission],
) -> bool:
    """추천 장소로 내보낼지 정한다.

    TODO: 추천 정책 확정 시 선별 기준 교체.
          지금은 "미션이 없는 장소는 전부" 이지만, 앞으로는 사용자 취향·방문 이력·
          방명록 수 같은 기준으로 좁히거나 순위를 매길 수 있다.
          그때 바꿀 곳은 이 함수 하나이고, 필요한 값은 인자로 더 받으면 된다.
    """
    return (
        location.id not in treasure_missions and location.id not in cooperative_missions
    )


def build_mission_locations(
    locations: list[Location],
    treasure_missions: dict[int, LocationMission],
    cooperative_missions: dict[int, LocationMission],
    user_latitude: float,
    user_longitude: float,
) -> list[MissionLocationResponse]:
    """검색 결과에서 참여 가능한 미션 장소를 고른다.

    현재 기준: 보물찾기 또는 협동 미션이 연결된 장소를 전부 담는다.
    """
    mission_locations = []
    for location in locations:
        mission = _pick_mission(
            location, treasure_missions, cooperative_missions
        )
        if mission is None:
            continue

        mission_locations.append(
            _to_mission_location(location, mission, user_latitude, user_longitude)
        )
    return _sort_by_distance(mission_locations)


def _pick_mission(
    location: Location,
    treasure_missions: dict[int, LocationMission],
    cooperative_missions: dict[int, LocationMission],
) -> tuple[LocationMission, MissionType] | None:
    """장소에서 내보낼 미션 하나를 고른다. 대상이 아니면 `None`.

    한 장소에는 미션이 최대 하나라는 전제라,
    데이터 이상으로 두 유형이 다 있으면 세부 미션 id 가 작은 쪽 하나만 쓴다.
    (장소 상세의 `locationMission` 과 같은 기준)

    TODO: 참여 가능 조건 확정 시 선별 기준 교체.
          지금은 현재 사용자의 완료 여부와 관계없이 미션이 있으면 전부 내보낸다.
          앞으로 "이미 완료한 미션 제외" 같은 조건이 붙으면 이 함수에서 거르고,
          완료 여부는 `app/map/mission_completion.py` 의 판정을 그대로 쓰면 된다.
    """
    candidates = [
        (mission, mission_type)
        for mission, mission_type in (
            (treasure_missions.get(location.id), MissionType.TREASURE),
            (cooperative_missions.get(location.id), MissionType.COOPERATIVE),
        )
        if mission is not None
    ]
    if not candidates:
        return None

    return min(candidates, key=lambda candidate: candidate[0].id)


def _to_recommended_location(
    location: Location, user_latitude: float, user_longitude: float
) -> RecommendedLocationResponse:
    return RecommendedLocationResponse(
        location_id=location.id,
        location_title=location.location_title,
        location_category=location.location_category,
        # 이미지 조회에 실패해도 검색 전체를 실패시키지 않고 null 로 둔다.
        representative_image_url=get_location_image_url(location.content_id),
        distance_meter=_to_distance_meter(location, user_latitude, user_longitude),
    )


def _to_mission_location(
    location: Location,
    mission: tuple[LocationMission, MissionType],
    user_latitude: float,
    user_longitude: float,
) -> MissionLocationResponse:
    found_mission, mission_type = mission
    return MissionLocationResponse(
        location_id=location.id,
        mission_id=found_mission.id,
        mission_type=mission_type,
        location_title=location.location_title,
        mission_title=found_mission.mission_title,
        representative_image_url=get_location_image_url(location.content_id),
        distance_meter=_to_distance_meter(location, user_latitude, user_longitude),
    )


def _to_distance_meter(
    location: Location, user_latitude: float, user_longitude: float
) -> int:
    """사용자 위치에서 장소까지의 직선거리(m)."""
    return distance.calculate_distance_meter(
        user_latitude, user_longitude, location.my, location.mx
    )


def _sort_by_distance(locations: list[SearchedLocationT]) -> list[SearchedLocationT]:
    """가까운 순으로 정렬한다. 거리가 같으면 장소 id 가 작은 쪽이 앞이다."""
    return sorted(
        locations, key=lambda location: (location.distance_meter, location.location_id)
    )
