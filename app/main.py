from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.cooperative_mission.router import router as cooperative_mission_router
from app.core.config import Settings, get_settings
from app.core.database import get_db, ping_database
from app.culture_mission.router import router as culture_mission_router
from app.guestbook.router import router as guestbook_router
from app.home.router import router as home_router
from app.map.router import router as map_router
from app.mission.router import router as mission_router
from app.mypage.router import router as mypage_router
from app.onboarding.router import router as onboarding_router
from app.services.kto import KtoClient
from app.treasure_mission.router import router as treasure_mission_router


ROUTERS = (
    home_router,
    onboarding_router,
    map_router,
    mission_router,
    culture_mission_router,
    cooperative_mission_router,
    treasure_mission_router,
    guestbook_router,
    mypage_router,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for domain_router in ROUTERS:
        app.include_router(domain_router)

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
