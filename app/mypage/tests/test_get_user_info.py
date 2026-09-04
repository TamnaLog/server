"""GET /api/v1/users/me - 사용자 정보 조회 테스트.

기준 문서: app/mypage/docs/API_SPEC.md, app/mypage/docs/BUSINESS_RULES.md
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.treasure_mission.models import ArCharacter
from app.user.models import User, UserTravelStyle
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me"

OTHER_USER_ID = 2

# 어떤 사용자에게도 발급되지 않은 토큰용 id
UNKNOWN_USER_ID = 999

TRAVEL_STYLE_ID = 1
USER_TYPE = "동네 깊숙이 걷는 로컬 탐험가"

CHARACTER_ID = 2
CHARACTER_IMAGE_URL = "https://example.com/characters/local-explorer.png"

NICKNAME = "몽글몽글파도"
CATEGORIES = ["PHOTO", "LOCAL"]
TRANSPORTATION = ["WALK", "BUS"]
TRAVEL_STYLE = ["RIGHT_HERE", "NEAR_AROUND"]
TARGET_STEP = 12000


@pytest.fixture
def travel_style_and_character(db_session: Session) -> None:
    """여행 유형 1개 + AR 캐릭터 1개."""
    db_session.add_all(
        [
            UserTravelStyle(
                id=TRAVEL_STYLE_ID,
                user_type=USER_TYPE,
                type_description="설명",
                hashtags=["#로컬탐방", "#산책"],
            ),
            ArCharacter(
                id=CHARACTER_ID,
                character_name="로컬 탐험가",
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="획득 조건",
                character_img_url=CHARACTER_IMAGE_URL,
                hashtags=["#캐릭터"],
            ),
        ]
    )
    db_session.commit()


def _add_user(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    nickname: str | None = NICKNAME,
    categories: list[str] | None = None,
    transportation: list[str] | None = None,
    travel_style: list[str] | None = None,
    user_travel_style_id: int | None = TRAVEL_STYLE_ID,
    ar_character_id: int | None = CHARACTER_ID,
    target_step: int = TARGET_STEP,
) -> None:
    db_session.add(
        User(
            id=user_id,
            access_token_hash=access_token_hash(user_id),
            nickname=nickname,
            expectation=categories,
            transportation=transportation,
            travel_style=travel_style,
            user_travel_style_id=user_travel_style_id,
            ar_character_id=ar_character_id,
            target_step=target_step,
            point=0,
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------
# 응답 형식
# ---------------------------------------------------------------------


def test_여행_유형과_대표_캐릭터가_연결된_사용자의_정보를_모두_반환한다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    _add_user(
        db_session,
        categories=CATEGORIES,
        transportation=TRANSPORTATION,
        travel_style=TRAVEL_STYLE,
    )

    response = client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 200
    assert response.json() == {
        "userType": USER_TYPE,
        "arCharacterImageUrl": CHARACTER_IMAGE_URL,
        "nickname": NICKNAME,
        "categories": CATEGORIES,
        "transportation": TRANSPORTATION,
        "travelStyle": TRAVEL_STYLE,
        "targetStepCount": TARGET_STEP,
    }


def test_여행_유형과_대표_캐릭터가_없으면_두_값만_null이다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    # 두 FK 가 모두 NULL 이어도 사용자가 직접 저장한 값은 그대로 나와야 한다.
    _add_user(
        db_session,
        categories=CATEGORIES,
        transportation=TRANSPORTATION,
        travel_style=TRAVEL_STYLE,
        user_travel_style_id=None,
        ar_character_id=None,
    )

    body = client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID)).json()

    assert body["userType"] is None
    assert body["arCharacterImageUrl"] is None
    assert body["nickname"] == NICKNAME
    assert body["categories"] == CATEGORIES
    assert body["transportation"] == TRANSPORTATION
    assert body["travelStyle"] == TRAVEL_STYLE
    assert body["targetStepCount"] == TARGET_STEP


def test_닉네임을_설정하지_않았으면_null을_반환한다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    _add_user(db_session, nickname=None)

    body = client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID)).json()

    assert body["nickname"] is None


# ---------------------------------------------------------------------
# 선택값 세 컬럼의 null / 빈 배열 구분
# ---------------------------------------------------------------------


def test_선택값이_설정_전이면_null을_그대로_반환한다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    _add_user(db_session)

    body = client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID)).json()

    assert body["categories"] is None
    assert body["transportation"] is None
    assert body["travelStyle"] is None


def test_선택값이_빈_배열이면_null로_바꾸지_않고_빈_배열을_반환한다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    _add_user(db_session, categories=[], transportation=[], travel_style=[])

    body = client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID)).json()

    assert body["categories"] == []
    assert body["transportation"] == []
    assert body["travelStyle"] == []


def test_선택값은_저장_순서를_바꾸거나_중복을_제거하지_않는다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    # 저장값을 그대로 내려줘야 한다. (정렬/중복 제거/enum 변환 금지)
    saved_categories = ["WALKING", "PHOTO", "PHOTO"]
    _add_user(
        db_session,
        categories=saved_categories,
        transportation=["BUS", "WALK"],
        travel_style=[],
    )

    body = client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID)).json()

    assert body["categories"] == saved_categories
    assert body["transportation"] == ["BUS", "WALK"]
    assert body["travelStyle"] == []


# ---------------------------------------------------------------------
# 사용자 구분 / 상태 변경 없음
# ---------------------------------------------------------------------


def test_다른_사용자의_정보는_섞이지_않는다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    _add_user(db_session, categories=CATEGORIES)
    _add_user(
        db_session,
        user_id=OTHER_USER_ID,
        nickname="한라봉주스",
        categories=["CAFE"],
        user_travel_style_id=None,
        ar_character_id=None,
        target_step=3000,
    )

    body = client.get(ENDPOINT, headers=auth_headers(OTHER_USER_ID)).json()

    assert body["nickname"] == "한라봉주스"
    assert body["categories"] == ["CAFE"]
    assert body["userType"] is None
    assert body["arCharacterImageUrl"] is None
    assert body["targetStepCount"] == 3000


def test_조회해도_사용자_데이터가_바뀌지_않는다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    _add_user(
        db_session,
        categories=CATEGORIES,
        transportation=TRANSPORTATION,
        travel_style=TRAVEL_STYLE,
    )

    client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID))

    db_session.expire_all()
    saved = db_session.get(User, CURRENT_USER_ID)
    assert saved is not None
    assert saved.nickname == NICKNAME
    assert saved.expectation == CATEGORIES
    assert saved.transportation == TRANSPORTATION
    assert saved.travel_style == TRAVEL_STYLE
    assert saved.user_travel_style_id == TRAVEL_STYLE_ID
    assert saved.ar_character_id == CHARACTER_ID
    assert saved.target_step == TARGET_STEP


# ---------------------------------------------------------------------
# 추가 쿼리 (BUSINESS_RULES 사용자 정보 조회 2.)
# ---------------------------------------------------------------------


def test_여행_유형과_대표_캐릭터를_따로_조회하지_않는다(
    client: TestClient,
    db_session: Session,
    travel_style_and_character: None,
    executed_queries: list[str],
) -> None:
    """두 nullable 관계를 join 으로 함께 읽는지 본다. 따로 조회하면 쿼리 수가 늘어 걸린다."""
    _add_user(db_session, categories=CATEGORIES)

    executed_queries.clear()
    response = client.get(ENDPOINT, headers=auth_headers(CURRENT_USER_ID))

    assert response.status_code == 200
    # 인증(사용자 조회) 1 + 사용자 + 여행 유형 + 대표 캐릭터 조회 1 = 2 로 고정이다.
    assert len(executed_queries) == 2


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------

# 헤더 형식 등 인증 자체의 분기는 공통 규칙이라 app/core/tests/test_current_user_token.py 에서 본다.
# 여기서는 이 라우트가 공통 인증 의존성을 타는지만 확인한다.


def test_어떤_사용자의_토큰도_아니면_401을_반환한다(
    client: TestClient, db_session: Session, travel_style_and_character: None
) -> None:
    _add_user(db_session)

    response = client.get(ENDPOINT, headers=auth_headers(UNKNOWN_USER_ID))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
