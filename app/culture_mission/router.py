"""문화 미션 도메인 라우터.

API 명세: app/culture_mission/docs/API_SPEC.md
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.culture_mission import service
from app.culture_mission.schemas import (
    CultureMissionProgressSaveRequest,
    CultureMissionProgressSaveResponse,
    CultureMissionStartResponse,
)


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


@router.patch(
    "/{culture_mission_progress_id}/progress",
    summary="문화 미션 진행도 저장",
    status_code=status.HTTP_200_OK,
    response_model=CultureMissionProgressSaveResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "진행 중인 문화 미션 진행도를 찾을 수 없음",
            service.CULTURE_MISSION_PROGRESS_NOT_FOUND,
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "제출한 퀴즈 번호가 현재 퀴즈 번호와 다름",
            service.CULTURE_MISSION_QUIZ_INDEX_MISMATCH,
        ),
    },
)
def save_culture_mission_progress(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    culture_mission_progress_id: Annotated[
        int, Path(ge=1, description="저장할 CULTURE_MISSION_PROGRESS.id")
    ],
    request: Annotated[CultureMissionProgressSaveRequest, Body()],
    latitude: Annotated[float, Query(ge=-90, le=90, description="사용자 현재 위치의 위도")],
    longitude: Annotated[float, Query(ge=-180, le=180, description="사용자 현재 위치의 경도")],
) -> CultureMissionProgressSaveResponse:
    """PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress - 문화 미션 진행도 저장."""
    return service.save_culture_mission_progress(
        db=db,
        current_user_id=current_user_id,
        culture_mission_progress_id=culture_mission_progress_id,
        request=request,
        latitude=latitude,
        longitude=longitude,
    )
