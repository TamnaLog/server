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
        "contentId": content_id,
    }

    try:
        with httpx.Client(base_url=settings.kto_base_url, timeout=5.0) as client:
            response = client.get("/detailCommon2", params=params)
            response.encoding = "utf-8"
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    return _first_image_url(body)


def _first_image_url(body: dict[str, Any]) -> str | None:
    """TourAPI 응답에서 대표 이미지 URL 을 꺼낸다. 형식이 다르면 `None`."""
    items = body.get("response", {}).get("body", {}).get("items")
    if not isinstance(items, dict):
        return None

    item = items.get("item")
    if isinstance(item, list):
        item = item[0] if item else None
    if not isinstance(item, dict):
        return None

    return item.get("firstimage") or item.get("firstimage2") or None
