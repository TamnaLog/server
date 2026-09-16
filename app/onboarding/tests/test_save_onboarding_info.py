"""PATCH /api/v1/users/me - 사용자 온보딩 정보 저장 테스트.

기준 문서: app/onboarding/docs/API_SPEC.md, app/onboarding/docs/BUSINESS_RULES.md
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.onboarding.models import ArCharacter, User, UserTravelStyle
from app.onboarding.onboarding_matcher import ONBOARDING_AR_CHARACTER_IDS
from conftest import CURRENT_USER_ID, access_token_hash


ENDPOINT = "/api/v1/users/me"

ONBOARDING_CHARACTER_IDS = {7, 12}


@pytest.fixture
def onboarding_data(db_session: Session) -> None:
    """여행 유형 / AR 캐릭터 / 사용자 목업 데이터."""
    db_session.add_all(
        [
            UserTravelStyle(
                id=1,
                user_type="새로운 순간을 담는 기록 탐험가",
                type_description="사진과 포토스팟으로 순간을 남기는 타입이에요.",
                hashtags=["#인생사진", "#로컬 탐방"],
            ),
            UserTravelStyle(
                id=2,
                user_type="동네 깊숙이 걷는 로컬 탐험가",
                type_description="골목과 시장의 분위기를 좋아하는 타입이에요.",
                hashtags=["#로컬 탐방", "#골목 산책"],
            ),
            ArCharacter(
                id=1,
                character_name="바람 정령",
                character_description="온보딩 랜덤 후보에서 제외되는 기존 캐릭터입니다.",
                character_story_title="바람을 타고 온 제주 친구",
                acquire_condition="미션 보상으로 만날 수 있어요.",
                character_img_url="https://example.com/images/characters/wind_spirit.png",
                hashtags=["#제주바람"],
            ),
            ArCharacter(
                id=7,
                character_name="제주 사진작가",
                character_description="제주의 순간을 기록하는 사진작가입니다.",
                character_story_title="이야기 제목",
                acquire_condition="PHOTO 여행 취향으로 만날 수 있어요.",
                character_img_url="https://example.com/images/characters/001.png",
                hashtags=["#인생사진"],
            ),
            ArCharacter(
                id=12,
                character_name="올레길 산책가",
                character_description="제주를 천천히 걷는 산책가입니다.",
                character_story_title="이야기 제목",
                acquire_condition="WALKING 여행 취향으로 만날 수 있어요.",
                character_img_url="https://example.com/images/characters/006.png",
                hashtags=["#걷기여행"],
            ),
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
            ),
        ]
    )
    db_session.commit()


def test_온보딩을_정상_진행하면_선택값과_배정_결과를_저장한다(
    client: TestClient, db_session: Session, onboarding_data: None
) -> None:
    response = client.patch(
        ENDPOINT,
        json={
            "categories": ["PHOTO", "LOCAL", "NATURE", "CAFE"],
            "transportation": ["WALK", "BICYCLE"],
            "travelStyle": ["RIGHT_HERE", "NEAR_DESTINATION"],
        },
    )

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["id"] == CURRENT_USER_ID
    assert set(user["arCharacter"]) == {"id", "name", "imageUrl"}
    assert set(user["userTravelStyle"]) == {"id", "userType", "typeDescription", "hashtags"}

    saved = db_session.get(User, CURRENT_USER_ID)
    assert saved is not None
    db_session.refresh(saved)
    assert saved.expectation == ["PHOTO", "LOCAL", "NATURE", "CAFE"]
    assert saved.transportation == ["WALK", "BICYCLE"]
    assert saved.travel_style == ["RIGHT_HERE", "NEAR_DESTINATION"]
    assert saved.user_travel_style_id == user["userTravelStyle"]["id"]
    assert saved.ar_character_id == user["arCharacter"]["id"]


def test_배정_결과는_DB에_존재하는_값_중_하나다(
    client: TestClient, onboarding_data: None
) -> None:
    response = client.patch(ENDPOINT, json={"categories": ["PHOTO"]})

    user = response.json()["user"]
    assert user["userTravelStyle"]["id"] in {1, 2}
    assert user["arCharacter"]["id"] in ONBOARDING_CHARACTER_IDS


def test_나중에_할게요를_선택해도_온보딩_캐릭터를_랜덤_배정한다(
    client: TestClient, db_session: Session, onboarding_data: None
) -> None:
    response = client.patch(ENDPOINT, json={})

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["userTravelStyle"] is None
    assert user["arCharacter"]["id"] in ONBOARDING_CHARACTER_IDS

    saved = db_session.get(User, CURRENT_USER_ID)
    assert saved is not None
    db_session.refresh(saved)
    assert saved.expectation is None
    assert saved.transportation is None
    assert saved.travel_style is None
    assert saved.user_travel_style_id is None
    assert saved.ar_character_id == user["arCharacter"]["id"]


def test_토큰의_사용자가_없으면_401_UNAUTHORIZED_USER로_응답한다(
    client: TestClient, db_session: Session
) -> None:
    db_session.add_all(
        [
            UserTravelStyle(
                id=1, user_type="기록 탐험가", type_description="설명", hashtags=["#인생사진"]
            ),
            ArCharacter(
                id=ONBOARDING_AR_CHARACTER_IDS[0],
                character_name="제주 사진작가",
                character_description="온보딩 캐릭터입니다.",
                character_story_title="이야기 제목",
                acquire_condition="PHOTO 여행 취향으로 만날 수 있어요.",
                character_img_url="https://example.com/images/characters/001.png",
                hashtags=["#PHOTO"],
            ),
        ]
    )
    db_session.commit()

    # 현재 사용자는 액세스 토큰으로 정하고, 토큰의 사용자가 없으면 온보딩도 막는다.
    response = client.patch(ENDPOINT, json={})

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert db_session.get(User, CURRENT_USER_ID) is None


@pytest.mark.parametrize(
    "body",
    [
        {"categories": ["INVALID"]},
        {"transportation": ["AIRPLANE"]},
        {"travelStyle": ["FAR_AWAY"]},
        {"categories": "PHOTO"},
    ],
)
def test_허용되지_않은_값이면_400_INVALID_REQUEST를_반환한다(
    client: TestClient, onboarding_data: None, body: dict
) -> None:
    response = client.patch(ENDPOINT, json=body)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_배정할_데이터가_없으면_500_INTERNAL_SERVER_ERROR를_반환한다(
    client: TestClient, db_session: Session
) -> None:
    # 사용자는 있고 여행 유형 / AR 캐릭터 마스터만 비어 있는 상황
    db_session.add(
        User(
            id=CURRENT_USER_ID,
            access_token_hash=access_token_hash(CURRENT_USER_ID),
            nickname="몽글몽글파도",
            point=0,
        )
    )
    db_session.commit()

    response = client.patch(ENDPOINT, json={})

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}
