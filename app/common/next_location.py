"""미션 완료 후 다음 장소 추천 응답 스키마와 추천 로직.

미션을 끝낸 뒤 "다음엔 여기로 가보세요"를 내려주는 규칙은 미션 유형과 무관하게 같으므로
공용 모듈에 한 번만 두고 각 도메인에서 import해서 쓴다.

추천 기준이 확정되기 전까지는 `LOCATION` 에 있는 장소 중 하나를 무작위로 고른다.
장소에 여러 세부 미션이 연결돼 있으면 그중 하나도 무작위로 고른다.
추후 기준이 확정되면 이 모듈 내부 로직만 교체하면 된다.
(app/culture_mission/docs/BUSINESS_RULES.md - 6. 다음 장소 추천 / 7. 다음 장소의 미션 정보)

문화 미션은 장소를 갖지 않으므로 다음 장소에 연결될 수 있는 미션 유형은 협동/보물 찾기뿐이다.
"""

import random

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
    db: Session, latitude: float, longitude: float
) -> NextLocationResponse | None:
    """다음에 갈 장소를 추천한다. (현재는 랜덤)

    추천할 장소가 하나도 없으면 `None` 을 반환한다.
    """
    location = _pick_location(db)
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


def recommend_next_location_summary(db: Session) -> NextLocationSummaryResponse | None:
    """사용자 좌표 없이 다음에 갈 장소를 추천한다. (거리 제외, 현재는 랜덤)

    추천 기준은 좌표가 있는 경우와 같다. 거리만 계산하지 않는다.
    """
    location = _pick_location(db)
    if location is None:
        return None

    return NextLocationSummaryResponse(
        id=location.id,
        location_title=location.location_title,
        location_image_url=get_location_image_url(location.content_id),
        mission=_pick_mission(db, location.id),
    )


def _pick_location(db: Session) -> Location | None:
    """추천할 장소를 고른다. (현재는 랜덤)"""
    # TODO: 추천 기준 확정 시 사용자 위치/취향 기반 추천 로직으로 교체
    locations = list(db.scalars(select(Location)).all())
    if not locations:
        return None
    return random.choice(locations)


def _pick_mission(db: Session, location_id: int) -> NextLocationMissionResponse | None:
    """장소에 연결된 세부 미션 중 하나를 고른다. 연결된 미션이 없으면 `None`.

    id 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션 테이블의 id다.
    """
    # TODO: 추천 기준 확정 시 미션 선택 로직도 함께 교체
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
