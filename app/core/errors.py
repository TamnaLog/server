"""공통 에러 코드 / 에러 응답 처리.

- 에러 응답 본문은 `code` 하나만 내려준다.
- 400 에러는 `INVALID_REQUEST` 코드 하나로 통일한다.
- 500 에러는 `INTERNAL_SERVER_ERROR` 코드 하나로 통일한다.
- 그 외 상태 코드(404 등)는 각 API 명세의 `code`를 `AppError`로 발생시킨다.
- `message`는 응답에 포함하지 않고 예외 메시지(서버 로그)로만 사용한다.
- OpenAPI(Swagger) 문서의 에러 응답도 `use_common_error_responses()`로 같은 형식에 맞춘다.
"""

import json
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


INVALID_REQUEST = "INVALID_REQUEST"
INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
UNAUTHORIZED_USER = "UNAUTHORIZED_USER"

# 현재 사용자 인증에 쓰는 OpenAPI 보안 스키마 이름.
# app/core/deps.py 가 이 이름으로 Bearer 스키마를 만들고,
# 아래 문서 처리에서 401 을 붙일 API 를 고르는 기준으로도 쓴다.
OPENAPI_SECURITY_SCHEME_NAME = "AccessToken"


class ErrorResponse(BaseModel):
    """모든 에러 응답의 공통 형식."""

    code: str


class AppError(Exception):
    """API 명세에 정의된 에러를 발생시킬 때 사용하는 예외.

    `detail`은 응답에 포함되지 않고 서버 로그 확인용으로만 쓴다.
    """

    def __init__(self, status_code: int, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.status_code = status_code
        self.code = code


class InvalidRequestError(AppError):
    """400 - 잘못된 요청."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(status.HTTP_400_BAD_REQUEST, INVALID_REQUEST, detail)


class UnauthorizedError(AppError):
    """401 - 현재 사용자를 확인할 수 없다."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, code, detail)


class NotFoundError(AppError):
    """404 - 각 API 명세에 정의된 코드를 사용한다."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, code, detail)


class ConflictError(AppError):
    """409 - 각 API 명세에 정의된 코드를 사용한다."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(status.HTTP_409_CONFLICT, code, detail)


def _error_response(status_code: int, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """앱에 공통 에러 핸들러를 등록한다."""

    @app.exception_handler(AppError)
    def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code)

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI 기본값은 422지만, 명세에 맞춰 400 INVALID_REQUEST 로 통일한다.
        return _error_response(status.HTTP_400_BAD_REQUEST, INVALID_REQUEST)

    @app.exception_handler(StarletteHTTPException)
    def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            return _error_response(exc.status_code, INTERNAL_SERVER_ERROR)
        return _error_response(exc.status_code, INVALID_REQUEST)

    @app.exception_handler(Exception)
    def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_SERVER_ERROR)


# ---------------------------------------------------------------------
# OpenAPI(Swagger) 문서
# ---------------------------------------------------------------------

_ERROR_SCHEMA_NAME = "ErrorResponse"
_ERROR_SCHEMA_REF = f"#/components/schemas/{_ERROR_SCHEMA_NAME}"

# FastAPI가 기본으로 넣는 검증 에러 스키마. 422를 없애면 참조하는 곳이 사라진다.
_VALIDATION_SCHEMA_NAMES = ("HTTPValidationError", "ValidationError")


def _error_response_doc(description: str, code: str) -> dict[str, Any]:
    """OpenAPI 에러 응답 문서 한 건을 만든다."""
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": _ERROR_SCHEMA_REF},
                "example": {"code": code},
            }
        },
    }


def _uses_current_user(operation: dict[str, Any]) -> bool:
    """액세스 토큰으로 현재 사용자를 확인하는 API 인지 본다. (401 문서를 붙일 대상)"""
    return any(
        OPENAPI_SECURITY_SCHEME_NAME in requirement
        for requirement in operation.get("security", [])
    )


def _drop_unused_validation_schemas(schema: dict[str, Any]) -> None:
    """더 이상 참조되지 않는 FastAPI 기본 검증 에러 스키마를 제거한다."""
    schemas = schema.get("components", {}).get("schemas", {})
    for name in _VALIDATION_SCHEMA_NAMES:
        remaining = {
            "paths": schema.get("paths", {}),
            "schemas": {key: value for key, value in schemas.items() if key != name},
        }
        if f"#/components/schemas/{name}" not in json.dumps(remaining):
            schemas.pop(name, None)


def use_common_error_responses(app: FastAPI) -> None:
    """OpenAPI 문서의 에러 응답을 공통 형식으로 맞춘다.

    - FastAPI 기본 422 응답은 공통 핸들러가 400 `INVALID_REQUEST`로 변환하므로 문서에서 제거한다.
    - 요청 값(query/path/body)이 있는 API에는 400을, 모든 API에는 500을 문서에 추가한다.
    - 각 라우터가 `responses`로 직접 정의한 에러(404 등)는 그대로 둔다.
    """

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema.setdefault("components", {}).setdefault("schemas", {})[_ERROR_SCHEMA_NAME] = (
            ErrorResponse.model_json_schema()
        )

        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                responses = operation.get("responses")
                if responses is None:
                    continue

                responses.pop(str(status.HTTP_422_UNPROCESSABLE_ENTITY), None)
                if operation.get("parameters") or operation.get("requestBody"):
                    responses.setdefault(
                        str(status.HTTP_400_BAD_REQUEST),
                        _error_response_doc("잘못된 요청", INVALID_REQUEST),
                    )
                if _uses_current_user(operation):
                    responses.setdefault(
                        str(status.HTTP_401_UNAUTHORIZED),
                        _error_response_doc("현재 사용자를 확인할 수 없음", UNAUTHORIZED_USER),
                    )
                responses.setdefault(
                    str(status.HTTP_500_INTERNAL_SERVER_ERROR),
                    _error_response_doc("서버 오류", INTERNAL_SERVER_ERROR),
                )

        _drop_unused_validation_schemas(schema)

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
