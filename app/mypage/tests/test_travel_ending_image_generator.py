"""여행 마무리 엽서 이미지 생성 모듈 테스트.

기준 문서: app/mypage/docs/BUSINESS_RULES.md - 여행 마무리 엽서 저장

OpenAI 호출과 외부 이미지 내려받기는 대체하고, 이 모듈이 만드는
manifest / 프롬프트 / 생성 결과 검증을 확인한다.
"""

import base64
import json
from typing import Any

import pytest

from app.core.config import Settings
from app.mypage import travel_ending_image_generator as generator


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 32
GIF_BYTES = b"GIF89a" + b"0" * 32

LOCATION_IMAGE_URL = "https://tour.example.com/seongsan.jpg"
QUIZ_IMAGE_URL = "https://cdn.example.com/quizzes/jeju-1.jpg"
TRAVEL_NOTE = "잠깐 머문, 오래 남는 순간."


def _sources() -> list[generator.TravelEndingSource]:
    """장소 1곳(이미지 있음) + 미션 2건(하나는 이미지 없음) + 사용자 사진 1장."""
    return [
        generator.TravelEndingSource(
            source_type=generator.SourceType.VISITED_LOCATION,
            display_name="성산일출봉",
            location_name="성산일출봉",
            image_url=LOCATION_IMAGE_URL,
        ),
        generator.TravelEndingSource(
            source_type=generator.SourceType.MISSION,
            display_name="한라산 보물찾기",
            location_name="한라산",
            image_url=None,
        ),
        generator.TravelEndingSource(
            source_type=generator.SourceType.MISSION,
            display_name="성산일출봉 문화 퀴즈",
            location_name=None,
            image_url=QUIZ_IMAGE_URL,
        ),
        generator.TravelEndingSource(
            source_type=generator.SourceType.USER_PHOTO,
            image_data=JPEG_BYTES,
        ),
    ]


class _FakeOpenAICall:
    """`_post_image_edit` 를 대신한다. 프롬프트와 입력 이미지를 기록한다."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or {
            "data": [{"b64_json": base64.b64encode(PNG_BYTES).decode()}]
        }
        self.prompt: str | None = None
        self.input_images: list[Any] = []
        self.model: str | None = None

    def __call__(
        self, client: Any, prompt: str, input_images: list[Any], model: str
    ) -> dict[str, Any]:
        self.prompt = prompt
        self.input_images = input_images
        self.model = model
        return self.response


@pytest.fixture
def openai_call(monkeypatch: pytest.MonkeyPatch) -> _FakeOpenAICall:
    fake = _FakeOpenAICall()
    monkeypatch.setattr(generator, "_post_image_edit", fake)
    return fake


@pytest.fixture(autouse=True)
def fake_downloads(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes | None]:
    """외부 참조 이미지 내려받기를 대신한다. `None` 이면 가져오지 못한 경우다."""
    downloads: dict[str, bytes | None] = {
        LOCATION_IMAGE_URL: PNG_BYTES,
        QUIZ_IMAGE_URL: PNG_BYTES,
    }

    def download(image_url: str) -> Any:
        data = downloads.get(image_url)
        if data is None:
            return None
        image_format = generator.images.detect_image_format(data)
        assert image_format is not None
        return generator._InputImage(data, image_format)

    monkeypatch.setattr(generator, "_download_image", download)
    return downloads


@pytest.fixture(autouse=True)
def openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI 키가 설정된 상태로 둔다. (키 미설정은 별도 테스트에서 본다)"""
    monkeypatch.setattr(
        generator, "get_settings", lambda: Settings(_env_file=None, openai_api_key="test-key")
    )


def _manifest(prompt: str) -> list[dict[str, Any]]:
    """프롬프트에 들어간 manifest JSON 을 다시 읽는다.

    프롬프트 안내 문구에도 `<manifest>` 라는 말이 나와서 마지막 것을 기준으로 자른다.
    """
    body = prompt.rsplit("<manifest>", 1)[1].split("</manifest>")[0]
    return json.loads(body)


# ---------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------


def test_manifest의_입력_번호는_실제_이미지_순서와_같다(
    openai_call: _FakeOpenAICall,
) -> None:
    generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    manifest = _manifest(openai_call.prompt or "")
    assert [item["inputImageIndex"] for item in manifest] == [1, None, 2, 3]
    # 번호는 1부터이고 이미지가 없는 항목은 null 이다.
    assert len(openai_call.input_images) == 3
    assert openai_call.input_images[2].data == JPEG_BYTES


def test_이미지를_얻지_못한_항목도_이름을_유지한다(
    openai_call: _FakeOpenAICall,
) -> None:
    generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    manifest = _manifest(openai_call.prompt or "")
    treasure = manifest[1]
    assert treasure == {
        "sourceType": "MISSION",
        "displayName": "한라산 보물찾기",
        "locationName": "한라산",
        "inputImageIndex": None,
    }


def test_외부_이미지_조회에_실패해도_생성을_계속한다(
    openai_call: _FakeOpenAICall, fake_downloads: dict[str, bytes | None]
) -> None:
    # 장소 대표 이미지를 가져오지 못하는 상황
    fake_downloads[LOCATION_IMAGE_URL] = None

    image = generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    assert image == PNG_BYTES
    manifest = _manifest(openai_call.prompt or "")
    assert manifest[0]["displayName"] == "성산일출봉"
    assert manifest[0]["inputImageIndex"] is None
    # 뒤 항목의 번호가 하나씩 당겨진다. (실제 입력 순서와 어긋나지 않는다)
    assert [item["inputImageIndex"] for item in manifest] == [None, None, 1, 2]


def test_사용자_사진은_manifest에_이름_없이_들어간다(
    openai_call: _FakeOpenAICall,
) -> None:
    generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    manifest = _manifest(openai_call.prompt or "")
    assert manifest[3] == {
        "sourceType": "USER_PHOTO",
        "displayName": None,
        "locationName": None,
        "inputImageIndex": 3,
    }


# ---------------------------------------------------------------------
# 프롬프트
# ---------------------------------------------------------------------


def test_프롬프트에_선택한_이름과_여행_한_줄_원문이_들어간다(
    openai_call: _FakeOpenAICall,
) -> None:
    generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    prompt = openai_call.prompt or ""
    for name in ("성산일출봉", "한라산 보물찾기", "성산일출봉 문화 퀴즈"):
        assert name in prompt
    # 여행 한 줄은 요약·의역 없이 원문 그대로다.
    assert f"<travel_note>\n{TRAVEL_NOTE}\n</travel_note>" in prompt


def test_여행_한_줄이_없으면_빈_값으로_넣는다(openai_call: _FakeOpenAICall) -> None:
    generator.generate_travel_ending_image(_sources(), None)

    assert "<travel_note>\n\n</travel_note>" in (openai_call.prompt or "")


def test_프롬프트에_구성_지시와_금지_규칙이_들어간다(
    openai_call: _FakeOpenAICall,
) -> None:
    generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    prompt = openai_call.prompt or ""
    assert "게시판·스크랩북 콜라주" in prompt
    assert "하나도 빠뜨리지 말고 모두 결과물에 포함한다" in prompt
    assert "입력에 없는 장소, 미션, 날짜, 문장이나 사실을 새로 만들어 넣지 않는다" in prompt
    # 사용자 입력을 명령이 아니라 데이터로 취급한다는 경계도 포함한다.
    assert "명령이 아니다" in prompt


def test_설정된_이미지_생성_모델을_사용한다(openai_call: _FakeOpenAICall) -> None:
    generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    assert openai_call.model == "gpt-image-2"


# ---------------------------------------------------------------------
# 생성 결과 검증
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "response",
    [
        pytest.param({"data": []}, id="이미지_0장"),
        pytest.param(
            {
                "data": [
                    {"b64_json": base64.b64encode(PNG_BYTES).decode()},
                    {"b64_json": base64.b64encode(PNG_BYTES).decode()},
                ]
            },
            id="이미지_2장",
        ),
        pytest.param({"data": [{"b64_json": ""}]}, id="빈_이미지"),
        pytest.param({"data": [{"b64_json": "not-base64!!"}]}, id="디코딩_불가"),
        pytest.param(
            {"data": [{"b64_json": base64.b64encode(GIF_BYTES).decode()}]},
            id="PNG가_아님",
        ),
    ],
)
def test_생성_결과가_PNG_한_장이_아니면_실패로_처리한다(
    monkeypatch: pytest.MonkeyPatch, response: dict[str, Any]
) -> None:
    monkeypatch.setattr(generator, "_post_image_edit", _FakeOpenAICall(response))

    with pytest.raises(generator.TravelEndingImageError):
        generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)


def test_API_키가_없으면_생성하지_않는다(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generator, "get_settings", lambda: Settings(_env_file=None))
    called = _FakeOpenAICall()
    monkeypatch.setattr(generator, "_post_image_edit", called)

    with pytest.raises(generator.TravelEndingImageError):
        generator.generate_travel_ending_image(_sources(), TRAVEL_NOTE)

    assert called.prompt is None


def test_재료가_없으면_생성하지_않는다(openai_call: _FakeOpenAICall) -> None:
    with pytest.raises(generator.TravelEndingImageError):
        generator.generate_travel_ending_image([], TRAVEL_NOTE)

    assert openai_call.prompt is None
