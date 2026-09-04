"""보물 찾기 도메인 비즈니스 로직.

기준 문서: app/treasure_mission/docs/API_SPEC.md, app/treasure_mission/docs/BUSINESS_RULES.md
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import images, next_location, rewards
from app.common.datetimes import now_kst
from app.common.distance import calculate_distance_meter, calculate_duration_minutes
from app.common.next_location import NextLocationResponse
from app.common.rewards import GrantedRewards
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantStatus,
)
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.map.models import Location
from app.mission import reward_history
from app.mission.models import MissionStatus, MissionType
from app.services import blob_storage, kto
from app.treasure_mission import reward_granter, treasure_placer
from app.treasure_mission.models import (
    ArCharacter,
    PictureWithCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.treasure_mission.schemas import (
    CompletedTreasureMissionResponse,
    NearbyTreasureMissionResponse,
    ReceivedCouponResponse,
    TreasureItemResponse,
    TreasureLocationResponse,
    TreasureMissionLocationResponse,
    TreasureMissionCompletionResponse,
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
        location_id=location.id,
        location_title=location.location_title,
        location_address=location.location_address,
        lat=location.my,
        lng=location.mx,
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


# ---------------------------------------------------------------------
# AR 캐릭터와 사진 저장
# ---------------------------------------------------------------------

# 사진 형식/크기 정책은 app/common/images.py 가 공용으로 가진다. (JPEG/PNG/WebP, 최대 10MB)

# Blob 저장 경로의 최상위 prefix. 그 아래를 사용자 id로 나눈다.
PICTURE_BLOB_PREFIX = "ar_character_picture"


def save_picture_with_character(
    db: Session, current_user_id: int, picture: BinaryIO, taken_at: str
) -> None:
    """AR 캐릭터와 사진 저장.

    사진은 컨테이너 로컬 디스크가 아니라 Azure Blob Storage 에 올리고 DB에는 URL만 남긴다.
    Blob 업로드가 실패하면 DB 데이터를 만들지 않고, DB 저장이 실패하면 올린 Blob 을 지워
    DB가 참조하지 않는 파일이 남지 않게 한다.
    """
    saved_at = _parse_taken_at(taken_at)
    data, image_format = images.read_and_detect(picture)

    picture_url = blob_storage.upload_file(
        data,
        prefix=f"{PICTURE_BLOB_PREFIX}/{current_user_id}",
        content_type=image_format.content_type,
        extension=image_format.extension,
    )

    try:
        db.add(
            PictureWithCharacter(
                user_id=current_user_id,
                picture_url=picture_url,
                saved_at=saved_at,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        blob_storage.delete_file(picture_url)
        raise


def _parse_taken_at(taken_at: str) -> datetime:
    """촬영 시각을 KST 기준 offset 없는 ISO 8601 로 해석한다."""
    try:
        parsed = datetime.fromisoformat(taken_at)
    except ValueError as error:
        raise InvalidRequestError(f"촬영 시각 형식이 올바르지 않습니다: {taken_at}") from error

    if parsed.tzinfo is not None:
        # 시간은 KST 로 취급하므로 offset 이 붙은 값은 받지 않는다.
        raise InvalidRequestError(f"촬영 시각에 offset 을 포함할 수 없습니다: {taken_at}")

    if "T" not in taken_at and " " not in taken_at:
        # 날짜만 온 경우. date-time 이 필요하다.
        raise InvalidRequestError(f"촬영 시각에 시간이 없습니다: {taken_at}")

    return parsed


# ---------------------------------------------------------------------
# 완료한 보물찾기 추천 화면
# ---------------------------------------------------------------------


TREASURE_ITEMS_REMAINING = "TREASURE_ITEMS_REMAINING"

# 추천할 근처 보물찾기 개수
NEARBY_TREASURE_MISSION_LIMIT = 3

# 현재 사용자의 쿠폰 수령 이력을 찾을 미션 유형별 진행도 조회 설정
# (유형마다 진행도 테이블과 사용자 연결 방식이 달라 조회를 따로 만든다)


@dataclass(frozen=True)
class _ReceivedCoupon:
    """수령한 쿠폰 한 건. `(미션 유형, 세부 미션 id)` 당 하나만 만든다."""

    mission_type: MissionType
    mission_id: int
    coupon_location: str
    coupon_price: int


def get_treasure_mission_completion(
    db: Session,
    current_user_id: int,
    mission_type: MissionType,
    treasure_mission_id: int,
    latitude: float,
    longitude: float,
) -> TreasureMissionCompletionResponse:
    """완료한 보물찾기 추천 화면 데이터를 조회한다.

    미션 홈 조회에서 남은 보상이 하나도 없는 보물찾기(= 보물을 다 찾은 미션)일 때 호출한다.

    완료 미션 정보 + 근처 보물찾기 추천 + 지금까지 받은 쿠폰을 함께 내려준다.
    읽기 전용이라 진행도·보상·포인트·쿠폰 상태를 바꾸지 않는다.
    """
    if mission_type is not MissionType.TREASURE:
        # 이 화면은 보물찾기 전용이라 다른 유형은 대상 미션이 없는 것으로 본다.
        raise NotFoundError(
            TREASURE_MISSION_NOT_FOUND,
            detail=f"보물찾기 완료 화면은 TREASURE 만 지원합니다: {mission_type.value}",
        )

    treasure_mission = _get_treasure_mission(db, treasure_mission_id)
    progress = _get_latest_completed_progress(db, current_user_id, treasure_mission_id)
    _validate_all_items_found(progress)

    return TreasureMissionCompletionResponse(
        completed_mission=_to_completed_mission(db, treasure_mission, progress),
        nearby_treasure_missions=_find_nearby_treasure_missions(
            db, current_user_id, treasure_mission_id, latitude, longitude
        ),
        received_coupons=_find_received_coupons(db, current_user_id),
    )


def _get_latest_completed_progress(
    db: Session, current_user_id: int, treasure_mission_id: int
) -> TreasureMissionProgress:
    """현재 사용자의 가장 최근 완료 진행도. 없으면 404.

    같은 미션을 여러 번 완료했으면 완료 시각이 가장 늦은 진행도를 쓰고,
    완료 시각이 같으면 나중에 만든(id 가 큰) 진행도를 쓴다.
    """
    statement = (
        select(TreasureMissionProgress)
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.treasure_mission_id == treasure_mission_id,
            TreasureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
        )
        .order_by(
            TreasureMissionProgress.completed_at.desc(),
            TreasureMissionProgress.id.desc(),
        )
    )
    progress = db.scalars(statement).first()
    if progress is None:
        raise NotFoundError(
            TREASURE_MISSION_NOT_FOUND,
            detail=(
                f"보물찾기 미션 {treasure_mission_id} 의 완료 진행도를 "
                f"사용자 {current_user_id} 의 것으로 찾을 수 없습니다."
            ),
        )
    return progress


def _validate_all_items_found(progress: TreasureMissionProgress) -> None:
    """설정된 보물을 모두 한 번 이상 찾았는지 확인한다. 아니면 409.

    `current_found_item_idx` 의 중복값은 다른 보물을 찾은 것으로 세지 않는다.
    (완료로 저장돼 있어도 실제로 다 찾지 않았으면 이 화면을 보여주지 않는다)
    """
    found = set(progress.current_found_item_idx or [])
    missing = sorted(
        item["index"] for item in progress.item_detail or [] if item["index"] not in found
    )
    if missing:
        raise ConflictError(
            TREASURE_ITEMS_REMAINING,
            detail=f"진행도 {progress.id} 에서 아직 찾지 않은 보물이 있습니다: {missing}",
        )


def _to_completed_mission(
    db: Session, treasure_mission: TreasureMission, progress: TreasureMissionProgress
) -> CompletedTreasureMissionResponse:
    """완료 미션 정보. 캐릭터 보상이 없으면 이미지는 `None` 이다."""
    ar_character = rewards.to_ar_character(
        db, (treasure_mission.reward_detail or {}).get("ar_character_id")
    )
    return CompletedTreasureMissionResponse(
        mission_id=treasure_mission.id,
        mission_type=MissionType.TREASURE,
        # 완료 진행도만 고르므로 완료 시각은 항상 있다.
        completed_at=progress.completed_at,
        ar_character_image_url=ar_character.image_url if ar_character else None,
    )


# ---------------------------------------------------------------------
# 근처 보물찾기 추천
# ---------------------------------------------------------------------


def _find_nearby_treasure_missions(
    db: Session,
    current_user_id: int,
    treasure_mission_id: int,
    latitude: float,
    longitude: float,
) -> list[NearbyTreasureMissionResponse]:
    """가까운 보물찾기를 최대 3개 추천한다.

    지금 보고 있는 미션과 찾을 보물이 없는 미션(`item_total_count <= 0`)은 빼고,
    이미 완료한 다른 보물찾기는 그대로 후보에 둔다.
    거리가 같으면 `TREASURE_MISSION.id` 오름차순으로 순서를 고정한다.
    """
    statement = (
        select(TreasureMission, Location)
        .join(Location, Location.id == TreasureMission.location_id)
        .where(
            TreasureMission.id != treasure_mission_id,
            TreasureMission.item_total_count > 0,
        )
    )
    candidates = [
        (
            treasure_mission,
            location,
            calculate_distance_meter(latitude, longitude, location.my, location.mx),
        )
        for treasure_mission, location in db.execute(statement).all()
    ]
    nearest = sorted(
        candidates, key=lambda candidate: (candidate[2], candidate[0].id)
    )[:NEARBY_TREASURE_MISSION_LIMIT]

    # 보상 수령 여부는 미션마다 다시 조회하지 않고 한 번에 모은다. (N+1 방지)
    granted = reward_history.get_granted_rewards_map(
        db,
        MissionType.TREASURE,
        [treasure_mission.id for treasure_mission, _, _ in nearest],
        current_user_id,
    )
    # 공용 보상 변환이 캐릭터를 id 로 하나씩 조회하므로 먼저 한 번에 읽어 세션에 올려 둔다.
    # (세션의 identity map 은 약한 참조라 함수가 끝날 때까지 목록을 들고 있어야 한다)
    reward_characters = _preload_reward_characters(  # noqa: F841
        db, [treasure_mission.reward_detail for treasure_mission, _, _ in nearest]
    )

    return [
        NearbyTreasureMissionResponse(
            mission_id=treasure_mission.id,
            mission_type=MissionType.TREASURE,
            location_id=location.id,
            mission_title=treasure_mission.mission.mission_title,
            representative_image_url=kto.get_location_image_url(location.content_id),
            distance_meter=distance_meter,
            duration_minutes=calculate_duration_minutes(distance_meter),
            reward_detail=rewards.to_full_reward_detail(
                db,
                treasure_mission.reward_detail,
                granted.get(treasure_mission.id, GrantedRewards()),
            ),
        )
        for treasure_mission, location, distance_meter in nearest
    ]


def _preload_reward_characters(
    db: Session, reward_details: list[dict[str, Any] | None]
) -> list[ArCharacter]:
    """보상 캐릭터를 한 번에 읽어 세션에 올린다."""
    character_ids = {(reward or {}).get("ar_character_id") for reward in reward_details}
    character_ids.discard(None)
    if not character_ids:
        return []

    statement = select(ArCharacter).where(ArCharacter.id.in_(character_ids))
    return list(db.scalars(statement).all())


# ---------------------------------------------------------------------
# 받은 쿠폰
# ---------------------------------------------------------------------


def _find_received_coupons(
    db: Session, current_user_id: int
) -> list[ReceivedCouponResponse]:
    """현재 사용자가 지금까지 받은 쿠폰을 모은다.

    쿠폰 테이블은 없으므로 세부 미션의 `reward_detail` 과 진행도의
    `coupon_reward_granted` 를 조합한다. 같은 세부 미션을 여러 번 해도 한 번만 넣고,
    다른 미션에서 받은 같은 사용처·금액의 쿠폰은 각각 남긴다.
    """
    coupons = [
        *_find_culture_coupons(db, current_user_id),
        *_find_treasure_coupons(db, current_user_id),
        *_find_cooperative_coupons(db, current_user_id),
    ]
    # 순서는 명세에 없어서 유형명 → 세부 미션 id 오름차순으로 고정한다.
    coupons.sort(key=lambda coupon: (coupon.mission_type.value, coupon.mission_id))

    locations = _find_coupon_locations(db, coupons)
    image_urls = _find_coupon_location_image_urls(locations.values())

    return [
        _to_received_coupon(coupon, locations.get(coupon.coupon_location), image_urls)
        for coupon in coupons
    ]


def _to_received_coupon(
    coupon: _ReceivedCoupon, location: Location | None, image_urls: dict[int, str | None]
) -> ReceivedCouponResponse:
    """쿠폰 한 건에 장소 정보를 붙인다.

    이름이 같은 장소가 없으면 장소 id·주소·이미지가 모두 `None` 이고,
    장소는 찾았는데 대표 이미지만 없으면 이미지만 `None` 이다.
    """
    return ReceivedCouponResponse(
        coupon_location=coupon.coupon_location,
        coupon_price=coupon.coupon_price,
        location_id=location.id if location else None,
        location_address=location.location_address if location else None,
        location_image_url=image_urls.get(location.content_id) if location else None,
    )


def _to_received_coupon_or_none(
    mission_type: MissionType, mission_id: int, reward_detail: dict[str, Any] | None
) -> _ReceivedCoupon | None:
    """세부 미션의 보상에서 쿠폰 정보를 꺼낸다. 쿠폰 보상이 없으면 `None`."""
    coupon = rewards.to_coupon(reward_detail or {})
    if coupon is None:
        return None

    return _ReceivedCoupon(
        mission_type=mission_type,
        mission_id=mission_id,
        coupon_location=coupon.coupon_location,
        coupon_price=coupon.coupon_price,
    )


def _to_received_coupons(
    mission_type: MissionType, rows: list[tuple[int, dict[str, Any] | None]]
) -> list[_ReceivedCoupon]:
    """`(세부 미션 id, reward_detail)` 목록을 쿠폰 목록으로 바꾼다.

    같은 세부 미션을 여러 번 진행해 행이 여러 개여도 한 번만 넣는다.
    """
    coupons: dict[int, _ReceivedCoupon] = {}
    for mission_id, reward_detail in rows:
        if mission_id in coupons:
            continue
        coupon = _to_received_coupon_or_none(mission_type, mission_id, reward_detail)
        if coupon is not None:
            coupons[mission_id] = coupon
    return list(coupons.values())


def _find_culture_coupons(db: Session, current_user_id: int) -> list[_ReceivedCoupon]:
    """문화 미션에서 받은 쿠폰."""
    statement = (
        select(CultureMission.id, CultureMission.reward_detail)
        .join(
            CultureMissionProgress,
            CultureMissionProgress.culture_mission_id == CultureMission.id,
        )
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.coupon_reward_granted.is_(True),
        )
        .order_by(CultureMission.id)
    )
    return _to_received_coupons(MissionType.CULTURE, list(db.execute(statement).all()))


def _find_treasure_coupons(db: Session, current_user_id: int) -> list[_ReceivedCoupon]:
    """보물찾기 미션에서 받은 쿠폰."""
    statement = (
        select(TreasureMission.id, TreasureMission.reward_detail)
        .join(
            TreasureMissionProgress,
            TreasureMissionProgress.treasure_mission_id == TreasureMission.id,
        )
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.coupon_reward_granted.is_(True),
        )
        .order_by(TreasureMission.id)
    )
    return _to_received_coupons(MissionType.TREASURE, list(db.execute(statement).all()))


def _find_cooperative_coupons(db: Session, current_user_id: int) -> list[_ReceivedCoupon]:
    """협동 미션에서 받은 쿠폰.

    협동 진행도에는 사용자 정보가 없어서 참가 행으로 현재 사용자를 찾는다.
    나갔거나(삭제된 참가) 아직 수락되지 않은 참가, 삭제된 방은 수령 이력으로 보지 않는다.
    """
    statement = (
        select(CooperativeMission.id, CooperativeMission.reward_detail)
        .join(
            CooperativeMissionProgress,
            CooperativeMissionProgress.cooperative_mission_id == CooperativeMission.id,
        )
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.cooperative_mission_progress_id
            == CooperativeMissionProgress.id,
        )
        .where(
            CooperativeMissionProgress.coupon_reward_granted.is_(True),
            CooperativeMissionProgress.deleted_at.is_(None),
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
        )
        .order_by(CooperativeMission.id)
    )
    return _to_received_coupons(
        MissionType.COOPERATIVE, list(db.execute(statement).all())
    )


def _find_coupon_locations(
    db: Session, coupons: list[_ReceivedCoupon]
) -> dict[str, Location]:
    """쿠폰 사용처 이름과 **완전히 같은** 장소를 한 번에 찾는다. `사용처 이름 → 장소`.

    부분 일치나 유사어 검색은 하지 않는다. 이름이 같은 장소가 여러 개면 id 가 작은 장소를 쓴다.
    """
    coupon_locations = {coupon.coupon_location for coupon in coupons}
    if not coupon_locations:
        return {}

    statement = (
        select(Location)
        .where(Location.location_title.in_(coupon_locations))
        .order_by(Location.id)
    )
    locations: dict[str, Location] = {}
    for location in db.scalars(statement).all():
        locations.setdefault(location.location_title, location)
    return locations


def _find_coupon_location_image_urls(
    locations: Iterable[Location],
) -> dict[int, str | None]:
    """쿠폰 장소의 대표 이미지를 조회한다. `content_id → 이미지 URL`.

    같은 장소를 여러 쿠폰이 가리켜도 TourAPI 는 한 번만 호출한다.
    이미지를 얻지 못해도 조회 전체를 실패시키지 않고 그 장소만 `None` 이다.
    """
    return {
        content_id: kto.get_location_image_url(content_id)
        for content_id in {location.content_id for location in locations}
    }
