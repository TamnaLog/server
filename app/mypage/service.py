"""마이페이지 도메인 비즈니스 로직.

기준 문서: app/mypage/docs/API_SPEC.md, app/mypage/docs/BUSINESS_RULES.md

실제 미션 한 건은 미션 유형별 테이블(CULTURE/COOPERATIVE/TREASURE_MISSION)의 행이다.
그래서 응답의 미션 id 는 유형별 테이블의 id 이고, 유형/제목은 그 행이 속한 `MISSION` 에서 온다.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import ColumnElement, distinct, func, select
from sqlalchemy.orm import Mapped, Session

from app.common import images, rewards
from app.common.rewards import GrantedRewards
from app.core.errors import ConflictError, InvalidRequestError
from app.mission import reward_history
from app.mypage import travel_ending_image_generator
from app.mypage.constants import (
    AR_CHARACTER_COLLECTION_MAX_ID,
    AR_CHARACTER_COLLECTION_MIN_ID,
    TRAVEL_ENDING_CREATION_POINT_COST,
)
from app.mypage.travel_ending_image_generator import SourceType, TravelEndingSource
from app.onboarding import onboarding_matcher
from app.onboarding.schemas import OnboardingSaveRequest
from app.services import blob_storage, kto

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
    TravelEndingContent,
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
    TravelEndingCompletedMissionResponse,
    TravelEndingContentCreateRequest,
    TravelEndingContentCreateResponse,
    TravelEndingElementsResponse,
    TravelEndingMissionRequest,
    TravelEndingVisitedLocationResponse,
    TravelStyleResponse,
    UserInfoResponse,
)


logger = logging.getLogger(__name__)

# 캐릭터 하나에 노출할 획득 가능 미션 개수
ACQUIRED_MISSION_LIMIT = 3

# 엽서 이미지는 항상 PNG 로 생성해 저장한다.
PNG_CONTENT_TYPE = images.ImageFormat.PNG.content_type
PNG_EXTENSION = images.ImageFormat.PNG.extension


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
    도감의 id 1~6 제한은 대표 캐릭터에는 적용하지 않는다.
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
                character_color=ar_character.character_color,
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


def _in_collection_range(column: Mapped[int]) -> ColumnElement[bool]:
    """도감에 넣을 캐릭터 id 범위 조건. (`BETWEEN 1 AND 6`)"""
    return column.between(AR_CHARACTER_COLLECTION_MIN_ID, AR_CHARACTER_COLLECTION_MAX_ID)


def _is_in_collection_range(ar_character_id: int) -> bool:
    """도감에 넣을 캐릭터 id 인지 판단한다."""
    return AR_CHARACTER_COLLECTION_MIN_ID <= ar_character_id <= AR_CHARACTER_COLLECTION_MAX_ID


def _build_ar_characters(
    db: Session, current_user_id: int
) -> list[ArCharacterCollectionResponse]:
    """도감을 만든다. 획득 여부와 관계없이 id 1~6 캐릭터를 담는다.

    범위 밖 캐릭터는 획득했거나 미션 보상으로 설정돼 있어도 도감에 넣지 않는다.
    캐릭터마다 다시 조회하지 않도록 획득 이력·보상 미션·획득 장소를 먼저 한 번씩만
    모아 두고 맞춘다. (N+1 방지)
    """
    characters = db.scalars(
        select(ArCharacter)
        .where(_in_collection_range(ArCharacter.id))
        .order_by(ArCharacter.id)
    ).all()
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
    획득했어도 장소가 없는 미션(문화 미션)이거나 획득 출처가 없으면 장소는 `null` 이다.
    """
    return ArCharacterCollectionResponse(
        id=character.id,
        name=character.character_name,
        image_url=character.character_img_url,
        character_color=character.character_color,
        is_acquired=acquired is not None,
        acquired_at=_to_acquired_date(acquired),
        acquired_location=_to_acquired_location(acquired, location_titles),
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


def _to_acquired_location(
    acquired: AcquiredArCharacter | None, location_titles: dict[int, str]
) -> str | None:
    """획득 장소. 미획득이거나 장소를 확인할 수 없으면 `None`.

    획득 출처가 없는 기록(`acquired_mission_id` 가 `NULL`)은 연결할 미션이 없으므로
    장소도 `None` 이다. (예: 걸음 수 목표 달성 보상, 출처 미션이 삭제된 기록)
    """
    if acquired is None or acquired.acquired_mission_id is None:
        return None
    return location_titles.get(acquired.acquired_mission_id)


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
    도감에 넣을 id 1~6 캐릭터의 이력만 읽는다.
    """
    statement = select(AcquiredArCharacter).where(
        AcquiredArCharacter.user_id == current_user_id,
        _in_collection_range(AcquiredArCharacter.ar_character_id),
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
            # 도감에 없는 캐릭터(id 1~6 밖)의 보상 미션은 조합하지 않는다.
            if not ar_character_id or not _is_in_collection_range(ar_character_id):
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
# 사용자 정보 조회
# ---------------------------------------------------------------------


def get_user_info(db: Session, current_user_id: int) -> UserInfoResponse:
    """프로필 수정 화면에 채울 현재 사용자 정보를 조회한다.

    여행 유형과 대표 캐릭터는 `USER` 의 nullable FK 라서 연결이 없으면 그 값만 `null` 이다.
    두 관계는 `User` 의 `lazy="joined"` 관계로 함께 읽어 추가 쿼리를 만들지 않는다.

    선택값 세 컬럼은 저장된 값을 그대로 내려준다. `NULL`(설정 전)과 `[]`(아무것도 선택 안 함)을
    구분해야 해서 한쪽을 다른 쪽으로 바꾸지 않고, 정렬이나 중복 제거도 하지 않는다.

    대표 캐릭터의 선택 상태와 획득 여부는 다른 개념이라 `ACQUIRED_AR_CHARACTER` 는 보지 않는다.

    읽기 전용이라 아무것도 저장하지 않는다.
    """
    user = _get_user(db, current_user_id)
    travel_style = user.user_travel_style
    ar_character = user.ar_character

    return UserInfoResponse(
        user_type=travel_style.user_type if travel_style is not None else None,
        ar_character_image_url=(
            ar_character.character_img_url if ar_character is not None else None
        ),
        nickname=user.nickname,
        # `USER.expectation` 을 API 에서는 `categories` 로 쓴다.
        categories=user.expectation,
        transportation=user.transportation,
        travel_style=user.travel_style,
        target_step_count=user.target_step,
    )


# ---------------------------------------------------------------------
# 여행 마무리 엽서 요소 조회
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class _CompletedMission:
    """완료한 미션 한 건. 중복 제거와 정렬을 마친 뒤 응답으로 바꾼다.

    `id` 는 응답에 나가는 유형별 세부 미션 id 다.
    """

    mission_type: MissionType
    id: int
    mission_title: str
    completed_location: str | None
    completed_at: datetime
    reward_detail: dict[str, Any] | None


@dataclass(frozen=True)
class _CompletedMissionSource:
    """엽서에 넣을 완료 미션 하나. (프롬프트 재료를 만들 때 쓴다)"""

    mission_type: MissionType
    id: int
    mission_title: str
    location_title: str | None


def get_travel_ending_elements(
    db: Session, current_user_id: int
) -> TravelEndingElementsResponse:
    """여행 마무리 엽서에 넣을 요소를 조회한다.

    포인트는 합산하지 않고 조회 시점의 `USER.point` 를 그대로 쓴다.
    두 count 는 따로 집계하지 않고 최종 목록의 길이를 쓴다. (목록과 수가 어긋나지 않게)
    사진은 이 API 가 다루지 않으므로 사진 테이블을 조회하지 않는다.

    읽기 전용이라 아무것도 저장하지 않는다.
    """
    user = _get_user(db, current_user_id)
    visited_locations = _find_ending_visited_locations(db, current_user_id)
    completed_missions = _find_ending_completed_missions(db, current_user_id)

    return TravelEndingElementsResponse(
        point=user.point,
        visited_location_count=len(visited_locations),
        visited_locations=visited_locations,
        completed_mission_count=len(completed_missions),
        completed_missions=completed_missions,
    )


def _find_ending_visited_locations(
    db: Session, current_user_id: int
) -> list[TravelEndingVisitedLocationResponse]:
    """방문 장소 목록. 같은 장소는 한 번만 넣고 최근 방문 순으로 정렬한다.

    같은 장소의 방문 기록이 여러 건이면 그중 가장 최근 방문 시각을 정렬 기준으로 쓴다.
    최근 시각까지 같으면 `LOCATION.id` 내림차순으로 순서를 고정한다.
    """
    latest_visited_at = func.max(VisitedLocation.visited_at)
    statement = (
        select(Location.id, Location.location_title)
        .select_from(VisitedLocation)
        .join(Location, Location.id == VisitedLocation.location_id)
        .where(VisitedLocation.user_id == current_user_id)
        .group_by(Location.id, Location.location_title)
        .order_by(latest_visited_at.desc(), Location.id.desc())
    )
    return [
        TravelEndingVisitedLocationResponse(id=location_id, location_title=location_title)
        for location_id, location_title in db.execute(statement).all()
    ]


def _find_ending_completed_missions(
    db: Session, current_user_id: int
) -> list[TravelEndingCompletedMissionResponse]:
    """완료 미션 목록. 중단으로 완료 처리된 진행도도 포함한다.

    같은 미션을 여러 번 완료했으면 가장 최근 완료 진행도 하나만 남기고,
    완료 시각 내림차순(같으면 유형명 → 세부 미션 id 오름차순)으로 정렬한다.
    """
    completed = [
        *_find_completed_culture_missions(db, current_user_id),
        *_find_completed_treasure_missions(db, current_user_id),
        *_find_completed_cooperative_missions(db, current_user_id),
    ]
    missions = _pick_latest_completions(completed)

    # 보상 수령 여부는 고른 완료 진행도 하나가 아니라 그 미션의 전체 진행도 이력을 봐야 한다.
    # 미션마다 다시 조회하지 않도록 유형별로 한 번에 모아 둔다. (N+1 방지)
    granted = {
        mission_type: reward_history.get_granted_rewards_map(
            db,
            mission_type,
            [mission.id for mission in missions if mission.mission_type is mission_type],
            current_user_id,
        )
        for mission_type in MissionType
    }

    # 공용 보상 변환은 캐릭터를 id 로 하나씩 조회한다. 필요한 캐릭터를 먼저 한 번에 읽어
    # 세션에 올려 두면 그 조회가 DB 까지 가지 않는다. (미션 수만큼 쿼리가 늘지 않게)
    # 세션의 identity map 은 약한 참조라서, 아래에서 쓰지 않아도 이 지역 변수로 목록을
    # 함수가 끝날 때까지 들고 있어야 읽어 둔 캐릭터가 사라지지 않는다.
    reward_characters = _preload_reward_characters(db, missions)  # noqa: F841

    return [
        TravelEndingCompletedMissionResponse(
            mission_id=mission.id,
            mission_type=mission.mission_type,
            mission_title=mission.mission_title,
            completed_location=mission.completed_location,
            completed_at=mission.completed_at,
            reward_detail=rewards.to_full_reward_detail(
                db,
                mission.reward_detail,
                granted[mission.mission_type].get(mission.id, GrantedRewards()),
            ),
        )
        for mission in missions
    ]


def _preload_reward_characters(
    db: Session, missions: list[_CompletedMission]
) -> list[ArCharacter]:
    """완료 미션들의 보상 캐릭터를 한 번에 읽어 세션에 올린다."""
    character_ids = {
        (mission.reward_detail or {}).get("ar_character_id") for mission in missions
    }
    character_ids.discard(None)
    if not character_ids:
        return []

    statement = select(ArCharacter).where(ArCharacter.id.in_(character_ids))
    return list(db.scalars(statement).all())


def _pick_latest_completions(completed: list[_CompletedMission]) -> list[_CompletedMission]:
    """같은 미션의 완료 기록이 여러 건이면 가장 최근 것만 남기고 정렬한다.

    중복 기준은 `(미션 유형, 유형별 세부 미션 id)` 다. (유형이 다르면 id 가 같아도 다른 미션)
    """
    latest: dict[tuple[MissionType, int], _CompletedMission] = {}
    for mission in completed:
        key = (mission.mission_type, mission.id)
        before = latest.get(key)
        if before is None or mission.completed_at > before.completed_at:
            latest[key] = mission

    missions = sorted(
        latest.values(), key=lambda mission: (mission.mission_type.value, mission.id)
    )
    # 완료 시각이 같으면 위에서 만든 순서(유형명 → 세부 미션 id)가 그대로 유지된다.
    missions.sort(key=lambda mission: mission.completed_at, reverse=True)
    return missions


def _find_completed_culture_missions(
    db: Session, current_user_id: int
) -> list[_CompletedMission]:
    """완료한 문화 미션. 장소를 갖지 않는 유형이라 완료 장소는 항상 `None` 이다."""
    statement = (
        select(CultureMission, CultureMissionProgress.completed_at)
        .select_from(CultureMissionProgress)
        .join(
            CultureMission,
            CultureMission.id == CultureMissionProgress.culture_mission_id,
        )
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
            # 완료 처리는 완료 시각을 항상 채우지만, 응답 필드가 null 이 아니라서 한 번 더 건다.
            CultureMissionProgress.completed_at.is_not(None),
        )
    )
    return [
        _CompletedMission(
            mission_type=MissionType(culture_mission.mission.mission_type),
            id=culture_mission.id,
            mission_title=culture_mission.mission.mission_title,
            completed_location=None,
            completed_at=completed_at,
            reward_detail=culture_mission.reward_detail,
        )
        for culture_mission, completed_at in db.execute(statement).all()
    ]


def _find_completed_treasure_missions(
    db: Session, current_user_id: int
) -> list[_CompletedMission]:
    """완료한 보물 찾기 미션. 완료 장소는 미션에 연결된 장소다."""
    statement = (
        select(
            TreasureMission,
            Location.location_title,
            TreasureMissionProgress.completed_at,
        )
        .select_from(TreasureMissionProgress)
        .join(
            TreasureMission,
            TreasureMission.id == TreasureMissionProgress.treasure_mission_id,
        )
        .join(Location, Location.id == TreasureMission.location_id)
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
            TreasureMissionProgress.completed_at.is_not(None),
        )
    )
    return [
        _CompletedMission(
            mission_type=MissionType(treasure_mission.mission.mission_type),
            id=treasure_mission.id,
            mission_title=treasure_mission.mission.mission_title,
            completed_location=location_title,
            completed_at=completed_at,
            reward_detail=treasure_mission.reward_detail,
        )
        for treasure_mission, location_title, completed_at in db.execute(statement).all()
    ]


def _find_completed_cooperative_missions(
    db: Session, current_user_id: int
) -> list[_CompletedMission]:
    """완료한 협동 미션.

    완료 수 집계와 같은 조건으로 현재 사용자의 방을 찾는다.
    (삭제되지 않은 `ACCEPTED` 참가 행 + 삭제되지 않은 진행도)
    """
    statement = (
        select(
            CooperativeMission,
            Location.location_title,
            CooperativeMissionProgress.completed_at,
        )
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
        .join(Location, Location.id == CooperativeMission.location_id)
        .where(
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeMissionProgress.mission_status == MissionStatus.COMPLETED.value,
            CooperativeMissionProgress.deleted_at.is_(None),
            CooperativeMissionProgress.completed_at.is_not(None),
        )
    )
    return [
        _CompletedMission(
            mission_type=MissionType(cooperative_mission.mission.mission_type),
            id=cooperative_mission.id,
            mission_title=cooperative_mission.mission.mission_title,
            completed_location=location_title,
            completed_at=completed_at,
            reward_detail=cooperative_mission.reward_detail,
        )
        for cooperative_mission, location_title, completed_at in db.execute(statement).all()
    ]


# ---------------------------------------------------------------------
# 여행 마무리 엽서 저장
# ---------------------------------------------------------------------


INSUFFICIENT_POINT = "INSUFFICIENT_POINT"

# Blob 저장 경로의 최상위 prefix. 그 아래를 사용자 id 로 나눈다.
TRAVEL_ENDING_BLOB_PREFIX = "travel-ending"


def create_travel_ending_content(
    db: Session, current_user_id: int, request: TravelEndingContentCreateRequest
) -> TravelEndingContentCreateResponse:
    """여행 마무리 엽서를 만들어 저장한다.

    검증 → 포인트 확인 → 재료 조합 → 이미지 생성 → Blob 업로드 → 포인트 차감/행 생성 순서다.
    어느 하나라도 잘못되면 유효한 항목만 골라 만드는 부분 성공 없이 전체를 실패시킨다.

    비싼 작업(OpenAI / TourAPI / Blob)은 형식 검증과 포인트 확인을 모두 통과한 뒤에 시작한다.
    같은 입력을 다시 보내도 기존 행을 갱신하지 않고 매번 새로 만들고 포인트를 다시 차감한다.
    """
    # 1. 사진 내용 검증. (형식·크기가 잘못되면 여기서 400 이고 외부 호출은 하지 않는다)
    photos = [images.read_and_detect(photo.file) for photo in request.photos]

    # 2. 포인트 확인. 부족하면 OpenAI/TourAPI 호출과 Blob 생성 없이 끝낸다.
    user = _get_user(db, current_user_id)
    _check_point(user)

    # 3. 현재 사용자의 방문 장소 / 완료 미션인지 확인하고 프롬프트 재료를 만든다.
    locations = _get_visited_locations(db, current_user_id, request.visited_location_ids)
    missions = _get_completed_missions(db, current_user_id, request.missions)

    sources = [
        *(_to_location_source(location) for location in locations),
        *(_to_mission_source(db, mission) for mission in missions),
        *(
            travel_ending_image_generator.TravelEndingSource(
                source_type=travel_ending_image_generator.SourceType.USER_PHOTO,
                image_data=data,
            )
            for data, _ in photos
        ),
    ]

    # 4. 이미지 생성. 실패하면 예외가 올라가고 Blob·DB·포인트는 그대로다.
    image = travel_ending_image_generator.generate_travel_ending_image(
        sources, request.travel_note
    )

    # 5. 생성된 PNG 만 Blob 에 올린다. (사용자 원본 사진과 외부 대표 이미지는 저장하지 않는다)
    image_url = blob_storage.upload_file(
        image,
        prefix=f"{TRAVEL_ENDING_BLOB_PREFIX}/{current_user_id}",
        content_type=PNG_CONTENT_TYPE,
        extension=PNG_EXTENSION,
    )

    return _save_travel_ending_content(db, current_user_id, image_url)


def _check_point(user: User) -> None:
    """엽서를 만들 포인트가 있는지 확인한다. 부족하면 409."""
    if user.point < TRAVEL_ENDING_CREATION_POINT_COST:
        raise ConflictError(
            INSUFFICIENT_POINT,
            detail=(
                f"엽서 생성에는 {TRAVEL_ENDING_CREATION_POINT_COST} 포인트가 필요합니다. "
                f"(보유 {user.point})"
            ),
        )


def _save_travel_ending_content(
    db: Session, current_user_id: int, image_url: str
) -> TravelEndingContentCreateResponse:
    """포인트를 차감하고 엽서 행을 만든다. 저장에 실패하면 올린 Blob 을 지운다.

    업로드와 저장 사이에 다른 요청이 포인트를 써서 모자라졌을 수 있으므로,
    사용자 행을 쓰기 잠금으로 다시 읽어 확인한다. (SQLite 는 행 잠금을 지원하지 않아
    테스트에서는 무시된다)
    """
    try:
        user = _get_user_for_update(db, current_user_id)
        _check_point(user)

        user.point -= TRAVEL_ENDING_CREATION_POINT_COST
        content = TravelEndingContent(user_id=current_user_id, image_url=image_url)
        db.add(content)
        db.commit()
        db.refresh(content)
        db.refresh(user)
    except Exception:
        # 포인트만 깎이거나, DB 가 참조하지 않는 Blob 이 남지 않게 한다.
        db.rollback()
        _delete_uploaded_image(image_url)
        raise

    return TravelEndingContentCreateResponse(
        id=content.id,
        image_url=content.image_url,
        # 별도로 계산하지 않고 커밋된 값을 그대로 쓴다.
        remaining_point=user.point,
    )


def _get_user_for_update(db: Session, current_user_id: int) -> User:
    """포인트를 차감할 사용자 행을 잠그고 조회한다."""
    statement = select(User).where(User.id == current_user_id).with_for_update()
    user = db.scalars(statement).first()
    if user is None:
        raise RuntimeError(f"현재 사용자 {current_user_id} 를 찾을 수 없습니다.")
    return user


def _delete_uploaded_image(image_url: str) -> None:
    """저장에 실패한 엽서 이미지를 지운다.

    삭제까지 실패해도 원래 실패를 덮지 않고 로그만 남긴다.
    """
    try:
        blob_storage.delete_file(image_url)
    except Exception:
        logger.exception("엽서 이미지 Blob 을 삭제하지 못했습니다.")


def _get_visited_locations(
    db: Session, current_user_id: int, location_ids: list[int]
) -> list[Location]:
    """요청한 장소를 요청 순서대로 조회한다.

    현재 사용자가 방문하지 않은 장소가 하나라도 있으면 전체 요청을 400 으로 막는다.
    같은 장소의 방문 횟수나 방문 시각은 선택 가능 여부에 영향을 주지 않는다.
    """
    statement = (
        select(Location)
        .join(VisitedLocation, VisitedLocation.location_id == Location.id)
        .where(
            VisitedLocation.user_id == current_user_id,
            Location.id.in_(location_ids),
        )
        .distinct()
    )
    visited = {location.id: location for location in db.scalars(statement).all()}

    missing = [location_id for location_id in location_ids if location_id not in visited]
    if missing:
        raise InvalidRequestError(
            f"현재 사용자가 방문하지 않은 장소가 있습니다: {missing}"
        )

    # 요청 배열 순서를 그대로 유지한다.
    return [visited[location_id] for location_id in location_ids]


def _get_completed_missions(
    db: Session, current_user_id: int, requested: list[TravelEndingMissionRequest]
) -> list[_CompletedMissionSource]:
    """요청한 미션을 요청 순서대로 조회한다.

    완료 미션 목록 조회와 같은 기준을 쓴다. (중단으로 완료된 진행도도 완료로 본다)
    현재 사용자가 완료하지 않은 미션이 하나라도 있으면 전체 요청을 400 으로 막는다.
    """
    completed = {
        (mission.mission_type, mission.id): mission
        for mission in [
            *_find_completed_culture_missions(db, current_user_id),
            *_find_completed_treasure_missions(db, current_user_id),
            *_find_completed_cooperative_missions(db, current_user_id),
        ]
    }

    sources: list[_CompletedMissionSource] = []
    missing: list[str] = []
    for mission in requested:
        found = completed.get((mission.mission_type, mission.mission_id))
        if found is None:
            missing.append(f"{mission.mission_type.value}:{mission.mission_id}")
            continue
        sources.append(
            _CompletedMissionSource(
                mission_type=found.mission_type,
                id=found.id,
                mission_title=found.mission_title,
                location_title=found.completed_location,
            )
        )

    if missing:
        raise InvalidRequestError(
            f"현재 사용자가 완료하지 않은 미션이 있습니다: {missing}"
        )
    return sources


def _to_location_source(location: Location) -> TravelEndingSource:
    """방문 장소 재료. 대표 이미지를 얻지 못하면 이름만 쓴다."""
    return TravelEndingSource(
        source_type=SourceType.VISITED_LOCATION,
        display_name=location.location_title,
        location_name=location.location_title,
        image_url=kto.get_location_image_url(location.content_id),
    )


def _to_mission_source(db: Session, mission: _CompletedMissionSource) -> TravelEndingSource:
    """완료 미션 재료.

    장소가 있는 보물찾기·협동 미션은 그 장소의 대표 이미지를 쓰고,
    장소가 없는 문화 미션은 장소를 추론하지 않고 퀴즈 이미지를 참조로 쓴다.
    """
    if mission.mission_type is MissionType.CULTURE:
        image_url = _find_quiz_image_url(db, mission.id)
    else:
        image_url = _find_mission_location_image_url(db, mission)

    return TravelEndingSource(
        source_type=SourceType.MISSION,
        display_name=mission.mission_title,
        location_name=mission.location_title,
        image_url=image_url,
    )


def _find_quiz_image_url(db: Session, culture_mission_id: int) -> str | None:
    """문화 미션의 퀴즈 이미지. 배열 순서상 값이 있는 첫 번째 `img_url` 을 쓴다."""
    culture_mission = db.get(CultureMission, culture_mission_id)
    if culture_mission is None:
        return None

    for quiz in culture_mission.quiz_detail or []:
        image_url = quiz.get("img_url")
        if image_url:
            return str(image_url)
    return None


def _find_mission_location_image_url(
    db: Session, mission: _CompletedMissionSource
) -> str | None:
    """보물찾기·협동 미션 장소의 TourAPI 대표 이미지."""
    model = (
        TreasureMission
        if mission.mission_type is MissionType.TREASURE
        else CooperativeMission
    )
    statement = (
        select(Location.content_id)
        .join(model, model.location_id == Location.id)
        .where(model.id == mission.id)
    )
    content_id = db.scalars(statement).first()
    if content_id is None:
        return None

    return kto.get_location_image_url(content_id)


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
    단, `categories`(`USER.expectation`)가 이전과 같으면 대표 캐릭터는 다시 뽑지 않는다.

    선택 배열은 요청값을 그대로 저장한다. 빈 배열도 `NULL` 로 바꾸지 않고 빈 배열로 둔다.

    필드 갱신과 재배정은 한 트랜잭션이고, 중간에 실패하면 전부 롤백된다.
    """
    user = _get_user(db, current_user_id)
    expectation_changed = _is_expectation_changed(user, request)

    user.nickname = request.nickname
    user.expectation = [category.value for category in request.categories]
    user.transportation = [value.value for value in request.transportation]
    user.travel_style = [value.value for value in request.travel_style]
    user.target_step = request.target_step_count

    _reassign(db, user, request, reassign_ar_character=expectation_changed)
    db.commit()


def _is_expectation_changed(user: User, request: UserProfileUpdateRequest) -> bool:
    """요청한 `categories` 가 저장된 `USER.expectation` 과 다른지 판단한다.

    선택 순서는 의미가 없으므로 집합으로 비교한다. (중복은 요청 검증에서 이미 막는다)
    `NULL`(설정 전)은 어떤 요청값과도 다르게 본다.
    """
    if user.expectation is None:
        return True
    requested = {category.value for category in request.categories}
    return set(user.expectation) != requested


def _get_user(db: Session, current_user_id: int) -> User:
    """현재 사용자를 조회한다.

    인증에서 이미 확인한 사용자라 없을 수 없지만, 조용히 넘기지 않도록 확인한다.
    """
    user = db.get(User, current_user_id)
    if user is None:
        raise RuntimeError(f"현재 사용자 {current_user_id} 를 찾을 수 없습니다.")
    return user


def _reassign(
    db: Session,
    user: User,
    request: UserProfileUpdateRequest,
    *,
    reassign_ar_character: bool,
) -> None:
    """바뀐 선택값으로 여행 유형과 대표 캐릭터를 다시 배정한다.

    세 선택 배열이 모두 비어 있으면 온보딩 건너뛰기와 같게 여행 유형은 비운다.
    일부만 비어 있으면 빈 배열을 포함한 전체 선택값으로 배정한다.
    대표 캐릭터는 온보딩과 같이 건너뛰기 여부와 관계없이 온보딩 전용 캐릭터(id 7~12) 중에서 배정한다.

    `reassign_ar_character` 가 거짓이면(`categories` 가 이전과 같으면) 대표 캐릭터는
    다시 뽑지 않고 기존 값을 그대로 둔다.

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
    else:
        user.user_travel_style_id = onboarding_matcher.assign_travel_style(
            db, onboarding_request
        ).id

    if not reassign_ar_character:
        return

    # 온보딩과 같이 건너뛰기 여부와 관계없이 온보딩 전용 캐릭터(id 7~12) 중 하나를 배정한다.
    ar_character = onboarding_matcher.assign_ar_character(db, onboarding_request)
    user.ar_character_id = ar_character.id
