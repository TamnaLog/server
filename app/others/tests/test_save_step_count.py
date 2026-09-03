"""PUT /api/v1/users/me/step-counts - 걸음 수 저장 테스트.

기준 문서: app/others/docs/API_SPEC.md, app/others/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.datetimes import now_kst
from app.others import service
from app.user.models import StepCount, User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me/step-counts"

OTHER_USER_ID = 2

RECORDED_DATE = "2026-09-02"
RECORDED_MIDNIGHT = datetime(2026, 9, 2, 0, 0, 0)
CREATED_AT = datetime(2026, 9, 2, 23, 50, 0)


@pytest.fixture
def step_data(db_session: Session) -> None:
    """사용자 2명. 걸음 수 기록은 각 테스트에서 만든다."""
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
        ]
    )
    db_session.commit()


def _add_step_count(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    saved_at: datetime = RECORDED_MIDNIGHT,
    steps_count: int = 5000,
    created_at: datetime = CREATED_AT,
) -> None:
    db_session.add(
        StepCount(
            user_id=user_id,
            saved_at=saved_at,
            steps_count=steps_count,
            created_at=created_at,
        )
    )
    db_session.commit()


def _put(
    client: TestClient,
    *,
    body: dict[str, object] | None = None,
    recorded_date: str = RECORDED_DATE,
    steps_count: int = 8241,
    user_id: int = CURRENT_USER_ID,
) -> Any:
    payload = (
        {"recordedDate": recorded_date, "stepsCount": steps_count}
        if body is None
        else body
    )
    return client.put(ENDPOINT, json=payload, headers=auth_headers(user_id))


def _step_counts(db_session: Session) -> list[StepCount]:
    db_session.expire_all()
    return list(db_session.scalars(select(StepCount).order_by(StepCount.id)).all())


def _today() -> str:
    return now_kst().date().isoformat()


# ---------------------------------------------------------------------
# 저장 (신규)
# ---------------------------------------------------------------------


def test_걸음_수를_저장하면_204와_빈_본문을_반환한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    response = _put(client)

    assert response.status_code == 204
    assert response.content == b""

    step_counts = _step_counts(db_session)
    assert len(step_counts) == 1
    assert step_counts[0].user_id == CURRENT_USER_ID
    assert step_counts[0].steps_count == 8241


def test_saved_at은_기록_날짜의_KST_자정으로_저장한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _put(client, recorded_date="2026-09-02")

    # 요청을 받은 시각이 아니라 기록 대상 날짜다.
    assert _step_counts(db_session)[0].saved_at == datetime(2026, 9, 2, 0, 0, 0)


def test_걸음_수가_0이어도_저장한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    response = _put(client, steps_count=0)

    assert response.status_code == 204
    assert _step_counts(db_session)[0].steps_count == 0


def test_오늘_날짜로도_저장할_수_있다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    response = _put(client, recorded_date=_today())

    assert response.status_code == 204
    assert len(_step_counts(db_session)) == 1


# ---------------------------------------------------------------------
# 저장 (갱신)
# ---------------------------------------------------------------------


def test_같은_날짜로_다시_보내면_행을_추가하지_않고_갱신한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _add_step_count(db_session, steps_count=5000)

    _put(client, steps_count=8241)

    step_counts = _step_counts(db_session)
    assert len(step_counts) == 1
    assert step_counts[0].steps_count == 8241
    # 처음 기록한 시각은 그대로 둔다.
    assert step_counts[0].created_at == CREATED_AT


def test_기존_값보다_작아도_요청값으로_덮어쓴다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _add_step_count(db_session, steps_count=9000)

    _put(client, steps_count=1200)

    # 서버가 최댓값을 고르거나 누적해서 더하지 않는다.
    assert _step_counts(db_session)[0].steps_count == 1200


def test_여러_번_보내도_마지막_요청값이_남는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _put(client, steps_count=3000)
    _put(client, steps_count=7000)
    _put(client, steps_count=4500)

    step_counts = _step_counts(db_session)
    assert len(step_counts) == 1
    assert step_counts[0].steps_count == 4500


def test_날짜가_다르면_새_행을_만든다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _put(client, recorded_date="2026-09-01", steps_count=3000)
    _put(client, recorded_date="2026-09-02", steps_count=8241)

    step_counts = _step_counts(db_session)
    assert [(item.saved_at, item.steps_count) for item in step_counts] == [
        (datetime(2026, 9, 1, 0, 0, 0), 3000),
        (datetime(2026, 9, 2, 0, 0, 0), 8241),
    ]


def test_다른_사용자의_같은_날짜_기록은_건드리지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _add_step_count(db_session, user_id=OTHER_USER_ID, steps_count=5000)

    _put(client, steps_count=8241)

    step_counts = _step_counts(db_session)
    # 사용자별로 행이 따로 생긴다.
    assert [(item.user_id, item.steps_count) for item in step_counts] == [
        (OTHER_USER_ID, 5000),
        (CURRENT_USER_ID, 8241),
    ]


def test_토큰의_사용자로_저장한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _put(client, user_id=OTHER_USER_ID)

    # 요청 Body 에 사용자 id 가 없으므로 토큰 주인이 저장된다.
    assert _step_counts(db_session)[0].user_id == OTHER_USER_ID


# ---------------------------------------------------------------------
# 동시 요청 (유니크 제약)
# ---------------------------------------------------------------------


def test_한_사용자는_같은_날짜에_기록을_하나만_가진다(
    db_session: Session, step_data: None
) -> None:
    """`(user_id, saved_at)` 유니크 제약이 DB 수준에서도 중복을 막는다."""
    _add_step_count(db_session, steps_count=5000)

    with pytest.raises(IntegrityError):
        _add_step_count(db_session, steps_count=8241)

    db_session.rollback()


def test_유니크_충돌이_나면_기존_행을_갱신하고_중복_행을_만들지_않는다(
    client: TestClient,
    db_session: Session,
    step_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 조회 직후 다른 요청이 같은 날짜의 행을 먼저 만든 상황을 흉내 낸다.
    # (행은 이미 있는데 우리 쪽 조회 결과는 None 이라 INSERT 를 시도한다)
    _add_step_count(db_session, steps_count=5000)
    original_find = service._find_step_count
    calls: list[int] = []

    def find_once_missing(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            return None
        return original_find(*args, **kwargs)

    monkeypatch.setattr(service, "_find_step_count", find_once_missing)

    response = _put(client, steps_count=8241)

    assert response.status_code == 204
    step_counts = _step_counts(db_session)
    # 중복 행을 만들지 않고 기존 행을 갱신한다.
    assert len(step_counts) == 1
    assert step_counts[0].steps_count == 8241
    assert step_counts[0].created_at == CREATED_AT


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


def test_미래_날짜는_저장하지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    tomorrow = (now_kst().date() + timedelta(days=1)).isoformat()

    response = _put(client, recorded_date=tomorrow)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _step_counts(db_session) == []


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"stepsCount": 8241}, id="날짜_누락"),
        pytest.param({"recordedDate": RECORDED_DATE}, id="걸음_수_누락"),
        pytest.param(
            {"recordedDate": RECORDED_DATE, "stepsCount": -1}, id="음수_걸음_수"
        ),
        pytest.param(
            {"recordedDate": RECORDED_DATE, "stepsCount": 1.5}, id="정수가_아닌_걸음_수"
        ),
        pytest.param(
            {"recordedDate": "2026-09-02T10:00:00", "stepsCount": 8241},
            id="날짜가_아닌_recordedDate",
        ),
        pytest.param({"recordedDate": "어제", "stepsCount": 8241}, id="형식이_아닌_날짜"),
        pytest.param(
            {"recordedDate": RECORDED_DATE, "stepsCount": 8241, "userId": 2},
            id="정의되지_않은_필드",
        ),
        pytest.param({}, id="빈_body"),
    ],
)
def test_요청_Body가_잘못되면_400이다(
    client: TestClient, db_session: Session, step_data: None, body: dict
) -> None:
    response = _put(client, body=body)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _step_counts(db_session) == []


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


def test_인증_헤더가_없으면_401이다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.put(
        ENDPOINT, json={"recordedDate": RECORDED_DATE, "stepsCount": 8241}
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _step_counts(db_session) == []


def test_토큰의_사용자가_없으면_401이다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    response = _put(client, user_id=999)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _step_counts(db_session) == []


def test_문서에_401을_노출한다(client: TestClient) -> None:
    responses = client.get("/openapi.json").json()["paths"][ENDPOINT]["put"]["responses"]

    assert sorted(responses) == ["204", "400", "401", "500"]
