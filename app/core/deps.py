"""공통 FastAPI 의존성."""

# 로그인 기능 구현 전까지 현재 사용자는 항상 id=1로 처리한다.
CURRENT_USER_ID = 1


def get_current_user_id() -> int:
    """현재 로그인한 사용자 id를 반환한다."""
    return CURRENT_USER_ID
