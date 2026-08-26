"""현재 사용자 헤더(`X-Test-User-Id`) 처리 테스트.

로그인 기능 전까지 현재 사용자는 요청 헤더로 정한다.
특정 도메인이 아니라 모든 API에 공통으로 걸리는 규칙이라 core 에서 검증한다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import CURRENT_USER_ID
from app.core.errors import TEST_USER_ID_HEADER
from app.guestbook.models import Guestbook, RoadGuestbook  # noqa: F401  (테이블 등록)
from app.treasure_mission.models import ArCharacter
from app.user.models import User


# 현재 사용자가 필요한 API 중 준비할 데이터가 가장 적은 것을 쓴다.
ENDPOINT = "/api/v1/users/me/home"
PARAMS = {"latitude": 33.4996, "longitude": 126.5312}

OTHER_USER_ID = 2
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
            User(id=CURRENT_USER_ID, nickname="몽글몽글파도", point=0, ar_character_id=1),
            User(id=OTHER_USER_ID, nickname="한라봉주스", point=0, ar_character_id=2),
        ]
    )
    db_session.commit()


def test_헤더로_보낸_사용자를_현재_사용자로_사용한다(
    client: TestClient, users: None
) -> None:
    response = client.get(
        ENDPOINT, params=PARAMS, headers={TEST_USER_ID_HEADER: str(OTHER_USER_ID)}
    )

    assert response.status_code == 200
    # 기본 헤더(사용자 1)가 아니라 요청에 넣은 사용자 2의 데이터가 나와야 한다.
    assert response.json()["characterImgUrl"] == OTHER_USER_IMG_URL


def test_헤더를_바꾸면_현재_사용자도_바뀐다(client: TestClient, users: None) -> None:
    first = client.get(
        ENDPOINT, params=PARAMS, headers={TEST_USER_ID_HEADER: str(CURRENT_USER_ID)}
    )
    second = client.get(
        ENDPOINT, params=PARAMS, headers={TEST_USER_ID_HEADER: str(OTHER_USER_ID)}
    )

    assert first.json()["characterImgUrl"] == CURRENT_USER_IMG_URL
    assert second.json()["characterImgUrl"] == OTHER_USER_IMG_URL


def test_존재하지_않는_사용자면_401_UNAUTHORIZED_USER로_응답한다(
    client: TestClient, users: None
) -> None:
    response = client.get(ENDPOINT, params=PARAMS, headers={TEST_USER_ID_HEADER: "999"})

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_헤더가_없으면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, users: None
) -> None:
    # TestClient 기본 헤더를 지워서 헤더 없는 요청을 만든다.
    client.headers.pop(TEST_USER_ID_HEADER, None)

    response = client.get(ENDPOINT, params=PARAMS)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


@pytest.mark.parametrize(
    "header_value",
    [
        pytest.param("abc", id="정수가_아님"),
        pytest.param("0", id="0"),
        pytest.param("-1", id="음수"),
    ],
)
def test_헤더_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, users: None, header_value: str
) -> None:
    response = client.get(ENDPOINT, params=PARAMS, headers={TEST_USER_ID_HEADER: header_value})

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}


def test_현재_사용자가_필요한_API는_401을_문서에_노출한다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    operation = schema["paths"][ENDPOINT]["get"]
    header_names = [parameter["name"] for parameter in operation["parameters"]]
    assert TEST_USER_ID_HEADER in header_names

    response_doc = operation["responses"]["401"]
    content = response_doc["content"]["application/json"]
    assert content["example"] == {"code": "UNAUTHORIZED_USER"}


def test_현재_사용자가_필요없는_API에는_401을_넣지_않는다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/health"]["get"]["responses"]

    assert "401" not in responses
