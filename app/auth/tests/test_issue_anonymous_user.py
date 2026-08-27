"""익명 사용자 발급 API 테스트.

API 명세: app/auth/docs/API_SPEC.md
비즈니스 룰: app/auth/docs/BUSINESS_RULES.md
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.service import ANONYMOUS_NICKNAMES, MAX_TOKEN_ATTEMPTS
from app.core.security import hash_access_token
from app.user.models import User, UserSetting


ENDPOINT = "/api/v1/auth/anonymous"

# 현재 사용자가 필요한 API 중 준비할 데이터가 가장 적은 것을 쓴다. (발급 토큰 실제 사용 확인용)
HOME_ENDPOINT = "/api/v1/users/me/home"
HOME_PARAMS = {"latitude": 33.4996, "longitude": 126.5312}


@pytest.fixture
def no_auth_client(client: TestClient) -> TestClient:
    """인증 헤더가 없는 클라이언트. (아직 토큰이 없는 상태에서 호출하는 API라서)"""
    client.headers.pop("Authorization", None)
    return client


def _users(db_session: Session) -> list[User]:
    return list(db_session.scalars(select(User)))


def test_익명_사용자를_발급하면_201과_토큰을_반환한다(no_auth_client: TestClient) -> None:
    response = no_auth_client.post(ENDPOINT)

    assert response.status_code == 201
    body = response.json()
    assert body.keys() == {"accessToken", "tokenType"}
    assert body["tokenType"] == "Bearer"
    assert isinstance(body["accessToken"], str)
    assert body["accessToken"] != ""


def test_사용자와_사용자_설정을_함께_만든다(
    no_auth_client: TestClient, db_session: Session
) -> None:
    response = no_auth_client.post(ENDPOINT)

    assert response.status_code == 201
    users = _users(db_session)
    assert len(users) == 1
    created = users[0]

    # 온보딩 정보와 캐릭터는 아직 정하지 않는다.
    assert created.expectation is None
    assert created.transportation is None
    assert created.travel_style is None
    assert created.user_travel_style_id is None
    assert created.ar_character_id is None
    assert created.point == 0
    assert created.nickname in ANONYMOUS_NICKNAMES

    setting = db_session.scalar(select(UserSetting).where(UserSetting.user_id == created.id))
    assert setting is not None
    assert setting.push_notification is True
    assert setting.near_mission_notification is True


def test_DB에는_토큰_원문이_아니라_해시를_저장한다(
    no_auth_client: TestClient, db_session: Session
) -> None:
    access_token = no_auth_client.post(ENDPOINT).json()["accessToken"]

    created = _users(db_session)[0]
    assert created.access_token_hash != access_token
    assert created.access_token_hash == hash_access_token(access_token)
    assert len(created.access_token_hash) == 64


def test_발급받은_토큰으로_다른_API를_호출할_수_있다(no_auth_client: TestClient) -> None:
    access_token = no_auth_client.post(ENDPOINT).json()["accessToken"]

    response = no_auth_client.get(
        HOME_ENDPOINT,
        params=HOME_PARAMS,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200


def test_호출할_때마다_새로운_사용자와_토큰을_발급한다(
    no_auth_client: TestClient, db_session: Session
) -> None:
    first = no_auth_client.post(ENDPOINT).json()["accessToken"]
    second = no_auth_client.post(ENDPOINT).json()["accessToken"]

    assert first != second
    users = _users(db_session)
    assert len(users) == 2
    assert users[0].id != users[1].id
    assert users[0].access_token_hash != users[1].access_token_hash


def test_토큰이_충돌하면_새_토큰으로_다시_시도한다(
    no_auth_client: TestClient, db_session: Session
) -> None:
    duplicated = "duplicated-token"
    tokens = iter([duplicated, duplicated, "unique-token"])

    with patch("app.auth.service.generate_access_token", side_effect=lambda: next(tokens)):
        first = no_auth_client.post(ENDPOINT)
        second = no_auth_client.post(ENDPOINT)

    assert first.json()["accessToken"] == duplicated
    # 충돌한 토큰은 응답하지 않고 새로 만든 토큰을 내려준다.
    assert second.status_code == 201
    assert second.json()["accessToken"] == "unique-token"

    users = _users(db_session)
    assert len(users) == 2
    assert {user.access_token_hash for user in users} == {
        hash_access_token(duplicated),
        hash_access_token("unique-token"),
    }


def test_토큰_충돌이_계속되면_500으로_응답하고_사용자를_만들지_않는다(
    no_auth_client: TestClient, db_session: Session
) -> None:
    def always_same() -> str:
        return "always-same-token"

    with patch("app.auth.service.generate_access_token", side_effect=always_same):
        first = no_auth_client.post(ENDPOINT)
        second = no_auth_client.post(ENDPOINT)

    assert first.status_code == 201
    assert second.status_code == 500
    assert second.json() == {"code": "INTERNAL_SERVER_ERROR"}
    # 재시도 횟수를 넘겨도 절반만 저장되는 일은 없어야 한다.
    assert len(_users(db_session)) == 1


def test_재시도_횟수만큼만_시도한다(no_auth_client: TestClient) -> None:
    calls: list[str] = []

    def always_same() -> str:
        calls.append("always-same-token")
        return "always-same-token"

    with patch("app.auth.service.generate_access_token", side_effect=always_same):
        no_auth_client.post(ENDPOINT)
        calls.clear()
        no_auth_client.post(ENDPOINT)

    assert len(calls) == MAX_TOKEN_ATTEMPTS


def test_사용자_저장에_실패하면_사용자_설정도_남지_않는다(
    no_auth_client: TestClient, db_session: Session
) -> None:
    with patch("app.auth.service.UserSetting", side_effect=RuntimeError("설정 저장 실패")):
        response = no_auth_client.post(ENDPOINT)

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}
    assert _users(db_session) == []
    assert list(db_session.scalars(select(UserSetting))) == []


def test_인증_헤더_없이도_호출할_수_있다(no_auth_client: TestClient) -> None:
    assert "Authorization" not in no_auth_client.headers

    response = no_auth_client.post(ENDPOINT)

    assert response.status_code == 201


def test_문서에_401을_넣지_않는다(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"][ENDPOINT]["post"]["responses"]

    # 토큰이 없는 상태에서 호출하는 API라 인증 관련 에러가 없다.
    assert "401" not in responses
    assert "500" in responses
