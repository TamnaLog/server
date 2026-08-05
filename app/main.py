from typing import Any

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db, ping_database
from app.services.kto import KtoClient


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "jamkkan-jeju-api is running"}

    @app.get("/health")
    def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
        return {
            "status": "ok",
            "environment": settings.environment,
        }

    @app.get("/health/db")
    def health_db(_: Session = Depends(get_db)) -> dict[str, str]:
        ping_database()
        return {"status": "ok"}

    @app.get("/external/kto/area-codes")
    async def kto_area_codes(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
        return await KtoClient(settings).get_area_codes()

    return app


app = create_app()
