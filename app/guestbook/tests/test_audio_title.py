"""방명록 오디오 제목 생성(OpenAI) 테스트.

기준 문서: app/guestbook/docs/BUSINESS_RULES.md - 수정사항 / OpenAI 오디오 제목 생성

방명록 작성 API 테스트(`test_create_guestbook.py`)는 이 모듈을 스텁으로 바꿔 쓰므로,
여기서는 HTTP 호출만 가짜로 만들고 **모듈 자체의 규칙**을 확인한다.
- 여러 오디오를 요청 순서대로 전사해 제목은 한 개만 만든다
- 길이 규칙(2~10자 우선 / 10자 초과는 1회 재생성 / 50자 초과는 실패)
- 키 미설정·호출 실패·빈 제목은 예외 (공통 처리기가 500 으로 응답)
"""

from typing import Any

import httpx
import pytest

from app.common.audios import AudioFormat
from app.core.config import Settings
from app.services import openai_audio_title
from app.services.openai_audio_title import (
    AudioTitleError,
    ValidatedAudio,
    generate_audio_title,
)


API_KEY = "test-openai-key"

MP3 = ValidatedAudio(data=b"first-audio", audio_format=AudioFormat.MP3)
M4A = ValidatedAudio(data=b"second-audio", audio_format=AudioFormat.M4A)


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    """`httpx.Client` 대신 쓰는 가짜 클라이언트. 호출 인자를 기록한다."""

    def __init__(self, calls: list[dict[str, Any]], responses: list[Any]) -> None:
        self._calls = calls
        self._responses = responses

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(self, path: str, **kwargs: Any) -> _FakeResponse:
        self._calls.append({"path": path, **kwargs})
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _transcription(text: str) -> _FakeResponse:
    return _FakeResponse({"text": text})


def _title(content: str) -> _FakeResponse:
    return _FakeResponse({"choices": [{"message": {"content": content}}]})


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """API 키가 설정된 상태. (`.env` 를 읽지 않도록 직접 만든다)"""
    fake_settings = Settings(
        openai_api_key=API_KEY,
        openai_audio_transcription_model="transcribe-model",
        openai_audio_title_model="title-model",
        openai_timeout_seconds=5,
    )
    monkeypatch.setattr(openai_audio_title, "get_settings", lambda: fake_settings)
    return fake_settings


class FakeOpenAI:
    """가짜 OpenAI. 응답을 미리 넣어 두고, 실제로 나간 요청을 `calls` 로 확인한다."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: list[Any] = []

    def queue(self, *responses: Any) -> None:
        """호출 순서대로 돌려줄 응답(또는 발생시킬 예외)을 넣는다."""
        self.responses.extend(responses)

    def client(self, **_kwargs: Any) -> "_FakeClient":
        return _FakeClient(self.calls, self.responses)

    @property
    def paths(self) -> list[str]:
        return [call["path"] for call in self.calls]


@pytest.fixture
def openai(monkeypatch: pytest.MonkeyPatch) -> FakeOpenAI:
    """`httpx.Client` 를 가짜로 바꾼다. (실제 OpenAI 로 나가지 않게)"""
    fake = FakeOpenAI()
    monkeypatch.setattr(openai_audio_title.httpx, "Client", fake.client)
    return fake


# ---------------------------------------------------------------------
# 정상 생성
# ---------------------------------------------------------------------


def test_전사문으로_제목_한_개를_만든다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    openai.queue(_transcription("파도 소리가 계속 들린다"), _title("파도소리"))

    assert generate_audio_title([MP3]) == "파도소리"


def test_오디오가_여러_개면_요청_순서대로_전사하고_제목은_한_번만_만든다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    openai.queue(_transcription("첫 번째"), _transcription("두 번째"), _title("돌담길 산책"))

    title = generate_audio_title([MP3, M4A])

    assert title == "돌담길 산책"
    # 전사 2번 + 제목 생성 1번
    assert openai.paths == [
        openai_audio_title.TRANSCRIPTION_PATH,
        openai_audio_title.TRANSCRIPTION_PATH,
        openai_audio_title.CHAT_COMPLETION_PATH,
    ]
    # 전사문은 요청 순서대로 이어 붙인다.
    user_message = openai.calls[2]["json"]["messages"][1]["content"]
    assert user_message.index("첫 번째") < user_message.index("두 번째")


def test_전사_요청에_설정된_모델과_실제_형식을_쓴다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    openai.queue(_transcription("내용"), _title("새소리"))

    generate_audio_title([M4A])

    transcription = openai.calls[0]
    assert transcription["data"]["model"] == "transcribe-model"
    filename, content, content_type = transcription["files"]["file"]
    # 원본 파일명이 아니라 판별된 형식으로 보낸다.
    assert filename == "audio.m4a"
    assert content == M4A.data
    assert content_type == "audio/mp4"


def test_제목_요청은_짧은_출력과_낮은_무작위성을_쓴다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    openai.queue(_transcription("내용"), _title("새소리"))

    generate_audio_title([MP3])

    payload = openai.calls[1]["json"]
    assert payload["model"] == "title-model"
    assert payload["max_tokens"] == openai_audio_title.TITLE_MAX_TOKENS
    assert payload["temperature"] == openai_audio_title.TITLE_TEMPERATURE
    # 프롬프트는 모듈 상수를 그대로 쓴다.
    assert payload["messages"][0]["content"] == openai_audio_title.AUDIO_TITLE_PROMPT


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        pytest.param("  파도소리\n", "파도소리", id="앞뒤_공백"),
        pytest.param('"파도소리"', "파도소리", id="따옴표"),
        pytest.param("파도소리\n설명은 이렇습니다", "파도소리", id="여러_줄"),
    ],
)
def test_모델_출력을_한_줄_제목으로_정리한다(
    settings: Settings, openai: FakeOpenAI, content: str, expected: str
) -> None:
    openai.queue(_transcription("내용"), _title(content))

    assert generate_audio_title([MP3]) == expected


# ---------------------------------------------------------------------
# 길이 규칙
# ---------------------------------------------------------------------


def test_10자를_넘으면_더_짧게_한_번_다시_만든다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    openai.queue(_transcription("내용"), _title("아주 긴 제목을 만들어 버린 경우"), _title("돌담길"))

    title = generate_audio_title([MP3])

    assert title == "돌담길"
    # 재생성 요청에는 더 짧게 만들라는 지시가 붙는다.
    retry_prompt = openai.calls[2]["json"]["messages"][0]["content"]
    assert openai_audio_title.SHORTER_TITLE_INSTRUCTION in retry_prompt


def test_재생성해도_10자를_넘으면_자르지_않고_그대로_쓴다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    long_title = "열 자를 넘지만 오십 자는 넘지 않는 제목"
    openai.queue(_transcription("내용"), _title(long_title), _title(long_title))

    # 서버가 임의로 절단하지 않는다. 재생성은 한 번만 한다.
    assert generate_audio_title([MP3]) == long_title
    assert len(openai.calls) == 3


def test_50자를_넘는_제목은_실패로_처리한다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    too_long = "가" * 51
    openai.queue(_transcription("내용"), _title(too_long), _title(too_long))

    with pytest.raises(AudioTitleError):
        generate_audio_title([MP3])


# ---------------------------------------------------------------------
# 실패 처리
# ---------------------------------------------------------------------


def test_API_키가_없으면_호출하지_않고_실패한다(
    monkeypatch: pytest.MonkeyPatch, openai: FakeOpenAI
) -> None:
    monkeypatch.setattr(
        openai_audio_title, "get_settings", lambda: Settings(openai_api_key="")
    )

    with pytest.raises(AudioTitleError):
        generate_audio_title([MP3])

    assert openai.calls == []


def test_오디오가_없으면_호출하지_않고_실패한다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    # 오디오가 없으면 호출하는 쪽에서 걸러야 한다. (audio_title = NULL)
    with pytest.raises(AudioTitleError):
        generate_audio_title([])

    assert openai.calls == []


def test_전사문이_비어_있으면_제목을_만들지_않고_실패한다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    openai.queue(_transcription("   "))

    with pytest.raises(AudioTitleError):
        generate_audio_title([MP3])

    # 제목 생성 요청까지 가지 않는다.
    assert openai.paths == [openai_audio_title.TRANSCRIPTION_PATH]


@pytest.mark.parametrize(
    "content",
    [pytest.param("", id="빈_문자열"), pytest.param("   \n ", id="공백만")],
)
def test_빈_제목을_받으면_실패한다(
    settings: Settings, openai: FakeOpenAI, content: str
) -> None:
    openai.queue(_transcription("내용"), _title(content))

    with pytest.raises(AudioTitleError):
        generate_audio_title([MP3])


def test_시간_초과는_실패로_처리한다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    openai.queue(httpx.ReadTimeout("timeout"))

    with pytest.raises(AudioTitleError):
        generate_audio_title([MP3])


def test_HTTP_오류는_실패로_처리한다(
    settings: Settings, openai: FakeOpenAI
) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")
    response = httpx.Response(500, request=request)
    openai.queue(httpx.HTTPStatusError("error", request=request, response=response))

    with pytest.raises(AudioTitleError):
        generate_audio_title([MP3])
