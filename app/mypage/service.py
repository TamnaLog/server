"""마이페이지 도메인 비즈니스 로직.

기준 문서: app/mypage/docs/API_SPEC.md, app/mypage/docs/BUSINESS_RULES.md

실제 미션 한 건은 미션 유형별 테이블(CULTURE/COOPERATIVE/TREASURE_MISSION)의 행이다.
그래서 응답의 미션 id 는 유형별 테이블의 id 이고, 유형/제목은 그 행이 속한 `MISSION` 에서 온다.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.onboarding import onboarding_matcher
from app.onboarding.schemas import OnboardingSaveRequest

from app.mypage.models import (
    AcquiredArCharacter,
    ArCharacter,
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    CultureMission,
    CultureMissionProgress,
    Location,
    Mission,
    MissionStatus,
    MissionType,
    ParticipantStatus,
    TreasureMission,
    TreasureMissionProgress,
    User,
    VisitedLocation,
)
from app.mypage.schemas import (
    AcquiredMissionResponse,
    UserProfileUpdateRequest,
    ArCharacterCollectionResponse,
    DailyStepResponse,
    MyPageResponse,
    ProfileResponse,
    ProgressMissionResponse,
    SelectedArCharacterResponse,
    SummaryResponse,
    TravelStyleResponse,
)


# 캐릭터 하나에 노출할 획득 가능 미션 개수
ACQUIRED_MISSION_LIMIT = 3


def get_mypage(db: Session, current_user_id: int) -> MyPageResponse:
    """마이페이지 첫 화면 데이터를 조회한다.

    프로필·목표 걸음 수·요약 수치·진행 중인 미션·AR 캐릭터 도감을 한 번에 내려준다.
    사용자별 데이터는 모두 토큰으로 식별한 현재 사용자 기준이고,
    도감만 전체 캐릭터를 기준으로 만들고 획득 여부를 사용자별로 판정한다.

    읽기 전용이라 아무것도 저장하지 않는다.
    """
    user = _get_user(db, current_user_id)

    return MyPageResponse(
        profile=_build_profile(user),
        daily_step=DailyStepResponse(target_step_count=user.target_step),
        summary=_build_summary(db, current_user_id, user),
        progress_missions=_find_progress_missions(db, current_user_id),
        ar_characters=_build_ar_characters(db, current_user_id),
    )


# ---------------------------------------------------------------------
# 프로필
# ---------------------------------------------------------------------


def _build_profile(user: User) -> ProfileResponse:
    """프로필을 만든다.

    여행 유형과 대표 캐릭터는 없을 수 있고, 그때는 일부만 채우지 않고 통째로 `null` 이다.
    대표 캐릭터는 `USER.ar_character_id` 로만 정한다. 획득 여부는 도감에서 따로 판정한다.
    """
    travel_style = user.user_travel_style
    ar_character = user.ar_character

    return ProfileResponse(
        nickname=user.nickname,
        travel_style=(
            TravelStyleResponse(
                user_type=travel_style.user_type, hashtags=travel_style.hashtags
            )
            if travel_style is not None
            else None
        ),
        selected_ar_character=(
            SelectedArCharacterResponse(
                id=ar_character.id,
                name=ar_character.character_name,
                image_url=ar_character.character_img_url,
            )
            if ar_character is not None
            else None
        ),
    )


# ---------------------------------------------------------------------
# 요약 수치
# ---------------------------------------------------------------------


def _build_summary(db: Session, current_user_id: int, user: User) -> SummaryResponse:
    """요약 수치를 만든다. 포인트는 집계하지 않고 `USER.point` 를 그대로 쓴다."""
    return SummaryResponse(
        visited_location_count=_count_visited_locations(db, current_user_id),
        completed_mission_count=_count_completed_missions(db, current_user_id),
        point=user.point,
    )


def _count_visited_locations(db: Session, current_user_id: int) -> int:
    """방문한 장소 수. 같은 장소를 여러 번 방문해도 한 곳으로 센다."""
    count = db.scalar(
        select(func.count(distinct(VisitedLocation.location_id))).where(
            VisitedLocation.user_id == current_user_id
        )
    )
    return count or 0


def _count_completed_missions(db: Session, current_user_id: int) -> int:
    """완료한 미션 수. 세 유형의 완료 진행도를 합산한다."""
    culture = db.scalar(
        select(func.count())
        .select_from(CultureMissionProgress)
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
        )
    )
    treasure = db.scalar(
        select(func.count())
        .select_from(TreasureMissionProgress)
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
        )
    )
    # 협동 미션 진행도에는 user_id 가 없어서 참가 행으로 현재 사용자를 찾는다.
    # 나갔거나(삭제된 참가) 아직 수락되지 않은 참가, 삭제된 방은 세지 않는다.
    cooperative = db.scalar(
        select(func.count())
        .select_from(CooperativeMissionParticipant)
        .join(
            CooperativeMissionProgress,
            CooperativeMissionProgress.id
            == CooperativeMissionParticipant.cooperative_mission_progress_id,
        )
        .where(
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeMissionProgress.mission_status == MissionStatus.COMPLETED.value,
            CooperativeMissionProgress.deleted_at.is_(None),
        )
    )
    return (culture or 0) + (treasure or 0) + (cooperative or 0)


# ---------------------------------------------------------------------
# 진행 중인 미션
# ---------------------------------------------------------------------


def _find_progress_missions(
    db: Session, current_user_id: int
) -> list[ProgressMissionResponse]:
    """진행 중인 미션 목록. 유형마다 진행 수의 의미가 다르다."""
    return [
        *_find_culture_progresses(db, current_user_id),
        *_find_treasure_progresses(db, current_user_id),
        *_find_cooperative_progresses(db, current_user_id),
    ]


def _find_culture_progresses(
    db: Session, current_user_id: int
) -> list[ProgressMissionResponse]:
    """진행 중인 문화 미션. 진행 수는 퀴즈 번호와 전체 퀴즈 수다."""
    statement = (
        select(CultureMission, CultureMissionProgress.current_quiz_index)
        .select_from(CultureMissionProgress)
        .join(
            CultureMission,
            CultureMission.id == CultureMissionProgress.culture_mission_id,
        )
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
    )
    return [
        _to_progress_mission(
            mission_id=culture_mission.id,
            mission=culture_mission.mission,
            current_count=current_quiz_index,
            total_count=culture_mission.quiz_total_count,
        )
        for culture_mission, current_quiz_index in db.execute(statement).all()
    ]


def _find_treasure_progresses(
    db: Session, current_user_id: int
) -> list[ProgressMissionResponse]:
    """진행 중인 보물 찾기 미션. 진행 수는 찾은 보물 개수와 전체 보물 수다.

    현재 진행 수는 단계(`current_step`)가 아니라 **찾은 보물 목록의 길이**다.
    """
    statement = (
        select(TreasureMission, TreasureMissionProgress.current_found_item_idx)
        .select_from(TreasureMissionProgress)
        .join(
            TreasureMission,
            TreasureMission.id == TreasureMissionProgress.treasure_mission_id,
        )
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
    )
    return [
        _to_progress_mission(
            mission_id=treasure_mission.id,
            mission=treasure_mission.mission,
            current_count=len(found_item_idx or []),
            total_count=treasure_mission.item_total_count,
        )
        for treasure_mission, found_item_idx in db.execute(statement).all()
    ]


def _find_cooperative_progresses(
    db: Session, current_user_id: int
) -> list[ProgressMissionResponse]:
    """진행 중인 협동 미션. 진행 수는 현재 단계와 공통 미션의 전체 단계 수다.

    완료 집계와 같은 조건으로 현재 사용자의 방을 찾는다.
    (삭제되지 않은 `ACCEPTED` 참가 행 + 삭제되지 않은 진행도)
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
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
            CooperativeMissionProgress.deleted_at.is_(None),
        )
    )
    return [
        _to_progress_mission(
            mission_id=cooperative_mission.id,
            mission=cooperative_mission.mission,
            current_count=current_step,
            total_count=cooperative_mission.mission.total_step,
        )
        for cooperative_mission, current_step in db.execute(statement).all()
    ]


def _to_progress_mission(
    *, mission_id: int, mission: Mission, current_count: int, total_count: int
) -> ProgressMissionResponse:
    return ProgressMissionResponse(
        mission_id=mission_id,
        mission_type=MissionType(mission.mission_type),
        mission_title=mission.mission_title,
        current_count=current_count,
        total_count=total_count,
    )


# ---------------------------------------------------------------------
# AR 캐릭터 도감
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class _RewardMission:
    """캐릭터를 보상으로 주는 미션 한 건.

    `mission_id` 는 정렬 기준인 공통 `MISSION.id`, `id` 는 응답에 나가는 세부 미션 id 다.
    """

    mission_id: int
    id: int
    mission_type: MissionType
    mission_title: str


def _build_ar_characters(
    db: Session, current_user_id: int
) -> list[ArCharacterCollectionResponse]:
    """도감을 만든다. 획득 여부와 관계없이 전체 캐릭터를 담는다.

    캐릭터마다 다시 조회하지 않도록 획득 이력·보상 미션·획득 장소를 먼저 한 번씩만
    모아 두고 맞춘다. (N+1 방지)
    """
    characters = db.scalars(select(ArCharacter).order_by(ArCharacter.id)).all()
    acquired = _find_acquired(db, current_user_id)
    reward_missions = _find_reward_missions(db)
    location_titles = _find_mission_location_titles(db)

    return [
        _to_collection_response(
            character=character,
            acquired=acquired.get(character.id),
            reward_missions=reward_missions.get(character.id, []),
            location_titles=location_titles,
        )
        for character in characters
    ]


def _to_collection_response(
    *,
    character: ArCharacter,
    acquired: AcquiredArCharacter | None,
    reward_missions: list[_RewardMission],
    location_titles: dict[int, str],
) -> ArCharacterCollectionResponse:
    """도감 한 칸을 만든다.

    미획득이면 획득 날짜·장소만 `null` 이고 나머지 정보는 획득한 캐릭터와 똑같이 준다.
    획득했어도 장소가 없는 미션(문화 미션)으로 받았으면 장소는 `null` 이다.
    """
    return ArCharacterCollectionResponse(
        id=character.id,
        name=character.character_name,
        image_url=character.character_img_url,
        is_acquired=acquired is not None,
        acquired_at=_to_acquired_date(acquired),
        acquired_location=(
            location_titles.get(acquired.acquired_mission_id)
            if acquired is not None
            else None
        ),
        story_title=character.character_story_title,
        story_content=character.character_description,
        hashtags=character.hashtags,
        acquire_condition=character.acquire_condition,
        acquired_missions=[
            AcquiredMissionResponse(
                id=reward_mission.id,
                mission_type=reward_mission.mission_type,
                mission_title=reward_mission.mission_title,
            )
            # 공통 MISSION.id 오름차순으로 정렬한 뒤 앞에서부터 최대 3개만 쓴다.
            for reward_mission in reward_missions[:ACQUIRED_MISSION_LIMIT]
        ],
    )


def _to_acquired_date(acquired: AcquiredArCharacter | None) -> date | None:
    """획득 날짜. 미획득이면 `None`.

    획득 시각(`created_at`)은 KST 로 저장돼 있으므로 변환 없이 날짜만 잘라 쓴다.
    """
    if acquired is None:
        return None
    return acquired.created_at.date()


def _find_acquired(
    db: Session, current_user_id: int
) -> dict[int, AcquiredArCharacter]:
    """현재 사용자의 캐릭터 획득 이력. `캐릭터 id → 획득 기록`.

    `(user_id, ar_character_id)` 가 유니크라 캐릭터당 한 건이다.
    """
    statement = select(AcquiredArCharacter).where(
        AcquiredArCharacter.user_id == current_user_id
    )
    return {acquired.ar_character_id: acquired for acquired in db.scalars(statement).all()}


def _find_reward_missions(db: Session) -> dict[int, list[_RewardMission]]:
    """캐릭터를 보상으로 주는 미션. `캐릭터 id → 미션 목록(공통 MISSION.id 오름차순)`.

    보상 설정은 세 유형별 테이블의 `reward_detail.ar_character_id` 에 들어 있다.
    JSON 컬럼 조건은 DB 마다 문법이 달라서, 미션 수가 많지 않은 지금은
    세 테이블을 한 번씩 읽어 파이썬에서 묶는다.
    """
    reward_missions: dict[int, list[_RewardMission]] = {}

    for model in (CultureMission, TreasureMission, CooperativeMission):
        for mission in db.scalars(select(model)).all():
            ar_character_id = (mission.reward_detail or {}).get("ar_character_id")
            if not ar_character_id:
                continue

            reward_missions.setdefault(ar_character_id, []).append(
                _RewardMission(
                    mission_id=mission.mission_id,
                    id=mission.id,
                    mission_type=MissionType(mission.mission.mission_type),
                    mission_title=mission.mission.mission_title,
                )
            )

    for missions in reward_missions.values():
        missions.sort(key=lambda reward_mission: reward_mission.mission_id)
    return reward_missions


def _find_mission_location_titles(db: Session) -> dict[int, str]:
    """공통 `MISSION.id → 장소 이름`.

    캐릭터 획득 기록은 공통 `MISSION.id` 만 가지고 있어서, 장소를 알려면 유형별 미션을
    거쳐야 한다. 문화 미션은 장소가 없으므로 이 표에도 들어가지 않는다. (→ 장소 `null`)
    """
    location_titles: dict[int, str] = {}

    for model in (TreasureMission, CooperativeMission):
        statement = (
            select(model.mission_id, Location.location_title)
            .join(Location, Location.id == model.location_id)
            .order_by(model.id)
        )
        for mission_id, location_title in db.execute(statement).all():
            # 같은 공통 미션에 세부 미션이 여러 개면 id 가 작은 쪽 장소를 쓴다.
            location_titles.setdefault(mission_id, location_title)

    return location_titles


# ---------------------------------------------------------------------
# 사용자 정보 변경
# ---------------------------------------------------------------------


def update_user_info(
    db: Session, current_user_id: int, request: UserProfileUpdateRequest
) -> None:
    """사용자 프로필을 요청값으로 통째로 교체한다.

    선택값이 바뀌면 여행 유형과 대표 캐릭터도 다시 배정한다. 배정 규칙은 온보딩과 같아야 하므로
    마이페이지에 옮겨 적지 않고 `app/onboarding/onboarding_matcher.py` 를 그대로 쓴다.
    (지금은 임시 랜덤 배정이라 같은 값으로 다시 저장해도 결과가 달라질 수 있다)

    선택 배열은 요청값을 그대로 저장한다. 빈 배열도 `NULL` 로 바꾸지 않고 빈 배열로 둔다.

    필드 갱신과 재배정은 한 트랜잭션이고, 중간에 실패하면 전부 롤백된다.
    """
    user = _get_user(db, current_user_id)

    user.nickname = request.nickname
    user.expectation = [category.value for category in request.categories]
    user.transportation = [value.value for value in request.transportation]
    user.travel_style = [value.value for value in request.travel_style]
    user.target_step = request.target_step_count

    _reassign(db, user, request)
    db.commit()


def _get_user(db: Session, current_user_id: int) -> User:
    """현재 사용자를 조회한다.

    인증에서 이미 확인한 사용자라 없을 수 없지만, 조용히 넘기지 않도록 확인한다.
    """
    user = db.get(User, current_user_id)
    if user is None:
        raise RuntimeError(f"현재 사용자 {current_user_id} 를 찾을 수 없습니다.")
    return user


def _reassign(db: Session, user: User, request: UserProfileUpdateRequest) -> None:
    """바뀐 선택값으로 여행 유형과 대표 캐릭터를 다시 배정한다.

    세 선택 배열이 모두 비어 있으면 온보딩 건너뛰기와 같게 여행 유형은 비우고
    기본 캐릭터를 배정한다. 일부만 비어 있으면 빈 배열을 포함한 전체 선택값으로 배정한다.

    대표 캐릭터만 바꾸고 `ACQUIRED_AR_CHARACTER` 는 만들지도 지우지도 않는다.
    (도감의 획득 이력은 이 API 로 달라지지 않는다)
    """
    # 매칭 모듈이 온보딩 요청 형태를 받으므로 선택값만 담아 그대로 넘긴다.
    onboarding_request = OnboardingSaveRequest(
        categories=request.categories,
        transportation=request.transportation,
        travel_style=request.travel_style,
    )

    if onboarding_request.is_skipped:
        user.user_travel_style_id = None
        ar_character = onboarding_matcher.get_default_ar_character(db)
    else:
        user.user_travel_style_id = onboarding_matcher.assign_travel_style(
            db, onboarding_request
        ).id
        ar_character = onboarding_matcher.assign_ar_character(db, onboarding_request)

    user.ar_character_id = ar_character.id
