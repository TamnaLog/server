"""OpenAPI(Swagger) 공통 에러 응답 문서 테스트.

CLAUDE.md의 공통 에러 정책대로 Swagger 문서에도
FastAPI 기본 422 대신 400 `INVALID_REQUEST` / 500 `INTERNAL_SERVER_ERROR` 가 보여야 한다.
"""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.errors import INTERNAL_SERVER_ERROR, INVALID_REQUEST


# 요청 값(query/body)이 있어서 400이 날 수 있는 API
REQUEST_VALUE_ENDPOINTS = [
    pytest.param("/api/v1/users/me/home", "get", id="홈_조회"),
    pytest.param("/api/v1/users/me", "patch", id="사용자_온보딩_정보_저장"),
]


@pytest.fixture
def openapi_schema(client: TestClient) -> dict[str, Any]:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_어떤_API에도_기본_422_응답이_문서에_남아_있지_않다(
    openapi_schema: dict[str, Any],
) -> None:
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            assert "422" not in operation["responses"], f"{method.upper()} {path}"


def test_사용하지_않는_기본_검증_에러_스키마가_문서에_남아_있지_않다(
    openapi_schema: dict[str, Any],
) -> None:
    schemas = openapi_schema["components"]["schemas"]

    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas
    # 공통 에러 응답 스키마는 반대로 문서에 있어야 한다.
    assert schemas["ErrorResponse"]["properties"].keys() == {"code"}


@pytest.mark.parametrize(("path", "method"), REQUEST_VALUE_ENDPOINTS)
def test_요청_값이_있는_API는_400_INVALID_REQUEST를_문서에_노출한다(
    openapi_schema: dict[str, Any], path: str, method: str
) -> None:
    response_doc = openapi_schema["paths"][path][method]["responses"]["400"]

    content = response_doc["content"]["application/json"]
    assert content["schema"]["$ref"] == "#/components/schemas/ErrorResponse"
    assert content["example"] == {"code": INVALID_REQUEST}


@pytest.mark.parametrize(("path", "method"), REQUEST_VALUE_ENDPOINTS)
def test_모든_API는_500_INTERNAL_SERVER_ERROR를_문서에_노출한다(
    openapi_schema: dict[str, Any], path: str, method: str
) -> None:
    response_doc = openapi_schema["paths"][path][method]["responses"]["500"]

    content = response_doc["content"]["application/json"]
    assert content["schema"]["$ref"] == "#/components/schemas/ErrorResponse"
    assert content["example"] == {"code": INTERNAL_SERVER_ERROR}


def test_요청_값이_없는_API에는_400을_넣지_않는다(openapi_schema: dict[str, Any]) -> None:
    # /health 는 query/path/body 가 없어서 400이 날 수 없다.
    responses = openapi_schema["paths"]["/health"]["get"]["responses"]

    assert "400" not in responses
    assert "500" in responses


def test_문서에_남은_참조는_모두_실제_스키마를_가리킨다(
    openapi_schema: dict[str, Any],
) -> None:
    # 422 제거 과정에서 참조만 남고 스키마가 사라지는 일이 없는지 확인한다.
    defined = set(openapi_schema["components"]["schemas"])
    referenced = {
        ref.split("/")[-1]
        for ref in json.dumps(openapi_schema).split('"$ref": "')[1:]
        for ref in [ref.split('"')[0]]
    }

    assert referenced <= defined, f"정의되지 않은 스키마 참조: {referenced - defined}"
