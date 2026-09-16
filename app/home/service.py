"""홈 도메인 비즈니스 로직.

기준 문서: app/home/docs/API_SPEC.md, app/home/docs/BUSINESS_RULES.md

실제 미션 한 건은 미션 유형별 테이블(CULTURE/COOPERATIVE/TREASURE_MISSION)의 행이다.
그래서 응답의 `missionId` 는 유형별 테이블의 id이고, 유형/이름/단계는 그 행이 속한
`MISSION` 에서, 장소는 유형별 테이블에서 가져온다. (문화 미션은 장소가 없다)
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import distance
from app.home import guestbook_counter, mission_recommender
from app.home.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    CultureMission,
    CultureMissionProgress,
    Location,
    Mission,
    MissionStatus,
    TreasureMission,
    TreasureMissionProgress,
    User,
)
from app.home.schemas import (
    HomeResponse,
    LocationPoint,
    MissionType,
    ProgressMission,
    RecommendedMission,
)


def get_home(db: Session, current_user_id: int, latitude: float, longitude: float) -> HomeResponse:
    """홈 조회.

    추천 미션, 진행 중인 미션, 쌓인 방명록 개수, 사용자 캐릭터 이미지를 한 번에 반환한다.
    거리/예상 소요 시간은 요청으로 받은 사용자 위치를 기준으로 계산한다.
    """
    return HomeResponse(
        mission_recommend=_build_mission_recommend(db, current_user_id, latitude, longitude),
        progress_mission=_build_progress_mission(db, current_user_id, latitude, longitude),
        guestbook_count=guestbook_counter.count_guestbooks(db),
        character_img_url=_get_character_img_url(db, current_user_id),
    )


# ---------------------------------------------------------------------
# 추천 미션
# ---------------------------------------------------------------------


def _build_mission_recommend(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> list[RecommendedMission]:
    """추천 미션 목록을 만든다. (문화/협동/보물 찾기 각 1건)"""
    return [
        _to_recommended_mission(candidate, latitude, longitude)
        for candidate in mission_recommender.recommend_missions(
            db, current_user_id, latitude, longitude
        )
    ]


def _to_recommended_mission(
    candidate: mission_recommender.RecommendableMission, latitude: float, longitude: float
) -> RecommendedMission:
    mission = candidate.mission
    location = candidate.location
    if location is None:
        # 장소가 없는 미션은 장소 관련 필드를 모두 null 로 반환한다.
        return RecommendedMission(
            mission_id=candidate.id,
            mission_type=MissionType(mission.mission_type),
            mission_title=mission.mission_title,
        )

    distance_meter = _distance_meter(latitude, longitude, location)
    return RecommendedMission(
        mission_id=candidate.id,
        mission_type=MissionType(mission.mission_type),
        mission_title=mission.mission_title,
        location_title=location.location_title,
        location=LocationPoint(lat=location.my, lng=location.mx),
        distance_meter=distance_meter,
        duration_minutes=distance.calculate_duration_minutes(distance_meter),
    )


# ---------------------------------------------------------------------
# 진행 중인 미션
# ---------------------------------------------------------------------


def _build_progress_mission(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> list[ProgressMission]:
    """진행 중인 미션 목록을 만든다. (문화 / 보물 찾기 / 협동)"""
    return [
        *_find_culture_progresses(db, current_user_id, latitude, longitude),
        *_find_treasure_progresses(db, current_user_id, latitude, longitude),
        *_find_cooperative_progresses(db, current_user_id, latitude, longitude),
    ]


def _find_culture_progresses(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> list[ProgressMission]:
    """진행 중인 문화 미션을 찾는다.

    문화 미션만 공통 단계 정보(`step_detail`) 대신 퀴즈 진행도를 단계 정보로 쓴다.
    (`quiz_total_count` → `totalStep`, `current_quiz_index` → `currentStep`)
    또한 문화 미션은 장소를 갖지 않아 장소 관련 필드가 모두 `null` 이다.
    """
    statement = (
        select(CultureMission, CultureMissionProgress.current_quiz_index)
        .select_from(CultureMissionProgress)
        .join(CultureMission, CultureMission.id == CultureMissionProgress.culture_mission_id)
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
    )
    return [
        _to_progress_mission(
            mission_id=culture_mission.id,
            mission=culture_mission.mission,
            location=None,
            total_step=culture_mission.quiz_total_count,
            current_step=current_step,
            latitude=latitude,
            longitude=longitude,
        )
        for culture_mission, current_step in db.execute(statement).all()
    ]


def _find_treasure_progresses(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> list[ProgressMission]:
    """진행 중인 보물 찾기 미션을 찾는다. 단계 정보는 공통 미션 단계 정보를 쓴다."""
    statement = (
        select(TreasureMission, TreasureMissionProgress.current_step)
        .select_from(TreasureMissionProgress)
        .join(TreasureMission, TreasureMission.id == TreasureMissionProgress.treasure_mission_id)
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
    )
    return [
        _to_progress_mission(
            mission_id=treasure_mission.id,
            mission=treasure_mission.mission,
            location=treasure_mission.location,
            total_step=treasure_mission.mission.total_step,
            current_step=current_step,
            latitude=latitude,
            longitude=longitude,
        )
        for treasure_mission, current_step in db.execute(statement).all()
    ]


def _find_cooperative_progresses(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> list[ProgressMission]:
    """진행 중인 협동 미션을 찾는다.

    협동 미션 진행도에는 `user_id` 가 없으므로 참여자를 통해 현재 사용자의 방을 찾는다.
    단계 정보는 보물 찾기와 같이 공통 미션 단계 정보를 쓴다.
    """
    statement = (
        select(CooperativeMission, CooperativeMissionProgress.current_step)
        .select_from(CooperativeMissionParticipant)
        .join(
            CooperativeMissionProgress,
            CooperativeMissionProgress.id
            == CooperativeMissionParticipant.cooperative_mission_progress_id,
        )
        .join(
            CooperativeMission,
            CooperativeMission.id == CooperativeMissionProgress.cooperative_mission_id,
        )
        .where(
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
            CooperativeMissionProgress.deleted_at.is_(None),
        )
    )
    return [
        _to_progress_mission(
            mission_id=cooperative_mission.id,
            mission=cooperative_mission.mission,
            location=cooperative_mission.location,
            total_step=cooperative_mission.mission.total_step,
            current_step=current_step,
            latitude=latitude,
            longitude=longitude,
        )
        for cooperative_mission, current_step in db.execute(statement).all()
    ]


def _to_progress_mission(
    mission_id: int,
    mission: Mission,
    location: Location | None,
    total_step: int,
    current_step: int,
    latitude: float,
    longitude: float,
) -> ProgressMission:
    if location is None:
        return ProgressMission(
            mission_id=mission_id,
            mission_type=MissionType(mission.mission_type),
            mission_title=mission.mission_title,
            total_step=total_step,
            current_step=current_step,
        )

    distance_meter = _distance_meter(latitude, longitude, location)
    return ProgressMission(
        mission_id=mission_id,
        mission_type=MissionType(mission.mission_type),
        mission_title=mission.mission_title,
        location_title=location.location_title,
        distance_meter=distance_meter,
        duration_minutes=distance.calculate_duration_minutes(distance_meter),
        total_step=total_step,
        current_step=current_step,
    )


# ---------------------------------------------------------------------
# 공통
# ---------------------------------------------------------------------


def _distance_meter(latitude: float, longitude: float, location: Location) -> int:
    """사용자 위치에서 미션 장소까지의 직선거리(m).

    LOCATION 은 `my` = 위도, `mx` = 경도로 저장한다.
    """
    return distance.calculate_distance_meter(latitude, longitude, location.my, location.mx)


def _get_character_img_url(db: Session, current_user_id: int) -> str | None:
    """사용자에게 배정된 AR 캐릭터 이미지 URL을 반환한다. 없으면 `None`."""
    user = db.get(User, current_user_id)
    if user is None or user.ar_character is None:
        return None
    return user.ar_character.character_img_url
