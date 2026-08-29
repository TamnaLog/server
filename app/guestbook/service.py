"""방명록 도메인 비즈니스 로직.

기준 문서: app/guestbook/docs/API_SPEC.md, app/guestbook/docs/BUSINESS_RULES.md

`LOCATION` / `VISITED_LOCATION` 은 소유 도메인인 app/map/models.py 에서 import해서 쓴다.
"""

import logging

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import audios, images
from app.common.datetimes import now_kst
from app.core.errors import ConflictError, NotFoundError
from app.guestbook.models import Guestbook, RoadGuestbook
from app.guestbook.schemas import (
    GeneralGuestbookResponse,
    GuestbookCreateRequest,
    GuestbookCreateResponse,
    GuestbookListResponse,
    GuestbookLocationResponse,
    GuestbookMissionResponse,
    GuestbookType,
    RoadGuestbookResponse,
    GuestbookWriteAvailabilityResponse,
    VisitedLocationResponse,
    WriteAvailabilityQuery,
)
from app.map.models import Location, VisitedLocation
from app.mission.completion import is_mission_completed
from app.mission.models import Mission, MissionType
from app.services import blob_storage


logger = logging.getLogger(__name__)

LOCATION_NOT_FOUND = "LOCATION_NOT_FOUND"
LOCATION_NOT_VISITED = "LOCATION_NOT_VISITED"
MISSION_NOT_FOUND = "MISSION_NOT_FOUND"

# Blob 저장 경로. 유형과 생성된 방명록 id 로 나눈다.
GUESTBOOK_BLOB_PREFIX = "guestbook"
IMAGE_BLOB_FOLDER = "images"
AUDIO_BLOB_FOLDER = "audios"


def get_write_availability(
    db: Session, current_user_id: int, query: WriteAvailabilityQuery
) -> GuestbookWriteAvailabilityResponse:
    """방명록 작성 가능 여부 조회.

    현재 사용자가 그 장소를 방문한 기록이 있는지만 본다.
    이미 방명록을 썼는지, 미션을 했는지, 방문한 지 얼마나 지났는지는 따지지 않는다.

    읽기 전용이라 아무것도 저장하지 않는다.
    """
    location = _get_location(db, query.location_id)
    visited_at = _find_latest_visited_at(db, current_user_id, location.id)
    if visited_at is None:
        # 방문하지 않은 것은 정상 결과다. 오류로 처리하지 않는다.
        return GuestbookWriteAvailabilityResponse(can_write=False, visited_location=None)

    return GuestbookWriteAvailabilityResponse(
        can_write=True,
        visited_location=VisitedLocationResponse(
            location_id=location.id,
            location_name=location.location_title,
            visited_at=visited_at,
        ),
    )


def _get_location(db: Session, location_id: int) -> Location:
    """장소를 먼저 조회한다.

    없는 장소와 "있지만 방문하지 않은 장소"를 같은 `canWrite=false` 로 합치지 않기 위해
    방문 기록보다 먼저 확인한다.
    """
    location = db.get(Location, location_id)
    if location is None:
        raise NotFoundError(
            LOCATION_NOT_FOUND, detail=f"장소 {location_id} 를 찾을 수 없습니다."
        )
    return location


def _find_latest_visited_at(db: Session, current_user_id: int, location_id: int):
    """현재 사용자의 가장 최근 방문 시각을 찾는다. 방문한 적이 없으면 `None`.

    같은 장소를 여러 번 방문할 수 있으므로 목록을 파이썬에서 정렬하지 않고
    DB에서 정렬해 한 건만 가져온다. 방문 시각이 같으면 나중에 저장된 기록을 쓴다.
    """
    statement = (
        select(VisitedLocation.visited_at)
        .where(
            VisitedLocation.user_id == current_user_id,
            VisitedLocation.location_id == location_id,
        )
        .order_by(VisitedLocation.visited_at.desc(), VisitedLocation.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


# ---------------------------------------------------------------------
# 방명록 작성
# ---------------------------------------------------------------------


def create_guestbook(
    db: Session, current_user_id: int, request: GuestbookCreateRequest
) -> GuestbookCreateResponse:
    """방명록 작성. (일반 / 길바닥)

    - `GENERAL`: 장소 존재 → 방문 이력 → 미션 순서로 확인한 뒤 `GUESTBOOK` 에 저장한다.
    - `ROAD`: 장소/방문/미션을 보지 않고 전달받은 좌표로 `ROAD_GUESTBOOK` 에 저장한다.

    파일은 방명록 id 가 필요한 경로에 올려야 해서 먼저 `flush()` 로 id 를 얻고,
    업로드가 모두 끝난 뒤 한 번만 커밋한다. 중간에 실패하면 이미 올린 파일을 지운다.

    같은 요청을 여러 번 보내면 그때마다 새 방명록이 생긴다. (멱등 API 가 아니다)
    """
    mission_id = _resolve_general_mission_id(db, current_user_id, request)
    guestbook = _create_guestbook_row(db, current_user_id, request, mission_id)
    db.add(guestbook)
    # Blob 경로에 넣을 방명록 id 를 얻기 위해 커밋 전에 flush 한다.
    db.flush()

    uploaded_urls: list[str] = []
    try:
        guestbook.content_img_url = _upload_images(
            request.image_files, request.guestbook_type, guestbook.id, uploaded_urls
        )
        guestbook.content_audio_url = _upload_audios(
            request.audio_files, request.guestbook_type, guestbook.id, uploaded_urls
        )
        db.commit()
    except Exception:
        # DB 가 참조하지 않는 파일이 남지 않도록 올린 파일을 모두 되돌린다.
        db.rollback()
        _delete_uploaded(uploaded_urls)
        raise

    db.refresh(guestbook)
    return _to_create_response(guestbook)


def _resolve_general_mission_id(
    db: Session, current_user_id: int, request: GuestbookCreateRequest
) -> int | None:
    """`GENERAL` 요청의 장소·방문·미션을 확인하고 저장할 미션 id 를 정한다.

    `ROAD` 는 장소도 미션도 쓰지 않으므로 아무것도 조회하지 않는다.
    미션이 있는데 아직 완료하지 않았으면 오류가 아니라 `None` 으로 저장한다.

    `GENERAL` 의 `location_id` 는 요청 스키마에서 이미 검증했다. (없으면 여기까지 오지 않고 400)
    """
    if request.guestbook_type is GuestbookType.ROAD:
        return None

    assert request.location_id is not None
    location = _get_location(db, request.location_id)
    _check_visited(db, current_user_id, location.id)

    if request.mission_id is None:
        return None

    mission = db.get(Mission, request.mission_id)
    if mission is None:
        raise NotFoundError(
            MISSION_NOT_FOUND, detail=f"미션 {request.mission_id} 를 찾을 수 없습니다."
        )

    return mission.id if is_mission_completed(db, current_user_id, mission) else None


def _check_visited(db: Session, current_user_id: int, location_id: int) -> None:
    """현재 사용자의 방문 이력이 한 건이라도 있는지 확인한다.

    방문 날짜와 요청의 `visitedAt` 이 같은지는 보지 않는다.
    이미 방명록을 썼는지도 보지 않으므로 같은 장소에 몇 번이든 쓸 수 있다.
    """
    visited_id = db.scalar(
        select(VisitedLocation.id)
        .where(
            VisitedLocation.user_id == current_user_id,
            VisitedLocation.location_id == location_id,
        )
        .limit(1)
    )
    if visited_id is None:
        raise ConflictError(
            LOCATION_NOT_VISITED,
            detail=(
                f"사용자 {current_user_id} 는 장소 {location_id} 를 방문한 기록이 없습니다."
            ),
        )


def _create_guestbook_row(
    db: Session,
    current_user_id: int,
    request: GuestbookCreateRequest,
    mission_id: int | None,
) -> Guestbook | RoadGuestbook:
    """유형에 맞는 방명록 행을 만든다. 파일 URL 은 업로드 후에 채운다.

    유형별 필수 값은 요청 스키마에서 이미 검증했다. (없으면 여기까지 오지 않고 400)
    아래 `assert` 는 그 사실을 타입으로도 좁혀 주기 위한 것이다.
    """
    if request.guestbook_type is GuestbookType.GENERAL:
        assert request.location_id is not None
        return Guestbook(
            user_id=current_user_id,
            location_id=request.location_id,
            visited_at=request.visited_at,
            content_writing=request.content_writing,
            content_weather=request.content_weather,
            content_color_code=request.content_color_code,
            saved_at=now_kst(),
            mission_id=mission_id,
        )

    assert request.location_alias is not None
    assert request.latitude is not None
    assert request.longitude is not None
    return RoadGuestbook(
        user_id=current_user_id,
        location_id=None,
        location_alias=request.location_alias,
        visited_at=request.visited_at,
        content_writing=request.content_writing,
        content_weather=request.content_weather,
        content_color_code=request.content_color_code,
        # LOCATION 과 같게 mx = 경도, my = 위도로 저장한다.
        mx=request.longitude,
        my=request.latitude,
        saved_at=now_kst(),
    )


def _upload_images(
    image_files: list[UploadFile] | None,
    guestbook_type: GuestbookType,
    guestbook_id: int,
    uploaded_urls: list[str],
) -> list[str] | None:
    """이미지를 요청 순서대로 올리고 URL 목록을 만든다. 파일이 없으면 `None`."""
    if not image_files:
        return None

    prefix = _blob_prefix(guestbook_type, guestbook_id, IMAGE_BLOB_FOLDER)
    urls = []
    for image in image_files:
        data, image_format = images.read_and_detect(image.file)
        url = blob_storage.upload_file(
            data,
            prefix=prefix,
            content_type=image_format.content_type,
            extension=image_format.extension,
        )
        uploaded_urls.append(url)
        urls.append(url)
    return urls


def _upload_audios(
    audio_files: list[UploadFile] | None,
    guestbook_type: GuestbookType,
    guestbook_id: int,
    uploaded_urls: list[str],
) -> list[str] | None:
    """오디오를 요청 순서대로 올리고 URL 목록을 만든다. 파일이 없으면 `None`."""
    if not audio_files:
        return None

    prefix = _blob_prefix(guestbook_type, guestbook_id, AUDIO_BLOB_FOLDER)
    urls = []
    for audio in audio_files:
        data, audio_format = audios.read_and_detect(audio.file)
        url = blob_storage.upload_file(
            data,
            prefix=prefix,
            content_type=audio_format.content_type,
            extension=audio_format.extension,
        )
        uploaded_urls.append(url)
        urls.append(url)
    return urls


def _blob_prefix(guestbook_type: GuestbookType, guestbook_id: int, folder: str) -> str:
    """`guestbook/{유형}/{방명록 id}/{images|audios}` 형태의 저장 경로."""
    return f"{GUESTBOOK_BLOB_PREFIX}/{guestbook_type.value.lower()}/{guestbook_id}/{folder}"


def _delete_uploaded(uploaded_urls: list[str]) -> None:
    """실패 전에 올린 파일을 지운다.

    삭제에 실패해도 원래 발생한 예외를 가리지 않도록 로그만 남기고 넘어간다.
    """
    for url in uploaded_urls:
        try:
            blob_storage.delete_file(url)
        except Exception:
            logger.exception("업로드한 방명록 파일 삭제에 실패했습니다: %s", url)


def _to_create_response(
    guestbook: Guestbook | RoadGuestbook,
) -> GuestbookCreateResponse:
    """저장된 값만으로 1-depth 응답을 만든다.

    두 테이블이 가진 컬럼이 달라서 공통 값을 먼저 채우고 유형별 값만 덧붙인다.
    유형에서 쓰지 않는 필드는 키를 지우지 않고 `null` 로 남는다.
    """
    is_general = isinstance(guestbook, Guestbook)
    response = GuestbookCreateResponse(
        guestbook_id=guestbook.id,
        guestbook_type=GuestbookType.GENERAL if is_general else GuestbookType.ROAD,
        visited_at=guestbook.visited_at,
        content_image_urls=guestbook.content_img_url,
        content_writing=guestbook.content_writing,
        content_audio_urls=guestbook.content_audio_url,
        content_weather=guestbook.content_weather,
        content_color_code=guestbook.content_color_code,
        saved_at=guestbook.saved_at,
    )

    if isinstance(guestbook, Guestbook):
        response.location_id = guestbook.location_id
        response.mission_id = guestbook.mission_id
    else:
        response.location_alias = guestbook.location_alias
        # LOCATION 과 같게 mx = 경도, my = 위도로 저장돼 있다.
        response.latitude = guestbook.my
        response.longitude = guestbook.mx

    return response


# ---------------------------------------------------------------------
# 방명록 조회
# ---------------------------------------------------------------------


def get_guestbooks(db: Session, current_user_id: int) -> GuestbookListResponse:
    """현재 사용자가 쓴 방명록 전체를 유형별로 조회한다.

    페이지네이션 없이 전부 내려주고, 두 목록을 각각 최신순으로 정렬한다.
    지운 방명록(`deleted_at`)은 제외하고, 결과가 없어도 빈 배열로 응답한다.

    읽기 전용이라 아무것도 저장하지 않고 Blob 도 건드리지 않는다.
    """
    return GuestbookListResponse(
        general_guestbooks=_find_general_guestbooks(db, current_user_id),
        road_guestbooks=_find_road_guestbooks(db, current_user_id),
    )


def _find_general_guestbooks(
    db: Session, current_user_id: int
) -> list[GeneralGuestbookResponse]:
    """일반 방명록을 장소/미션과 함께 한 번의 쿼리로 읽는다. (N+1 방지)

    장소는 NOT NULL FK 라 반드시 붙고, 미션은 없을 수 있어 OUTER JOIN 한다.
    """
    statement = (
        select(Guestbook, Location, Mission)
        .join(Location, Location.id == Guestbook.location_id)
        .outerjoin(Mission, Mission.id == Guestbook.mission_id)
        .where(
            Guestbook.user_id == current_user_id,
            Guestbook.deleted_at.is_(None),
        )
        .order_by(Guestbook.saved_at.desc(), Guestbook.id.desc())
    )
    return [
        GeneralGuestbookResponse(
            id=guestbook.id,
            location=_to_location_response(location),
            visited_at=guestbook.visited_at,
            content_image_urls=guestbook.content_img_url,
            content_writing=guestbook.content_writing,
            content_audio_urls=guestbook.content_audio_url,
            content_weather=guestbook.content_weather,
            content_color_code=guestbook.content_color_code,
            saved_at=guestbook.saved_at,
            mission=_to_mission_response(mission),
        )
        for guestbook, location, mission in db.execute(statement).all()
    ]


def _find_road_guestbooks(
    db: Session, current_user_id: int
) -> list[RoadGuestbookResponse]:
    """길바닥 방명록을 읽는다. 장소/미션은 붙이지 않는다."""
    statement = (
        select(RoadGuestbook)
        .where(
            RoadGuestbook.user_id == current_user_id,
            RoadGuestbook.deleted_at.is_(None),
        )
        .order_by(RoadGuestbook.saved_at.desc(), RoadGuestbook.id.desc())
    )
    return [
        RoadGuestbookResponse(
            id=guestbook.id,
            location_alias=guestbook.location_alias,
            # 저장할 때와 같게 my = 위도, mx = 경도다.
            latitude=guestbook.my,
            longitude=guestbook.mx,
            visited_at=guestbook.visited_at,
            content_image_urls=guestbook.content_img_url,
            content_writing=guestbook.content_writing,
            content_audio_urls=guestbook.content_audio_url,
            content_weather=guestbook.content_weather,
            content_color_code=guestbook.content_color_code,
            saved_at=guestbook.saved_at,
        )
        for guestbook in db.scalars(statement).all()
    ]


def _to_location_response(location: Location) -> GuestbookLocationResponse:
    """LOCATION 은 my=위도 / mx=경도로 저장한다."""
    return GuestbookLocationResponse(
        id=location.id,
        location_title=location.location_title,
        location_address=location.location_address,
        location_category=location.location_category,
        latitude=location.my,
        longitude=location.mx,
    )


def _to_mission_response(mission: Mission | None) -> GuestbookMissionResponse | None:
    """연결된 미션이 없으면 `None`. 완료 여부를 다시 확인하지 않는다."""
    if mission is None:
        return None

    return GuestbookMissionResponse(
        id=mission.id,
        mission_type=MissionType(mission.mission_type),
        mission_title=mission.mission_title,
    )
