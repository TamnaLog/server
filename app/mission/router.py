"""미션 도메인 라우터.

API 명세: app/mission/docs/API_SPEC.md
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.mission import service
from app.mission.schemas import MissionHomeResponse, MissionType


router = APIRouter(prefix="/api/v1/missions", tags=["mission"])


@router.get(
    "/{mission_type}/{mission_id}",
    summary="미션 홈 조회",
    status_code=status.HTTP_200_OK,
    response_model=MissionHomeResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "미션을 찾을 수 없음",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "example": {"code": service.MISSION_NOT_FOUND},
                }
            },
        }
    },
)
def get_mission_home(
    db: Annotated[Session, Depends(get_db)],
    mission_type: Annotated[MissionType, Path(description="조회할 미션 유형")],
    mission_id: Annotated[
        int, Path(ge=1, description="missionType에 해당하는 유형별 세부 미션 id")
    ],
) -> MissionHomeResponse:
    """GET /api/v1/missions/{missionType}/{missionId} - 미션 홈 조회."""
    return service.get_mission_home(db=db, mission_type=mission_type, mission_id=mission_id)
