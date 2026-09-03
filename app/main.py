from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.auth.router import router as auth_router
from app.cooperative_mission.router import router as cooperative_mission_router
from app.core.config import Settings, get_settings
from app.core.database import get_db, ping_database
from app.core.errors import register_exception_handlers, use_common_error_responses
from app.culture_mission.router import router as culture_mission_router
from app.guestbook.router import router as guestbook_router
from app.home.router import router as home_router
from app.map.router import router as map_router
from app.mission.router import router as mission_router
from app.mypage.router import router as mypage_router
from app.onboarding.router import router as onboarding_router
from app.others.router import router as others_router
from app.services.kto import KtoClient
from app.treasure_mission.router import router as treasure_mission_router


ROUTERS = (
    auth_router,
    home_router,
    onboarding_router,
    map_router,
    mission_router,
    culture_mission_router,
    cooperative_mission_router,
    treasure_mission_router,
    guestbook_router,
    mypage_router,
    others_router,
)


def create_app() -> FastAPI:
    settings = get_settings()
    # debug=True 이면 500 응답이 traceback 으로 나가서 공통 에러 형식이 깨진다.
    # traceback 은 서버 로그로 출력되므로 응답 형식은 환경과 무관하게 통일한다.
    app = FastAPI(
        title=settings.app_name,
        debug=False,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    for domain_router in ROUTERS:
        app.include_router(domain_router)

    # 라우터 등록 후에 호출해야 모든 API 문서에 공통 에러 응답이 반영된다.
    use_common_error_responses(app)

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
