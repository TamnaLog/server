"""지도 도메인 비즈니스 로직.

기준 문서: app/map/docs/API_SPEC.md, app/map/docs/BUSINESS_RULES.md
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common import distance, rewards
from app.common.rewards import GrantedRewards
from app.cooperative_mission.models import CooperativeMission
from app.core.errors import InvalidRequestError, NotFoundError
from app.guestbook.models import Guestbook, RoadGuestbook
from app.map import (
    location_missions,
    mission_completion,
    mission_detail,
    mission_recommender,
    search_classifier,
)
from app.map.location_missions import LocationMission
from app.map.models import Location
from app.map.schemas import (
    ClusteredLocationResponse,
    ClusteredMapContentsResponse,
    ClusteredRoadGuestbookResponse,
    LocationDetailQuery,
    LocationDetailResponse,
    LocationGuestbookResponse,
    LocationMissionResponse,
    LocationModalGuestbookResponse,
    LocationModalResponse,
    MapContentsQuery,
    MapContentsResponse,
    MapLocationResponse,
    MapMissionResponse,
    MapModalMissionResponse,
    MapModalQuery,
    MapModalTargetType,
    NearbyMissionResponse,
    MapRoadGuestbookResponse,
    MapSearchQuery,
    MapSearchResponse,
    RoadGuestbookModalResponse,
)
from app.map.viewport import Point, Viewport
from app.mission import reward_history
from app.mission.completion import is_mission_completed
from app.mission.models import Mission
from app.mission.schemas import MissionType
from app.services.kto import (
    get_location_detail_image_urls,
    get_location_image_url,
    get_location_overview,
)
from app.treasure_mission.models import TreasureMission
from app.user.models import User


def get_map_contents(
    db: Session, current_user_id: int, query: MapContentsQuery
) -> MapContentsResponse | ClusteredMapContentsResponse:
    """지도 홈 조회.

    지도 화면 안의 장소와 길바닥 방명록을 내려준다.
    클러스터링 상태(`isClustered = true`)에서는 식별자·좌표와 장소의 미션 id/유형만 주고
    거리 계산·미션 제목/완료 여부·방명록 집계·TourAPI 이미지 조회는 아예 하지 않는다.
    """
    viewport = _to_viewport(query)
    locations = _find_locations_in_viewport(db, viewport)
    road_guestbooks = _find_road_guestbooks_in_viewport(db, viewport)

    if query.is_clustered:
        return _to_clustered_response(db, locations, road_guestbooks)

    return MapContentsResponse(
        locations=_to_location_responses(db, current_user_id, locations, query),
        road_guestbooks=[
            _to_road_guestbook_response(road_guestbook) for road_guestbook in road_guestbooks
        ],
    )


def _to_viewport(query: MapContentsQuery) -> Viewport:
    """Query 의 네 꼭짓점으로 조회 영역을 만든다.

    네 점이 한 점에 모이거나 한 직선 위에 있으면 화면 영역이 될 수 없어 400 으로 막는다.
    """
    viewport = Viewport(
        left_top=Point(query.left_top_latitude, query.left_top_longitude),
        right_top=Point(query.right_top_latitude, query.right_top_longitude),
        right_bottom=Point(query.right_bottom_latitude, query.right_bottom_longitude),
        left_bottom=Point(query.left_bottom_latitude, query.left_bottom_longitude),
    )
    if not viewport.is_valid():
        raise InvalidRequestError("네 꼭짓점이 넓이가 있는 지도 조회 영역을 만들지 못합니다.")
    return viewport


def _find_locations_in_viewport(db: Session, viewport: Viewport) -> list[Location]:
    """조회 영역 안의 장소를 찾는다.

    미션이나 방명록이 없는 장소도 그대로 내려준다.
    (미션은 `null`, 방명록 개수는 `0` 으로 나간다)
    DB 에서는 사각형을 감싸는 위도·경도 범위로 후보만 좁히고,
    회전된 화면 밖으로 삐져나온 후보는 실제 영역 판정으로 걸러낸다.
    """
    statement = select(Location).where(
        Location.my.between(viewport.min_latitude, viewport.max_latitude),
        Location.mx.between(viewport.min_longitude, viewport.max_longitude),
    )
    return [
        location
        for location in db.scalars(statement).all()
        if viewport.contains(location.my, location.mx)
    ]


def _find_road_guestbooks_in_viewport(
    db: Session, viewport: Viewport
) -> list[RoadGuestbook]:
    """조회 영역 안의 길바닥 방명록을 찾는다. 삭제된 방명록은 제외한다."""
    statement = select(RoadGuestbook).where(
        RoadGuestbook.deleted_at.is_(None),
        RoadGuestbook.my.between(viewport.min_latitude, viewport.max_latitude),
        RoadGuestbook.mx.between(viewport.min_longitude, viewport.max_longitude),
    )
    return [
        road_guestbook
        for road_guestbook in db.scalars(statement).all()
        if viewport.contains(road_guestbook.my, road_guestbook.mx)
    ]


def _to_clustered_response(
    db: Session, locations: list[Location], road_guestbooks: list[RoadGuestbook]
) -> ClusteredMapContentsResponse:
    """클러스터링 응답을 만든다.

    프론트가 마커 모양을 정할 수 있게 장소의 미션 id/유형까지만 함께 준다.
    공통 `MISSION` 제목, 사용자 진행도, 방명록, TourAPI 는 조회하지 않는다.
    """
    mission_refs = location_missions.find_location_mission_refs(
        db, [location.id for location in locations]
    )
    return ClusteredMapContentsResponse(
        locations=[
            _to_clustered_location(location, mission_refs.get(location.id))
            for location in locations
        ],
        road_guestbooks=[
            ClusteredRoadGuestbookResponse(
                id=road_guestbook.id,
                latitude=road_guestbook.my,
                longitude=road_guestbook.mx,
            )
            for road_guestbook in road_guestbooks
        ],
    )


def _to_clustered_location(
    location: Location, mission_ref: location_missions.LocationMissionRef | None
) -> ClusteredLocationResponse:
    """미션이 없는 장소는 `mission_id` 와 `mission_type` 을 함께 비운다."""
    return ClusteredLocationResponse(
        id=location.id,
        latitude=location.my,
        longitude=location.mx,
        mission_id=mission_ref.id if mission_ref else None,
        mission_type=mission_ref.mission_type if mission_ref else None,
    )


def _to_location_responses(
    db: Session,
    current_user_id: int,
    locations: list[Location],
    query: MapContentsQuery,
) -> list[MapLocationResponse]:
    """장소 상세 응답을 만든다.

    한 장소에는 보물찾기 또는 협동 미션이 최대 하나라, 두 미션 필드 중 하나만 값이 있다.
    미션·완료 이력·방명록은 장소마다 다시 조회하지 않고 한 번에 가져와 맞춘다. (N+1 방지)
    """
    location_ids = [location.id for location in locations]
    treasure_missions = location_missions.find_treasure_missions(db, location_ids)
    cooperative_missions = location_missions.find_cooperative_missions(db, location_ids)
    completed_treasure_ids = mission_completion.find_completed_treasure_mission_ids(
        db, current_user_id, [mission.id for mission in treasure_missions.values()]
    )
    completed_cooperative_ids = (
        mission_completion.find_completed_cooperative_mission_ids(
            db, current_user_id, [mission.id for mission in cooperative_missions.values()]
        )
    )
    written_guestbooks = _find_written_mission_guestbooks(db, current_user_id, location_ids)
    guestbook_counts = _count_guestbooks_by_location(db, location_ids)

    responses = []
    for location in locations:
        distance_meter = distance.calculate_distance_meter(
            query.user_latitude, query.user_longitude, location.my, location.mx
        )
        responses.append(
            MapLocationResponse(
                id=location.id,
                location_title=location.location_title,
                latitude=location.my,
                longitude=location.mx,
                distance_meter=distance_meter,
                duration_minutes=distance.calculate_duration_minutes(distance_meter),
                # 한 장소에는 미션이 최대 하나라 둘 중 하나만 값이 있다.
                treasure_mission=_to_mission_response(
                    location_id=location.id,
                    mission=treasure_missions.get(location.id),
                    completed_mission_ids=completed_treasure_ids,
                    written_guestbooks=written_guestbooks,
                ),
                cooperative_mission=(
                    _to_mission_response(
                        location_id=location.id,
                        mission=cooperative_missions.get(location.id),
                        completed_mission_ids=completed_cooperative_ids,
                        written_guestbooks=written_guestbooks,
                    )
                    # 데이터 이상으로 두 유형이 다 있으면 보물찾기를 쓰고 이쪽은 비운다.
                    if location.id not in treasure_missions
                    else None
                ),
                guestbooks_count=guestbook_counts.get(location.id, 0),
                # 이미지 조회에 실패해도 지도 조회 전체를 실패시키지 않고 null 로 둔다.
                representative_image_url=get_location_image_url(location.content_id),
            )
        )
    return responses


def _to_mission_response(
    *,
    location_id: int,
    mission: LocationMission | None,
    completed_mission_ids: set[int],
    written_guestbooks: set[tuple[int, int]],
) -> MapMissionResponse | None:
    """미션 응답을 만든다. 그 유형의 미션이 없으면 `None`.

    방명록 작성 여부는 미션을 완료한 경우에만 본다. 미완료면 조회하지 않고 `null` 이다.
    """
    if mission is None:
        return None

    is_completed = mission.id in completed_mission_ids
    return MapMissionResponse(
        id=mission.id,
        mission_title=mission.mission_title,
        is_completed=is_completed,
        has_written_guestbook=(
            (location_id, mission.mission_id) in written_guestbooks if is_completed else None
        ),
    )


def _find_written_mission_guestbooks(
    db: Session, current_user_id: int, location_ids: list[int]
) -> set[tuple[int, int]]:
    """현재 사용자가 미션을 참조해 쓴 방명록의 `(장소 id, MISSION.id)` 집합.

    `GUESTBOOK.mission_id` 는 세부 미션 id 가 아니라 공통 `MISSION.id` 라
    장소와 함께 봐야 어느 미션의 방명록인지 알 수 있다.
    """
    if not location_ids:
        return set()

    statement = select(Guestbook.location_id, Guestbook.mission_id).where(
        Guestbook.location_id.in_(location_ids),
        Guestbook.user_id == current_user_id,
        Guestbook.mission_id.is_not(None),
        Guestbook.deleted_at.is_(None),
    )
    return {(location_id, mission_id) for location_id, mission_id in db.execute(statement)}


def _count_guestbooks_by_location(db: Session, location_ids: list[int]) -> dict[int, int]:
    """장소 id → 삭제되지 않은 방명록 개수를 한 번에 센다."""
    if not location_ids:
        return {}

    statement = (
        select(Guestbook.location_id, func.count())
        .where(
            Guestbook.location_id.in_(location_ids),
            Guestbook.deleted_at.is_(None),
        )
        .group_by(Guestbook.location_id)
    )
    return {location_id: count for location_id, count in db.execute(statement).all()}


def _to_road_guestbook_response(
    road_guestbook: RoadGuestbook,
) -> MapRoadGuestbookResponse:
    """길바닥 방명록 상세 응답을 만든다. 대표 이미지는 첨부 이미지 중 첫 번째다."""
    return MapRoadGuestbookResponse(
        id=road_guestbook.id,
        latitude=road_guestbook.my,
        longitude=road_guestbook.mx,
        location_alias=road_guestbook.location_alias,
        representative_guestbook_image_url=_first_image_url(road_guestbook.content_img_url),
    )


def _first_image_url(content_img_url: list[str] | None) -> str | None:
    """첨부 이미지 목록의 첫 번째 URL. 이미지가 없으면 `None`."""
    if not content_img_url:
        return None
    return content_img_url[0]


# ---------------------------------------------------------------------
# 지도 모달 조회
# ---------------------------------------------------------------------


# 장소 모달에 함께 보여줄 최신 방명록 개수
LOCATION_MODAL_GUESTBOOK_LIMIT = 3

MAP_MODAL_TARGET_NOT_FOUND = "MAP_MODAL_TARGET_NOT_FOUND"


def get_map_modal(
    db: Session, current_user_id: int, query: MapModalQuery
) -> LocationModalResponse | RoadGuestbookModalResponse:
    """지도에서 아이콘을 눌렀을 때 띄울 모달 정보를 조회한다.

    조회 대상은 장소와 길바닥 방명록 두 가지뿐이고, 유형에 따라 응답 형태가 다르다.
    장소 모달의 미션 완료/보상 수령 여부는 현재 사용자 기준으로 판단한다.
    조회만 하고 데이터를 바꾸지 않는다. (보상을 지급하거나 지급 여부를 바꾸지 않는다)
    """
    if query.target_type is MapModalTargetType.LOCATION:
        return _to_location_modal(db, current_user_id, query)
    return _to_road_guestbook_modal(db, query)


def _to_location_modal(
    db: Session, current_user_id: int, query: MapModalQuery
) -> LocationModalResponse:
    """장소 모달 응답을 만든다.

    방명록이 없어도, 연결된 미션이 없어도 오류가 아니다.
    (각각 개수 0 / 빈 배열, `mission = null`)
    """
    location = db.get(Location, query.target_id)
    if location is None:
        raise NotFoundError(
            MAP_MODAL_TARGET_NOT_FOUND,
            detail=f"장소 {query.target_id} 를 찾을 수 없습니다.",
        )

    distance_meter = distance.calculate_distance_meter(
        query.user_latitude, query.user_longitude, location.my, location.mx
    )
    return LocationModalResponse(
        id=location.id,
        location_title=location.location_title,
        location_category=location.location_category,
        distance_meter=distance_meter,
        duration_minutes=distance.calculate_duration_minutes(distance_meter),
        mission=_find_modal_mission(db, current_user_id, location.id),
        guestbooks_count=_count_guestbooks(db, location.id),
        guestbooks=_find_latest_guestbooks(db, location.id),
    )


def _find_modal_mission(
    db: Session, current_user_id: int, location_id: int
) -> MapModalMissionResponse | None:
    """장소 모달에 넣을 미션. 연결된 미션이 없으면 `None`.

    조합 규칙은 장소 상세와 같고, 모달 응답에는 미션 설명이 없는 것만 다르다.
    """
    found = mission_detail.find_location_mission(db, current_user_id, location_id)
    if found is None:
        return None

    return MapModalMissionResponse(
        mission_id=found.mission_id,
        mission_type=found.mission_type,
        mission_title=found.mission_title,
        is_completed=found.is_completed,
        reward_detail=found.reward_detail,
    )


def _count_guestbooks(db: Session, location_id: int) -> int:
    """장소를 참조하는 삭제되지 않은 방명록 전체 개수. (응답 목록 길이와 다르다)"""
    count = db.scalar(
        select(func.count())
        .select_from(Guestbook)
        .where(
            Guestbook.location_id == location_id,
            Guestbook.deleted_at.is_(None),
        )
    )
    return count or 0


def _find_latest_guestbooks(
    db: Session, location_id: int
) -> list[LocationModalGuestbookResponse]:
    """장소의 최신 방명록을 최대 3개 가져온다.

    최신 기준은 저장 시각이 아니라 방문일(`visited_at`)이고, 같으면 id 가 큰 쪽이 최신이다.
    작성자와 미션은 방명록마다 다시 조회하지 않고 JOIN 으로 한 번에 가져온다. (N+1 방지)
    """
    statement = (
        select(Guestbook, User.nickname, Mission.mission_title)
        .join(User, User.id == Guestbook.user_id)
        .outerjoin(Mission, Mission.id == Guestbook.mission_id)
        .where(
            Guestbook.location_id == location_id,
            Guestbook.deleted_at.is_(None),
        )
        .order_by(Guestbook.visited_at.desc(), Guestbook.id.desc())
        .limit(LOCATION_MODAL_GUESTBOOK_LIMIT)
    )
    return [
        LocationModalGuestbookResponse(
            id=guestbook.id,
            representative_image_url=_first_image_url(guestbook.content_img_url),
            user_nickname=nickname or "",
            mission_title=mission_title,
            visited_at=guestbook.visited_at,
            content_writing=guestbook.content_writing,
        )
        for guestbook, nickname, mission_title in db.execute(statement).all()
    ]


def _to_road_guestbook_modal(
    db: Session, query: MapModalQuery
) -> RoadGuestbookModalResponse:
    """길바닥 방명록 모달 응답을 만든다. 저장된 콘텐츠를 그대로 내려준다."""
    statement = (
        select(RoadGuestbook, User.nickname)
        .join(User, User.id == RoadGuestbook.user_id)
        .where(
            RoadGuestbook.id == query.target_id,
            RoadGuestbook.deleted_at.is_(None),
        )
    )
    row = db.execute(statement).first()
    if row is None:
        raise NotFoundError(
            MAP_MODAL_TARGET_NOT_FOUND,
            detail=f"길바닥 방명록 {query.target_id} 를 찾을 수 없습니다.",
        )

    road_guestbook, nickname = row
    distance_meter = distance.calculate_distance_meter(
        query.user_latitude, query.user_longitude, road_guestbook.my, road_guestbook.mx
    )
    return RoadGuestbookModalResponse(
        id=road_guestbook.id,
        user_nickname=nickname or "",
        location_alias=road_guestbook.location_alias,
        distance_meter=distance_meter,
        duration_minutes=distance.calculate_duration_minutes(distance_meter),
        visited_at=road_guestbook.visited_at,
        content_image_urls=_to_content_list(road_guestbook.content_img_url),
        content_writing=road_guestbook.content_writing,
        content_audio_urls=_to_content_list(road_guestbook.content_audio_url),
        content_weather=road_guestbook.content_weather,
        content_color_code=road_guestbook.content_color_code,
    )


def _to_content_list(values: list[str] | None) -> list[str] | None:
    """빈 배열은 `null` 로 맞춘다. 값이 있으면 순서를 바꾸지 않고 그대로 쓴다."""
    return values or None


# ---------------------------------------------------------------------
# 지도 장소 상세 조회
# ---------------------------------------------------------------------


LOCATION_NOT_FOUND = "LOCATION_NOT_FOUND"

# 장소 상세에 노출할 TourAPI 상세 이미지 개수
LOCATION_DETAIL_IMAGE_LIMIT = 5


def get_location_detail(
    db: Session, current_user_id: int, location_id: int, query: LocationDetailQuery
) -> LocationDetailResponse:
    """장소 상세 화면 데이터를 조회한다.

    모달에서 이미 준 값(장소명·분류·거리·시간)도 상세에서 다시 모두 내려준다.
    상세 API 는 모달 요청의 좌표를 들고 있지 않아서 거리는 요청 좌표로 다시 계산한다.
    TourAPI 설명·이미지는 부가 정보라 실패해도 해당 필드만 `null` 이고 전체는 200 이다.
    조회 전용이라 보상을 지급하거나 지급 여부를 바꾸지 않는다.
    """
    location = db.get(Location, location_id)
    if location is None:
        raise NotFoundError(
            LOCATION_NOT_FOUND, detail=f"장소 {location_id} 를 찾을 수 없습니다."
        )

    distance_meter = distance.calculate_distance_meter(
        query.user_latitude, query.user_longitude, location.my, location.mx
    )
    return LocationDetailResponse(
        location_title=location.location_title,
        location_category=location.location_category,
        distance_meter=distance_meter,
        duration_minutes=distance.calculate_duration_minutes(distance_meter),
        location_address=location.location_address,
        location_description=get_location_overview(location.content_id),
        location_image_urls=get_location_detail_image_urls(
            location.content_id, LOCATION_DETAIL_IMAGE_LIMIT
        ),
        nearby_missions=_recommend_nearby_missions(db, current_user_id),
        guestbooks=_find_location_guestbooks(db, location.id),
        location_mission=_find_location_mission(db, current_user_id, location.id),
    )


def _recommend_nearby_missions(
    db: Session, current_user_id: int
) -> list[NearbyMissionResponse]:
    """추천 모듈이 고른 미션에 상세 정보와 장소 대표 이미지를 붙인다.

    어떤 미션을 보여줄지는 추천 모듈이 정하고, 여기서는 응답 값만 만든다.
    """
    missions = []
    for recommended in mission_recommender.recommend_nearby_missions(db, current_user_id):
        found = mission_detail.build(
            db, current_user_id, recommended.mission_type, recommended.id
        )
        if found is None:
            continue

        missions.append(
            NearbyMissionResponse(
                mission_id=found.mission_id,
                mission_type=found.mission_type,
                mission_title=found.mission_title,
                description=found.description,
                is_completed=found.is_completed,
                reward_detail=found.reward_detail,
                # 추천 미션은 각각 다른 장소라 미션마다 그 장소의 이름과 대표 이미지를 쓴다.
                location_title=found.location_title,
                representative_image_url=get_location_image_url(
                    found.location_content_id
                ),
            )
        )

    return missions


def _find_location_guestbooks(
    db: Session, location_id: int
) -> list[LocationGuestbookResponse]:
    """장소의 방명록을 최신순으로 모두 가져온다. (개수 제한/페이지네이션 없음)

    최신 기준은 저장 시각이 아니라 방문일(`visited_at`)이고, 같으면 id 가 큰 쪽이 최신이다.
    작성자와 미션은 방명록마다 다시 조회하지 않고 JOIN 으로 한 번에 가져온다. (N+1 방지)
    """
    statement = (
        select(Guestbook, User.nickname, Mission.mission_title)
        .join(User, User.id == Guestbook.user_id)
        .outerjoin(Mission, Mission.id == Guestbook.mission_id)
        .where(
            Guestbook.location_id == location_id,
            Guestbook.deleted_at.is_(None),
        )
        .order_by(Guestbook.visited_at.desc(), Guestbook.id.desc())
    )
    return [
        LocationGuestbookResponse(
            id=guestbook.id,
            mission_title=mission_title,
            representative_image_url=_first_image_url(guestbook.content_img_url),
            user_id=guestbook.user_id,
            user_nickname=nickname or "",
            visited_at=guestbook.visited_at,
            content_writing=guestbook.content_writing,
        )
        for guestbook, nickname, mission_title in db.execute(statement).all()
    ]


def _find_location_mission(
    db: Session, current_user_id: int, location_id: int
) -> LocationMissionResponse | None:
    """이 장소에 직접 연결된 미션을 찾는다. 없으면 `None`.

    조합 규칙은 지도 모달과 같고, 상세 응답에는 미션 설명이 더 붙는다.
    """
    found = mission_detail.find_location_mission(db, current_user_id, location_id)
    if found is None:
        return None

    return LocationMissionResponse(
        mission_id=found.mission_id,
        mission_type=found.mission_type,
        mission_title=found.mission_title,
        description=found.description,
        is_completed=found.is_completed,
        reward_detail=found.reward_detail,
    )


# ---------------------------------------------------------------------
# 지도 검색 결과 조회
# ---------------------------------------------------------------------


def search_map(db: Session, query: MapSearchQuery) -> MapSearchResponse:
    """장소 이름으로 검색해 미션 없는 장소와 미션 있는 장소로 나눠 돌려준다.

    검색 대상은 미션 제목이 아니라 `LOCATION.location_title` 이다.
    개수 제한과 페이지네이션은 없다.
    """
    locations = _search_locations_by_keyword(db, query.keyword)
    location_ids = [location.id for location in locations]
    # 장소마다 다시 조회하지 않도록 미션은 여기서 한 번에 가져와 분류 모듈에 넘긴다.
    treasure_missions = location_missions.find_treasure_missions(db, location_ids)
    cooperative_missions = location_missions.find_cooperative_missions(db, location_ids)

    return MapSearchResponse(
        recommended_locations=search_classifier.build_recommended_locations(
            locations,
            treasure_missions,
            cooperative_missions,
            query.user_latitude,
            query.user_longitude,
        ),
        mission_locations=search_classifier.build_mission_locations(
            locations,
            treasure_missions,
            cooperative_missions,
            query.user_latitude,
            query.user_longitude,
        ),
    )


def _search_locations_by_keyword(db: Session, keyword: str) -> list[Location]:
    """장소 이름에 검색어가 들어간 장소를 모두 찾는다.

    이름의 앞·중간·끝 어디에 있어도 잡는다.
    검색어는 문자열을 이어 붙이지 않고 바인딩하며, `%` 나 `_` 도 글자 그대로 찾는다.
    """
    statement = select(Location).where(
        Location.location_title.contains(keyword, autoescape=True)
    )
    return list(db.scalars(statement).all())
