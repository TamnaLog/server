"""홈 도메인 비즈니스 로직.

기준 문서: app/home/docs/API_SPEC.md, app/home/docs/BUSINESS_RULES.md
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.home import distance, guestbook_counter, mission_recommender
from app.home.models import (
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    CultureMission,
    CultureMissionProgress,
    Mission,
    MissionStatus,
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
        mission_recommend=_build_mission_recommend(db, latitude, longitude),
        progress_mission=_build_progress_mission(db, current_user_id, latitude, longitude),
        guestbook_count=guestbook_counter.count_guestbooks(db),
        character_img_url=_get_character_img_url(db, current_user_id),
    )


def _build_mission_recommend(
    db: Session, latitude: float, longitude: float
) -> list[RecommendedMission]:
    """추천 미션 목록을 만든다."""
    missions = mission_recommender.recommend_missions(db)
    return [_to_recommended_mission(mission, latitude, longitude) for mission in missions]


def _to_recommended_mission(
    mission: Mission, latitude: float, longitude: float
) -> RecommendedMission:
    location = mission.location
    if location is None:
        # 장소가 없는 미션은 장소 관련 필드를 모두 null 로 반환한다.
        return RecommendedMission(
            mission_id=mission.id,
            mission_type=MissionType(mission.mission_type),
            mission_title=mission.mission_title,
        )

    distance_meter = distance.calculate_distance_meter(latitude, longitude, location.my, location.mx)
    return RecommendedMission(
        mission_id=mission.id,
        mission_type=MissionType(mission.mission_type),
        mission_title=mission.mission_title,
        location_title=location.location_title,
        location=LocationPoint(lat=location.my, lng=location.mx),
        distance_meter=distance_meter,
        duration_minutes=distance.calculate_duration_minutes(distance_meter),
    )


def _build_progress_mission(
    db: Session, current_user_id: int, latitude: float, longitude: float
) -> list[ProgressMission]:
    """진행 중인 미션 목록을 만든다. (문화 / 보물 찾기 / 협동)"""
    progresses = [
        *_find_culture_progresses(db, current_user_id),
        *_find_treasure_progresses(db, current_user_id),
        *_find_cooperative_progresses(db, current_user_id),
    ]
    return [
        _to_progress_mission(mission, total_step, current_step, latitude, longitude)
        for mission, total_step, current_step in progresses
    ]


def _find_culture_progresses(
    db: Session, current_user_id: int
) -> list[tuple[Mission, int, int]]:
    """진행 중인 문화 미션을 찾는다.

    문화 미션만 공통 단계 정보(`step_detail`) 대신 퀴즈 진행도를 단계 정보로 쓴다.
    (`quiz_total_count` → `totalStep`, `current_quiz_index` → `currentStep`)
    """
    # CULTURE_MISSION_PROGRESS.culture_mission_id 는 CULTURE_MISSION.mission_id,
    # 즉 MISSION.id 와 같은 값이다. (MISSION 과 1:1 서브타입)
    statement = (
        select(
            Mission,
            CultureMission.quiz_total_count,
            CultureMissionProgress.current_quiz_index,
        )
        .select_from(CultureMissionProgress)
        .join(
            CultureMission,
            CultureMission.mission_id == CultureMissionProgress.culture_mission_id,
        )
        .join(Mission, Mission.id == CultureMissionProgress.culture_mission_id)
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
    )
    return [
        (mission, total_step, current_step)
        for mission, total_step, current_step in db.execute(statement).all()
    ]


def _find_treasure_progresses(
    db: Session, current_user_id: int
) -> list[tuple[Mission, int, int]]:
    """진행 중인 보물 찾기 미션을 찾는다. 단계 정보는 공통 미션 단계 정보를 쓴다."""
    statement = (
        select(Mission, TreasureMissionProgress.current_step)
        .select_from(TreasureMissionProgress)
        .join(Mission, Mission.id == TreasureMissionProgress.treasure_mission_id)
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
    )
    return [
        (mission, mission.total_step, current_step)
        for mission, current_step in db.execute(statement).all()
    ]


def _find_cooperative_progresses(
    db: Session, current_user_id: int
) -> list[tuple[Mission, int, int]]:
    """진행 중인 협동 미션을 찾는다.

    협동 미션 진행도에는 `user_id` 가 없으므로 참여자를 통해 현재 사용자의 방을 찾는다.
    단계 정보는 보물 찾기와 같이 공통 미션 단계 정보를 쓴다.
    """
    statement = (
        select(Mission, CooperativeMissionProgress.current_step)
        .select_from(CooperativeMissionParticipant)
        .join(
            CooperativeMissionProgress,
            CooperativeMissionProgress.id
            == CooperativeMissionParticipant.cooperative_mission_progress_id,
        )
        .join(Mission, Mission.id == CooperativeMissionProgress.cooperative_mission_id)
        .where(
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
    )
    return [
        (mission, mission.total_step, current_step)
        for mission, current_step in db.execute(statement).all()
    ]


def _to_progress_mission(
    mission: Mission,
    total_step: int,
    current_step: int,
    latitude: float,
    longitude: float,
) -> ProgressMission:
    location = mission.location
    if location is None:
        return ProgressMission(
            mission_id=mission.id,
            mission_type=MissionType(mission.mission_type),
            mission_title=mission.mission_title,
            total_step=total_step,
            current_step=current_step,
        )

    distance_meter = distance.calculate_distance_meter(latitude, longitude, location.my, location.mx)
    return ProgressMission(
        mission_id=mission.id,
        mission_type=MissionType(mission.mission_type),
        mission_title=mission.mission_title,
        location_title=location.location_title,
        distance_meter=distance_meter,
        duration_minutes=distance.calculate_duration_minutes(distance_meter),
        total_step=total_step,
        current_step=current_step,
    )


def _get_character_img_url(db: Session, current_user_id: int) -> str | None:
    """사용자에게 배정된 AR 캐릭터 이미지 URL을 반환한다. 없으면 `None`."""
    user = db.get(User, current_user_id)
    if user is None or user.ar_character is None:
        return None
    return user.ar_character.character_img_url
