"""GET /api/v1/map/modals - 지도 모달 조회 테스트.

기준 문서: app/map/docs/API_SPEC.md, app/map/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.common import distance
from app.guestbook.models import Guestbook, RoadGuestbook
from app.map.models import Location
from app.map.service import LOCATION_MODAL_GUESTBOOK_LIMIT
from app.mission.models import Mission
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/map/modals"

MISSION_ID = 1
MISSION_TITLE = "현애원의 숨은 보물 찾기"

LOCATION_ID = 39
LOCATION_TITLE = "현애원"
LOCATION_CATEGORY = "관광지"
LOCATION_LATITUDE = 33.4582
LOCATION_LONGITUDE = 126.9331

OTHER_LOCATION_ID = 40

ROAD_GUESTBOOK_ID = 100
ROAD_GUESTBOOK_ALIAS = "성산 바다 앞"
ROAD_LATITUDE = 33.4600
ROAD_LONGITUDE = 126.9400

OTHER_USER_ID = 2
NICKNAME = "여행자종화"
OTHER_NICKNAME = "제주도종화"

USER_LATITUDE = 33.4524
USER_LONGITUDE = 126.9248


def _params(**overrides: object) -> dict[str, object]:
    return {
        "targetType": "LOCATION",
        "targetId": LOCATION_ID,
        "userLatitude": USER_LATITUDE,
        "userLongitude": USER_LONGITUDE,
        **overrides,
    }


def _road_params(**overrides: object) -> dict[str, object]:
    return _params(
        **{"targetType": "ROAD_GUESTBOOK", "targetId": ROAD_GUESTBOOK_ID, **overrides}
    )


@pytest.fixture
def modal_data(db_session: Session) -> None:
    """장소 2곳 + 사용자 2명 + 미션 1개. 방명록은 테스트마다 직접 붙인다."""
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname=NICKNAME,
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname=OTHER_NICKNAME,
                point=0,
            ),
            Mission(
                id=MISSION_ID,
                mission_type="TREASURE",
                mission_title=MISSION_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "시작", "description": "설명"}],
            ),
            Location(
                id=LOCATION_ID,
                content_id=126273,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 표선면",
                location_category=LOCATION_CATEGORY,
                radius=300,
                mx=LOCATION_LONGITUDE,
                my=LOCATION_LATITUDE,
            ),
            Location(
                id=OTHER_LOCATION_ID,
                content_id=999,
                location_title="다른 장소",
                location_address="제주특별자치도 제주시",
                location_category="카페",
                radius=200,
                mx=126.95,
                my=33.47,
            ),
        ]
    )
    db_session.commit()


def _add_guestbook(
    db_session: Session,
    *,
    guestbook_id: int,
    location_id: int = LOCATION_ID,
    user_id: int = CURRENT_USER_ID,
    mission_id: int | None = None,
    visited_at: date = date(2026, 8, 25),
    content_img_url: list[str] | None = None,
    content_writing: str | None = None,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        Guestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=location_id,
            mission_id=mission_id,
            visited_at=visited_at,
            content_img_url=content_img_url,
            content_writing=content_writing,
            saved_at=datetime(2026, 8, 25, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_road_guestbook(
    db_session: Session,
    *,
    guestbook_id: int = ROAD_GUESTBOOK_ID,
    user_id: int = CURRENT_USER_ID,
    visited_at: date = date(2026, 8, 25),
    content_img_url: list[str] | None = None,
    content_writing: str | None = None,
    content_audio_url: list[str] | None = None,
    content_weather: str | None = None,
    content_color_code: str | None = None,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        RoadGuestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=None,
            location_alias=ROAD_GUESTBOOK_ALIAS,
            visited_at=visited_at,
            content_img_url=content_img_url,
            content_writing=content_writing,
            content_audio_url=content_audio_url,
            content_weather=content_weather,
            content_color_code=content_color_code,
            mx=ROAD_LONGITUDE,
            my=ROAD_LATITUDE,
            saved_at=datetime(2026, 8, 25, 12, 0, 0),
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _get(client: TestClient, params: dict[str, object]) -> dict:
    response = client.get(ENDPOINT, params=params)
    assert response.status_code == 200
    return response.json()


def _expected_distance(latitude: float, longitude: float) -> int:
    return distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, latitude, longitude
    )


# ---------------------------------------------------------------------
# targetType = LOCATION
# ---------------------------------------------------------------------


def test_장소_모달을_조회하면_기본_정보와_방명록을_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_guestbook(
        db_session,
        guestbook_id=300,
        mission_id=MISSION_ID,
        visited_at=date(2026, 8, 25),
        content_img_url=["https://example.com/guestbooks/300-1.jpg"],
        content_writing="현애원 산책하기 좋았어요.",
    )
    _add_guestbook(
        db_session,
        guestbook_id=302,
        user_id=OTHER_USER_ID,
        visited_at=date(2026, 8, 23),
    )

    expected_distance = _expected_distance(LOCATION_LATITUDE, LOCATION_LONGITUDE)
    assert _get(client, _params()) == {
        "id": LOCATION_ID,
        "locationTitle": LOCATION_TITLE,
        "locationCategory": LOCATION_CATEGORY,
        "distanceMeter": expected_distance,
        "durationMinutes": distance.calculate_duration_minutes(expected_distance),
        "guestbooksCount": 2,
        "guestbooks": [
            {
                "id": 300,
                "representativeImageUrl": "https://example.com/guestbooks/300-1.jpg",
                "userNickname": NICKNAME,
                "missionTitle": MISSION_TITLE,
                "visitedAt": "2026-08-25",
                "contentWriting": "현애원 산책하기 좋았어요.",
            },
            {
                "id": 302,
                "representativeImageUrl": None,
                "userNickname": OTHER_NICKNAME,
                "missionTitle": None,
                "visitedAt": "2026-08-23",
                "contentWriting": None,
            },
        ],
    }


def test_방명록이_없어도_200과_빈_배열을_반환한다(
    client: TestClient, modal_data: None
) -> None:
    body = _get(client, _params())

    assert body["guestbooksCount"] == 0
    assert body["guestbooks"] == []


def test_방명록은_방문일_최신순으로_최대_3개만_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    for guestbook_id, day in ((1, 20), (2, 24), (3, 22), (4, 25), (5, 21)):
        _add_guestbook(
            db_session, guestbook_id=guestbook_id, visited_at=date(2026, 8, day)
        )

    body = _get(client, _params())

    # 전체 개수는 목록 길이가 아니라 5 다.
    assert body["guestbooksCount"] == 5
    assert len(body["guestbooks"]) == LOCATION_MODAL_GUESTBOOK_LIMIT
    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [4, 2, 3]


def test_방문일이_같으면_id가_큰_방명록이_먼저다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    same_day = date(2026, 8, 25)
    for guestbook_id in (10, 12, 11):
        _add_guestbook(db_session, guestbook_id=guestbook_id, visited_at=same_day)

    body = _get(client, _params())

    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [12, 11, 10]


def test_최신순은_저장_시각이_아니라_방문일_기준이다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    # 나중에 저장했지만 방문일은 더 과거인 방명록
    db_session.add(
        Guestbook(
            id=1,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=date(2026, 8, 20),
            saved_at=datetime(2026, 8, 30, 12, 0, 0),
        )
    )
    db_session.add(
        Guestbook(
            id=2,
            user_id=CURRENT_USER_ID,
            location_id=LOCATION_ID,
            visited_at=date(2026, 8, 25),
            saved_at=datetime(2026, 8, 26, 12, 0, 0),
        )
    )
    db_session.commit()

    body = _get(client, _params())

    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [2, 1]


def test_삭제된_방명록은_개수와_목록에서_모두_빠진다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1)
    _add_guestbook(
        db_session, guestbook_id=2, deleted_at=datetime(2026, 8, 26, 9, 0, 0)
    )

    body = _get(client, _params())

    assert body["guestbooksCount"] == 1
    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [1]


def test_다른_장소의_방명록은_섞이지_않는다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_guestbook(db_session, guestbook_id=1, location_id=LOCATION_ID)
    _add_guestbook(db_session, guestbook_id=2, location_id=OTHER_LOCATION_ID)

    body = _get(client, _params())

    assert body["guestbooksCount"] == 1
    assert [guestbook["id"] for guestbook in body["guestbooks"]] == [1]


@pytest.mark.parametrize(
    "content_img_url",
    [
        pytest.param(None, id="이미지_없음"),
        pytest.param([], id="빈_배열"),
    ],
)
def test_방명록_이미지가_없으면_대표_이미지는_null이다(
    client: TestClient,
    db_session: Session,
    modal_data: None,
    content_img_url: list[str] | None,
) -> None:
    _add_guestbook(db_session, guestbook_id=1, content_img_url=content_img_url)

    body = _get(client, _params())

    assert body["guestbooks"][0]["representativeImageUrl"] is None


def test_방명록_이미지는_첫_번째_URL을_그대로_쓴다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    first = "https://example.com/guestbooks/1-1.jpg"
    _add_guestbook(
        db_session,
        guestbook_id=1,
        content_img_url=[first, "https://example.com/guestbooks/1-2.jpg"],
    )

    body = _get(client, _params())

    assert body["guestbooks"][0]["representativeImageUrl"] == first


def test_장소_거리와_예상_시간은_공통_모듈_결과와_같다(
    client: TestClient, modal_data: None
) -> None:
    body = _get(client, _params())

    expected_distance = _expected_distance(LOCATION_LATITUDE, LOCATION_LONGITUDE)
    assert body["distanceMeter"] == expected_distance
    assert body["durationMinutes"] == distance.calculate_duration_minutes(
        expected_distance
    )


def test_사용자_좌표가_장소와_같으면_거리가_0이다(
    client: TestClient, modal_data: None
) -> None:
    body = _get(
        client,
        _params(userLatitude=LOCATION_LATITUDE, userLongitude=LOCATION_LONGITUDE),
    )

    assert body["distanceMeter"] == 0


# ---------------------------------------------------------------------
# targetType = ROAD_GUESTBOOK
# ---------------------------------------------------------------------


def test_길바닥_방명록_모달을_조회하면_상세_콘텐츠를_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    image_urls = [
        "https://example.com/road/100-1.jpg",
        "https://example.com/road/100-2.jpg",
    ]
    _add_road_guestbook(
        db_session,
        content_img_url=image_urls,
        content_writing="잠시 쉬어가기 좋았어요.",
        content_weather="SUNNY",
    )

    expected_distance = _expected_distance(ROAD_LATITUDE, ROAD_LONGITUDE)
    assert _get(client, _road_params()) == {
        "id": ROAD_GUESTBOOK_ID,
        "userNickname": NICKNAME,
        "locationAlias": ROAD_GUESTBOOK_ALIAS,
        "distanceMeter": expected_distance,
        "durationMinutes": distance.calculate_duration_minutes(expected_distance),
        "visitedAt": "2026-08-25",
        # 저장된 순서를 바꾸지 않는다.
        "contentImageUrls": image_urls,
        "contentWriting": "잠시 쉬어가기 좋았어요.",
        "contentAudioUrls": None,
        "contentWeather": "SUNNY",
        "contentColorCode": None,
    }


def test_콘텐츠가_없으면_필드를_생략하지_않고_null로_반환한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session)

    body = _get(client, _road_params())

    assert body.keys() >= {
        "contentImageUrls",
        "contentWriting",
        "contentAudioUrls",
        "contentWeather",
        "contentColorCode",
    }
    for field in (
        "contentImageUrls",
        "contentWriting",
        "contentAudioUrls",
        "contentWeather",
        "contentColorCode",
    ):
        assert body[field] is None


def test_빈_배열로_저장된_콘텐츠는_null로_정규화한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session, content_img_url=[], content_audio_url=[])

    body = _get(client, _road_params())

    assert body["contentImageUrls"] is None
    assert body["contentAudioUrls"] is None


def test_길바닥_방명록_거리와_예상_시간은_공통_모듈_결과와_같다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session)

    body = _get(client, _road_params())

    expected_distance = _expected_distance(ROAD_LATITUDE, ROAD_LONGITUDE)
    assert body["distanceMeter"] == expected_distance
    assert body["durationMinutes"] == distance.calculate_duration_minutes(
        expected_distance
    )


def test_작성일은_저장_시각이_아니라_방문일이다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session, visited_at=date(2026, 8, 20))

    assert _get(client, _road_params())["visitedAt"] == "2026-08-20"


# ---------------------------------------------------------------------
# 404 MAP_MODAL_TARGET_NOT_FOUND
# ---------------------------------------------------------------------


def test_장소가_없으면_404로_응답한다(client: TestClient, modal_data: None) -> None:
    response = client.get(ENDPOINT, params=_params(targetId=999))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_길바닥_방명록이_없으면_404로_응답한다(
    client: TestClient, modal_data: None
) -> None:
    response = client.get(ENDPOINT, params=_road_params(targetId=999))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_삭제된_길바닥_방명록이면_404로_응답한다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session, deleted_at=datetime(2026, 8, 26, 9, 0, 0))

    response = client.get(ENDPOINT, params=_road_params())

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_다른_테이블에_같은_id가_있어도_targetType을_따른다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    # 장소 39 는 있지만 길바닥 방명록 39 는 없다.
    response = client.get(ENDPOINT, params=_road_params(targetId=LOCATION_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


def test_길바닥_방명록_id로_장소를_조회하면_404다(
    client: TestClient, db_session: Session, modal_data: None
) -> None:
    _add_road_guestbook(db_session)

    response = client.get(ENDPOINT, params=_params(targetId=ROAD_GUESTBOOK_ID))

    assert response.status_code == 404
    assert response.json() == {"code": "MAP_MODAL_TARGET_NOT_FOUND"}


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("targetType", id="targetType_누락"),
        pytest.param("targetId", id="targetId_누락"),
        pytest.param("userLatitude", id="userLatitude_누락"),
        pytest.param("userLongitude", id="userLongitude_누락"),
    ],
)
def test_필수_Query가_없으면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, modal_data: None, field: str
) -> None:
    params = _params()
    del params[field]

    response = client.get(ENDPOINT, params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("targetType", "MISSION", id="지원하지_않는_targetType"),
        pytest.param("targetType", "location", id="소문자_targetType"),
        pytest.param("targetId", "abc", id="targetId가_정수가_아님"),
        pytest.param("targetId", 0, id="targetId가_0"),
        pytest.param("targetId", -1, id="targetId가_음수"),
        pytest.param("userLatitude", "abc", id="위도가_숫자가_아님"),
        pytest.param("userLatitude", 91, id="위도_상한_초과"),
        pytest.param("userLatitude", -91, id="위도_하한_미만"),
        pytest.param("userLongitude", 181, id="경도_상한_초과"),
        pytest.param("userLongitude", -181, id="경도_하한_미만"),
    ],
)
def test_Query_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, modal_data: None, field: str, value: object
) -> None:
    response = client.get(ENDPOINT, params=_params(**{field: value}))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_인증_헤더가_없으면_401로_응답한다(client: TestClient, modal_data: None) -> None:
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT, params=_params())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, modal_data: None
) -> None:
    response = client.get(ENDPOINT, params=_params(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_문서에_401을_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"][ENDPOINT]["get"]["responses"]

    assert sorted(responses) == ["200", "400", "401", "404", "500"]
