"""GET /api/v1/map/search - 지도 검색 결과 조회 테스트.

기준 문서: app/map/docs/API_SPEC.md, app/map/docs/BUSINESS_RULES.md
"""

from collections.abc import Iterable
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.common import distance
from app.cooperative_mission.models import CooperativeMission
from app.map import search_classifier
from app.map.models import Location
from app.mission.models import Mission
from app.treasure_mission.models import TreasureMission
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/map/search"

TREASURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TITLE = "보물찾기"
COOPERATIVE_TITLE = "함께 키우는 귤나무"

# 미션이 없는 장소 (recommendedLocations)
SEONGSAN_ID = 39
SEONGSAN_TITLE = "성산일출봉"
SEONGSAN_CATEGORY = "자연"
SEONGSAN_CONTENT_ID = 126273
SEONGSAN_LATITUDE = 33.4582
SEONGSAN_LONGITUDE = 126.9331

PORT_ID = 41
PORT_TITLE = "성산포항"

# 미션이 있는 장소 (missionLocations)
COAST_ID = 52
COAST_TITLE = "성산 해안 산책로"
TREASURE_MISSION_ID = 3

VILLAGE_ID = 61
VILLAGE_TITLE = "성읍민속마을"
COOPERATIVE_MISSION_ID = 2

# 검색어가 들어가지 않는 장소
OTHER_ID = 70
OTHER_TITLE = "한담해안산책로"

IMAGE_URL = "https://example.com/locations/39.jpg"

USER_LATITUDE = 33.4524
USER_LONGITUDE = 126.9248

KEYWORD = "성산"


def _params(**overrides: object) -> dict[str, object]:
    return {
        "keyword": KEYWORD,
        "userLatitude": USER_LATITUDE,
        "userLongitude": USER_LONGITUDE,
        **overrides,
    }


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """TourAPI 이미지 조회를 막고 호출된 content_id 를 기록한다.

    검색 응답의 이미지는 분류 모듈(`search_classifier`)에서 조회한다.
    """
    called: list[int] = []

    def fake_get_location_image_url(content_id: int) -> str | None:
        called.append(content_id)
        return IMAGE_URL if content_id == SEONGSAN_CONTENT_ID else None

    def fake_get_location_image_urls(
        content_ids: Iterable[int], **_: object
    ) -> dict[int, str | None]:
        return {
            content_id: fake_get_location_image_url(content_id)
            for content_id in dict.fromkeys(content_ids)
        }

    monkeypatch.setattr(
        search_classifier, "get_location_image_urls", fake_get_location_image_urls
    )
    return called


@pytest.fixture
def user(db_session: Session) -> None:
    db_session.add(
        User(
            id=CURRENT_USER_ID,
            access_token_hash=access_token_hash(CURRENT_USER_ID),
            nickname="나민",
            point=0,
        )
    )
    db_session.commit()


def _add_location(
    db_session: Session,
    *,
    location_id: int,
    title: str,
    category: str = "관광지",
    content_id: int | None = None,
    latitude: float = SEONGSAN_LATITUDE,
    longitude: float = SEONGSAN_LONGITUDE,
) -> None:
    db_session.add(
        Location(
            id=location_id,
            content_id=content_id if content_id is not None else location_id,
            location_title=title,
            location_address="제주특별자치도",
            location_category=category,
            radius=300,
            mx=longitude,
            my=latitude,
        )
    )
    db_session.commit()


@pytest.fixture
def missions(db_session: Session) -> None:
    """세부 미션이 참조할 공통 미션."""
    db_session.add_all(
        [
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title=TREASURE_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "시작", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title=COOPERATIVE_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
        ]
    )
    db_session.commit()


def _add_treasure_mission(
    db_session: Session, *, mission_id: int, location_id: int
) -> None:
    db_session.add(
        TreasureMission(
            id=mission_id,
            mission_id=TREASURE_TYPE_ID,
            location_id=location_id,
            item_total_count=3,
            reward_detail={"point": 100},
        )
    )
    db_session.commit()


def _add_cooperative_mission(
    db_session: Session, *, mission_id: int, location_id: int
) -> None:
    db_session.add(
        CooperativeMission(
            id=mission_id,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=location_id,
            reward_detail={"point": 200},
        )
    )
    db_session.commit()


@pytest.fixture
def search_data(db_session: Session, user: None, missions: None) -> None:
    """검색어 '성산'이 들어간 장소 4곳 + 안 들어간 장소 1곳."""
    _add_location(
        db_session,
        location_id=SEONGSAN_ID,
        title=SEONGSAN_TITLE,
        category=SEONGSAN_CATEGORY,
        content_id=SEONGSAN_CONTENT_ID,
    )
    _add_location(db_session, location_id=PORT_ID, title=PORT_TITLE, category="항구")
    _add_location(db_session, location_id=COAST_ID, title=COAST_TITLE)
    _add_location(db_session, location_id=VILLAGE_ID, title=VILLAGE_TITLE)
    _add_location(db_session, location_id=OTHER_ID, title=OTHER_TITLE)

    _add_treasure_mission(
        db_session, mission_id=TREASURE_MISSION_ID, location_id=COAST_ID
    )
    _add_cooperative_mission(
        db_session, mission_id=COOPERATIVE_MISSION_ID, location_id=VILLAGE_ID
    )


def _get(client: TestClient, **overrides: object) -> dict:
    response = client.get(ENDPOINT, params=_params(**overrides))
    assert response.status_code == 200
    return response.json()


def _recommended_ids(body: dict) -> list[int]:
    return [location["locationId"] for location in body["recommendedLocations"]]


def _mission_ids(body: dict) -> list[int]:
    return [location["locationId"] for location in body["missionLocations"]]


def _expected_distance(latitude: float, longitude: float) -> int:
    return distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, latitude, longitude
    )


# ---------------------------------------------------------------------
# 검색과 분류
# ---------------------------------------------------------------------


def test_검색어가_포함된_장소를_두_배열로_나눠_반환한다(
    client: TestClient, search_data: None
) -> None:
    body = _get(client)

    # 성읍민속마을에는 '성산'이 없으므로 검색되지 않는다.
    assert sorted(_recommended_ids(body)) == [SEONGSAN_ID, PORT_ID]
    assert _mission_ids(body) == [COAST_ID]


def test_추천_장소_응답_필드를_모두_반환한다(
    client: TestClient, search_data: None
) -> None:
    body = _get(client)

    seongsan = next(
        location
        for location in body["recommendedLocations"]
        if location["locationId"] == SEONGSAN_ID
    )
    assert seongsan == {
        "locationId": SEONGSAN_ID,
        "locationTitle": SEONGSAN_TITLE,
        "locationCategory": SEONGSAN_CATEGORY,
        "representativeImageUrl": IMAGE_URL,
        "distanceMeter": _expected_distance(SEONGSAN_LATITUDE, SEONGSAN_LONGITUDE),
    }


def test_미션_장소_응답_필드를_모두_반환한다(
    client: TestClient, search_data: None
) -> None:
    body = _get(client)

    assert body["missionLocations"] == [
        {
            "locationId": COAST_ID,
            "missionId": TREASURE_MISSION_ID,
            "missionType": "TREASURE",
            "locationTitle": COAST_TITLE,
            "missionTitle": TREASURE_TITLE,
            "representativeImageUrl": None,
            "distanceMeter": _expected_distance(
                SEONGSAN_LATITUDE, SEONGSAN_LONGITUDE
            ),
        }
    ]


def test_협동_미션이_연결된_장소도_미션_장소로_분류한다(
    client: TestClient, search_data: None
) -> None:
    body = _get(client, keyword="성읍")

    assert body["recommendedLocations"] == []
    assert body["missionLocations"] == [
        {
            "locationId": VILLAGE_ID,
            "missionId": COOPERATIVE_MISSION_ID,
            "missionType": "COOPERATIVE",
            "locationTitle": VILLAGE_TITLE,
            "missionTitle": COOPERATIVE_TITLE,
            "representativeImageUrl": None,
            "distanceMeter": _expected_distance(
                SEONGSAN_LATITUDE, SEONGSAN_LONGITUDE
            ),
        }
    ]


def test_미션이_생기면_추천에서_미션_장소로_옮겨간다(
    client: TestClient, db_session: Session, search_data: None
) -> None:
    assert SEONGSAN_ID in _recommended_ids(_get(client))

    _add_treasure_mission(db_session, mission_id=99, location_id=SEONGSAN_ID)

    body = _get(client)
    assert SEONGSAN_ID not in _recommended_ids(body)
    assert SEONGSAN_ID in _mission_ids(body)


def test_두_유형이_모두_연결되면_세부_미션_id가_작은_쪽을_쓴다(
    client: TestClient, db_session: Session, search_data: None
) -> None:
    # 보물찾기 9 / 협동 4 -> 유형과 관계없이 id 가 작은 협동 미션
    _add_treasure_mission(db_session, mission_id=9, location_id=SEONGSAN_ID)
    _add_cooperative_mission(db_session, mission_id=4, location_id=SEONGSAN_ID)

    body = _get(client)

    seongsan = next(
        location
        for location in body["missionLocations"]
        if location["locationId"] == SEONGSAN_ID
    )
    assert seongsan["missionId"] == 4
    assert seongsan["missionType"] == "COOPERATIVE"
    # 미션 장소는 추천에 중복해서 넣지 않는다.
    assert SEONGSAN_ID not in _recommended_ids(body)


# ---------------------------------------------------------------------
# 검색어 매칭
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("keyword", "expected"),
    [
        pytest.param("성산", [SEONGSAN_ID, PORT_ID], id="이름_앞부분"),
        pytest.param("일출", [SEONGSAN_ID], id="이름_중간"),
        pytest.param("포항", [PORT_ID], id="이름_끝"),
        pytest.param("성산일출봉", [SEONGSAN_ID], id="이름_전체"),
    ],
)
def test_검색어가_이름의_어디에_있어도_찾는다(
    client: TestClient, search_data: None, keyword: str, expected: list[int]
) -> None:
    body = _get(client, keyword=keyword)

    assert sorted(_recommended_ids(body)) == sorted(expected)


def test_검색어_앞뒤_공백은_지우고_검색한다(
    client: TestClient, search_data: None
) -> None:
    body = _get(client, keyword="  성산일출봉  ")

    assert _recommended_ids(body) == [SEONGSAN_ID]


def test_LIKE_와일드카드는_글자_그대로_찾는다(
    client: TestClient, db_session: Session, search_data: None
) -> None:
    _add_location(db_session, location_id=80, title="100% 제주")

    # '%' 를 와일드카드로 쓰면 모든 장소가 걸린다.
    assert _recommended_ids(_get(client, keyword="%")) == [80]
    # '_' 도 마찬가지다.
    assert _get(client, keyword="_")["recommendedLocations"] == []


def test_검색_결과가_없어도_200과_빈_배열을_반환한다(
    client: TestClient, search_data: None
) -> None:
    assert _get(client, keyword="없는장소") == {
        "recommendedLocations": [],
        "missionLocations": [],
    }


def test_미션_장소만_검색되면_추천만_빈_배열이다(
    client: TestClient, search_data: None
) -> None:
    body = _get(client, keyword="해안 산책로")

    assert body["recommendedLocations"] == []
    assert _mission_ids(body) == [COAST_ID]


def test_검색_결과에_개수_제한이_없다(
    client: TestClient, db_session: Session, search_data: None
) -> None:
    for index in range(100, 120):
        _add_location(db_session, location_id=index, title=f"성산 {index}")

    body = _get(client)

    # 원래 2곳 + 새로 만든 20곳
    assert len(body["recommendedLocations"]) == 22


# ---------------------------------------------------------------------
# 거리와 정렬
# ---------------------------------------------------------------------


def test_거리는_공통_모듈_결과와_같다(
    client: TestClient, db_session: Session, search_data: None
) -> None:
    body = _get(client)

    port = next(
        location
        for location in body["recommendedLocations"]
        if location["locationId"] == PORT_ID
    )
    assert port["distanceMeter"] == _expected_distance(
        SEONGSAN_LATITUDE, SEONGSAN_LONGITUDE
    )


def test_가까운_순으로_정렬한다(
    client: TestClient, db_session: Session, search_data: None
) -> None:
    # 사용자 위치에서 점점 먼 장소들
    _add_location(
        db_session,
        location_id=201,
        title="성산 먼곳",
        latitude=33.60,
        longitude=127.00,
    )
    _add_location(
        db_session,
        location_id=202,
        title="성산 가까운곳",
        latitude=USER_LATITUDE,
        longitude=USER_LONGITUDE,
    )

    body = _get(client)

    distances = [
        location["distanceMeter"] for location in body["recommendedLocations"]
    ]
    assert distances == sorted(distances)
    assert _recommended_ids(body)[0] == 202
    assert _recommended_ids(body)[-1] == 201


def test_거리가_같으면_장소_id가_작은_순이다(
    client: TestClient, search_data: None
) -> None:
    # 픽스처의 장소들은 좌표가 같아 거리가 모두 같다.
    assert _recommended_ids(_get(client)) == [SEONGSAN_ID, PORT_ID]


def test_미션_장소도_가까운_순으로_정렬한다(
    client: TestClient, db_session: Session, search_data: None
) -> None:
    _add_location(
        db_session,
        location_id=203,
        title="성산 가까운 미션",
        latitude=USER_LATITUDE,
        longitude=USER_LONGITUDE,
    )
    _add_treasure_mission(db_session, mission_id=98, location_id=203)

    body = _get(client)

    assert _mission_ids(body) == [203, COAST_ID]


# ---------------------------------------------------------------------
# 대표 이미지
# ---------------------------------------------------------------------


def test_이미지를_조회하지_못하면_null로_두고_실패시키지_않는다(
    client: TestClient, search_data: None
) -> None:
    body = _get(client)

    port = next(
        location
        for location in body["recommendedLocations"]
        if location["locationId"] == PORT_ID
    )
    assert port["representativeImageUrl"] is None


def test_검색된_장소마다_TourAPI를_호출한다(
    client: TestClient, search_data: None, stub_location_image: list[int]
) -> None:
    _get(client)

    # 검색된 3곳(성산일출봉/성산포항/성산 해안 산책로)만 조회한다.
    assert sorted(stub_location_image) == sorted(
        [SEONGSAN_CONTENT_ID, PORT_ID, COAST_ID]
    )


# ---------------------------------------------------------------------
# 400 / 401
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("keyword", id="keyword_누락"),
        pytest.param("userLatitude", id="userLatitude_누락"),
        pytest.param("userLongitude", id="userLongitude_누락"),
    ],
)
def test_필수_Query가_없으면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, search_data: None, field: str
) -> None:
    params = _params()
    del params[field]

    response = client.get(ENDPOINT, params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("keyword", "", id="빈_검색어"),
        pytest.param("keyword", "   ", id="공백만_있는_검색어"),
        pytest.param("userLatitude", "abc", id="위도가_숫자가_아님"),
        pytest.param("userLatitude", 91, id="위도_상한_초과"),
        pytest.param("userLatitude", -91, id="위도_하한_미만"),
        pytest.param("userLongitude", 181, id="경도_상한_초과"),
        pytest.param("userLongitude", -181, id="경도_하한_미만"),
    ],
)
def test_Query_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, search_data: None, field: str, value: object
) -> None:
    response = client.get(ENDPOINT, params=_params(**{field: value}))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_한_글자_검색어도_허용한다(client: TestClient, search_data: None) -> None:
    body = _get(client, keyword="성")

    assert sorted(_recommended_ids(body)) == [SEONGSAN_ID, PORT_ID]


def test_인증_헤더가_없으면_401로_응답한다(
    client: TestClient, search_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT, params=_params())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_토큰의_사용자가_없으면_401로_응답한다(
    client: TestClient, search_data: None
) -> None:
    response = client.get(ENDPOINT, params=_params(), headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_인증에_실패하면_TourAPI를_호출하지_않는다(
    client: TestClient, search_data: None, stub_location_image: list[int]
) -> None:
    client.headers.pop("Authorization", None)

    client.get(ENDPOINT, params=_params())

    assert stub_location_image == []


def test_문서에_401을_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"][ENDPOINT]["get"]["responses"]

    assert sorted(responses) == ["200", "400", "401", "500"]
