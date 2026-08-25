"""공통 에러 코드 / 에러 응답 처리.

- 에러 응답 본문은 `code` 하나만 내려준다.
- 400 에러는 `INVALID_REQUEST` 코드 하나로 통일한다.
- 500 에러는 `INTERNAL_SERVER_ERROR` 코드 하나로 통일한다.
- 그 외 상태 코드(404 등)는 각 API 명세의 `code`를 `AppError`로 발생시킨다.
- `message`는 응답에 포함하지 않고 예외 메시지(서버 로그)로만 사용한다.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


INVALID_REQUEST = "INVALID_REQUEST"
INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


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


class NotFoundError(AppError):
    """404 - 각 API 명세에 정의된 코드를 사용한다."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, code, detail)


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
