"""기타 도메인 비즈니스 로직.

기준 문서: app/others/docs/API_SPEC.md, app/others/docs/BUSINESS_RULES.md

`STEP_COUNT` / `USER` 는 소유 도메인인 app/user/models.py,
`GPS` / `LOCATION` / `VISITED_LOCATION` 은 app/map/models.py,
`AR_CHARACTER` / `ACQUIRED_AR_CHARACTER` 는 app/treasure_mission/models.py 에서 import해서 쓴다.
"""

import random
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.map.models import Gps, Location, VisitedLocation
from app.others.schemas import (
    GpsSaveRequest,
    StepCountSaveRequest,
    StepCountSaveResponse,
)
from app.others.visit_detector import LocationArea, find_visited_location_ids
from app.treasure_mission.models import AcquiredArCharacter, ArCharacter
from app.user.models import StepCount, User


# 목표 걸음 수를 달성했을 때 보상으로 추첨하는 AR 캐릭터 후보.
# (app/others/docs/BUSINESS_RULES.md - 걸음 수 저장 / 목표 달성 캐릭터 추첨)
STEP_GOAL_REWARD_CHARACTER_IDS = (1, 2, 3)


def save_step_count(
    db: Session, current_user_id: int, request: StepCountSaveRequest
) -> StepCountSaveResponse:
    """걸음 수를 저장하고, 목표를 달성했으면 보상 캐릭터를 추첨해서 지급한다.

    `saved_at` 은 서버가 요청을 받은 시각이 아니라 프론트가 걸음 수를 측정한 시각
    (`recordedAt`)이다. 같은 시각으로 다시 보내면 행을 추가하지 않고 `steps_count` 만
    요청값으로 바꾼다. 프론트가 보낸 값이 그 시점의 최종값이므로,
    **기존 값보다 작아도 그대로 덮어쓴다.** (서버가 최댓값을 고르거나 누적해서 더하지 않는다)

    `isGoalAchieved` 는 프론트의 판정을 그대로 믿는다. 저장하지 않고, 걸음 수와
    목표 걸음 수를 다시 비교해서 뒤집지도 않는다.

    걸음 수 저장과 캐릭터 획득은 한 트랜잭션이고, 커밋까지 끝나야 성공이다.
    """
    target_step = _get_user(db, current_user_id).target_step
    # 추첨은 쓰기 전에 끝낸다. 후보 캐릭터가 없으면 걸음 수도 저장하지 않고 500 이다.
    character = _draw_goal_reward_character(db) if request.is_goal_achieved else None
    # 커밋하면 ORM 객체가 만료돼 다시 조회하므로 응답에 쓸 값은 미리 읽어 둔다.
    response = StepCountSaveResponse(
        character_name=character.character_name if character is not None else None,
        character_image_url=(
            character.character_img_url if character is not None else None
        ),
        target_step=target_step,
    )
    character_id = character.id if character is not None else None

    try:
        _save_step_count_and_reward(db, current_user_id, request, character_id)
        db.commit()
    except IntegrityError:
        # 동시 요청이 같은 행을 먼저 만든 경우다. 되돌린 뒤 그 행을 기준으로 한 번 더 반영한다.
        # (이미 있는 행은 조회로 찾아 갱신하거나 그대로 두므로 두 번째 시도는 충돌하지 않는다)
        db.rollback()
        _save_step_count_and_reward(db, current_user_id, request, character_id)
        db.commit()

    return response


def _get_user(db: Session, current_user_id: int) -> User:
    """현재 사용자. 인증 의존성이 이미 확인했으므로 없으면 500 으로 드러낸다."""
    user = db.get(User, current_user_id)
    if user is None:
        raise RuntimeError(f"사용자를 찾지 못했습니다. (id {current_user_id})")
    return user


def _draw_goal_reward_character(db: Session) -> ArCharacter:
    """보상 캐릭터를 후보 중에서 균등한 확률로 하나 뽑는다.

    이미 보유한 캐릭터가 뽑혀도 다시 추첨하지 않는다. (응답에는 그대로 내려간다)
    후보 id 의 캐릭터가 없으면 마스터/목업 데이터가 잘못된 것이라 500 으로 드러낸다.
    """
    character_id = random.choice(STEP_GOAL_REWARD_CHARACTER_IDS)
    character = db.get(ArCharacter, character_id)
    if character is None:
        raise RuntimeError(f"보상 AR 캐릭터가 없습니다. (id {character_id})")
    return character


def _save_step_count_and_reward(
    db: Session,
    current_user_id: int,
    request: StepCountSaveRequest,
    ar_character_id: int | None,
) -> None:
    """걸음 수 기록과 캐릭터 획득 기록을 한 트랜잭션에 담는다. (커밋은 호출한 쪽에서)"""
    step_count = _find_step_count(db, current_user_id, request.recorded_at)

    if step_count is None:
        db.add(
            StepCount(
                user_id=current_user_id,
                saved_at=request.recorded_at,
                steps_count=request.steps_count,
            )
        )
    else:
        # `created_at` 은 처음 기록한 시각 그대로 두고 걸음 수만 바꾼다.
        step_count.steps_count = request.steps_count

    if ar_character_id is not None:
        _acquire_character(db, current_user_id, ar_character_id)


def _find_step_count(
    db: Session, current_user_id: int, saved_at: datetime
) -> StepCount | None:
    """그 사용자·측정 시각의 기록. 없으면 `None`."""
    statement = select(StepCount).where(
        StepCount.user_id == current_user_id,
        StepCount.saved_at == saved_at,
    )
    return db.scalars(statement).first()


def _acquire_character(db: Session, current_user_id: int, ar_character_id: int) -> None:
    """보유하지 않은 캐릭터면 획득 기록을 만든다. 이미 보유했으면 아무것도 하지 않는다.

    걸음 수 달성 보상은 미션에서 받은 보상이 아니라 연결할 미션이 없다.
    그래서 `acquired_mission_id` 는 `NULL` 로 두고, 임의의 미션 id 로 출처를 위조하지 않는다.
    """
    existing = db.scalars(
        select(AcquiredArCharacter.id).where(
            AcquiredArCharacter.user_id == current_user_id,
            AcquiredArCharacter.ar_character_id == ar_character_id,
        )
    ).first()
    if existing is not None:
        return

    db.add(
        AcquiredArCharacter(
            user_id=current_user_id,
            ar_character_id=ar_character_id,
            acquired_mission_id=None,
        )
    )


# ---------------------------------------------------------------------
# GPS 및 방문 장소 저장
# ---------------------------------------------------------------------


def save_gps(db: Session, current_user_id: int, request: GpsSaveRequest) -> None:
    """GPS 좌표를 저장하고, 그 좌표로 판정한 방문 장소를 함께 기록한다.

    방문 시각은 서버가 요청을 받은 시각이 아니라 **좌표를 측정한 시각**(`recordedAt`)이다.
    GPS 한 건과 그 좌표에서 나온 방문 기록은 한 트랜잭션으로 저장하고,
    하나라도 실패하면 전부 롤백한다.

    같은 장소를 다시 판정받아도 **사용자·장소당 방문 기록은 한 건만** 남긴다.
    이미 기록이 있으면 새로 넣지 않고 기존 기록의 `visited_at` 도 건드리지 않는다.
    (판정 규칙은 `visit_detector` 가 담당한다)
    """
    db.add(
        Gps(
            user_id=current_user_id,
            # LOCATION 과 같게 mx = 경도, my = 위도로 저장한다.
            mx=request.longitude,
            my=request.latitude,
            saved_at=request.recorded_at,
        )
    )

    for location_id in _find_new_visited_location_ids(db, current_user_id, request):
        db.add(
            VisitedLocation(
                user_id=current_user_id,
                location_id=location_id,
                visited_at=request.recorded_at,
            )
        )

    db.commit()


def _find_new_visited_location_ids(
    db: Session, current_user_id: int, request: GpsSaveRequest
) -> list[int]:
    """이번 좌표로 방문 판정을 받은 장소 중 **아직 기록이 없는** 장소 id 목록.

    `(user_id, location_id)` 중복을 막는 지점이다. DB 유니크 제약 없이 여기서만 거르므로,
    같은 사용자의 요청이 동시에 들어오면 같은 장소가 두 번 들어갈 수 있다.
    (그 경우까지 막으려면 `VISITED_LOCATION` 에 유니크 제약이 필요하다)
    """
    visited_location_ids = _find_visited_location_ids(db, request)
    if not visited_location_ids:
        return []

    already_visited = set(
        db.scalars(
            select(VisitedLocation.location_id).where(
                VisitedLocation.user_id == current_user_id,
                VisitedLocation.location_id.in_(visited_location_ids),
            )
        ).all()
    )
    return [
        location_id
        for location_id in visited_location_ids
        if location_id not in already_visited
    ]


def _find_visited_location_ids(db: Session, request: GpsSaveRequest) -> list[int]:
    """요청 좌표로 방문한 장소를 찾는다.

    판정 자체는 `visit_detector` 가 하고, 여기서는 장소를 읽어 넘겨주기만 한다.
    판정이 `LOCATION.radius` 를 쓰지 않고 공통 반경을 쓰므로 반경은 넘기지 않는다.
    장소 수가 많아지면 이 조회에 좌표 범위 필터(또는 공간 질의)를 먼저 걸어야 한다.
    """
    locations = db.scalars(select(Location).order_by(Location.id)).all()
    return find_visited_location_ids(
        latitude=request.latitude,
        longitude=request.longitude,
        locations=[
            # LOCATION 은 my = 위도, mx = 경도로 저장돼 있다.
            LocationArea(id=location.id, latitude=location.my, longitude=location.mx)
            for location in locations
        ],
    )
