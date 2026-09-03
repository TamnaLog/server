"""기타 도메인 비즈니스 로직.

기준 문서: app/others/docs/API_SPEC.md, app/others/docs/BUSINESS_RULES.md

`STEP_COUNT` 는 소유 도메인인 app/user/models.py,
`GPS` / `LOCATION` / `VISITED_LOCATION` 은 app/map/models.py 에서 import해서 쓴다.
"""

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.map.models import Gps, Location, VisitedLocation
from app.others.schemas import GpsSaveRequest, StepCountSaveRequest
from app.others.visit_detector import LocationArea, find_visited_location_ids
from app.user.models import StepCount


def save_step_count(
    db: Session, current_user_id: int, request: StepCountSaveRequest
) -> None:
    """하루 누적 걸음 수를 저장한다. (사용자 + 기록 날짜당 한 행)

    같은 날짜로 다시 보내면 행을 추가하지 않고 `steps_count` 만 요청값으로 바꾼다.
    프론트가 보낸 값이 그 날짜의 최종값이므로, **기존 값보다 작아도 그대로 덮어쓴다.**
    (서버가 최댓값을 고르거나 누적해서 더하지 않는다)

    조회·생성·갱신을 한 트랜잭션에서 처리하고 커밋까지 끝나야 성공이다.
    """
    saved_at = _to_kst_midnight(request.recorded_date)
    step_count = _find_step_count(db, current_user_id, saved_at)

    if step_count is None:
        _create_step_count(db, current_user_id, saved_at, request.steps_count)
    else:
        # `created_at` 은 처음 기록한 시각 그대로 두고 걸음 수만 바꾼다.
        step_count.steps_count = request.steps_count

    db.commit()


def _to_kst_midnight(recorded_date: date) -> datetime:
    """기록 날짜를 저장 키로 쓸 KST 자정으로 바꾼다.

    `saved_at` 은 요청을 받은 시각이 아니라 **기록 대상 날짜**다.
    요청 시각으로 날짜를 정하면 자정 전후 요청이 다른 날짜로 갈라진다.
    (입력값은 프로젝트 정책대로 timezone 변환 없이 KST 로 취급한다)
    """
    return datetime.combine(recorded_date, time.min)


def _find_step_count(
    db: Session, current_user_id: int, saved_at: datetime
) -> StepCount | None:
    """그 사용자·날짜의 기록. 없으면 `None`."""
    statement = select(StepCount).where(
        StepCount.user_id == current_user_id,
        StepCount.saved_at == saved_at,
    )
    return db.scalars(statement).first()


def _create_step_count(
    db: Session, current_user_id: int, saved_at: datetime, steps_count: int
) -> None:
    """기록을 새로 만든다.

    동시 요청이 먼저 같은 날짜의 행을 만들었으면 유니크 제약에 걸린다.
    그때는 중복 행을 만들지 않고 그 행을 다시 찾아 요청값으로 갱신한다.
    """
    db.add(
        StepCount(user_id=current_user_id, saved_at=saved_at, steps_count=steps_count)
    )
    try:
        db.flush()
        return
    except IntegrityError:
        db.rollback()

    existing = _find_step_count(db, current_user_id, saved_at)
    if existing is None:
        # 유니크 충돌이 아닌 다른 이유였다면 그대로 500 으로 드러낸다.
        raise RuntimeError(
            f"걸음 수 기록을 만들지 못했습니다. (사용자 {current_user_id}, {saved_at:%Y-%m-%d})"
        )

    existing.steps_count = steps_count


# ---------------------------------------------------------------------
# GPS 및 방문 장소 저장
# ---------------------------------------------------------------------


def save_gps(db: Session, current_user_id: int, request: GpsSaveRequest) -> None:
    """GPS 좌표를 저장하고, 그 좌표로 판정한 방문 장소를 함께 기록한다.

    방문 시각은 서버가 요청을 받은 시각이 아니라 **좌표를 측정한 시각**(`recordedAt`)이다.
    GPS 한 건과 그 좌표에서 나온 방문 기록은 한 트랜잭션으로 저장하고,
    하나라도 실패하면 전부 롤백한다.

    지금은 진입/이탈이나 체류 시간을 보지 않으므로, 반경 안에 머무는 동안
    요청할 때마다 방문 기록이 쌓인다. (판정 규칙은 `visit_detector` 가 담당한다)
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

    for location_id in _find_visited_location_ids(db, request):
        db.add(
            VisitedLocation(
                user_id=current_user_id,
                location_id=location_id,
                visited_at=request.recorded_at,
            )
        )

    db.commit()


def _find_visited_location_ids(db: Session, request: GpsSaveRequest) -> list[int]:
    """요청 좌표로 방문한 장소를 찾는다.

    판정 자체는 `visit_detector` 가 하고, 여기서는 장소를 읽어 넘겨주기만 한다.
    장소 수가 많아지면 이 조회에 좌표 범위 필터(또는 공간 질의)를 먼저 걸어야 한다.
    """
    locations = db.scalars(select(Location).order_by(Location.id)).all()
    return find_visited_location_ids(
        latitude=request.latitude,
        longitude=request.longitude,
        locations=[
            # LOCATION 은 my = 위도, mx = 경도로 저장돼 있다.
            LocationArea(
                id=location.id,
                latitude=location.my,
                longitude=location.mx,
                radius_meter=location.radius,
            )
            for location in locations
        ],
    )
