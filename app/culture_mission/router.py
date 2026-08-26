"""문화 미션 도메인 라우터.

API 명세: app/culture_mission/docs/API_SPEC.md
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.culture_mission import service
from app.culture_mission.schemas import CultureMissionStartResponse


router = APIRouter(prefix="/api/v1/culture-missions", tags=["culture-mission"])


def _error_response(description: str, code: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                "example": {"code": code},
            }
        },
    }


@router.post(
    "/{culture_mission_id}/progress",
    summary="문화 미션 시작/이어하기",
    # 진행도를 새로 만든 경우가 기본이고, 이어서 하는 경우에만 200으로 바꾼다.
    status_code=status.HTTP_201_CREATED,
    response_model=CultureMissionStartResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_200_OK: {
            "description": "이미 진행 중인 문화 미션을 이어서 하는 경우",
            "model": CultureMissionStartResponse,
        },
        status.HTTP_404_NOT_FOUND: _error_response(
            "문화 미션을 찾을 수 없음", service.CULTURE_MISSION_NOT_FOUND
        ),
    },
)
def start_culture_mission(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    culture_mission_id: Annotated[
        int, Path(ge=1, description="진행도를 생성하거나 조회할 CULTURE_MISSION.id")
    ],
) -> CultureMissionStartResponse:
    """POST /api/v1/culture-missions/{cultureMissionId}/progress - 문화 미션 시작/이어하기."""
    result = service.start_culture_mission(
        db=db, current_user_id=current_user_id, culture_mission_id=culture_mission_id
    )
    if not result.is_created:
        response.status_code = status.HTTP_200_OK
    return result.response
