"""홈 방명록 개수 집계 모듈.

집계 기준이 확정되기 전까지는 서비스에 쌓인 일반 방명록과 길 위의 방명록의
전체 개수를 합산한다. 삭제된 방명록(`deleted_at`)은 제외한다.
추후 기준이 확정되면 이 모듈 내부 로직만 교체하면 된다.
(app/home/docs/BUSINESS_RULES.md - 6. 방명록 개수)
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.home.models import Guestbook, RoadGuestbook


def count_guestbooks(db: Session) -> int:
    """홈에 노출할 방명록 개수를 집계한다. (현재는 전체 합산)

    현재 사용자가 쓴 방명록 수가 아니라 서비스에 쌓인 방명록 수다.
    """
    # TODO: 집계 기준 확정 시 실제 집계 로직으로 교체
    guestbook_count = db.scalar(
        select(func.count()).select_from(Guestbook).where(Guestbook.deleted_at.is_(None))
    )
    road_guestbook_count = db.scalar(
        select(func.count()).select_from(RoadGuestbook).where(RoadGuestbook.deleted_at.is_(None))
    )
    return (guestbook_count or 0) + (road_guestbook_count or 0)
