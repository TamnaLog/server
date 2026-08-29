"""GET /api/v1/guestbooks/write-availability - 방명록 작성 가능 여부 조회 테스트.

기준 문서: app/guestbook/docs/API_SPEC.md, app/guestbook/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.map.models import Location, VisitedLocation
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/guestbooks/write-availability"

LOCATION_ID = 39
LOCATION_TITLE = "섭지코지"
OTHER_LOCATION_ID = 40

OTHER_USER_ID = 2

VISITED_AT = datetime(2026, 8, 29, 14, 20, 0)
EARLIER_VISITED_AT = datetime(2026, 8, 20, 9, 0, 0)


def _params(location_id: object = LOCATION_ID) -> dict[str, object]:
    return {"locationId": location_id}


@pytest.fixture
def location_data(db_session: Session) -> None:
    """장소 두 곳과 사용자 두 명. 방문 기록은 각 테스트에서 만든다."""
    db_session.add_all(
        [
            Location(
                id=LOCATION_ID,
                content_id=126508,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 성산읍 섭지코지로 107",
                location_category="해변",
                radius=300,
                mx=126.9300,
                my=33.4250,
            ),
            Location(
                id=OTHER_LOCATION_ID,
                content_id=126273,
                location_title="협재해수욕장",
                location_address="제주특별자치도 제주시 한림읍 한림로 329-10",
                location_category="해변",
                radius=400,
                mx=126.2396,
                my=33.3940,
            ),
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


def _add_visit(
    db_session: Session,
    *,
    visit_id: int,
    visited_at: datetime = VISITED_AT,
    user_id: int = CURRENT_USER_ID,
    location_id: int = LOCATION_ID,
) -> None:
    db_session.add(
        VisitedLocation(
            id=visit_id,
            user_id=user_id,
            location_id=location_id,
            visited_at=visited_at,
        )
    )
    db_session.commit()


def _visits(db_session: Session) -> list[VisitedLocation]:
    db_session.expire_all()
    return list(
        db_session.scalars(select(VisitedLocation).order_by(VisitedLocation.id)).all()
    )


def _get(client: TestClient, **overrides: object) -> dict:
    response = client.get(
        ENDPOINT, params=_params(**overrides), headers=auth_headers(CURRENT_USER_ID)
    )
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------
# 방문 기록이 있는 경우
# ---------------------------------------------------------------------


def test_방문한_장소면_작성_가능과_장소_정보를_반환한다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    _add_visit(db_session, visit_id=1)

    body = _get(client)

    assert body == {
        "canWrite": True,
        "visitedLocation": {
            "locationId": LOCATION_ID,
            "locationName": LOCATION_TITLE,
            # KST 기준 offset 없는 ISO 8601
            "visitedAt": "2026-08-29T14:20:00",
        },
    }


def test_여러_번_방문했으면_가장_최근_방문_시각을_반환한다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    _add_visit(db_session, visit_id=1, visited_at=EARLIER_VISITED_AT)
    _add_visit(db_session, visit_id=2, visited_at=VISITED_AT)
    _add_visit(db_session, visit_id=3, visited_at=datetime(2026, 8, 25, 8, 0, 0))

    body = _get(client)

    assert body["visitedLocation"]["visitedAt"] == "2026-08-29T14:20:00"


def test_방문_시각이_같으면_id가_큰_기록을_사용한다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    # 같은 시각 기록이 여러 개여도 결과가 흔들리면 안 된다.
    _add_visit(db_session, visit_id=1, visited_at=VISITED_AT)
    _add_visit(db_session, visit_id=2, visited_at=VISITED_AT)

    body = _get(client)

    assert body["canWrite"] is True
    assert body["visitedLocation"]["visitedAt"] == "2026-08-29T14:20:00"


# ---------------------------------------------------------------------
# 방문 기록이 없는 경우
# ---------------------------------------------------------------------


def test_방문_기록이_없으면_작성_불가와_null을_반환한다(
    client: TestClient, location_data: None
) -> None:
    body = _get(client)

    # 키를 생략하지 않고 null 로 내려준다.
    assert body == {"canWrite": False, "visitedLocation": None}


def test_다른_사용자만_방문한_장소는_작성_가능이_아니다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    _add_visit(db_session, visit_id=1, user_id=OTHER_USER_ID)

    body = _get(client)

    assert body == {"canWrite": False, "visitedLocation": None}


def test_다른_장소_방문_기록은_이_장소의_작성_가능_여부에_영향을_주지_않는다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    _add_visit(db_session, visit_id=1, location_id=OTHER_LOCATION_ID)

    body = _get(client)

    assert body == {"canWrite": False, "visitedLocation": None}


def test_방명록_작성_이력은_판단_조건이_아니다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    # 이미 방명록을 썼는지는 보지 않으므로, 방문 기록만 있으면 계속 true 다.
    _add_visit(db_session, visit_id=1)

    first = _get(client)
    second = _get(client)

    assert first["canWrite"] is True
    assert second == first


# ---------------------------------------------------------------------
# 읽기 전용
# ---------------------------------------------------------------------


def test_조회는_방문_기록을_바꾸지_않는다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    _add_visit(db_session, visit_id=1)
    before = [(visit.id, visit.visited_at) for visit in _visits(db_session)]

    _get(client)

    assert [(visit.id, visit.visited_at) for visit in _visits(db_session)] == before


def test_방문_기록이_없어도_새로_만들지_않는다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    _get(client)

    assert _visits(db_session) == []


def test_장소를_찾지_못한_요청도_데이터를_바꾸지_않는다(
    client: TestClient, db_session: Session, location_data: None
) -> None:
    _add_visit(db_session, visit_id=1)

    client.get(ENDPOINT, params=_params(999), headers=auth_headers(CURRENT_USER_ID))

    assert len(_visits(db_session)) == 1


# ---------------------------------------------------------------------
# 404 LOCATION_NOT_FOUND
# ---------------------------------------------------------------------


def test_장소가_없으면_404_LOCATION_NOT_FOUND로_응답한다(
    client: TestClient, location_data: None
) -> None:
    response = client.get(
        ENDPOINT, params=_params(999), headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 404
    assert response.json() == {"code": "LOCATION_NOT_FOUND"}


def test_없는_장소는_방문하지_않은_장소와_구분한다(
    client: TestClient, location_data: None
) -> None:
    # 둘 다 canWrite=false 로 합쳐지면 안 된다.
    missing = client.get(
        ENDPOINT, params=_params(999), headers=auth_headers(CURRENT_USER_ID)
    )
    not_visited = client.get(
        ENDPOINT, params=_params(), headers=auth_headers(CURRENT_USER_ID)
    )

    assert missing.status_code == 404
    assert not_visited.status_code == 200
    assert not_visited.json()["canWrite"] is False


# ---------------------------------------------------------------------
# 400 / 401
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="장소_id_누락"),
        pytest.param({"locationId": 0}, id="0인_장소_id"),
        pytest.param({"locationId": -1}, id="음수_장소_id"),
        pytest.param({"locationId": "abc"}, id="정수가_아닌_장소_id"),
    ],
)
def test_장소_id가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, location_data: None, params: dict
) -> None:
    response = client.get(ENDPOINT, params=params, headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, location_data: None
) -> None:
    response = client.get(ENDPOINT, params=_params(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_인증_헤더가_없으면_401로_응답한다(
    client: TestClient, location_data: None
) -> None:
    # TestClient 기본 헤더를 지워서 헤더 없는 요청을 만든다.
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT, params=_params())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
