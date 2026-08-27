"""현재 사용자 식별(`Authorization: Bearer`) 처리 테스트.

특정 도메인이 아니라 현재 사용자가 필요한 모든 API에 공통으로 걸리는 규칙이라
core 에서 검증한다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.errors import OPENAPI_SECURITY_SCHEME_NAME
from app.guestbook.models import Guestbook, RoadGuestbook  # noqa: F401  (테이블 등록)
from app.treasure_mission.models import ArCharacter
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token, access_token_hash, auth_headers


# 현재 사용자가 필요한 API 중 준비할 데이터가 가장 적은 것을 쓴다.
ENDPOINT = "/api/v1/users/me/home"
PARAMS = {"latitude": 33.4996, "longitude": 126.5312}

OTHER_USER_ID = 2
UNKNOWN_USER_ID = 999
CURRENT_USER_IMG_URL = "https://example.com/characters/one.png"
OTHER_USER_IMG_URL = "https://example.com/characters/two.png"


@pytest.fixture
def users(db_session: Session) -> None:
    """서로 다른 캐릭터를 가진 사용자 두 명. (응답으로 누구인지 구분하려고)"""
    db_session.add_all(
        [
            ArCharacter(
                id=1,
                character_name="캐릭터1",
                character_description="설명",
                acquire_condition="조건",
                character_img_url=CURRENT_USER_IMG_URL,
                hashtags=["#1"],
            ),
            ArCharacter(
                id=2,
                character_name="캐릭터2",
                character_description="설명",
                acquire_condition="조건",
                character_img_url=OTHER_USER_IMG_URL,
                hashtags=["#2"],
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
                ar_character_id=1,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
                ar_character_id=2,
            ),
        ]
    )
    db_session.commit()


def test_토큰의_주인을_현재_사용자로_사용한다(client: TestClient, users: None) -> None:
    response = client.get(ENDPOINT, params=PARAMS, headers=auth_headers(OTHER_USER_ID))

    assert response.status_code == 200
    # 기본 토큰(사용자 1)이 아니라 요청에 넣은 사용자 2의 데이터가 나와야 한다.
    assert response.json()["characterImgUrl"] == OTHER_USER_IMG_URL


def test_토큰을_바꾸면_현재_사용자도_바뀐다(client: TestClient, users: None) -> None:
    first = client.get(ENDPOINT, params=PARAMS, headers=auth_headers(CURRENT_USER_ID))
    second = client.get(ENDPOINT, params=PARAMS, headers=auth_headers(OTHER_USER_ID))

    assert first.json()["characterImgUrl"] == CURRENT_USER_IMG_URL
    assert second.json()["characterImgUrl"] == OTHER_USER_IMG_URL


def test_어떤_사용자의_토큰도_아니면_401_UNAUTHORIZED_USER로_응답한다(
    client: TestClient, users: None
) -> None:
    response = client.get(ENDPOINT, params=PARAMS, headers=auth_headers(UNKNOWN_USER_ID))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_인증_헤더가_없으면_401_UNAUTHORIZED_USER로_응답한다(
    client: TestClient, users: None
) -> None:
    # TestClient 기본 헤더를 지워서 헤더 없는 요청을 만든다.
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT, params=PARAMS)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


@pytest.mark.parametrize(
    "header_value",
    [
        pytest.param(access_token(CURRENT_USER_ID), id="토큰만_보냄"),
        pytest.param(f"Basic {access_token(CURRENT_USER_ID)}", id="Bearer가_아닌_방식"),
        pytest.param("Bearer", id="토큰_없음"),
        pytest.param("Bearer ", id="빈_토큰"),
    ],
)
def test_인증_헤더_형식이_잘못되면_401_UNAUTHORIZED_USER로_응답한다(
    client: TestClient, users: None, header_value: str
) -> None:
    response = client.get(ENDPOINT, params=PARAMS, headers={"Authorization": header_value})

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_현재_사용자가_필요한_API는_401을_문서에_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    operation = schema["paths"][ENDPOINT]["get"]
    # Bearer 인증을 쓰는 API 로 문서에 표시되어야 한다.
    assert any(
        OPENAPI_SECURITY_SCHEME_NAME in requirement for requirement in operation["security"]
    )

    response_doc = operation["responses"]["401"]
    content = response_doc["content"]["application/json"]
    assert content["example"] == {"code": "UNAUTHORIZED_USER"}


def test_현재_사용자가_필요없는_API에는_401을_넣지_않는다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/health"]["get"]["responses"]

    assert "401" not in responses
