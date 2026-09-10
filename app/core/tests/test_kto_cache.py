"""TourAPI 응답 캐시와 대표 이미지 일괄 조회 테스트. (`app/services/kto.py`)

도메인이 아니라 여러 도메인이 함께 쓰는 외부 서비스 연동 모듈이라 여기에 둔다.

- 캐시: 같은 조회를 반복해도 TourAPI 를 다시 부르지 않는다.
- 일괄 조회: 장소 여러 곳의 대표 이미지를 동시에 가져오고, 총 시간에 상한을 둔다.
"""

import time
from typing import Any

import pytest

from app.core.config import Settings
from app.services import kto


SERVICE_KEY = "test-service-key"
CONTENT_ID = 126508
OTHER_CONTENT_ID = 126509
IMAGE_URL = "https://example.com/images/126508.jpg"
OTHER_IMAGE_URL = "https://example.com/images/126509.jpg"


def _body(content_id: int, first_image: str | None) -> dict[str, Any]:
    """TourAPI `detailCommon2` 응답 형태."""
    item: dict[str, Any] = {"contentid": str(content_id)}
    if first_image is not None:
        item["firstimage"] = first_image
    return {"response": {"body": {"items": {"item": [item]}}}}


class _FakeResponse:
    def __init__(self, body: Any) -> None:
        self._body = body
        self.encoding = "utf-8"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._body


class _FakeClient:
    """`httpx.Client` 대신 쓰는 가짜 클라이언트. 호출된 파라미터를 기록한다."""

    calls: list[dict[str, Any]] = []
    bodies: dict[str, Any] = {}

    def __init__(self, **_: Any) -> None:
        pass

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def get(self, path: str, params: dict[str, Any]) -> _FakeResponse:
        type(self).calls.append({"path": path, "params": params})
        content_id = int(params["contentId"])
        return _FakeResponse(
            type(self).bodies.get(str(content_id), _body(content_id, IMAGE_URL))
        )


@pytest.fixture
def kto_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """TourAPI 호출을 가짜 클라이언트로 막고, 나간 요청을 기록한다."""
    _FakeClient.calls = []
    _FakeClient.bodies = {}
    monkeypatch.setattr(kto.httpx, "Client", _FakeClient)
    monkeypatch.setattr(
        kto, "get_settings", lambda: Settings(kto_service_key=SERVICE_KEY)
    )
    return _FakeClient.calls


# ---------------------------------------------------------------------
# 응답 캐시
# ---------------------------------------------------------------------


def test_같은_장소를_다시_조회하면_TourAPI를_한_번만_부른다(
    kto_calls: list[dict[str, Any]],
) -> None:
    first = kto.get_location_image_url(CONTENT_ID)
    second = kto.get_location_image_url(CONTENT_ID)

    assert (first, second) == (IMAGE_URL, IMAGE_URL)
    assert len(kto_calls) == 1


def test_같은_응답을_쓰는_다른_함수도_캐시를_함께_쓴다(
    kto_calls: list[dict[str, Any]],
) -> None:
    """대표 이미지와 상세 설명은 같은 `detailCommon2` 응답에서 나온다."""
    kto.get_location_image_url(CONTENT_ID)
    kto.get_location_overview(CONTENT_ID)

    assert len(kto_calls) == 1


def test_장소가_다르면_각각_조회한다(kto_calls: list[dict[str, Any]]) -> None:
    kto.get_location_image_url(CONTENT_ID)
    kto.get_location_image_url(OTHER_CONTENT_ID)

    assert [int(call["params"]["contentId"]) for call in kto_calls] == [
        CONTENT_ID,
        OTHER_CONTENT_ID,
    ]


def test_조회에_실패해도_잠시_기억해_매번_다시_부르지_않는다(
    kto_calls: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """실패를 기억하지 않으면 TourAPI 가 느릴 때 장소마다 매번 타임아웃까지 기다린다."""

    def raise_error(self: Any, path: str, params: dict[str, Any]) -> _FakeResponse:
        kto_calls.append({"path": path, "params": params})
        raise kto.httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(_FakeClient, "get", raise_error)

    assert kto.get_location_image_url(CONTENT_ID) is None
    assert kto.get_location_image_url(CONTENT_ID) is None
    assert len(kto_calls) == 1


def test_실패_캐시는_성공_캐시보다_먼저_만료된다() -> None:
    assert kto._CACHE_FAILURE_TTL_SECONDS < kto._CACHE_TTL_SECONDS


def test_캐시가_만료되면_다시_조회한다(
    kto_calls: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(kto, "_CACHE_TTL_SECONDS", 0)

    kto.get_location_image_url(CONTENT_ID)
    kto.get_location_image_url(CONTENT_ID)

    assert len(kto_calls) == 2


def test_캐시를_비우면_다시_조회한다(kto_calls: list[dict[str, Any]]) -> None:
    kto.get_location_image_url(CONTENT_ID)
    kto.clear_cache()
    kto.get_location_image_url(CONTENT_ID)

    assert len(kto_calls) == 2


def test_캐시_항목_수가_상한을_넘지_않는다(
    kto_calls: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(kto, "_CACHE_MAX_ENTRIES", 3)

    for content_id in range(10):
        kto.get_location_image_url(content_id)

    assert len(kto._cache) == 3


def test_인증키가_없으면_호출하지_않고_None이다(
    monkeypatch: pytest.MonkeyPatch, kto_calls: list[dict[str, Any]]
) -> None:
    monkeypatch.setattr(kto, "get_settings", lambda: Settings(kto_service_key=""))

    assert kto.get_location_image_url(CONTENT_ID) is None
    assert kto_calls == []


# ---------------------------------------------------------------------
# 대표 이미지 일괄 조회
# ---------------------------------------------------------------------


def test_여러_장소의_대표_이미지를_한_번에_돌려준다(
    kto_calls: list[dict[str, Any]],
) -> None:
    _FakeClient.bodies = {
        str(CONTENT_ID): _body(CONTENT_ID, IMAGE_URL),
        str(OTHER_CONTENT_ID): _body(OTHER_CONTENT_ID, OTHER_IMAGE_URL),
    }

    image_urls = kto.get_location_image_urls([CONTENT_ID, OTHER_CONTENT_ID])

    assert image_urls == {CONTENT_ID: IMAGE_URL, OTHER_CONTENT_ID: OTHER_IMAGE_URL}


def test_같은_장소가_여러_번_들어와도_한_번만_조회한다(
    kto_calls: list[dict[str, Any]],
) -> None:
    image_urls = kto.get_location_image_urls([CONTENT_ID, CONTENT_ID, CONTENT_ID])

    assert image_urls == {CONTENT_ID: IMAGE_URL}
    assert len(kto_calls) == 1


def test_빈_목록이면_조회하지_않는다(kto_calls: list[dict[str, Any]]) -> None:
    assert kto.get_location_image_urls([]) == {}
    assert kto_calls == []


def test_이미지가_없는_장소는_None이다(kto_calls: list[dict[str, Any]]) -> None:
    _FakeClient.bodies = {str(CONTENT_ID): _body(CONTENT_ID, None)}

    assert kto.get_location_image_urls([CONTENT_ID]) == {CONTENT_ID: None}


def test_예산_안에_끝나지_못한_장소는_None이고_나머지는_그대로_준다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TourAPI 가 느려도 요청 하나가 이미지 때문에 무한정 길어지지 않는다."""

    def slow_for_one(content_id: int) -> str | None:
        if content_id == CONTENT_ID:
            time.sleep(1.0)
            return IMAGE_URL
        return OTHER_IMAGE_URL

    monkeypatch.setattr(kto, "get_location_image_url", slow_for_one)

    started = time.monotonic()
    image_urls = kto.get_location_image_urls(
        [CONTENT_ID, OTHER_CONTENT_ID], budget_seconds=0.1
    )
    elapsed = time.monotonic() - started

    assert image_urls == {CONTENT_ID: None, OTHER_CONTENT_ID: OTHER_IMAGE_URL}
    # 느린 장소를 기다리지 않고 예산 안에 돌아온다.
    assert elapsed < 1.0


def test_조회_중_예외가_나도_그_장소만_None이다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_for_one(content_id: int) -> str | None:
        if content_id == CONTENT_ID:
            raise RuntimeError("예상치 못한 오류")
        return OTHER_IMAGE_URL

    monkeypatch.setattr(kto, "get_location_image_url", raise_for_one)

    image_urls = kto.get_location_image_urls([CONTENT_ID, OTHER_CONTENT_ID])

    assert image_urls == {CONTENT_ID: None, OTHER_CONTENT_ID: OTHER_IMAGE_URL}
