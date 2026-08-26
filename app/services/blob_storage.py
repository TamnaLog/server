"""Azure Blob Storage 업로드 클라이언트.

방명록 사진/음성, AR 캐릭터 사진처럼 사용자가 올린 파일은 DB에 URL만 저장하고
실제 파일은 Blob Storage 에 둔다. 업로드 결과로 받은 URL 을 응답과 DB에 사용한다.

연결 문자열(`AZURE_STORAGE_CONNECTION_STRING`)은 계정 키를 포함하므로 절대 코드에 적지 않고
환경변수로만 주입한다. (로컬 `.env`, 배포는 App Service 환경변수)

- 컨테이너는 하나만 쓰고 용도는 blob 이름 앞의 prefix(`guestbook/`, `ar-character/`)로 나눈다.
- 컨테이너는 첫 업로드 시 없으면 blob 공개 읽기로 만든다.
  (업로드 URL 을 그대로 응답에 담아 프론트가 바로 열 수 있어야 한다)
- blob 이름은 `{prefix}/{uuid}{확장자}` 로 만들어 파일명이 겹치지 않게 한다.
- 연결 문자열이 없으면 업로드 시점에 예외를 발생시킨다. (공통 처리기가 500 으로 응답)
"""

from functools import lru_cache
from mimetypes import guess_extension
from pathlib import PurePosixPath
from uuid import uuid4

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
    ContentSettings,
    PublicAccess,
)

from app.core.config import get_settings


DEFAULT_CONTENT_TYPE = "application/octet-stream"

# 컨테이너가 이미 있을 때의 에러 코드. (같은 409 로 오는 다른 에러와 구분한다)
CONTAINER_ALREADY_EXISTS = "ContainerAlreadyExists"


@lru_cache
def get_container_client() -> ContainerClient:
    """업로드에 사용할 컨테이너 클라이언트를 반환한다. (프로세스당 한 번만 생성)"""
    settings = get_settings()
    if not settings.azure_storage_enabled:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not configured.")

    service_client = BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    )
    container_client = service_client.get_container_client(settings.azure_storage_container)
    try:
        # public_access="blob": blob URL 로는 읽을 수 있지만 목록 조회는 막는다.
        container_client.create_container(public_access=PublicAccess.BLOB)
    except ResourceExistsError as error:
        # 스토리지 계정에서 익명 접근을 막아 두면 같은 409 로 PublicAccessNotPermitted 가 온다.
        # 이미 있는 경우가 아니면 삼키지 않고 그대로 올린다.
        if error.error_code != CONTAINER_ALREADY_EXISTS:
            raise
    return container_client


def upload_file(
    data: bytes,
    *,
    prefix: str,
    filename: str | None = None,
    content_type: str | None = None,
) -> str:
    """파일을 업로드하고 접근 URL 을 반환한다.

    - `prefix`: blob 을 구분하는 폴더 이름. (예: `guestbook`, `ar-character`)
    - `filename`: 원본 파일명. 확장자를 정하는 데만 쓰고 blob 이름으로는 쓰지 않는다.
    - `content_type`: 없으면 `application/octet-stream` 으로 올린다.
    """
    blob_name = _build_blob_name(prefix, filename, content_type)
    blob_client = get_container_client().get_blob_client(blob_name)
    blob_client.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type or DEFAULT_CONTENT_TYPE),
    )
    return blob_client.url


def _build_blob_name(prefix: str, filename: str | None, content_type: str | None) -> str:
    """`{prefix}/{uuid}{확장자}` 형태의 blob 이름을 만든다."""
    return f"{prefix.strip('/')}/{uuid4().hex}{_extension(filename, content_type)}"


def _extension(filename: str | None, content_type: str | None) -> str:
    """원본 파일명 → content type 순서로 확장자를 정한다. 둘 다 없으면 확장자를 붙이지 않는다."""
    if filename:
        suffix = PurePosixPath(filename).suffix
        if suffix:
            return suffix.lower()

    if content_type:
        return guess_extension(content_type) or ""

    return ""
