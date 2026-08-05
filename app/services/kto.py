from typing import Any

import httpx

from app.core.config import Settings


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
