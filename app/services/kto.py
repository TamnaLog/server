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


def _get_detail_common_item(content_id: int) -> dict[str, Any] | None:
    """`detailCommon2` 에서 장소 공통 정보 한 건을 가져온다. 실패하면 `None`.

    DB 세션이 동기라 라우트도 동기로 동작하므로 여기서도 동기 클라이언트를 사용한다.
    """
    settings = get_settings()
    if not settings.kto_service_key:
        return None

    params = {
        "serviceKey": settings.kto_service_key,
        "MobileOS": settings.kto_mobile_os,
        "MobileApp": settings.kto_mobile_app,
        "_type": "json",
        "contentId": str(content_id),
    }

    try:
        with httpx.Client(base_url=settings.kto_base_url, timeout=5.0) as client:
            response = client.get("/detailCommon2", params=params)
            response.encoding = "utf-8"
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    return _first_item(body)


def _first_item(body: dict[str, Any]) -> dict[str, Any] | None:
    """TourAPI 응답에서 첫 번째 item 을 꺼낸다. 형식이 다르면 `None`."""
    items = body.get("response", {}).get("body", {}).get("items")
    if not isinstance(items, dict):
        return None

    item = items.get("item")
    if isinstance(item, list):
        item = item[0] if item else None
    if not isinstance(item, dict):
        return None

    return item


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
