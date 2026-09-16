"""POST /api/v1/users/me/gps - GPS 및 방문 장소 저장 테스트.

기준 문서: app/others/docs/API_SPEC.md, app/others/docs/BUSINESS_RULES.md
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.map.models import Gps, Location, VisitedLocation
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me/gps"

OTHER_USER_ID = 2

# 성산일출봉과 거기서 약 2km 떨어진 장소. (둘 다 판정 반경 5km 안이다)
LOCATION_ID = 39
LOCATION_LATITUDE = 33.4582
LOCATION_LONGITUDE = 126.9331
LOCATION_RADIUS = 300

NEARBY_LOCATION_ID = 40
# 이 위도에서 경도 1도는 약 92,768m 라 약 2km 떨어진 지점이다.
NEARBY_LONGITUDE = LOCATION_LONGITUDE + 2_000 / 92_768

# 위 장소들과 5km 넘게 떨어진 장소 (약 42km)
FAR_LOCATION_ID = 41
FAR_LATITUDE = 33.2500
FAR_LONGITUDE = 126.5600

RECORDED_AT = "2026-09-03T14:30:00"
RECORDED_DATETIME = datetime(2026, 9, 3, 14, 30, 0)


@pytest.fixture
def gps_data(db_session: Session) -> None:
    """사용자 2명 + 장소 3곳. (5km 안의 장소 2곳 + 멀리 있는 장소 1곳)

    `radius` 는 판정에 쓰이지 않지만 컬럼이 NOT NULL 이라 값은 채워 둔다.
    """
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
            Location(
                id=LOCATION_ID,
                content_id=126508,
                location_title="성산일출봉",
                location_address="제주특별자치도 서귀포시 성산읍",
                location_category="관광지",
                radius=LOCATION_RADIUS,
                mx=LOCATION_LONGITUDE,
                my=LOCATION_LATITUDE,
            ),
            Location(
                id=NEARBY_LOCATION_ID,
                content_id=126509,
                location_title="성산 포구",
                location_address="제주특별자치도 서귀포시 성산읍",
                location_category="해변",
                # 장소별 반경이 300m 라도 5km 안이면 방문이다.
                radius=300,
                mx=NEARBY_LONGITUDE,
                my=LOCATION_LATITUDE,
            ),
            Location(
                id=FAR_LOCATION_ID,
                content_id=126510,
                location_title="중문색달해변",
                location_address="제주특별자치도 서귀포시 색달동",
                location_category="해변",
                radius=300,
                mx=FAR_LONGITUDE,
                my=FAR_LATITUDE,
            ),
        ]
    )
    db_session.commit()


def _post(
    client: TestClient,
    *,
    body: dict[str, object] | None = None,
    recorded_at: str = RECORDED_AT,
    latitude: float = LOCATION_LATITUDE,
    longitude: float = LOCATION_LONGITUDE,
    user_id: int = CURRENT_USER_ID,
) -> Any:
    payload = (
        {"recordedAt": recorded_at, "latitude": latitude, "longitude": longitude}
        if body is None
        else body
    )
    return client.post(ENDPOINT, json=payload, headers=auth_headers(user_id))


def _gps_records(db_session: Session) -> list[Gps]:
    db_session.expire_all()
    return list(db_session.scalars(select(Gps).order_by(Gps.id)).all())


def _visits(db_session: Session) -> list[VisitedLocation]:
    db_session.expire_all()
    return list(
        db_session.scalars(select(VisitedLocation).order_by(VisitedLocation.id)).all()
    )


# ---------------------------------------------------------------------
# GPS 저장
# ---------------------------------------------------------------------


def test_좌표를_저장하면_204와_빈_본문을_반환한다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    response = _post(client, latitude=FAR_LATITUDE + 1, longitude=FAR_LONGITUDE + 1)

    assert response.status_code == 204
    assert response.content == b""
    assert len(_gps_records(db_session)) == 1


def test_경도는_mx_위도는_my에_저장한다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, latitude=33.1234, longitude=126.5678)

    gps = _gps_records(db_session)[0]
    assert (gps.my, gps.mx) == (33.1234, 126.5678)


def test_saved_at은_요청의_recordedAt을_그대로_쓴다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, recorded_at="2026-09-03T14:30:00")

    # 서버가 요청을 받은 시각이 아니라 좌표를 측정한 시각이다.
    assert _gps_records(db_session)[0].saved_at == RECORDED_DATETIME


def test_토큰의_사용자로_저장한다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, user_id=OTHER_USER_ID)

    # 요청 Body 에 사용자 id 가 없으므로 토큰 주인이 저장된다.
    assert _gps_records(db_session)[0].user_id == OTHER_USER_ID


def test_같은_좌표를_여러_번_보내면_기록이_쌓인다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, recorded_at="2026-09-03T14:30:00")
    _post(client, recorded_at="2026-09-03T14:35:00")

    # GPS 는 upsert 가 아니라 매번 새 기록이다.
    assert len(_gps_records(db_session)) == 2


# ---------------------------------------------------------------------
# 방문 장소 판정
# ---------------------------------------------------------------------


def test_5km_안이면_방문_기록을_함께_남긴다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, latitude=LOCATION_LATITUDE, longitude=LOCATION_LONGITUDE)

    visits = _visits(db_session)
    assert [visit.location_id for visit in visits] == [
        LOCATION_ID,
        NEARBY_LOCATION_ID,
    ]
    assert visits[0].user_id == CURRENT_USER_ID


def test_방문_시각은_GPS와_같은_recordedAt이다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, recorded_at="2026-09-03T14:30:00")

    visits = _visits(db_session)
    assert visits != []
    for visit in visits:
        assert visit.visited_at == RECORDED_DATETIME
    assert _gps_records(db_session)[0].saved_at == RECORDED_DATETIME


def test_5km_밖이면_GPS만_저장하고_방문은_남기지_않는다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    # 어느 장소에서도 5km 넘게 떨어진 좌표
    response = _post(client, latitude=33.9000, longitude=126.2000)

    assert response.status_code == 204
    assert len(_gps_records(db_session)) == 1
    assert _visits(db_session) == []


def test_5km_안의_장소를_모두_기록한다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client)

    # 가장 가까운 한 곳만 고르지 않는다.
    assert len(_visits(db_session)) == 2


def test_장소별_radius_밖이어도_5km_안이면_방문으로_기록한다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    # 두 장소의 radius 는 300m 인데 서로 2km 떨어져 있다.
    _post(client, latitude=LOCATION_LATITUDE, longitude=NEARBY_LONGITUDE)

    assert [visit.location_id for visit in _visits(db_session)] == [
        LOCATION_ID,
        NEARBY_LOCATION_ID,
    ]


def test_멀리_있는_장소는_방문으로_잡지_않는다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client)

    assert FAR_LOCATION_ID not in {visit.location_id for visit in _visits(db_session)}


def test_다른_장소로_이동하면_그_장소가_기록된다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, latitude=FAR_LATITUDE, longitude=FAR_LONGITUDE)

    assert [visit.location_id for visit in _visits(db_session)] == [FAR_LOCATION_ID]


def test_같은_장소를_다시_판정받아도_방문_기록은_한_건이다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, recorded_at="2026-09-03T14:30:00")
    _post(client, recorded_at="2026-09-03T14:35:00")

    # 판정 반경 안에 머물러 두 번 다 걸리지만, (사용자, 장소)당 한 건만 남는다.
    assert [visit.location_id for visit in _visits(db_session)] == [
        LOCATION_ID,
        NEARBY_LOCATION_ID,
    ]
    # GPS 는 중복 제거 대상이 아니라 요청마다 쌓인다.
    assert len(_gps_records(db_session)) == 2


def test_이미_방문한_장소의_visited_at은_바뀌지_않는다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, recorded_at="2026-09-03T14:30:00")

    _post(client, recorded_at="2026-09-04T09:00:00")

    # 기존 기록을 갱신하지도 않는다. 처음 방문한 시각 그대로다.
    for visit in _visits(db_session):
        assert visit.visited_at == RECORDED_DATETIME


def test_이미_방문한_장소는_건너뛰고_새_장소만_기록한다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    # 먼저 멀리 있는 장소만 방문해 둔다.
    _post(client, latitude=FAR_LATITUDE, longitude=FAR_LONGITUDE)

    _post(client)

    assert [visit.location_id for visit in _visits(db_session)] == [
        FAR_LOCATION_ID,
        LOCATION_ID,
        NEARBY_LOCATION_ID,
    ]


def test_다른_사용자의_방문_이력은_중복_판정에_영향을_주지_않는다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, user_id=OTHER_USER_ID)

    _post(client, user_id=CURRENT_USER_ID)

    # 중복 기준은 (사용자, 장소)라 사용자마다 따로 남는다.
    visits = _visits(db_session)
    assert {visit.user_id for visit in visits} == {OTHER_USER_ID, CURRENT_USER_ID}
    assert len(visits) == 4


def test_방문_기록도_토큰의_사용자로_남는다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    _post(client, user_id=OTHER_USER_ID)

    assert {visit.user_id for visit in _visits(db_session)} == {OTHER_USER_ID}


def test_장소가_하나도_없으면_GPS만_저장한다(
    client: TestClient, db_session: Session
) -> None:
    # 장소 없이 사용자만 있는 상태 (gps_data 픽스처를 쓰지 않는다)
    db_session.add(
        User(
            id=CURRENT_USER_ID,
            access_token_hash=access_token_hash(CURRENT_USER_ID),
            nickname="몽글몽글파도",
            point=0,
        )
    )
    db_session.commit()

    response = _post(client)

    assert response.status_code == 204
    assert len(_gps_records(db_session)) == 1
    assert _visits(db_session) == []


# ---------------------------------------------------------------------
# 트랜잭션
# ---------------------------------------------------------------------


def test_저장에_실패하면_GPS와_방문_기록이_모두_남지_않는다(
    client: TestClient,
    db_session: Session,
    gps_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(self: Session) -> None:
        raise RuntimeError("DB 저장 실패")

    monkeypatch.setattr(Session, "commit", boom)

    response = _post(client)

    assert response.status_code == 500
    assert _gps_records(db_session) == []
    assert _visits(db_session) == []


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            {"latitude": LOCATION_LATITUDE, "longitude": LOCATION_LONGITUDE},
            id="시각_누락",
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "longitude": LOCATION_LONGITUDE}, id="위도_누락"
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "latitude": LOCATION_LATITUDE}, id="경도_누락"
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "latitude": 90.1, "longitude": 126.9},
            id="위도_범위_초과",
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "latitude": 33.4, "longitude": -180.1},
            id="경도_범위_미만",
        ),
        pytest.param(
            {"recordedAt": "어제", "latitude": 33.4, "longitude": 126.9},
            id="형식이_아닌_시각",
        ),
        pytest.param(
            {
                "recordedAt": "2026-09-03T14:30:00+09:00",
                "latitude": 33.4,
                "longitude": 126.9,
            },
            id="offset이_붙은_시각",
        ),
        pytest.param(
            {
                "recordedAt": RECORDED_AT,
                "latitude": 33.4,
                "longitude": 126.9,
                "userId": 2,
            },
            id="정의되지_않은_필드",
        ),
        pytest.param({}, id="빈_body"),
    ],
)
def test_요청_Body가_잘못되면_400이다(
    client: TestClient, db_session: Session, gps_data: None, body: dict
) -> None:
    response = _post(client, body=body)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _gps_records(db_session) == []
    assert _visits(db_session) == []


def test_시각_없이_날짜만_보내면_그_날_자정으로_본다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    # `2026-09-03` 처럼 시각이 빠진 값은 자정으로 해석해 그대로 저장한다.
    response = _post(client, recorded_at="2026-09-03")

    assert response.status_code == 204
    assert _gps_records(db_session)[0].saved_at == datetime(2026, 9, 3, 0, 0, 0)


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


def test_인증_헤더가_없으면_401이다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.post(
        ENDPOINT,
        json={
            "recordedAt": RECORDED_AT,
            "latitude": LOCATION_LATITUDE,
            "longitude": LOCATION_LONGITUDE,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _gps_records(db_session) == []


def test_토큰의_사용자가_없으면_401이다(
    client: TestClient, db_session: Session, gps_data: None
) -> None:
    response = _post(client, user_id=999)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _gps_records(db_session) == []
    assert _visits(db_session) == []


def test_문서에_401을_노출한다(client: TestClient) -> None:
    responses = client.get("/openapi.json").json()["paths"][ENDPOINT]["post"]["responses"]

    assert sorted(responses) == ["204", "400", "401", "500"]
