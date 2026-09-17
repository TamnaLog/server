"""미션 완료 후 다음 장소 추천 응답 스키마와 추천 로직.

미션을 끝낸 뒤 "다음엔 여기로 가보세요"를 내려주는 규칙은 미션 유형과 무관하게 같으므로
공용 모듈에 한 번만 두고 각 도메인에서 import해서 쓴다.

추천 기준
- 기준 좌표에서 직선거리가 가장 가까운 `LOCATION` 하나를 고른다.
- 방금 미션을 진행한 장소는 제외한다. (그 자리에 있는 사용자에게 같은 장소를 다시 추천하지 않는다)
- 거리가 같으면 `LOCATION.id` 가 작은 장소를 고른다.
- 장소에 연결된 세부 미션이 있으면 그중 하나를 함께 내려주고, 없으면 `mission` 은 `null` 이다.
  여러 개가 연결돼 있으면 그중 하나를 무작위로 고른다.

문화 미션은 장소를 갖지 않으므로 다음 장소에 연결될 수 있는 미션 유형은 협동/보물 찾기뿐이다.
"""

import random
from math import cos, radians

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import distance
from app.cooperative_mission.models import CooperativeMission
from app.map.models import Location
from app.mission.schemas import MissionType
from app.services.kto import get_location_image_url
from app.treasure_mission.models import TreasureMission


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class NextLocationMissionResponse(CamelModel):
    """다음 장소에서 수행할 미션.

    `id` 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션 테이블의 id다.
    문화 미션은 장소를 갖지 않으므로 협동/보물 찾기 미션만 올 수 있다.
    """

    id: int
    mission_type: MissionType


class NextLocationSummaryResponse(CamelModel):
    """미션 완료 후 추천하는 다음 장소. (거리 없음)

    사용자 좌표를 받지 않는 API(협동 미션 나가기)는 거리를 계산할 수 없어 이 형식을 쓴다.
    `location_image_url` 은 TourAPI 에서 조회하므로 조회하지 못하면 `null` 이다.
    """

    id: int
    location_title: str
    location_image_url: str | None = None
    mission: NextLocationMissionResponse | None = None


class NextLocationResponse(NextLocationSummaryResponse):
    """미션 완료 후 추천하는 다음 장소. (사용자 위치에서의 직선거리 포함)"""

    distance_meter: int


def recommend_next_location(
    db: Session,
    latitude: float,
    longitude: float,
    exclude_location_id: int | None = None,
) -> NextLocationResponse | None:
    """사용자 위치에서 가장 가까운 장소를 다음 장소로 추천한다.

    `exclude_location_id` 에는 방금 미션을 진행한 장소를 넘긴다. (장소가 없는 문화 미션은 `None`)
    추천할 장소가 하나도 없으면 `None` 을 반환한다.
    """
    location = _pick_location(db, latitude, longitude, exclude_location_id)
    if location is None:
        return None

    return NextLocationResponse(
        id=location.id,
        location_title=location.location_title,
        location_image_url=get_location_image_url(location.content_id),
        distance_meter=distance.calculate_distance_meter(
            latitude, longitude, location.my, location.mx
        ),
        mission=_pick_mission(db, location.id),
    )


def recommend_next_location_summary(
    db: Session, base_location: Location
) -> NextLocationSummaryResponse | None:
    """사용자 좌표 없이 다음에 갈 장소를 추천한다. (거리 제외)

    사용자 좌표 대신 방금 미션을 진행한 장소(`base_location`)를 기준 좌표로 삼고,
    그 장소를 제외한 가장 가까운 장소를 고른다. 추천 기준은 좌표가 있는 경우와 같다.
    """
    location = _pick_location(db, base_location.my, base_location.mx, base_location.id)
    if location is None:
        return None

    return NextLocationSummaryResponse(
        id=location.id,
        location_title=location.location_title,
        location_image_url=get_location_image_url(location.content_id),
        mission=_pick_mission(db, location.id),
    )


def _pick_location(
    db: Session, latitude: float, longitude: float, exclude_location_id: int | None
) -> Location | None:
    """기준 좌표에서 가장 가까운 장소를 고른다. 거리가 같으면 id 가 작은 장소.

    정렬은 DB 에서 하되, 하버사인 대신 경도 차이에 cos(위도)를 곱한 평면 거리의 제곱을 쓴다.
    제주 안의 거리에서는 하버사인과 순서가 사실상 같고, MySQL/SQLite 모두 사칙연산만으로 계산된다.
    """
    lng_scale = cos(radians(latitude))
    squared_distance = (Location.my - latitude) * (Location.my - latitude) + (
        (Location.mx - longitude) * lng_scale
    ) * ((Location.mx - longitude) * lng_scale)

    statement = select(Location).order_by(squared_distance, Location.id).limit(1)
    if exclude_location_id is not None:
        statement = statement.where(Location.id != exclude_location_id)
    return db.scalars(statement).first()


def _pick_mission(db: Session, location_id: int) -> NextLocationMissionResponse | None:
    """장소에 연결된 세부 미션 중 하나를 고른다. 연결된 미션이 없으면 `None`.

    id 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션 테이블의 id다.
    """
    cooperative_ids = db.scalars(
        select(CooperativeMission.id).where(CooperativeMission.location_id == location_id)
    ).all()
    treasure_ids = db.scalars(
        select(TreasureMission.id).where(TreasureMission.location_id == location_id)
    ).all()

    missions = [
        NextLocationMissionResponse(id=mission_id, mission_type=MissionType.COOPERATIVE)
        for mission_id in cooperative_ids
    ] + [
        NextLocationMissionResponse(id=mission_id, mission_type=MissionType.TREASURE)
        for mission_id in treasure_ids
    ]
    if not missions:
        return None
    return random.choice(missions)
