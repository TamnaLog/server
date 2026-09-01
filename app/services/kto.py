import html
import re
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class KtoClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_area_codes(self) -> dict[str, Any]:
        return await self._get("/areaCode2", {"numOfRows": 20, "pageNo": 1})

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.kto_service_key:
            raise RuntimeError("KTO_SERVICE_KEY is not configured.")

        request_params = {
            "serviceKey": self.settings.kto_service_key,
            "MobileOS": self.settings.kto_mobile_os,
            "MobileApp": self.settings.kto_mobile_app,
            "_type": "json",
            **params,
        }

        async with httpx.AsyncClient(base_url=self.settings.kto_base_url, timeout=10.0) as client:
            response = await client.get(path, params=request_params)
            response.encoding = "utf-8"
            response.raise_for_status()
            return response.json()


def get_location_image_url(content_id: int) -> str | None:
    """TourAPI 에서 장소 대표 이미지 URL 을 조회한다.

    이미지 URL 은 부가 정보라, 인증키 미설정·통신 실패·이미지 없음 등 어떤 이유로든
    조회하지 못하면 예외를 올리지 않고 `None` 을 반환한다.
    (이미지 하나 때문에 미션 완료 응답 전체가 실패하면 안 되기 때문)
    """
    item = _get_detail_common_item(content_id)
    if item is None:
        return None

    return item.get("firstimage") or item.get("firstimage2") or None


def get_location_overview(content_id: int) -> str | None:
    """TourAPI 에서 장소 상세 설명(`overview`)을 조회한다.

    `overview` 에는 HTML 태그와 엔티티가 섞여 있어 프론트가 그대로 쓸 수 있는
    일반 문자열로 정리해서 돌려준다.
    이미지와 마찬가지로 조회하지 못하면 `None` 이고 호출한 API 를 실패시키지 않는다.
    """
    item = _get_detail_common_item(content_id)
    if item is None:
        return None

    return _to_plain_text(item.get("overview"))


# 상세 이미지 기본 조회 개수. 정렬·중복 제거 후 잘라내므로 요청 개수보다 넉넉히 받는다.
_DETAIL_IMAGE_ROWS = 20


def get_location_detail_image_urls(content_id: int, limit: int = 5) -> list[str] | None:
    """TourAPI 에서 장소 상세 이미지 URL 을 최대 `limit` 개 조회한다.

    대표 이미지 한 장을 주는 `get_location_image_url()` 과 달리
    `detailImage2` 의 `originimgurl` 목록을 쓴다. (둘은 서로 대체하지 않는다)
    이미지가 없거나 조회하지 못하면 빈 배열이 아니라 `None` 을 돌려준다.
    응답에서 "이미지 없음"을 `[]` 가 아니라 `null` 로 내려주기 위해서다.
    (app/map/docs/BUSINESS_RULES.md - 지도 장소 상세 조회 3장)
    """
    if limit <= 0:
        raise ValueError("limit 은 1 이상이어야 합니다.")

    items = _get_detail_image_items(content_id)
    if not items:
        return None

    urls: list[str] = []
    for item in _sort_by_serial_number(items):
        url = item.get("originimgurl")
        # 같은 URL 이 여러 번 오면 처음 한 건만 남긴다.
        if not isinstance(url, str) or not url.strip() or url in urls:
            continue

        urls.append(url)
        if len(urls) == limit:
            break

    return urls or None


def _sort_by_serial_number(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`serialnum` 오름차순으로 정렬한다.

    숫자로 해석되지 않는 `serialnum` 은 정렬 기준이 없으므로
    받은 순서를 유지한 채 숫자 항목 뒤에 둔다.
    """
    return [
        item
        for _, item in sorted(
            enumerate(items), key=lambda pair: _serial_number_sort_key(*pair)
        )
    ]


def _serial_number_sort_key(index: int, item: dict[str, Any]) -> tuple[int, int, int]:
    """정렬 키. 숫자 `serialnum` 이 먼저, 그다음이 원래 순서다."""
    try:
        return (0, int(str(item.get("serialnum")).strip()), index)
    except (TypeError, ValueError):
        return (1, index, index)


def _get_detail_image_items(content_id: int) -> list[dict[str, Any]] | None:
    """`detailImage2` 에서 장소 상세 이미지 목록을 가져온다. 실패하면 `None`."""
    body = _get_json(
        "/detailImage2",
        {
            "contentId": str(content_id),
            # 콘텐츠 이미지를 받으려면 TourAPI 가 요구하는 값이다.
            "imageYN": "Y",
            "numOfRows": str(_DETAIL_IMAGE_ROWS),
            "pageNo": "1",
        },
    )
    if body is None:
        return None

    return _items(body)


def _get_detail_common_item(content_id: int) -> dict[str, Any] | None:
    """`detailCommon2` 에서 장소 공통 정보 한 건을 가져온다. 실패하면 `None`."""
    body = _get_json("/detailCommon2", {"contentId": str(content_id)})
    if body is None:
        return None

    items = _items(body)
    return items[0] if items else None


def _get_json(path: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """TourAPI 를 동기로 호출해 응답 JSON 을 돌려준다. 실패하면 `None`.

    DB 세션이 동기라 라우트도 동기로 동작하므로 여기서도 동기 클라이언트를 사용한다.
    TourAPI 값은 부가 정보라, 인증키 미설정·통신 실패·JSON 오류를 예외로 올리지 않는다.
    """
    settings = get_settings()
    if not settings.kto_service_key:
        return None

    request_params = {
        "serviceKey": settings.kto_service_key,
        "MobileOS": settings.kto_mobile_os,
        "MobileApp": settings.kto_mobile_app,
        "_type": "json",
        **params,
    }

    try:
        with httpx.Client(base_url=settings.kto_base_url, timeout=5.0) as client:
            response = client.get(path, params=request_params)
            response.encoding = "utf-8"
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    return body if isinstance(body, dict) else None


def _items(body: dict[str, Any]) -> list[dict[str, Any]]:
    """TourAPI 응답에서 item 목록을 꺼낸다. 형식이 다르거나 비어 있으면 빈 목록."""
    items = body.get("response", {}).get("body", {}).get("items")
    if not isinstance(items, dict):
        return []

    item = items.get("item")
    if isinstance(item, dict):
        item = [item]
    if not isinstance(item, list):
        return []

    return [row for row in item if isinstance(row, dict)]


# HTML 태그. `overview` 에는 <br>, <p> 등이 그대로 들어 있다.
_HTML_TAG = re.compile(r"<[^>]*>")

# 연속된 공백/줄바꿈
_WHITESPACE = re.compile(r"\s+")


def _to_plain_text(overview: Any) -> str | None:
    """`overview` 를 프론트가 그대로 표시할 수 있는 문자열로 정리한다.

    엔티티 변환 → 태그 제거 → 공백 정리 순서로 처리하고, 남는 게 없으면 `None`.
    (app/map/docs/BUSINESS_RULES.md - 지도 장소 상세 조회 2장)

    이 순서라 `&lt;b&gt;` 처럼 엔티티로 감싼 태그도 태그로 보고 지운다.
    """
    if not isinstance(overview, str):
        return None

    text = _HTML_TAG.sub(" ", html.unescape(overview))
    return _WHITESPACE.sub(" ", text).strip() or None
