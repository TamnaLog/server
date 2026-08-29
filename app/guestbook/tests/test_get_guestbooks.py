"""GET /api/v1/guestbooks - 방명록 조회 테스트.

기준 문서: app/guestbook/docs/API_SPEC.md, app/guestbook/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.guestbook.models import Guestbook, RoadGuestbook
from app.map.models import Location
from app.mission.models import Mission
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/guestbooks"

LOCATION_ID = 39
LOCATION_TITLE = "현애원"
LOCATION_ADDRESS = "제주특별자치도 서귀포시 성산읍"
LOCATION_CATEGORY = "관광지"
LOCATION_LAT = 33.4582
LOCATION_LNG = 126.9331

MISSION_ID = 501
MISSION_TITLE = "현애원의 숨은 보물 찾기"

OTHER_USER_ID = 2

VISITED_ON = date(2026, 8, 21)
SAVED_AT = datetime(2026, 8, 21, 14, 20, 0)
LATER_SAVED_AT = datetime(2026, 8, 22, 9, 0, 0)

IMAGE_URLS = [
    "https://example.blob.core.windows.net/media/guestbook/general/101/images/4b690ea8.jpg"
]
AUDIO_URLS = [
    "https://example.blob.core.windows.net/media/guestbook/general/101/audios/16bc1c76.m4a"
]


@pytest.fixture
def guestbook_data(db_session: Session) -> None:
    """장소 / 미션 / 사용자. 방명록은 각 테스트에서 만든다."""
    db_session.add_all(
        [
            Location(
                id=LOCATION_ID,
                content_id=126508,
                location_title=LOCATION_TITLE,
                location_address=LOCATION_ADDRESS,
                location_category=LOCATION_CATEGORY,
                radius=300,
                mx=LOCATION_LNG,
                my=LOCATION_LAT,
            ),
            Mission(
                id=MISSION_ID,
                mission_type="TREASURE",
                mission_title=MISSION_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "탐색", "description": "설명"}],
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


def _add_general(
    db_session: Session,
    *,
    guestbook_id: int,
    user_id: int = CURRENT_USER_ID,
    saved_at: datetime = SAVED_AT,
    mission_id: int | None = None,
    image_urls: list[str] | None = None,
    audio_urls: list[str] | None = None,
    deleted_at: datetime | None = None,
    content_writing: str | None = None,
) -> None:
    db_session.add(
        Guestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=LOCATION_ID,
            visited_at=VISITED_ON,
            content_img_url=image_urls,
            content_writing=content_writing,
            content_audio_url=audio_urls,
            content_weather=None,
            content_color_code=None,
            saved_at=saved_at,
            mission_id=mission_id,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_road(
    db_session: Session,
    *,
    guestbook_id: int,
    user_id: int = CURRENT_USER_ID,
    saved_at: datetime = SAVED_AT,
    image_urls: list[str] | None = None,
    audio_urls: list[str] | None = None,
    deleted_at: datetime | None = None,
    content_writing: str | None = None,
) -> None:
    db_session.add(
        RoadGuestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=None,
            location_alias="성산 바다 앞",
            visited_at=VISITED_ON,
            content_img_url=image_urls,
            content_writing=content_writing,
            content_audio_url=audio_urls,
            content_weather=None,
            content_color_code=None,
            mx=126.9331,
            my=33.4582,
            saved_at=saved_at,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _get(client: TestClient, user_id: int = CURRENT_USER_ID) -> dict:
    response = client.get(ENDPOINT, headers=auth_headers(user_id))
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------
# 응답 형식
# ---------------------------------------------------------------------


def test_일반_방명록은_장소와_미션을_포함해_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(
        db_session,
        guestbook_id=101,
        mission_id=MISSION_ID,
        image_urls=IMAGE_URLS,
        content_writing="현애원 산책하기 좋았어요.",
    )

    body = _get(client)

    assert body["roadGuestbooks"] == []
    assert body["generalGuestbooks"] == [
        {
            "id": 101,
            "location": {
                "id": LOCATION_ID,
                "locationTitle": LOCATION_TITLE,
                "locationAddress": LOCATION_ADDRESS,
                "locationCategory": LOCATION_CATEGORY,
                # LOCATION 은 my=위도 / mx=경도로 저장한다.
                "latitude": LOCATION_LAT,
                "longitude": LOCATION_LNG,
            },
            "visitedAt": "2026-08-21",
            "contentImageUrls": IMAGE_URLS,
            "contentWriting": "현애원 산책하기 좋았어요.",
            "contentAudioUrls": None,
            "contentWeather": None,
            "contentColorCode": None,
            "savedAt": "2026-08-21T14:20:00",
            "mission": {
                "id": MISSION_ID,
                "missionType": "TREASURE",
                "missionTitle": MISSION_TITLE,
            },
        }
    ]


def test_길바닥_방명록은_별칭과_좌표를_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_road(
        db_session,
        guestbook_id=201,
        audio_urls=AUDIO_URLS,
        content_writing="바다가 잘 보이는 길이에요.",
    )

    body = _get(client)

    assert body["generalGuestbooks"] == []
    assert body["roadGuestbooks"] == [
        {
            "id": 201,
            "locationAlias": "성산 바다 앞",
            "latitude": 33.4582,
            "longitude": 126.9331,
            "visitedAt": "2026-08-21",
            "contentImageUrls": None,
            "contentWriting": "바다가 잘 보이는 길이에요.",
            "contentAudioUrls": AUDIO_URLS,
            "contentWeather": None,
            "contentColorCode": None,
            "savedAt": "2026-08-21T14:20:00",
        }
    ]


def test_미션이_없는_일반_방명록은_mission이_null이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)

    assert _get(client)["generalGuestbooks"][0]["mission"] is None


def test_결과가_없어도_두_배열을_빈_배열로_반환한다(
    client: TestClient, guestbook_data: None
) -> None:
    body = _get(client)

    assert body == {"generalGuestbooks": [], "roadGuestbooks": []}


def test_한_유형만_있어도_다른_배열은_빈_배열이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)

    body = _get(client)

    assert len(body["generalGuestbooks"]) == 1
    assert body["roadGuestbooks"] == []


def test_항목에_guestbookType이나_페이지_정보를_넣지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_road(db_session, guestbook_id=201)

    body = _get(client)

    assert set(body) == {"generalGuestbooks", "roadGuestbooks"}
    assert "guestbookType" not in body["generalGuestbooks"][0]
    assert "guestbookType" not in body["roadGuestbooks"][0]


# ---------------------------------------------------------------------
# 조회 범위 (BUSINESS_RULES C.2)
# ---------------------------------------------------------------------


def test_다른_사용자의_방명록은_반환하지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, user_id=OTHER_USER_ID)
    _add_road(db_session, guestbook_id=201, user_id=OTHER_USER_ID)

    body = _get(client)

    assert body == {"generalGuestbooks": [], "roadGuestbooks": []}


def test_삭제된_방명록은_두_목록_모두에서_제외한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, deleted_at=datetime(2026, 8, 23, 10, 0, 0))
    _add_general(db_session, guestbook_id=102)
    _add_road(db_session, guestbook_id=201, deleted_at=datetime(2026, 8, 23, 10, 0, 0))
    _add_road(db_session, guestbook_id=202)

    body = _get(client)

    assert [item["id"] for item in body["generalGuestbooks"]] == [102]
    assert [item["id"] for item in body["roadGuestbooks"]] == [202]


def test_토큰의_사용자에_따라_결과가_달라진다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_general(db_session, guestbook_id=102, user_id=OTHER_USER_ID)

    mine = _get(client)
    theirs = _get(client, user_id=OTHER_USER_ID)

    assert [item["id"] for item in mine["generalGuestbooks"]] == [101]
    assert [item["id"] for item in theirs["generalGuestbooks"]] == [102]


# ---------------------------------------------------------------------
# 정렬 (BUSINESS_RULES C.3)
# ---------------------------------------------------------------------


def test_두_목록_모두_최신_저장순으로_정렬한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, saved_at=SAVED_AT)
    _add_general(db_session, guestbook_id=102, saved_at=LATER_SAVED_AT)
    _add_road(db_session, guestbook_id=201, saved_at=SAVED_AT)
    _add_road(db_session, guestbook_id=202, saved_at=LATER_SAVED_AT)

    body = _get(client)

    assert [item["id"] for item in body["generalGuestbooks"]] == [102, 101]
    assert [item["id"] for item in body["roadGuestbooks"]] == [202, 201]


def test_저장_시각이_같으면_id가_큰_방명록이_앞에_온다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, saved_at=SAVED_AT)
    _add_general(db_session, guestbook_id=103, saved_at=SAVED_AT)
    _add_general(db_session, guestbook_id=102, saved_at=SAVED_AT)

    assert [item["id"] for item in _get(client)["generalGuestbooks"]] == [103, 102, 101]


def test_페이지네이션_없이_전부_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    for guestbook_id in range(101, 126):
        _add_general(db_session, guestbook_id=guestbook_id)

    body = _get(client)

    assert len(body["generalGuestbooks"]) == 25


# ---------------------------------------------------------------------
# 콘텐츠 보존 (BUSINESS_RULES C.6)
# ---------------------------------------------------------------------


def test_URL이_NULL이면_null_빈_배열이면_빈_배열로_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, image_urls=None, audio_urls=[])
    _add_road(db_session, guestbook_id=201, image_urls=[], audio_urls=None)

    body = _get(client)

    general = body["generalGuestbooks"][0]
    road = body["roadGuestbooks"][0]
    assert general["contentImageUrls"] is None
    assert general["contentAudioUrls"] == []
    assert road["contentImageUrls"] == []
    assert road["contentAudioUrls"] is None


def test_URL_배열의_순서와_중복을_그대로_유지한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    urls = ["https://example.com/b.jpg", "https://example.com/a.jpg", "https://example.com/b.jpg"]
    _add_general(db_session, guestbook_id=101, image_urls=urls)

    assert _get(client)["generalGuestbooks"][0]["contentImageUrls"] == urls


# ---------------------------------------------------------------------
# 읽기 전용 / 401
# ---------------------------------------------------------------------


def test_조회는_방명록_데이터를_바꾸지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, mission_id=MISSION_ID)
    _add_road(db_session, guestbook_id=201)
    db_session.expire_all()
    before = [
        (guestbook.id, guestbook.saved_at, guestbook.deleted_at)
        for guestbook in db_session.scalars(select(Guestbook)).all()
    ]

    _get(client)

    db_session.expire_all()
    assert [
        (guestbook.id, guestbook.saved_at, guestbook.deleted_at)
        for guestbook in db_session.scalars(select(Guestbook)).all()
    ] == before
    assert len(db_session.scalars(select(RoadGuestbook)).all()) == 1


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, guestbook_data: None
) -> None:
    response = client.get(ENDPOINT, headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_인증_헤더가_없으면_401로_응답한다(
    client: TestClient, guestbook_data: None
) -> None:
    # TestClient 기본 헤더를 지워서 헤더 없는 요청을 만든다.
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
