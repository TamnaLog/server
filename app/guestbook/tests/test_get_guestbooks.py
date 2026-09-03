"""GET /api/v1/guestbooks - 방명록 조회 테스트.

기준 문서: app/guestbook/docs/API_SPEC.md, app/guestbook/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.guestbook.models import (
    Guestbook,
    GuestbookLike,
    RoadGuestbook,
    RoadGuestbookLike,
)
from app.map.models import Location, VisitedLocation
from app.mission.models import Mission
from app.treasure_mission.models import ArCharacter
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
THIRD_USER_ID = 3
FOURTH_USER_ID = 4

NICKNAME = "몽글몽글파도"

OTHER_LOCATION_ID = 40
OTHER_LOCATION_TITLE = "성산일출봉"

AR_CHARACTER_ID = 7
AR_CHARACTER_IMAGE_URL = "https://example.com/ar-characters/7.png"

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
            User(
                id=THIRD_USER_ID,
                access_token_hash=access_token_hash(THIRD_USER_ID),
                nickname="돌하르방",
                point=0,
            ),
            User(
                id=FOURTH_USER_ID,
                access_token_hash=access_token_hash(FOURTH_USER_ID),
                nickname="감귤이",
                point=0,
            ),
            Location(
                id=OTHER_LOCATION_ID,
                content_id=126273,
                location_title=OTHER_LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 성산읍 일출로",
                location_category="관광지",
                radius=300,
                mx=126.9410,
                my=33.4580,
            ),
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name="돌담 지킴이",
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="미션 완료",
                character_img_url=AR_CHARACTER_IMAGE_URL,
                hashtags=["#돌담"],
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
    audio_title: str | None = None,
    content_temperature_celsius: Decimal | None = None,
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
            audio_title=audio_title,
            content_weather=None,
            content_temperature_celsius=content_temperature_celsius,
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
    audio_title: str | None = None,
    content_temperature_celsius: Decimal | None = None,
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
            audio_title=audio_title,
            content_weather=None,
            content_temperature_celsius=content_temperature_celsius,
            content_color_code=None,
            mx=126.9331,
            my=33.4582,
            saved_at=saved_at,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_like(
    db_session: Session,
    *,
    guestbook_id: int,
    user_id: int,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        GuestbookLike(
            guestbook_id=guestbook_id, user_id=user_id, deleted_at=deleted_at
        )
    )
    db_session.commit()


def _add_road_like(
    db_session: Session,
    *,
    guestbook_id: int,
    user_id: int,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        RoadGuestbookLike(
            road_guestbook_id=guestbook_id, user_id=user_id, deleted_at=deleted_at
        )
    )
    db_session.commit()


def _add_visit(
    db_session: Session,
    *,
    location_id: int = LOCATION_ID,
    user_id: int = CURRENT_USER_ID,
    visited_at: datetime = datetime(2026, 8, 21, 10, 0, 0),
) -> None:
    db_session.add(
        VisitedLocation(
            user_id=user_id, location_id=location_id, visited_at=visited_at
        )
    )
    db_session.commit()


def _assign_ar_character(db_session: Session, *, user_id: int) -> None:
    """작성자에게 AR 캐릭터를 배정한다. (`USER.ar_character_id`)"""
    user = db_session.get(User, user_id)
    assert user is not None
    user.ar_character_id = AR_CHARACTER_ID
    db_session.commit()


def _get(
    client: TestClient,
    user_id: int = CURRENT_USER_ID,
    *,
    scope: str | None = None,
) -> dict:
    params = {} if scope is None else {"scope": scope}
    response = client.get(ENDPOINT, params=params, headers=auth_headers(user_id))
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
            "userId": CURRENT_USER_ID,
            # 이 사용자에게는 배정된 AR 캐릭터가 없다.
            "characterImgUrl": None,
            "userNickname": NICKNAME,
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
            "audioTitle": None,
            "contentWeather": None,
            "contentTemperatureCelsius": None,
            "contentColorCode": None,
            "isLiked": False,
            "likeCount": 0,
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
            "userId": CURRENT_USER_ID,
            "characterImgUrl": None,
            "userNickname": NICKNAME,
            "locationAlias": "성산 바다 앞",
            "latitude": 33.4582,
            "longitude": 126.9331,
            "visitedAt": "2026-08-21",
            "contentImageUrls": None,
            "contentWriting": "바다가 잘 보이는 길이에요.",
            "contentAudioUrls": AUDIO_URLS,
            "audioTitle": None,
            "contentWeather": None,
            "contentTemperatureCelsius": None,
            "contentColorCode": None,
            "isLiked": False,
            "likeCount": 0,
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

    assert body == {
        "visitedLocations": [],
        "generalGuestbooks": [],
        "roadGuestbooks": [],
    }


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

    assert set(body) == {"visitedLocations", "generalGuestbooks", "roadGuestbooks"}
    assert "guestbookType" not in body["generalGuestbooks"][0]
    assert "guestbookType" not in body["roadGuestbooks"][0]


# ---------------------------------------------------------------------
# 작성자 정보 (BUSINESS_RULES 수정사항 - 방명록 조회)
# ---------------------------------------------------------------------


def test_작성자에게_배정된_AR_캐릭터_이미지를_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _assign_ar_character(db_session, user_id=CURRENT_USER_ID)
    _add_general(db_session, guestbook_id=101)
    _add_road(db_session, guestbook_id=201)

    body = _get(client)

    assert body["generalGuestbooks"][0]["characterImgUrl"] == AR_CHARACTER_IMAGE_URL
    assert body["roadGuestbooks"][0]["characterImgUrl"] == AR_CHARACTER_IMAGE_URL


def test_배정된_AR_캐릭터가_없으면_characterImgUrl은_null이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)

    assert _get(client)["generalGuestbooks"][0]["characterImgUrl"] is None


def test_닉네임이_없으면_userNickname은_null이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.nickname = None
    db_session.commit()
    _add_general(db_session, guestbook_id=101)
    _add_road(db_session, guestbook_id=201)

    body = _get(client)

    # 닉네임이 없어도 빈 문자열이 아니라 null 이다.
    assert body["generalGuestbooks"][0]["userNickname"] is None
    assert body["roadGuestbooks"][0]["userNickname"] is None


# ---------------------------------------------------------------------
# 오디오 제목 / 기온 (BUSINESS_RULES 수정사항 - 방명록 조회)
# ---------------------------------------------------------------------


def test_저장된_오디오_제목과_기온을_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(
        db_session,
        guestbook_id=101,
        audio_urls=AUDIO_URLS,
        audio_title="새소리",
        content_temperature_celsius=Decimal("24.5"),
    )
    _add_road(
        db_session,
        guestbook_id=201,
        audio_urls=AUDIO_URLS,
        audio_title="파도소리",
        content_temperature_celsius=Decimal("21.3"),
    )

    body = _get(client)

    general = body["generalGuestbooks"][0]
    road = body["roadGuestbooks"][0]
    assert general["audioTitle"] == "새소리"
    # 문자열이 아니라 JSON 숫자로 내려준다.
    assert general["contentTemperatureCelsius"] == 24.5
    assert road["audioTitle"] == "파도소리"
    assert road["contentTemperatureCelsius"] == 21.3


def test_오디오_제목과_기온이_없으면_키를_생략하지_않고_null이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_road(db_session, guestbook_id=201)

    body = _get(client)

    for guestbook in (body["generalGuestbooks"][0], body["roadGuestbooks"][0]):
        assert guestbook["audioTitle"] is None
        assert guestbook["contentTemperatureCelsius"] is None


def test_영하_기온도_그대로_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(
        db_session, guestbook_id=101, content_temperature_celsius=Decimal("-3.5")
    )

    assert _get(client)["generalGuestbooks"][0]["contentTemperatureCelsius"] == -3.5


# ---------------------------------------------------------------------
# 좋아요 (BUSINESS_RULES 수정사항 - 방명록 조회)
# ---------------------------------------------------------------------


def test_좋아요가_없으면_isLiked는_false이고_likeCount는_0이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)

    general = _get(client)["generalGuestbooks"][0]

    assert general["isLiked"] is False
    assert general["likeCount"] == 0


def test_현재_사용자가_누른_좋아요는_isLiked가_true다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_like(db_session, guestbook_id=101, user_id=CURRENT_USER_ID)

    general = _get(client)["generalGuestbooks"][0]

    assert general["isLiked"] is True
    assert general["likeCount"] == 1


def test_다른_사용자만_누른_좋아요는_isLiked가_false다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_like(db_session, guestbook_id=101, user_id=OTHER_USER_ID)

    general = _get(client)["generalGuestbooks"][0]

    # isLiked 는 현재 사용자 기준이지만 likeCount 는 사용자를 가리지 않는다.
    assert general["isLiked"] is False
    assert general["likeCount"] == 1


def test_취소된_좋아요는_isLiked와_likeCount에서_모두_빠진다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_like(
        db_session,
        guestbook_id=101,
        user_id=CURRENT_USER_ID,
        deleted_at=datetime(2026, 8, 22, 9, 0, 0),
    )
    _add_like(
        db_session,
        guestbook_id=101,
        user_id=OTHER_USER_ID,
        deleted_at=datetime(2026, 8, 22, 9, 0, 0),
    )

    general = _get(client)["generalGuestbooks"][0]

    assert general["isLiked"] is False
    assert general["likeCount"] == 0


def test_likeCount는_현재_사용자를_포함한_모든_좋아요를_센다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_like(db_session, guestbook_id=101, user_id=CURRENT_USER_ID)
    _add_like(db_session, guestbook_id=101, user_id=OTHER_USER_ID)
    _add_like(db_session, guestbook_id=101, user_id=THIRD_USER_ID)
    # 취소한 사용자는 개수에서 빠진다.
    _add_like(
        db_session,
        guestbook_id=101,
        user_id=FOURTH_USER_ID,
        deleted_at=datetime(2026, 8, 22, 9, 0, 0),
    )

    general = _get(client)["generalGuestbooks"][0]

    assert general["isLiked"] is True
    assert general["likeCount"] == 3


def test_다른_방명록의_좋아요는_섞이지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, saved_at=LATER_SAVED_AT)
    _add_general(db_session, guestbook_id=102)
    _add_like(db_session, guestbook_id=101, user_id=CURRENT_USER_ID)
    _add_like(db_session, guestbook_id=101, user_id=OTHER_USER_ID)

    body = _get(client)

    assert [(item["id"], item["isLiked"], item["likeCount"]) for item in body["generalGuestbooks"]] == [
        (101, True, 2),
        (102, False, 0),
    ]


def test_길바닥_방명록의_좋아요는_ROAD_GUESTBOOK_LIKE로_판정한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_road(db_session, guestbook_id=201)
    _add_road_like(db_session, guestbook_id=201, user_id=CURRENT_USER_ID)
    _add_road_like(db_session, guestbook_id=201, user_id=OTHER_USER_ID)

    road = _get(client)["roadGuestbooks"][0]

    assert road["isLiked"] is True
    assert road["likeCount"] == 2


def test_길바닥_방명록도_다른_사용자만_누르면_isLiked가_false다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_road(db_session, guestbook_id=201)
    _add_road_like(db_session, guestbook_id=201, user_id=OTHER_USER_ID)

    road = _get(client)["roadGuestbooks"][0]

    assert road["isLiked"] is False
    assert road["likeCount"] == 1


def test_길바닥_방명록의_취소된_좋아요는_세지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_road(db_session, guestbook_id=201)
    _add_road_like(
        db_session,
        guestbook_id=201,
        user_id=CURRENT_USER_ID,
        deleted_at=datetime(2026, 8, 22, 9, 0, 0),
    )
    _add_road_like(
        db_session,
        guestbook_id=201,
        user_id=OTHER_USER_ID,
        deleted_at=datetime(2026, 8, 22, 9, 0, 0),
    )

    road = _get(client)["roadGuestbooks"][0]

    assert road["isLiked"] is False
    assert road["likeCount"] == 0


def test_좋아요가_없는_길바닥_방명록은_false와_0이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_road(db_session, guestbook_id=201)

    road = _get(client)["roadGuestbooks"][0]

    assert road["isLiked"] is False
    assert road["likeCount"] == 0


def test_두_유형의_좋아요는_같은_id여도_서로_섞이지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    # 두 방명록 테이블은 id 가 겹칠 수 있다. 좋아요도 각자의 테이블에서만 센다.
    _add_general(db_session, guestbook_id=300)
    _add_road(db_session, guestbook_id=300)
    _add_like(db_session, guestbook_id=300, user_id=CURRENT_USER_ID)
    _add_like(db_session, guestbook_id=300, user_id=OTHER_USER_ID)
    _add_road_like(db_session, guestbook_id=300, user_id=THIRD_USER_ID)

    body = _get(client)

    general = body["generalGuestbooks"][0]
    road = body["roadGuestbooks"][0]
    assert (general["isLiked"], general["likeCount"]) == (True, 2)
    assert (road["isLiked"], road["likeCount"]) == (False, 1)


def test_다른_길바닥_방명록의_좋아요는_섞이지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_road(db_session, guestbook_id=201, saved_at=LATER_SAVED_AT)
    _add_road(db_session, guestbook_id=202)
    _add_road_like(db_session, guestbook_id=201, user_id=CURRENT_USER_ID)
    _add_road_like(db_session, guestbook_id=201, user_id=OTHER_USER_ID)

    body = _get(client)

    assert [
        (item["id"], item["isLiked"], item["likeCount"]) for item in body["roadGuestbooks"]
    ] == [(201, True, 2), (202, False, 0)]


def test_한_사용자는_같은_길바닥_방명록에_좋아요_행을_하나만_가진다(
    db_session: Session, guestbook_data: None
) -> None:
    _add_road(db_session, guestbook_id=201)
    _add_road_like(
        db_session,
        guestbook_id=201,
        user_id=CURRENT_USER_ID,
        deleted_at=datetime(2026, 8, 22, 9, 0, 0),
    )

    with pytest.raises(IntegrityError):
        _add_road_like(db_session, guestbook_id=201, user_id=CURRENT_USER_ID)

    db_session.rollback()


def test_한_사용자는_같은_방명록에_좋아요_행을_하나만_가진다(
    db_session: Session, guestbook_data: None
) -> None:
    """취소는 행 삭제가 아니라 `deleted_at` 이므로 같은 쌍의 행이 두 개면 안 된다.

    (`GUESTBOOK_LIKE` 의 `guestbook_id` + `user_id` 유니크. 다시 누르면 기존 행을 되살린다)
    """
    _add_general(db_session, guestbook_id=101)
    _add_like(
        db_session,
        guestbook_id=101,
        user_id=CURRENT_USER_ID,
        deleted_at=datetime(2026, 8, 22, 9, 0, 0),
    )

    with pytest.raises(IntegrityError):
        _add_like(db_session, guestbook_id=101, user_id=CURRENT_USER_ID)

    db_session.rollback()


# ---------------------------------------------------------------------
# visitedLocations (BUSINESS_RULES 수정사항 - 방명록 조회)
# ---------------------------------------------------------------------


def test_방문한_장소를_id와_장소명으로_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_visit(db_session, location_id=LOCATION_ID)

    assert _get(client)["visitedLocations"] == [
        {"id": LOCATION_ID, "locationTitle": LOCATION_TITLE}
    ]


def test_같은_장소를_여러_번_방문해도_한_번만_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_visit(db_session, visited_at=datetime(2026, 8, 20, 10, 0, 0))
    _add_visit(db_session, visited_at=datetime(2026, 8, 21, 10, 0, 0))
    _add_visit(db_session, visited_at=datetime(2026, 8, 22, 10, 0, 0))

    assert [item["id"] for item in _get(client)["visitedLocations"]] == [LOCATION_ID]


def test_방문_장소는_장소별_최근_방문_시각_내림차순이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    # 39 는 오래된 방문이 여러 건, 40 은 그보다 나중 방문 한 건이다.
    _add_visit(db_session, location_id=LOCATION_ID, visited_at=datetime(2026, 8, 18, 9, 0, 0))
    _add_visit(db_session, location_id=LOCATION_ID, visited_at=datetime(2026, 8, 19, 9, 0, 0))
    _add_visit(
        db_session, location_id=OTHER_LOCATION_ID, visited_at=datetime(2026, 8, 20, 9, 0, 0)
    )

    assert [item["id"] for item in _get(client)["visitedLocations"]] == [
        OTHER_LOCATION_ID,
        LOCATION_ID,
    ]


def test_최근_방문_시각이_같으면_장소_id가_큰_순이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    same_time = datetime(2026, 8, 20, 9, 0, 0)
    _add_visit(db_session, location_id=LOCATION_ID, visited_at=same_time)
    _add_visit(db_session, location_id=OTHER_LOCATION_ID, visited_at=same_time)

    assert [item["id"] for item in _get(client)["visitedLocations"]] == [
        OTHER_LOCATION_ID,
        LOCATION_ID,
    ]


def test_다른_사용자의_방문_기록은_반환하지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_visit(db_session, user_id=OTHER_USER_ID)

    assert _get(client)["visitedLocations"] == []


def test_방명록이_없어도_방문_장소는_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_visit(db_session)

    body = _get(client)

    # 두 값은 서로 독립이다. 방명록이 없어도 방문 장소는 그대로 내려간다.
    assert body["generalGuestbooks"] == []
    assert body["roadGuestbooks"] == []
    assert [item["id"] for item in body["visitedLocations"]] == [LOCATION_ID]


def test_방문하지_않은_장소에_방명록만_있어도_visitedLocations는_비어_있다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    # visitedLocations 는 VISITED_LOCATION 만 본다. 방명록으로 만들지 않는다.
    _add_general(db_session, guestbook_id=101)

    assert _get(client)["visitedLocations"] == []


# ---------------------------------------------------------------------
# N+1 (BUSINESS_RULES C.11 / 수정사항 - 방명록 조회)
# ---------------------------------------------------------------------


def test_방명록이_늘어도_쿼리_수가_늘지_않는다(
    client: TestClient,
    db_session: Session,
    guestbook_data: None,
    executed_queries: list[str],
) -> None:
    """장소·미션·작성자·캐릭터·좋아요를 방명록마다 다시 조회하면 여기서 걸린다."""
    _add_general(db_session, guestbook_id=101, mission_id=MISSION_ID)
    _add_road(db_session, guestbook_id=201)
    _add_visit(db_session)
    _add_like(db_session, guestbook_id=101, user_id=OTHER_USER_ID)
    _add_road_like(db_session, guestbook_id=201, user_id=OTHER_USER_ID)

    executed_queries.clear()
    _get(client)
    before = len(executed_queries)

    # 방명록과 방문 장소, 좋아요를 늘린다.
    for guestbook_id in (102, 103, 104):
        _add_general(db_session, guestbook_id=guestbook_id, mission_id=MISSION_ID)
        _add_like(db_session, guestbook_id=guestbook_id, user_id=THIRD_USER_ID)
    for guestbook_id in (202, 203, 204):
        _add_road(db_session, guestbook_id=guestbook_id)
        _add_road_like(db_session, guestbook_id=guestbook_id, user_id=THIRD_USER_ID)
    _add_visit(db_session, location_id=OTHER_LOCATION_ID)

    executed_queries.clear()
    body = _get(client)

    assert len(body["generalGuestbooks"]) == 4
    assert len(body["roadGuestbooks"]) == 4
    assert len(body["visitedLocations"]) == 2
    # 인증(사용자 조회) 1 + 방문 장소 1 + 일반 목록 1 + 길바닥 목록 1 = 4 로 고정이다.
    assert len(executed_queries) == before == 4


# ---------------------------------------------------------------------
# 조회 범위 (BUSINESS_RULES C.2)
# ---------------------------------------------------------------------


def test_scope를_생략하면_다른_사용자의_방명록도_함께_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, user_id=OTHER_USER_ID)
    _add_road(db_session, guestbook_id=201, user_id=OTHER_USER_ID)

    body = _get(client)

    # scope 를 생략하면 ALL 이라 작성자로 거르지 않는다.
    assert [item["id"] for item in body["generalGuestbooks"]] == [101]
    assert [item["id"] for item in body["roadGuestbooks"]] == [201]
    assert body["generalGuestbooks"][0]["userId"] == OTHER_USER_ID
    assert body["roadGuestbooks"][0]["userId"] == OTHER_USER_ID


def test_scope가_ALL이면_작성자로_거르지_않는다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, saved_at=LATER_SAVED_AT)
    _add_general(db_session, guestbook_id=102, user_id=OTHER_USER_ID)
    _add_road(db_session, guestbook_id=201, saved_at=LATER_SAVED_AT)
    _add_road(db_session, guestbook_id=202, user_id=OTHER_USER_ID)

    body = _get(client, scope="ALL")

    assert [item["id"] for item in body["generalGuestbooks"]] == [101, 102]
    assert [item["id"] for item in body["roadGuestbooks"]] == [201, 202]


def test_scope가_MINE이면_내가_쓴_방명록만_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, saved_at=LATER_SAVED_AT)
    _add_general(db_session, guestbook_id=102, user_id=OTHER_USER_ID)
    _add_road(db_session, guestbook_id=201, saved_at=LATER_SAVED_AT)
    _add_road(db_session, guestbook_id=202, user_id=OTHER_USER_ID)

    body = _get(client, scope="MINE")

    # 두 유형 모두 같은 범위가 걸린다.
    assert [item["id"] for item in body["generalGuestbooks"]] == [101]
    assert [item["id"] for item in body["roadGuestbooks"]] == [201]


def test_scope가_MINE이면_토큰에_따라_결과가_달라진다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_general(db_session, guestbook_id=102, user_id=OTHER_USER_ID)

    mine = _get(client, scope="MINE")
    theirs = _get(client, OTHER_USER_ID, scope="MINE")

    assert [item["id"] for item in mine["generalGuestbooks"]] == [101]
    assert [item["id"] for item in theirs["generalGuestbooks"]] == [102]


def test_scope가_MINE이어도_삭제된_방명록은_제외한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, deleted_at=datetime(2026, 8, 23, 10, 0, 0))
    _add_general(db_session, guestbook_id=102)

    assert [item["id"] for item in _get(client, scope="MINE")["generalGuestbooks"]] == [102]


def test_scope가_MINE이어도_좋아요와_방문_장소는_현재_사용자_기준_그대로다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101)
    _add_like(db_session, guestbook_id=101, user_id=OTHER_USER_ID)
    _add_like(db_session, guestbook_id=101, user_id=THIRD_USER_ID)
    _add_visit(db_session)

    body = _get(client, scope="MINE")

    general = body["generalGuestbooks"][0]
    # 내 방명록이라 내 좋아요는 없지만 남들이 누른 개수는 그대로 센다.
    assert (general["isLiked"], general["likeCount"]) == (False, 2)
    # 방문 장소는 범위와 무관하게 항상 현재 사용자 기준이다.
    assert [item["id"] for item in body["visitedLocations"]] == [LOCATION_ID]


def test_scope가_MINE이면_결과가_없어도_세_배열을_반환한다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, user_id=OTHER_USER_ID)
    _add_road(db_session, guestbook_id=201, user_id=OTHER_USER_ID)

    assert _get(client, scope="MINE") == {
        "visitedLocations": [],
        "generalGuestbooks": [],
        "roadGuestbooks": [],
    }


@pytest.mark.parametrize(
    "scope",
    [
        pytest.param("EVERYONE", id="정의되지_않은_값"),
        pytest.param("mine", id="소문자"),
        pytest.param("", id="빈_문자열"),
    ],
)
def test_scope가_허용값이_아니면_400이다(
    client: TestClient, db_session: Session, guestbook_data: None, scope: str
) -> None:
    _add_general(db_session, guestbook_id=101)

    response = client.get(
        ENDPOINT, params={"scope": scope}, headers=auth_headers(CURRENT_USER_ID)
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_정의되지_않은_Query는_400이다(
    client: TestClient, guestbook_data: None
) -> None:
    response = client.get(
        ENDPOINT, params={"page": 1}, headers=auth_headers(CURRENT_USER_ID)
    )

    # 페이지네이션 Query 는 받지 않는다.
    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_여러_사용자의_방명록이_한_목록에_섞여_나온다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, user_id=CURRENT_USER_ID, saved_at=LATER_SAVED_AT)
    _add_general(db_session, guestbook_id=102, user_id=OTHER_USER_ID)
    _add_general(db_session, guestbook_id=103, user_id=THIRD_USER_ID)

    body = _get(client)

    # 작성자와 상관없이 정렬 규칙 하나로만 줄을 세운다.
    assert [(item["id"], item["userId"]) for item in body["generalGuestbooks"]] == [
        (101, CURRENT_USER_ID),
        (103, THIRD_USER_ID),
        (102, OTHER_USER_ID),
    ]


def test_작성자_정보는_방명록마다_각자의_것을_붙인다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _assign_ar_character(db_session, user_id=OTHER_USER_ID)
    _add_general(db_session, guestbook_id=101, user_id=CURRENT_USER_ID, saved_at=LATER_SAVED_AT)
    _add_general(db_session, guestbook_id=102, user_id=OTHER_USER_ID)

    body = _get(client)

    assert [
        (item["userId"], item["userNickname"], item["characterImgUrl"])
        for item in body["generalGuestbooks"]
    ] == [
        (CURRENT_USER_ID, NICKNAME, None),
        (OTHER_USER_ID, "한라봉주스", AR_CHARACTER_IMAGE_URL),
    ]


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


def test_토큰이_달라도_방명록_목록_자체는_같다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, saved_at=LATER_SAVED_AT)
    _add_general(db_session, guestbook_id=102, user_id=OTHER_USER_ID)

    mine = _get(client)
    theirs = _get(client, user_id=OTHER_USER_ID)

    assert [item["id"] for item in mine["generalGuestbooks"]] == [101, 102]
    assert [item["id"] for item in theirs["generalGuestbooks"]] == [101, 102]


def test_토큰에_따라_달라지는_것은_isLiked와_방문_장소뿐이다(
    client: TestClient, db_session: Session, guestbook_data: None
) -> None:
    _add_general(db_session, guestbook_id=101, user_id=THIRD_USER_ID)
    _add_like(db_session, guestbook_id=101, user_id=CURRENT_USER_ID)
    _add_visit(db_session, user_id=CURRENT_USER_ID)

    mine = _get(client)["generalGuestbooks"][0]
    theirs = _get(client, user_id=OTHER_USER_ID)["generalGuestbooks"][0]

    # 같은 방명록이지만 좋아요 여부는 토큰 주인 기준이다. 개수는 같다.
    assert (mine["isLiked"], mine["likeCount"]) == (True, 1)
    assert (theirs["isLiked"], theirs["likeCount"]) == (False, 1)
    assert _get(client)["visitedLocations"] != []
    assert _get(client, user_id=OTHER_USER_ID)["visitedLocations"] == []


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
