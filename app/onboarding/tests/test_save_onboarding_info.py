"""PATCH /api/v1/users/me - 사용자 온보딩 정보 저장 테스트.

기준 문서: app/onboarding/docs/API_SPEC.md, app/onboarding/docs/BUSINESS_RULES.md
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import CURRENT_USER_ID
from app.onboarding.models import ArCharacter, User, UserTravelStyle
from app.onboarding.onboarding_matcher import DEFAULT_AR_CHARACTER_NAME


ENDPOINT = "/api/v1/users/me"

DEFAULT_CHARACTER_ID = 11


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
                character_name="자청비 모티브 탐험가",
                character_description="기록 탐험가 캐릭터입니다.",
                acquire_condition="온보딩에서 기록형 여행 스타일을 선택하면 만날 수 있어요.",
                character_img_url="https://example.com/images/characters/jacheongbi.png",
                hashtags=["#인생사진"],
            ),
            ArCharacter(
                id=DEFAULT_CHARACTER_ID,
                character_name=DEFAULT_AR_CHARACTER_NAME,
                character_description="기본 캐릭터입니다.",
                acquire_condition="온보딩에서 나중에 할게요를 선택하면 만날 수 있어요.",
                character_img_url="https://example.com/images/characters/dolmungii.png",
                hashtags=["#기본캐릭터"],
            ),
            User(id=CURRENT_USER_ID, nickname="몽글몽글파도", point=0),
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
    assert user["arCharacter"]["id"] in {1, DEFAULT_CHARACTER_ID}


def test_나중에_할게요를_선택하면_여행_유형은_null이고_기본_캐릭터를_반환한다(
    client: TestClient, db_session: Session, onboarding_data: None
) -> None:
    response = client.patch(ENDPOINT, json={})

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["userTravelStyle"] is None
    assert user["arCharacter"]["id"] == DEFAULT_CHARACTER_ID
    assert user["arCharacter"]["name"] == DEFAULT_AR_CHARACTER_NAME

    saved = db_session.get(User, CURRENT_USER_ID)
    assert saved is not None
    db_session.refresh(saved)
    assert saved.expectation is None
    assert saved.transportation is None
    assert saved.travel_style is None
    assert saved.user_travel_style_id is None
    assert saved.ar_character_id == DEFAULT_CHARACTER_ID


def test_사용자가_없으면_생성한다(client: TestClient, db_session: Session) -> None:
    db_session.add_all(
        [
            UserTravelStyle(
                id=1, user_type="기록 탐험가", type_description="설명", hashtags=["#인생사진"]
            ),
            ArCharacter(
                id=DEFAULT_CHARACTER_ID,
                character_name=DEFAULT_AR_CHARACTER_NAME,
                character_description="기본 캐릭터입니다.",
                acquire_condition="온보딩에서 나중에 할게요를 선택하면 만날 수 있어요.",
                character_img_url="https://example.com/images/characters/dolmungii.png",
                hashtags=["#기본캐릭터"],
            ),
        ]
    )
    db_session.commit()

    response = client.patch(ENDPOINT, json={})

    assert response.status_code == 201
    assert db_session.get(User, CURRENT_USER_ID) is not None


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
    client: TestClient,
) -> None:
    response = client.patch(ENDPOINT, json={})

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}
