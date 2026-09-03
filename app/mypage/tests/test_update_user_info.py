"""PUT /api/v1/users/me/profile - 사용자 정보 변경 테스트.

기준 문서: app/mypage/docs/API_SPEC.md, app/mypage/docs/BUSINESS_RULES.md
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.onboarding.onboarding_matcher import DEFAULT_AR_CHARACTER_NAME
from app.treasure_mission.models import AcquiredArCharacter, ArCharacter
from app.user.models import User, UserTravelStyle
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me/profile"

OTHER_USER_ID = 2

TRAVEL_STYLE_IDS = (1, 2, 3)
CHARACTER_IDS = (1, 2, 3)
DEFAULT_CHARACTER_ID = 3

BEFORE_NICKNAME = "몽글몽글파도"
BEFORE_TARGET_STEP = 10000

NEW_NICKNAME = "돌담산책"
NEW_CATEGORIES = ["PHOTO", "LOCAL"]
NEW_TRANSPORTATION = ["WALK", "BUS"]
NEW_TRAVEL_STYLE = ["RIGHT_HERE", "NEAR_AROUND"]
NEW_TARGET_STEP = 12000


@pytest.fixture
def profile_data(db_session: Session) -> None:
    """사용자 2명 + 여행 유형 3개 + 캐릭터 3개(기본 캐릭터 포함)."""
    db_session.add_all(
        [
            UserTravelStyle(
                id=travel_style_id,
                user_type=f"유형 {travel_style_id}",
                type_description="설명",
                hashtags=["#태그"],
            )
            for travel_style_id in TRAVEL_STYLE_IDS
        ]
    )
    db_session.add_all(
        [
            ArCharacter(
                id=character_id,
                character_name=(
                    DEFAULT_AR_CHARACTER_NAME
                    if character_id == DEFAULT_CHARACTER_ID
                    else f"캐릭터 {character_id}"
                ),
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="조건",
                character_img_url=f"https://example.com/{character_id}.png",
                hashtags=["#태그"],
            )
            for character_id in CHARACTER_IDS
        ]
    )
    db_session.commit()

    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname=BEFORE_NICKNAME,
                point=100,
                target_step=BEFORE_TARGET_STEP,
                expectation=["CULTURE"],
                transportation=["CAR"],
                travel_style=["NEAR_DESTINATION"],
                user_travel_style_id=TRAVEL_STYLE_IDS[0],
                ar_character_id=CHARACTER_IDS[0],
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


def _body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "nickname": NEW_NICKNAME,
        "categories": NEW_CATEGORIES,
        "transportation": NEW_TRANSPORTATION,
        "travelStyle": NEW_TRAVEL_STYLE,
        "targetStepCount": NEW_TARGET_STEP,
    }
    body.update(overrides)
    return body


def _put(
    client: TestClient,
    *,
    body: dict[str, object] | None = None,
    user_id: int = CURRENT_USER_ID,
    **overrides: object,
) -> Any:
    payload = _body(**overrides) if body is None else body
    return client.put(ENDPOINT, json=payload, headers=auth_headers(user_id))


def _user(db_session: Session, user_id: int = CURRENT_USER_ID) -> User:
    db_session.expire_all()
    user = db_session.get(User, user_id)
    assert user is not None
    return user


# ---------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------


def test_프로필을_바꾸면_204와_빈_본문을_반환한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    response = _put(client)

    assert response.status_code == 204
    assert response.content == b""


def test_다섯_필드를_모두_요청값으로_교체한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client)

    user = _user(db_session)
    assert user.nickname == NEW_NICKNAME
    assert user.expectation == NEW_CATEGORIES
    assert user.transportation == NEW_TRANSPORTATION
    assert user.travel_style == NEW_TRAVEL_STYLE
    assert user.target_step == NEW_TARGET_STEP


def test_닉네임은_앞뒤_공백을_지운_값으로_저장한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client, nickname="  돌담산책  ")

    assert _user(db_session).nickname == "돌담산책"


def test_닉네임은_다른_사용자와_겹쳐도_된다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    response = _put(client, nickname="한라봉주스")

    assert response.status_code == 204
    assert _user(db_session).nickname == "한라봉주스"


def test_빈_배열로_보낸_선택값은_빈_배열로_저장한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client, categories=[], transportation=[], travelStyle=NEW_TRAVEL_STYLE)

    user = _user(db_session)
    # 빈 배열을 null 로 바꾸지 않고 요청값 그대로 저장한다.
    assert user.expectation == []
    assert user.transportation == []
    assert user.travel_style == NEW_TRAVEL_STYLE


def test_빈_배열로_보내면_이전_선택값이_남지_않는다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    # 픽스처의 사용자는 세 선택값을 모두 가지고 있다.
    _put(client, categories=[], transportation=[], travelStyle=[])

    user = _user(db_session)
    assert (user.expectation, user.transportation, user.travel_style) == ([], [], [])


def test_다른_사용자의_정보는_바뀌지_않는다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client)

    other = _user(db_session, OTHER_USER_ID)
    assert other.nickname == "한라봉주스"
    assert other.expectation is None


def test_토큰의_사용자_정보를_바꾼다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client, user_id=OTHER_USER_ID)

    # 요청 Body 에 사용자 id 가 없으므로 토큰 주인이 바뀐다.
    assert _user(db_session, OTHER_USER_ID).nickname == NEW_NICKNAME
    assert _user(db_session).nickname == BEFORE_NICKNAME


# ---------------------------------------------------------------------
# 여행 유형 / 캐릭터 재배정
# ---------------------------------------------------------------------


def test_여행_유형과_대표_캐릭터를_다시_배정한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client)

    user = _user(db_session)
    # 임시 랜덤 배정이라 값 자체가 아니라 DB 에 있는 값 중 하나인지로 확인한다.
    assert user.user_travel_style_id in TRAVEL_STYLE_IDS
    assert user.ar_character_id in CHARACTER_IDS


def test_선택_배열이_모두_비면_여행_유형을_비우고_기본_캐릭터를_배정한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client, categories=[], transportation=[], travelStyle=[])

    user = _user(db_session)
    # 온보딩 건너뛰기와 같은 처리다.
    assert user.user_travel_style_id is None
    assert user.ar_character_id == DEFAULT_CHARACTER_ID


def test_일부만_비면_일반_매칭을_한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client, categories=[], transportation=[], travelStyle=NEW_TRAVEL_STYLE)

    user = _user(db_session)
    # 건너뛰기가 아니라 빈 배열을 포함한 전체 선택값으로 배정한다.
    assert user.user_travel_style_id in TRAVEL_STYLE_IDS


def test_선택_배열이_모두_비어도_선택값은_빈_배열로_저장한다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    _put(client, categories=[], transportation=[], travelStyle=[])

    user = _user(db_session)
    # 여행 유형과 캐릭터만 건너뛰기와 같게 처리하고, 선택값 컬럼은 요청값 그대로 둔다.
    # (온보딩 건너뛰기가 세 컬럼을 NULL 로 두는 것과 다르다)
    assert user.expectation == []
    assert user.transportation == []
    assert user.travel_style == []


def test_대표_캐릭터만_바꾸고_획득_이력은_건드리지_않는다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    db_session.add(
        AcquiredArCharacter(
            ar_character_id=CHARACTER_IDS[0],
            user_id=CURRENT_USER_ID,
            acquired_mission_id=1,
        )
    )
    db_session.commit()

    _put(client)

    acquired = list(db_session.scalars(select(AcquiredArCharacter)))
    # 재배정으로 도감의 획득 이력이 생기거나 사라지지 않는다.
    assert len(acquired) == 1
    assert acquired[0].ar_character_id == CHARACTER_IDS[0]


def test_배정할_캐릭터가_없으면_500이고_아무것도_바뀌지_않는다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    for character_id in CHARACTER_IDS:
        character = db_session.get(ArCharacter, character_id)
        assert character is not None
        db_session.delete(character)
    db_session.commit()

    response = _put(client)

    assert response.status_code == 500
    # 매칭이 실패하면 필드 갱신도 롤백된다.
    assert _user(db_session).nickname == BEFORE_NICKNAME


def test_저장에_실패하면_모든_변경이_롤백된다(
    client: TestClient,
    db_session: Session,
    profile_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(self: Session) -> None:
        raise RuntimeError("DB 저장 실패")

    monkeypatch.setattr(Session, "commit", boom)

    response = _put(client)

    assert response.status_code == 500
    user = _user(db_session)
    assert user.nickname == BEFORE_NICKNAME
    assert user.target_step == BEFORE_TARGET_STEP
    assert user.expectation == ["CULTURE"]


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing",
    ["nickname", "categories", "transportation", "travelStyle", "targetStepCount"],
)
def test_필드가_하나라도_빠지면_400이다(
    client: TestClient, db_session: Session, profile_data: None, missing: str
) -> None:
    body = _body()
    del body[missing]

    response = _put(client, body=body)

    # 부분 갱신이 아니라 전체 교체라 다섯 필드가 모두 필수다.
    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _user(db_session).nickname == BEFORE_NICKNAME


@pytest.mark.parametrize(
    "nickname",
    [
        pytest.param("", id="빈_문자열"),
        pytest.param("   ", id="공백만"),
        pytest.param("가" * 21, id="21자"),
    ],
)
def test_닉네임_길이가_규칙을_벗어나면_400이다(
    client: TestClient, db_session: Session, profile_data: None, nickname: str
) -> None:
    response = _put(client, nickname=nickname)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _user(db_session).nickname == BEFORE_NICKNAME


def test_공백을_지우면_20자인_닉네임은_저장된다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    nickname = "가" * 20

    response = _put(client, nickname=f"  {nickname}  ")

    # 길이는 앞뒤 공백을 지운 값 기준이다.
    assert response.status_code == 204
    assert _user(db_session).nickname == nickname


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"categories": ["PHOTO", "PHOTO"]}, id="categories_중복"),
        pytest.param({"transportation": ["WALK", "WALK"]}, id="transportation_중복"),
        pytest.param(
            {"travelStyle": ["RIGHT_HERE", "RIGHT_HERE"]}, id="travelStyle_중복"
        ),
    ],
)
def test_선택_배열에_중복이_있으면_400이다(
    client: TestClient, db_session: Session, profile_data: None, overrides: dict
) -> None:
    response = _put(client, **overrides)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _user(db_session).nickname == BEFORE_NICKNAME


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"categories": ["MOUNTAIN"]}, id="정의되지_않은_categories"),
        pytest.param({"categories": ["photo"]}, id="소문자_categories"),
        pytest.param({"transportation": ["TRAIN"]}, id="정의되지_않은_transportation"),
        pytest.param({"travelStyle": ["FAR_AWAY"]}, id="정의되지_않은_travelStyle"),
        pytest.param({"categories": "PHOTO"}, id="배열이_아닌_값"),
    ],
)
def test_허용되지_않은_선택값이면_400이다(
    client: TestClient, db_session: Session, profile_data: None, overrides: dict
) -> None:
    response = _put(client, **overrides)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    "target_step_count",
    [
        pytest.param(0, id="0"),
        pytest.param(-1, id="음수"),
        pytest.param(100001, id="최대값_초과"),
        pytest.param(True, id="bool"),
        pytest.param(1000.5, id="소수"),
        pytest.param(10000.0, id="소수점이_붙은_정수"),
        pytest.param("10000", id="문자열"),
    ],
)
def test_목표_걸음_수가_규칙을_벗어나면_400이다(
    client: TestClient,
    db_session: Session,
    profile_data: None,
    target_step_count: object,
) -> None:
    response = _put(client, targetStepCount=target_step_count)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _user(db_session).target_step == BEFORE_TARGET_STEP


@pytest.mark.parametrize(
    "target_step_count", [pytest.param(1, id="최소값"), pytest.param(100000, id="최대값")]
)
def test_목표_걸음_수의_경계값은_저장된다(
    client: TestClient, db_session: Session, profile_data: None, target_step_count: int
) -> None:
    response = _put(client, targetStepCount=target_step_count)

    assert response.status_code == 204
    assert _user(db_session).target_step == target_step_count


def test_정의되지_않은_필드가_있으면_400이다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    response = _put(client, userId=2)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_빈_body는_400이다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    response = _put(client, body={})

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


def test_인증_헤더가_없으면_401이다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.put(ENDPOINT, json=_body())

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _user(db_session).nickname == BEFORE_NICKNAME


def test_토큰의_사용자가_없으면_401이다(
    client: TestClient, db_session: Session, profile_data: None
) -> None:
    response = _put(client, user_id=999)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _user(db_session).nickname == BEFORE_NICKNAME


def test_문서에_401을_노출한다(client: TestClient) -> None:
    responses = client.get("/openapi.json").json()["paths"][ENDPOINT]["put"]["responses"]

    assert sorted(responses) == ["204", "400", "401", "500"]
