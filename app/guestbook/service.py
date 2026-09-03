"""방명록 도메인 비즈니스 로직.

기준 문서: app/guestbook/docs/API_SPEC.md, app/guestbook/docs/BUSINESS_RULES.md

`LOCATION` / `VISITED_LOCATION` 은 소유 도메인인 app/map/models.py 에서 import해서 쓴다.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from fastapi import UploadFile
from sqlalchemy import ColumnElement, Exists, Subquery, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.common import audios, images
from app.common.datetimes import now_kst
from app.core.errors import ConflictError, NotFoundError
from app.guestbook.models import (
    Guestbook,
    GuestbookLike,
    RoadGuestbook,
    RoadGuestbookLike,
)
from app.guestbook.schemas import (
    GeneralGuestbookResponse,
    GuestbookCreateRequest,
    GuestbookCreateResponse,
    GuestbookLikeRequest,
    GuestbookLikeResponse,
    GuestbookListQuery,
    GuestbookListResponse,
    GuestbookScope,
    GuestbookLocationResponse,
    GuestbookMissionResponse,
    GuestbookType,
    RoadGuestbookResponse,
    GuestbookWriteAvailabilityResponse,
    VisitedLocationResponse,
    VisitedLocationSummaryResponse,
    WriteAvailabilityQuery,
)
from app.map.models import Location, VisitedLocation
from app.mission.completion import is_mission_completed
from app.mission.models import Mission, MissionType
from app.services import blob_storage
from app.services.openai_audio_title import ValidatedAudio, generate_audio_title
from app.treasure_mission.models import ArCharacter
from app.user.models import User


logger = logging.getLogger(__name__)

LOCATION_NOT_FOUND = "LOCATION_NOT_FOUND"
LOCATION_NOT_VISITED = "LOCATION_NOT_VISITED"
MISSION_NOT_FOUND = "MISSION_NOT_FOUND"
GUESTBOOK_NOT_FOUND = "GUESTBOOK_NOT_FOUND"
OWN_GUESTBOOK_LIKE_NOT_ALLOWED = "OWN_GUESTBOOK_LIKE_NOT_ALLOWED"

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

    오디오가 있으면 커밋 전에 OpenAI 로 오디오 제목을 만든다. 제목 생성에 실패하면
    방명록도 만들지 않는다. (rollback + 업로드한 파일 삭제 후 공통 처리기가 500 으로 응답)

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
        # 업로드와 제목 생성이 같은 내용을 쓰도록 파일을 한 번만 읽어 둔다.
        validated_audios = _read_audios(request.audio_files)
        guestbook.content_audio_url = _upload_audios(
            validated_audios, request.guestbook_type, guestbook.id, uploaded_urls
        )
        guestbook.audio_title = _generate_audio_title(validated_audios)
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
            content_temperature_celsius=request.content_temperature_celsius,
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
        content_temperature_celsius=request.content_temperature_celsius,
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


def _read_audios(audio_files: list[UploadFile] | None) -> list[ValidatedAudio]:
    """업로드 오디오를 요청 순서대로 읽고 형식을 검증한다. 파일이 없으면 빈 목록.

    업로드 스트림은 한 번만 읽을 수 있어서 여기서 바이트로 들고 있는다.
    같은 내용을 Blob 업로드와 OpenAI 전사가 함께 쓴다. (허용 형식이 아니면 400)
    """
    if not audio_files:
        return []

    validated = []
    for audio in audio_files:
        data, audio_format = audios.read_and_detect(audio.file)
        validated.append(ValidatedAudio(data=data, audio_format=audio_format))
    return validated


def _upload_audios(
    validated_audios: list[ValidatedAudio],
    guestbook_type: GuestbookType,
    guestbook_id: int,
    uploaded_urls: list[str],
) -> list[str] | None:
    """오디오를 요청 순서대로 올리고 URL 목록을 만든다. 파일이 없으면 `None`."""
    if not validated_audios:
        return None

    prefix = _blob_prefix(guestbook_type, guestbook_id, AUDIO_BLOB_FOLDER)
    urls = []
    for audio in validated_audios:
        url = blob_storage.upload_file(
            audio.data,
            prefix=prefix,
            content_type=audio.audio_format.content_type,
            extension=audio.audio_format.extension,
        )
        uploaded_urls.append(url)
        urls.append(url)
    return urls


def _generate_audio_title(validated_audios: list[ValidatedAudio]) -> str | None:
    """첨부 오디오로 제목을 만든다. 오디오가 없으면 OpenAI 를 호출하지 않고 `None`.

    오디오가 여러 개여도 전체를 대표하는 제목 한 개만 만든다.
    생성에 실패하면 예외를 그대로 올려 방명록 작성 자체를 실패시킨다.
    """
    if not validated_audios:
        return None

    return generate_audio_title(validated_audios)


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
        audio_title=guestbook.audio_title,
        content_weather=guestbook.content_weather,
        content_temperature_celsius=_to_celsius(guestbook.content_temperature_celsius),
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


def _to_celsius(value: Decimal | float | None) -> float | None:
    """저장된 기온을 응답용 숫자로 바꾼다. 값이 없으면 `None`.

    DB 컬럼은 `DECIMAL(4,1)` 이라 `Decimal` 로 읽히는데, 응답에서는 문자열이 아니라
    JSON 숫자로 나가야 해서 `float` 로 바꾼다. (소수 첫째 자리라 값이 달라지지 않는다)
    """
    if value is None:
        return None
    return float(value)


# ---------------------------------------------------------------------
# 좋아요 공통 (방명록 조회 / 방명록 좋아요)
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class _LikeTable:
    """유형별로 다른 방명록/좋아요 테이블 묶음.

    두 방명록 테이블은 id 가 서로 겹칠 수 있어서, 요청의 `guestbookType` 으로만
    대상 테이블을 정한다. 선택한 유형에서 찾지 못해도 다른 유형을 다시 찾지 않는다.
    """

    guestbook_model: type[Guestbook] | type[RoadGuestbook]
    like_model: type[GuestbookLike] | type[RoadGuestbookLike]
    # 좋아요 테이블에서 방명록을 가리키는 FK 컬럼명. (유형마다 이름이 다르다)
    like_guestbook_id_field: str

    @property
    def like_guestbook_id(self) -> InstrumentedAttribute[int]:
        return getattr(self.like_model, self.like_guestbook_id_field)


_LIKE_TABLES: dict[GuestbookType, _LikeTable] = {
    GuestbookType.GENERAL: _LikeTable(Guestbook, GuestbookLike, "guestbook_id"),
    GuestbookType.ROAD: _LikeTable(RoadGuestbook, RoadGuestbookLike, "road_guestbook_id"),
}


def _active_like_counts(table: _LikeTable) -> Subquery:
    """`방명록 id → 활성 좋아요 수` 서브쿼리.

    방명록마다 개수를 다시 세지 않도록 한 번에 집계해서 목록 쿼리에 붙인다. (N+1 방지)
    좋아요가 하나도 없는 방명록은 이 결과에 없으므로 바깥에서 `0` 으로 채운다.
    """
    return (
        select(
            table.like_guestbook_id.label("guestbook_id"),
            func.count().label("like_count"),
        )
        .where(table.like_model.deleted_at.is_(None))
        .group_by(table.like_guestbook_id)
        .subquery()
    )


def _liked_by_current_user(
    table: _LikeTable, guestbook_id: InstrumentedAttribute[int], current_user_id: int
) -> Exists:
    """현재 사용자의 활성 좋아요가 있는지 판정하는 `EXISTS` 조각.

    개수와 달리 사용자 조건이 붙고, 취소된 좋아요는 없는 것으로 본다.
    """
    return (
        select(table.like_model.id)
        .where(
            table.like_guestbook_id == guestbook_id,
            table.like_model.user_id == current_user_id,
            table.like_model.deleted_at.is_(None),
        )
        .exists()
    )


# ---------------------------------------------------------------------
# 방명록 조회
# ---------------------------------------------------------------------


def get_guestbooks(
    db: Session, current_user_id: int, query: GuestbookListQuery
) -> GuestbookListResponse:
    """저장된 방명록을 조회 범위에 따라 유형별로 조회한다.

    `scope = ALL`(기본)이면 작성자로 거르지 않고, `scope = MINE` 이면 현재 사용자가
    쓴 방명록만 담는다. 범위와 무관하게 방문 장소(`visited_locations`)와 방명록별
    `is_liked` 는 **항상 현재 사용자 기준**이고, `like_count` 는 사용자를 가리지 않는다.

    페이지네이션 없이 전부 내려주고, 두 목록을 각각 최신순으로 정렬한다.
    지운 방명록(`deleted_at`)은 제외하고, 결과가 없어도 빈 배열로 응답한다.
    방문 장소는 방명록 유무와 상관없이 항상 함께 내려준다.

    읽기 전용이라 아무것도 저장하지 않고 Blob 도 건드리지 않는다.
    """
    return GuestbookListResponse(
        visited_locations=_find_visited_locations(db, current_user_id),
        general_guestbooks=_find_general_guestbooks(db, current_user_id, query.scope),
        road_guestbooks=_find_road_guestbooks(db, current_user_id, query.scope),
    )


def _scope_conditions(
    scope: GuestbookScope,
    user_id_column: InstrumentedAttribute[int],
    current_user_id: int,
) -> tuple[ColumnElement[bool], ...]:
    """조회 범위에 해당하는 `WHERE` 조건. 전체 조회면 조건이 없다.

    일반/길바닥이 같은 규칙을 쓰도록 컬럼만 바꿔 끼운다.
    """
    if scope is GuestbookScope.MINE:
        return (user_id_column == current_user_id,)
    return ()


def _find_visited_locations(
    db: Session, current_user_id: int
) -> list[VisitedLocationSummaryResponse]:
    """현재 사용자가 방문한 장소를 최근 방문순으로 중복 없이 가져온다.

    같은 장소를 여러 번 방문해도 장소는 한 번만 담는다. 그래서 방문 기록을 그대로
    나열하지 않고 장소별로 묶어 **가장 최근 방문 시각**으로 정렬한다.
    (최근 방문 시각이 같으면 장소 id 가 큰 쪽이 먼저다)
    """
    latest_visited_at = func.max(VisitedLocation.visited_at)
    statement = (
        select(Location.id, Location.location_title, latest_visited_at)
        .join(VisitedLocation, VisitedLocation.location_id == Location.id)
        .where(VisitedLocation.user_id == current_user_id)
        .group_by(Location.id, Location.location_title)
        .order_by(latest_visited_at.desc(), Location.id.desc())
    )
    return [
        VisitedLocationSummaryResponse(id=location_id, location_title=location_title)
        for location_id, location_title, _ in db.execute(statement).all()
    ]


def _find_general_guestbooks(
    db: Session, current_user_id: int, scope: GuestbookScope
) -> list[GeneralGuestbookResponse]:
    """일반 방명록을 장소/미션/작성자/좋아요와 함께 한 번의 쿼리로 읽는다. (N+1 방지)

    작성자 조건은 `scope = MINE` 일 때만 건다. `current_user_id` 는 그 외에는
    목록 범위가 아니라 `is_liked` 판정에만 쓴다.

    장소와 작성자는 NOT NULL FK 라 반드시 붙고, 미션과 AR 캐릭터는 없을 수 있어
    OUTER JOIN 한다. 좋아요는 방명록마다 세지 않고 개수 집계는 서브쿼리로,
    현재 사용자의 좋아요 여부는 `EXISTS` 로 한 번에 가져온다.
    """
    table = _LIKE_TABLES[GuestbookType.GENERAL]
    like_counts = _active_like_counts(table)
    is_liked = _liked_by_current_user(table, Guestbook.id, current_user_id)

    statement = (
        select(
            Guestbook,
            Location,
            Mission,
            User.nickname,
            ArCharacter.character_img_url,
            func.coalesce(like_counts.c.like_count, 0),
            is_liked,
        )
        .join(Location, Location.id == Guestbook.location_id)
        .join(User, User.id == Guestbook.user_id)
        .outerjoin(Mission, Mission.id == Guestbook.mission_id)
        .outerjoin(ArCharacter, ArCharacter.id == User.ar_character_id)
        .outerjoin(like_counts, like_counts.c.guestbook_id == Guestbook.id)
        .where(
            Guestbook.deleted_at.is_(None),
            *_scope_conditions(scope, Guestbook.user_id, current_user_id),
        )
        .order_by(Guestbook.saved_at.desc(), Guestbook.id.desc())
    )
    return [
        GeneralGuestbookResponse(
            id=guestbook.id,
            user_id=guestbook.user_id,
            character_img_url=character_img_url,
            user_nickname=nickname,
            location=_to_location_response(location),
            visited_at=guestbook.visited_at,
            content_image_urls=guestbook.content_img_url,
            content_writing=guestbook.content_writing,
            content_audio_urls=guestbook.content_audio_url,
            audio_title=guestbook.audio_title,
            content_weather=guestbook.content_weather,
            content_temperature_celsius=_to_celsius(guestbook.content_temperature_celsius),
            content_color_code=guestbook.content_color_code,
            is_liked=bool(liked),
            like_count=like_count,
            saved_at=guestbook.saved_at,
            mission=_to_mission_response(mission),
        )
        for (
            guestbook,
            location,
            mission,
            nickname,
            character_img_url,
            like_count,
            liked,
        ) in db.execute(statement).all()
    ]


def _find_road_guestbooks(
    db: Session, current_user_id: int, scope: GuestbookScope
) -> list[RoadGuestbookResponse]:
    """길바닥 방명록을 작성자/좋아요와 함께 읽는다. 장소와 미션은 붙이지 않는다.

    조회 범위는 일반 방명록과 같은 규칙을 쓴다.
    좋아요도 규칙이 같고 테이블만 `ROAD_GUESTBOOK_LIKE` 로 다르다.
    개수는 집계 서브쿼리로, 현재 사용자의 좋아요 여부는 `EXISTS` 로 한 번에 가져온다.
    """
    table = _LIKE_TABLES[GuestbookType.ROAD]
    like_counts = _active_like_counts(table)
    is_liked = _liked_by_current_user(table, RoadGuestbook.id, current_user_id)

    statement = (
        select(
            RoadGuestbook,
            User.nickname,
            ArCharacter.character_img_url,
            func.coalesce(like_counts.c.like_count, 0),
            is_liked,
        )
        .join(User, User.id == RoadGuestbook.user_id)
        .outerjoin(ArCharacter, ArCharacter.id == User.ar_character_id)
        .outerjoin(like_counts, like_counts.c.guestbook_id == RoadGuestbook.id)
        .where(
            RoadGuestbook.deleted_at.is_(None),
            *_scope_conditions(scope, RoadGuestbook.user_id, current_user_id),
        )
        .order_by(RoadGuestbook.saved_at.desc(), RoadGuestbook.id.desc())
    )
    return [
        RoadGuestbookResponse(
            id=guestbook.id,
            user_id=guestbook.user_id,
            character_img_url=character_img_url,
            user_nickname=nickname,
            location_alias=guestbook.location_alias,
            # 저장할 때와 같게 my = 위도, mx = 경도다.
            latitude=guestbook.my,
            longitude=guestbook.mx,
            visited_at=guestbook.visited_at,
            content_image_urls=guestbook.content_img_url,
            content_writing=guestbook.content_writing,
            content_audio_urls=guestbook.content_audio_url,
            audio_title=guestbook.audio_title,
            content_weather=guestbook.content_weather,
            content_temperature_celsius=_to_celsius(guestbook.content_temperature_celsius),
            content_color_code=guestbook.content_color_code,
            is_liked=bool(liked),
            like_count=like_count,
            saved_at=guestbook.saved_at,
        )
        for (
            guestbook,
            nickname,
            character_img_url,
            like_count,
            liked,
        ) in db.execute(statement).all()
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


# ---------------------------------------------------------------------
# 방명록 좋아요
# ---------------------------------------------------------------------


def set_guestbook_like(
    db: Session,
    current_user_id: int,
    guestbook_id: int,
    request: GuestbookLikeRequest,
) -> GuestbookLikeResponse:
    """방명록 좋아요 상태를 요청한 값으로 맞춘다.

    `is_liked` 는 현재 상태를 뒤집으라는 뜻이 아니라 **적용할 최종 상태**다.
    그래서 이미 같은 상태면 DB 를 건드리지 않고 성공 응답만 돌려준다. (멱등)

    좋아요는 지우지 않고 `deleted_at` 으로만 취소하며, 다시 누르면 새 행을 만들지 않고
    기존 행을 되살린다. (`created_at` 은 그대로 둔다)
    상태 변경과 개수 집계는 한 트랜잭션에서 하고, 중간에 실패하면 전부 롤백한다.
    """
    table = _LIKE_TABLES[request.guestbook_type]
    author_id = _get_like_target_author_id(db, table, guestbook_id)
    if author_id == current_user_id:
        raise ConflictError(
            OWN_GUESTBOOK_LIKE_NOT_ALLOWED,
            detail=f"사용자 {current_user_id} 는 자신의 방명록에 좋아요를 누를 수 없습니다.",
        )

    _apply_like(db, table, guestbook_id, current_user_id, request.is_liked)
    # 변경을 flush 한 뒤에 세야 방금 바꾼 상태가 개수에 반영된다.
    like_count = _count_active_likes(db, table, guestbook_id)
    db.commit()

    return GuestbookLikeResponse(
        guestbook_id=guestbook_id,
        guestbook_type=request.guestbook_type,
        is_liked=request.is_liked,
        like_count=like_count,
    )


def _get_like_target_author_id(
    db: Session, table: _LikeTable, guestbook_id: int
) -> int:
    """좋아요 대상 방명록의 작성자 id. 없거나 삭제됐으면 404.

    삭제된 방명록은 작성자 본인이 요청해도 "없는 방명록"으로 본다.
    (그래서 409 보다 이 검사가 먼저다)
    """
    author_id = db.scalar(
        select(table.guestbook_model.user_id).where(
            table.guestbook_model.id == guestbook_id,
            table.guestbook_model.deleted_at.is_(None),
        )
    )
    if author_id is None:
        raise NotFoundError(
            GUESTBOOK_NOT_FOUND,
            detail=f"방명록 {guestbook_id} 를 찾을 수 없습니다.",
        )
    return author_id


def _apply_like(
    db: Session,
    table: _LikeTable,
    guestbook_id: int,
    current_user_id: int,
    is_liked: bool,
) -> None:
    """좋아요 행을 요청한 상태로 맞춘다. 이미 같은 상태면 아무것도 바꾸지 않는다.

    바꾼 뒤에는 flush 한다. 세션이 `autoflush=False` 라서 flush 하지 않으면
    바로 뒤에 세는 활성 좋아요 수에 방금 바꾼 상태가 반영되지 않는다.
    """
    like = _find_like(db, table, guestbook_id, current_user_id)

    if is_liked:
        if like is None:
            _create_like(db, table, guestbook_id, current_user_id)
        elif like.deleted_at is not None:
            # 취소했던 좋아요는 새 행을 만들지 않고 되살린다. (`created_at` 유지)
            like.deleted_at = None
            db.flush()
        return

    if like is not None and like.deleted_at is None:
        like.deleted_at = now_kst()
        db.flush()


def _find_like(
    db: Session, table: _LikeTable, guestbook_id: int, current_user_id: int
) -> GuestbookLike | RoadGuestbookLike | None:
    """현재 사용자의 좋아요 행. 취소된 행도 되살려 써야 하므로 함께 찾는다."""
    statement = select(table.like_model).where(
        table.like_guestbook_id == guestbook_id,
        table.like_model.user_id == current_user_id,
    )
    return db.scalars(statement).first()


def _create_like(
    db: Session, table: _LikeTable, guestbook_id: int, current_user_id: int
) -> None:
    """좋아요 행을 새로 만든다.

    동시 요청이 먼저 행을 만들었으면 유니크 제약에 걸린다. 그때는 중복 행을 만들지 않고
    그 행을 다시 찾아 요청한 상태(활성)로 맞춘다.
    """
    like = table.like_model(
        **{table.like_guestbook_id_field: guestbook_id}, user_id=current_user_id
    )
    db.add(like)
    try:
        db.flush()
        return
    except IntegrityError:
        db.rollback()

    existing = _find_like(db, table, guestbook_id, current_user_id)
    if existing is None:
        # 유니크 충돌이 아닌 다른 이유였다면 그대로 500 으로 드러낸다.
        raise RuntimeError(
            f"좋아요 행을 만들지 못했습니다. (방명록 {guestbook_id})"
        )

    existing.deleted_at = None
    db.flush()


def _count_active_likes(db: Session, table: _LikeTable, guestbook_id: int) -> int:
    """방명록 한 건의 활성 좋아요 수. 취소된 좋아요는 세지 않는다.

    목록 조회의 `_active_like_counts()` 와 같은 조건이고, 여기서는 한 건만 세면 되므로
    집계 서브쿼리 대신 단일 COUNT 를 쓴다.
    """
    count = db.scalar(
        select(func.count())
        .select_from(table.like_model)
        .where(
            table.like_guestbook_id == guestbook_id,
            table.like_model.deleted_at.is_(None),
        )
    )
    return count or 0
