"""업로드 이미지 형식 판별.

파일명 확장자나 multipart 의 Content-Type 은 클라이언트가 마음대로 보낼 수 있으므로 믿지 않고,
**파일 내용의 시그니처(매직 넘버)** 로 실제 형식을 판별한다.
저장 확장자와 Content-Type 도 판별된 실제 형식을 기준으로 정한다.

방명록 사진 등 다른 도메인에서도 같은 규칙이 필요하므로 공용 모듈에 둔다.
(app/treasure_mission/docs/BUSINESS_RULES.md - 2. 허용 이미지 형식)

허용 형식은 JPEG / PNG / WebP 뿐이다. GIF, BMP, TIFF, SVG, HEIC/HEIF 등은 허용하지 않는다.
`.jpeg` 로 전달된 JPEG 도 저장 확장자는 `.jpg` 로 통일한다.
"""

from enum import Enum


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
