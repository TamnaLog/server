"""보물 찾기 도메인 비즈니스 로직.

기준 문서: app/treasure_mission/docs/API_SPEC.md, app/treasure_mission/docs/BUSINESS_RULES.md
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import next_location
from app.common.datetimes import now_kst
from app.common.next_location import NextLocationResponse
from app.core.errors import ConflictError, NotFoundError
from app.map.models import Location
from app.mission.models import MissionStatus
from app.treasure_mission import reward_granter, treasure_placer
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress
from app.treasure_mission.schemas import (
    TreasureItemResponse,
    TreasureLocationResponse,
    TreasureMissionLocationResponse,
    TreasureMissionProgressSaveRequest,
    TreasureMissionProgressSaveResponse,
    TreasureMissionStartResponse,
    TreasureMissionStopResponse,
)


TREASURE_MISSION_NOT_FOUND = "TREASURE_MISSION_NOT_FOUND"
TREASURE_MISSION_PROGRESS_NOT_FOUND = "TREASURE_MISSION_PROGRESS_NOT_FOUND"
TREASURE_ITEM_NOT_FOUND = "TREASURE_ITEM_NOT_FOUND"
TREASURE_ITEM_ALREADY_FOUND = "TREASURE_ITEM_ALREADY_FOUND"

# 신규 진행도 초기값
FIRST_STEP = 1

# 진행 단계. 보물을 하나라도 찾으면 2, 전부 찾으면 3(완료)
FINDING_STEP = 2
COMPLETED_STEP = 3


@dataclass(frozen=True)
class StartTreasureMissionResult:
    """보물찾기 시작/이어하기 결과.

    응답 본문은 같지만 상태 코드가 달라서(신규 201 / 이어하기 200)
    진행도를 새로 만들었는지를 라우터에 함께 전달한다.
    """

    response: TreasureMissionStartResponse
    is_created: bool


def start_treasure_mission(
    db: Session,
    current_user_id: int,
    treasure_mission_id: int,
    latitude: float,
    longitude: float,
) -> StartTreasureMissionResult:
    """보물찾기 시작/이어하기.

    - `IN_PROGRESS` 진행도가 있으면 새로 만들지 않고 그 진행도를 이어서 반환한다.
      이때 요청으로 받은 사용자 위치는 사용하지 않는다. (저장된 보물 좌표를 그대로 쓴다)
    - 없으면 사용자 위치를 기준으로 보물 좌표를 만들어 새 진행도를 생성한다.
      (최초 시작, 완료한 미션 재도전 모두 포함)
    """
    treasure_mission = _get_treasure_mission(db, treasure_mission_id)
    progress = _find_in_progress(db, current_user_id, treasure_mission_id)

    is_created = progress is None
    if progress is None:
        progress = _create_progress(db, current_user_id, treasure_mission, latitude, longitude)
        db.commit()
        db.refresh(progress)

    return StartTreasureMissionResult(
        response=_to_response(treasure_mission, progress),
        is_created=is_created,
    )


def _get_treasure_mission(db: Session, treasure_mission_id: int) -> TreasureMission:
    """보물찾기 미션을 조회한다. 없으면 진행도를 조회/생성하지 않고 404."""
    treasure_mission = db.get(TreasureMission, treasure_mission_id)
    if treasure_mission is None:
        raise NotFoundError(
            TREASURE_MISSION_NOT_FOUND,
            detail=f"보물찾기 미션 {treasure_mission_id} 을(를) 찾을 수 없습니다.",
        )
    return treasure_mission


def _find_in_progress(
    db: Session, current_user_id: int, treasure_mission_id: int
) -> TreasureMissionProgress | None:
    """이어서 진행할 `IN_PROGRESS` 진행도를 찾는다.

    같은 사용자/미션에 `IN_PROGRESS` 진행도는 최대 하나만 있어야 하지만,
    데이터가 여러 건이어도 결과가 흔들리지 않도록 가장 먼저 만든 진행도를 사용한다.
    """
    statement = (
        select(TreasureMissionProgress)
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.treasure_mission_id == treasure_mission_id,
            TreasureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
        .order_by(TreasureMissionProgress.id)
    )
    return db.scalars(statement).first()


def _create_progress(
    db: Session,
    current_user_id: int,
    treasure_mission: TreasureMission,
    latitude: float,
    longitude: float,
) -> TreasureMissionProgress:
    """보물 좌표를 만들어 새 진행도를 생성한다. 기존 `COMPLETED` 기록은 그대로 둔다."""
    progress = TreasureMissionProgress(
        treasure_mission_id=treasure_mission.id,
        user_id=current_user_id,
        item_detail=treasure_placer.place_treasures(
            treasure_mission.location,
            latitude=latitude,
            longitude=longitude,
            treasure_count=treasure_mission.item_total_count,
        ),
        current_found_item_idx=[],
        current_step=FIRST_STEP,
        mission_status=MissionStatus.IN_PROGRESS.value,
        completed_at=None,
    )
    db.add(progress)
    return progress


def _to_response(
    treasure_mission: TreasureMission, progress: TreasureMissionProgress
) -> TreasureMissionStartResponse:
    return TreasureMissionStartResponse(
        treasure_mission_progress_id=progress.id,
        mission_progress_status=MissionStatus(progress.mission_status),
        location=_to_mission_location(treasure_mission.location),
        treasure_count=treasure_mission.item_total_count,
        treasure_items=_to_treasure_items(
            progress.item_detail, progress.current_found_item_idx
        ),
    )


def _to_mission_location(location: Location) -> TreasureMissionLocationResponse:
    """LOCATION 은 my=위도 / mx=경도로 저장한다."""
    return TreasureMissionLocationResponse(
        location_title=location.location_title, lat=location.my, lng=location.mx
    )


def _to_treasure_items(
    item_detail: list[dict[str, Any]] | None, found_item_idx: list[int] | None
) -> list[TreasureItemResponse]:
    """보물 좌표와 발견 목록을 합쳐 `treasureIndex` 오름차순으로 반환한다."""
    found = set(found_item_idx or [])
    items = sorted(item_detail or [], key=lambda item: item["index"])
    return [
        TreasureItemResponse(
            treasure_index=item["index"],
            location=TreasureLocationResponse(lat=item["my"], lng=item["mx"]),
            is_found=item["index"] in found,
        )
        for item in items
    ]


# ---------------------------------------------------------------------
# 진행도 저장 (보물 발견)
# ---------------------------------------------------------------------


def save_treasure_mission_progress(
    db: Session,
    current_user_id: int,
    treasure_mission_progress_id: int,
    request: TreasureMissionProgressSaveRequest,
    latitude: float,
    longitude: float,
) -> TreasureMissionProgressSaveResponse:
    """보물찾기 진행도 저장.

    - 찾은 보물을 `current_found_item_idx` 에 추가하고, 보물 하나당 보상 하나를 즉시 지급한다.
    - 아직 남은 보물이 있으면 `IN_PROGRESS` 를 유지하고 다음 장소는 추천하지 않는다.
    - 마지막 보물이면 `COMPLETED` 로 바꾸고 다음 장소를 추천한다.

    보물 발견 저장 / 보상 지급 / 완료 처리는 같은 트랜잭션으로 커밋한다.
    """
    progress = _get_in_progress_by_id(db, current_user_id, treasure_mission_progress_id)
    treasure_mission = _get_treasure_mission(db, progress.treasure_mission_id)

    _validate_treasure_index(progress, request.treasure_index)

    # JSON 컬럼은 리스트를 새로 대입해야 변경으로 인식된다.
    progress.current_found_item_idx = sorted(
        [*progress.current_found_item_idx, request.treasure_index]
    )
    reward = reward_granter.grant_next_treasure_reward(db, progress, treasure_mission)

    is_completed = len(progress.current_found_item_idx) >= treasure_mission.item_total_count
    if is_completed:
        progress.current_step = COMPLETED_STEP
        progress.mission_status = MissionStatus.COMPLETED.value
        progress.completed_at = now_kst()
        recommended_location = _recommend_next_location(db, latitude, longitude)
    else:
        progress.current_step = FINDING_STEP
        recommended_location = None

    db.commit()
    db.refresh(progress)

    return TreasureMissionProgressSaveResponse(
        mission_progress_status=MissionStatus(progress.mission_status),
        treasure_count=treasure_mission.item_total_count,
        found_treasure_indexes=sorted(progress.current_found_item_idx),
        next_location=recommended_location,
        reward=reward,
    )


# ---------------------------------------------------------------------
# 진행도 중단
# ---------------------------------------------------------------------


def stop_treasure_mission(
    db: Session,
    current_user_id: int,
    treasure_mission_progress_id: int,
    latitude: float,
    longitude: float,
) -> TreasureMissionStopResponse:
    """보물찾기 중단.

    찾지 않은 보물이 남아 있어도 진행도를 즉시 완료 처리한다.
    보상은 보물을 찾을 때마다 이미 지급했으므로 중단 요청에서는 추가로 지급하지 않고,
    찾은 보물 목록도 그대로 둔다. 중단도 완료이므로 다음 장소는 추천한다.
    """
    progress = _get_in_progress_by_id(db, current_user_id, treasure_mission_progress_id)
    treasure_mission = _get_treasure_mission(db, progress.treasure_mission_id)

    progress.mission_status = MissionStatus.COMPLETED.value
    progress.current_step = COMPLETED_STEP
    progress.completed_at = now_kst()
    recommended_location = _recommend_next_location(db, latitude, longitude)

    db.commit()
    db.refresh(progress)

    return TreasureMissionStopResponse(
        mission_progress_status=MissionStatus(progress.mission_status),
        treasure_count=treasure_mission.item_total_count,
        found_treasure_indexes=sorted(progress.current_found_item_idx or []),
        next_location=recommended_location,
    )


def _get_in_progress_by_id(
    db: Session, current_user_id: int, treasure_mission_progress_id: int
) -> TreasureMissionProgress:
    """현재 사용자의 진행 중인 진행도를 조회한다.

    다른 사용자의 진행도이거나 이미 완료된 진행도면 갱신 대상이 아니므로 404로 처리한다.
    동시에 같은 보물이 두 번 저장되지 않도록 진행도 row 를 잠그고 읽는다.
    (SQLite 는 행 잠금을 지원하지 않아 테스트에서는 무시된다)
    """
    statement = (
        select(TreasureMissionProgress)
        .where(TreasureMissionProgress.id == treasure_mission_progress_id)
        .with_for_update()
    )
    progress = db.scalars(statement).first()
    if (
        progress is None
        or progress.user_id != current_user_id
        or progress.mission_status != MissionStatus.IN_PROGRESS.value
    ):
        raise NotFoundError(
            TREASURE_MISSION_PROGRESS_NOT_FOUND,
            detail=(
                f"진행 중인 보물찾기 진행도 {treasure_mission_progress_id} 를 "
                f"사용자 {current_user_id} 의 것으로 찾을 수 없습니다."
            ),
        )
    return progress


def _validate_treasure_index(progress: TreasureMissionProgress, treasure_index: int) -> None:
    """요청한 보물이 이 진행도에 있고 아직 찾지 않은 보물인지 확인한다."""
    treasure_indexes = {item["index"] for item in progress.item_detail or []}
    if treasure_index not in treasure_indexes:
        raise NotFoundError(
            TREASURE_ITEM_NOT_FOUND,
            detail=(
                f"보물 {treasure_index} 는 진행도 {progress.id} 의 보물 목록에 없습니다."
            ),
        )

    if treasure_index in (progress.current_found_item_idx or []):
        raise ConflictError(
            TREASURE_ITEM_ALREADY_FOUND,
            detail=f"보물 {treasure_index} 는 이미 찾은 보물입니다.",
        )


def _recommend_next_location(
    db: Session, latitude: float, longitude: float
) -> NextLocationResponse:
    """완료 응답에 넣을 다음 장소를 추천한다.

    완료 응답의 `nextLocation` 은 반드시 객체여야 하므로, 추천할 장소 데이터가 하나도 없으면
    정상 완료로 처리하지 않고 예외를 발생시킨다. (공통 처리기가 500 으로 응답)
    """
    recommended = next_location.recommend_next_location(db, latitude, longitude)
    if recommended is None:
        raise RuntimeError("추천할 수 있는 장소 데이터가 없어 미션 완료 응답을 만들 수 없습니다.")
    return recommended


# ---------------------------------------------------------------------
# TODO: 명세 확정 후 구현
# ---------------------------------------------------------------------


def save_picture_with_character(db: Session) -> dict[str, Any]:
    """ar 캐릭터와 사진 저장."""
    raise NotImplementedError
