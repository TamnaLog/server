"""TourAPI 장소 상세 이미지(`detailImage2`) 정리 테스트.

정리 규칙은 app/map/docs/BUSINESS_RULES.md - 지도 장소 상세 조회 3장에 있다.
장소 상세 조회 API 테스트는 이 함수를 스텁으로 막기 때문에
정렬·중복 제거·개수 제한 규칙이 거기서는 검증되지 않는다.
그래서 HTTP 호출만 대신하고 정리 로직은 실제로 태워서 확인한다.
"""

from typing import Any

import pytest

from app.services import kto


@pytest.fixture
def detail_image_items(monkeypatch: pytest.MonkeyPatch):
    """TourAPI 호출만 대신하고 정리 로직은 그대로 태운다."""

    def set_items(items: list[dict[str, Any]] | None) -> None:
        monkeypatch.setattr(kto, "_get_detail_image_items", lambda content_id: items)

    return set_items


def _items(*urls: str) -> list[dict[str, Any]]:
    """`serialnum` 이 순서대로 붙은 응답 항목을 만든다."""
    return [
        {"serialnum": str(index), "originimgurl": url}
        for index, url in enumerate(urls, start=1)
    ]


def test_이미지가_5개보다_많으면_최대_5개만_반환한다(detail_image_items) -> None:
    detail_image_items(_items(*[f"https://example.com/{index}.jpg" for index in range(7)]))

    urls = kto.get_location_detail_image_urls(1)

    assert urls is not None
    assert len(urls) == 5
    assert urls == [f"https://example.com/{index}.jpg" for index in range(5)]


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_이미지가_5개보다_적으면_있는_만큼만_반환한다(
    detail_image_items, count: int
) -> None:
    detail_image_items(_items(*[f"https://example.com/{index}.jpg" for index in range(count)]))

    urls = kto.get_location_detail_image_urls(1)

    assert urls is not None
    assert len(urls) == count


def test_serialnum_오름차순으로_정렬한다(detail_image_items) -> None:
    detail_image_items(
        [
            {"serialnum": "3", "originimgurl": "https://example.com/3.jpg"},
            {"serialnum": "1", "originimgurl": "https://example.com/1.jpg"},
            {"serialnum": "2", "originimgurl": "https://example.com/2.jpg"},
        ]
    )

    assert kto.get_location_detail_image_urls(1) == [
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
        "https://example.com/3.jpg",
    ]


def test_serialnum이_숫자가_아니면_받은_순서를_유지하고_뒤에_둔다(
    detail_image_items,
) -> None:
    detail_image_items(
        [
            {"serialnum": "", "originimgurl": "https://example.com/no-serial.jpg"},
            {"serialnum": "2", "originimgurl": "https://example.com/2.jpg"},
            {"serialnum": "1", "originimgurl": "https://example.com/1.jpg"},
        ]
    )

    assert kto.get_location_detail_image_urls(1) == [
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
        "https://example.com/no-serial.jpg",
    ]


def test_같은_URL은_한_번만_반환한다(detail_image_items) -> None:
    detail_image_items(
        [
            {"serialnum": "1", "originimgurl": "https://example.com/1.jpg"},
            {"serialnum": "2", "originimgurl": "https://example.com/1.jpg"},
            {"serialnum": "3", "originimgurl": "https://example.com/2.jpg"},
        ]
    )

    assert kto.get_location_detail_image_urls(1) == [
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
    ]


def test_중복을_제거한_뒤에_개수를_센다(detail_image_items) -> None:
    # 같은 URL 이 섞여 있어도 서로 다른 5장을 채워서 준다.
    detail_image_items(
        _items("https://example.com/1.jpg", "https://example.com/1.jpg")
        + _items(*[f"https://example.com/other-{index}.jpg" for index in range(5)])
    )

    urls = kto.get_location_detail_image_urls(1)

    assert urls is not None
    assert len(urls) == 5
    assert len(set(urls)) == 5


@pytest.mark.parametrize(
    "items",
    [
        pytest.param(None, id="조회_실패"),
        pytest.param([], id="이미지_없음"),
        pytest.param([{"serialnum": "1"}], id="URL_없음"),
        pytest.param([{"serialnum": "1", "originimgurl": ""}], id="빈_URL"),
        pytest.param([{"serialnum": "1", "originimgurl": "   "}], id="공백_URL"),
        pytest.param([{"serialnum": "1", "originimgurl": None}], id="URL이_null"),
    ],
)
def test_쓸_이미지가_없으면_빈_배열이_아니라_None이다(
    detail_image_items, items: list[dict[str, Any]] | None
) -> None:
    detail_image_items(items)

    # 응답에서 "이미지 없음"은 [] 가 아니라 null 이어야 한다.
    assert kto.get_location_detail_image_urls(1) is None


def test_limit으로_반환_개수를_줄일_수_있다(detail_image_items) -> None:
    detail_image_items(_items(*[f"https://example.com/{index}.jpg" for index in range(5)]))

    urls = kto.get_location_detail_image_urls(1, limit=2)

    assert urls == ["https://example.com/0.jpg", "https://example.com/1.jpg"]


@pytest.mark.parametrize("limit", [0, -1])
def test_limit이_양수가_아니면_ValueError다(detail_image_items, limit: int) -> None:
    detail_image_items(_items("https://example.com/1.jpg"))

    with pytest.raises(ValueError):
        kto.get_location_detail_image_urls(1, limit=limit)
