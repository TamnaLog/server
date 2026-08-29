"""업로드 오디오 형식 판별.

이미지(app/common/images.py)와 같은 이유로 파일명 확장자나 multipart 의 Content-Type 은 믿지 않고,
**파일 내용의 시그니처/컨테이너 헤더**로 실제 형식을 판별한다.
저장 확장자와 Content-Type 도 판별된 실제 형식을 기준으로 정한다.
(app/guestbook/docs/BUSINESS_RULES.md - B.9 오디오 검증과 저장)

허용 형식은 MP3 / M4A / AAC / WAV / OGG / WebM 이고 파일당 최대 30MB 다.
"""

from enum import Enum
from typing import BinaryIO

from app.core.errors import InvalidRequestError


# 업로드 오디오 최대 크기 (이미지보다 크다)
MAX_AUDIO_SIZE_BYTE = 30 * 1024 * 1024

# 크기 제한을 넘는 파일을 통째로 메모리에 올리지 않도록 나눠 읽는 단위
AUDIO_CHUNK_SIZE_BYTE = 1024 * 1024


class AudioFormat(str, Enum):
    """허용하는 오디오 형식."""

    MP3 = "MP3"
    M4A = "M4A"
    AAC = "AAC"
    WAV = "WAV"
    OGG = "OGG"
    WEBM = "WEBM"

    @property
    def extension(self) -> str:
        """저장에 사용할 확장자."""
        return _EXTENSIONS[self]

    @property
    def content_type(self) -> str:
        """저장에 사용할 Content-Type."""
        return _CONTENT_TYPES[self]


_EXTENSIONS = {
    AudioFormat.MP3: ".mp3",
    AudioFormat.M4A: ".m4a",
    AudioFormat.AAC: ".aac",
    AudioFormat.WAV: ".wav",
    AudioFormat.OGG: ".ogg",
    AudioFormat.WEBM: ".webm",
}

_CONTENT_TYPES = {
    AudioFormat.MP3: "audio/mpeg",
    AudioFormat.M4A: "audio/mp4",
    AudioFormat.AAC: "audio/aac",
    AudioFormat.WAV: "audio/wav",
    AudioFormat.OGG: "audio/ogg",
    AudioFormat.WEBM: "audio/webm",
}

# RIFF(WAV) / OggS / EBML(WebM) 컨테이너 시그니처
_RIFF_SIGNATURE = b"RIFF"
_WAVE_SIGNATURE = b"WAVE"
_WAV_HEADER_SIZE = 12
_OGG_SIGNATURE = b"OggS"
_EBML_SIGNATURE = b"\x1a\x45\xdf\xa3"

# MP4 계열(M4A/AAC in MP4)은 4~8 바이트가 'ftyp' 이고 그 뒤 4바이트가 브랜드다.
_FTYP_SIGNATURE = b"ftyp"
_FTYP_HEADER_SIZE = 12
_M4A_BRANDS = (b"M4A ", b"M4B ", b"mp42", b"isom", b"iso2", b"avc1", b"dash")

# MP3 는 ID3 태그로 시작하거나 프레임 동기 비트(11비트가 모두 1)로 시작한다.
_ID3_SIGNATURE = b"ID3"
_MPEG_SYNC_MASK = 0xE0

# ADTS 로 감싼 생 AAC 는 0xFFF1 / 0xFFF9 로 시작한다.
_ADTS_HEADERS = (b"\xff\xf1", b"\xff\xf9")


def detect_audio_format(data: bytes) -> AudioFormat | None:
    """파일 내용으로 오디오 형식을 판별한다. 허용 형식이 아니면 `None`."""
    if data.startswith(_ADTS_HEADERS):
        return AudioFormat.AAC

    if _is_mp3(data):
        return AudioFormat.MP3

    if _is_wav(data):
        return AudioFormat.WAV

    if data.startswith(_OGG_SIGNATURE):
        return AudioFormat.OGG

    if data.startswith(_EBML_SIGNATURE):
        # WebM 과 Matroska 가 같은 EBML 헤더를 쓰지만 오디오 업로드는 WebM 으로 다룬다.
        return AudioFormat.WEBM

    if _is_mp4_container(data):
        return AudioFormat.M4A

    return None


def _is_mp3(data: bytes) -> bool:
    """ID3 태그가 붙어 있거나 MPEG 프레임 동기로 시작하는지."""
    if data.startswith(_ID3_SIGNATURE):
        return True

    return (
        len(data) >= 2
        and data[0] == 0xFF
        and (data[1] & _MPEG_SYNC_MASK) == _MPEG_SYNC_MASK
    )


def _is_wav(data: bytes) -> bool:
    """RIFF 컨테이너이면서 WAVE 인지. (RIFF 는 WebP 등도 쓰므로 뒤 4바이트까지 본다)"""
    return (
        len(data) >= _WAV_HEADER_SIZE
        and data.startswith(_RIFF_SIGNATURE)
        and data[8:12] == _WAVE_SIGNATURE
    )


def _is_mp4_container(data: bytes) -> bool:
    """MP4 계열 컨테이너(M4A/AAC)인지. 4~8 바이트가 `ftyp` 이다."""
    if len(data) < _FTYP_HEADER_SIZE or data[4:8] != _FTYP_SIGNATURE:
        return False

    # 브랜드를 확인하되, 모르는 브랜드라도 ftyp 컨테이너면 오디오로 받아들인다.
    return True


def read_audio(audio: BinaryIO) -> bytes:
    """업로드 오디오를 크기 제한을 지키며 읽는다.

    전체를 한 번에 메모리로 읽지 않고 나눠 읽다가 최대 크기를 넘으면 즉시 중단한다.
    비어 있거나 최대 크기를 넘으면 400 으로 처리한다.
    """
    chunks: list[bytes] = []
    size = 0

    while chunk := audio.read(AUDIO_CHUNK_SIZE_BYTE):
        size += len(chunk)
        if size > MAX_AUDIO_SIZE_BYTE:
            raise InvalidRequestError(
                f"오디오 파일이 최대 크기({MAX_AUDIO_SIZE_BYTE} bytes)를 초과했습니다."
            )
        chunks.append(chunk)

    if size == 0:
        raise InvalidRequestError("오디오 파일이 비어 있습니다.")

    return b"".join(chunks)


def read_and_detect(audio: BinaryIO) -> tuple[bytes, AudioFormat]:
    """업로드 오디오를 읽고 실제 형식까지 판별한다. 허용 형식이 아니면 400."""
    data = read_audio(audio)
    audio_format = detect_audio_format(data)
    if audio_format is None:
        raise InvalidRequestError(
            "허용하지 않는 오디오 형식입니다. (MP3 / M4A / AAC / WAV / OGG / WebM 만 허용)"
        )
    return data, audio_format
