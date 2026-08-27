"""업로드 이미지 형식 판별.

파일명 확장자나 multipart 의 Content-Type 은 클라이언트가 마음대로 보낼 수 있으므로 믿지 않고,
**파일 내용의 시그니처(매직 넘버)** 로 실제 형식을 판별한다.
저장 확장자와 Content-Type 도 판별된 실제 형식을 기준으로 정한다.

방명록 사진 등 다른 도메인에서도 같은 규칙이 필요하므로 공용 모듈에 둔다.
(app/treasure_mission/docs/BUSINESS_RULES.md - 2. 허용 이미지 형식)

허용 형식은 JPEG / PNG / WebP 뿐이다. GIF, BMP, TIFF, SVG, HEIC/HEIF 등은 허용하지 않는다.
`.jpeg` 로 전달된 JPEG 도 저장 확장자는 `.jpg` 로 통일한다.

업로드 파일을 읽는 규칙(최대 10MB, 빈 파일 금지)도 도메인마다 같으므로 여기서 함께 관리한다.
"""

from enum import Enum
from typing import BinaryIO

from app.core.errors import InvalidRequestError


class ImageFormat(str, Enum):
    """허용하는 이미지 형식."""

    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WEBP"

    @property
    def extension(self) -> str:
        """저장에 사용할 확장자. (`.jpeg` 가 아니라 `.jpg` 로 통일)"""
        return _EXTENSIONS[self]

    @property
    def content_type(self) -> str:
        """저장에 사용할 Content-Type."""
        return _CONTENT_TYPES[self]


_EXTENSIONS = {
    ImageFormat.JPEG: ".jpg",
    ImageFormat.PNG: ".png",
    ImageFormat.WEBP: ".webp",
}

_CONTENT_TYPES = {
    ImageFormat.JPEG: "image/jpeg",
    ImageFormat.PNG: "image/png",
    ImageFormat.WEBP: "image/webp",
}

# 파일 시작 부분의 형식 시그니처
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# WebP 는 RIFF 컨테이너라 4~8 바이트가 파일 크기이고 그 뒤에 WEBP 가 온다.
_RIFF_SIGNATURE = b"RIFF"
_WEBP_SIGNATURE = b"WEBP"
_WEBP_HEADER_SIZE = 12


def detect_image_format(data: bytes) -> ImageFormat | None:
    """파일 내용으로 이미지 형식을 판별한다. 허용 형식이 아니면 `None`."""
    if data.startswith(_JPEG_SIGNATURE):
        return ImageFormat.JPEG

    if data.startswith(_PNG_SIGNATURE):
        return ImageFormat.PNG

    if (
        len(data) >= _WEBP_HEADER_SIZE
        and data.startswith(_RIFF_SIGNATURE)
        and data[8:12] == _WEBP_SIGNATURE
    ):
        return ImageFormat.WEBP

    return None


# 업로드 이미지 최대 크기
MAX_IMAGE_SIZE_BYTE = 10 * 1024 * 1024

# 크기 제한을 넘는 파일을 통째로 메모리에 올리지 않도록 나눠 읽는 단위
IMAGE_CHUNK_SIZE_BYTE = 1024 * 1024


def read_image(image: BinaryIO) -> bytes:
    """업로드 이미지를 크기 제한을 지키며 읽는다.

    전체를 한 번에 메모리로 읽지 않고 나눠 읽다가 최대 크기를 넘으면 즉시 중단한다.
    비어 있거나 최대 크기를 넘으면 400 으로 처리한다.
    """
    chunks: list[bytes] = []
    size = 0

    while chunk := image.read(IMAGE_CHUNK_SIZE_BYTE):
        size += len(chunk)
        if size > MAX_IMAGE_SIZE_BYTE:
            raise InvalidRequestError(
                f"이미지 파일이 최대 크기({MAX_IMAGE_SIZE_BYTE} bytes)를 초과했습니다."
            )
        chunks.append(chunk)

    if size == 0:
        raise InvalidRequestError("이미지 파일이 비어 있습니다.")

    return b"".join(chunks)


def read_and_detect(image: BinaryIO) -> tuple[bytes, ImageFormat]:
    """업로드 이미지를 읽고 실제 형식까지 판별한다. 허용 형식이 아니면 400."""
    data = read_image(image)
    image_format = detect_image_format(data)
    if image_format is None:
        raise InvalidRequestError(
            "허용하지 않는 이미지 형식입니다. (JPEG / PNG / WebP 만 허용)"
        )
    return data, image_format
