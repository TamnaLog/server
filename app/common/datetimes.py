"""시간 처리 유틸.

프로젝트 정책상 시간은 한국시간(KST) 기준으로 다루고 DB에는 timezone 없는 DATETIME 으로 저장한다.
서버가 어느 타임존에서 돌든 같은 값이 나오도록, 시스템 로컬 시간 대신 KST 로 계산한다.
KST 는 서머타임이 없어 고정 오프셋(+09:00)으로 계산해도 정확하다.
"""

from datetime import datetime, timedelta, timezone


KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """현재 한국시간을 timezone 정보 없는 `datetime` 으로 반환한다."""
    return datetime.now(KST).replace(tzinfo=None)
