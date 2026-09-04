"""보물 찾기 도메인 라우터.

API 명세: app/treasure_mission/docs/API_SPEC.md
"""

from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Path,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.treasure_mission import service
from app.treasure_mission.schemas import (
    MissionType,
    PictureWithCharacterSaveRequest,
    TreasureMissionCompletionResponse,
    TreasureMissionProgressSaveRequest,
    TreasureMissionProgressSaveResponse,
    TreasureMissionStartResponse,
    TreasureMissionStopResponse,
)


router = APIRouter(prefix="/api/v1/treasure-missions", tags=["treasure-mission"])

# 완료 화면만 미션 공통 경로(`/api/v1/missions/...`)를 쓰는 명세라 라우터를 따로 둔다.
# (조합하는 데이터는 보물찾기 도메인 것이라 서비스는 이 도메인에 있다)
completion_router = APIRouter(prefix="/api/v1/missions", tags=["treasure-mission"])


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
    "/{treasure_mission_id}/progress",
    summary="보물찾기 시작/이어하기",
    # 진행도를 새로 만든 경우가 기본이고, 이어서 하는 경우에만 200으로 바꾼다.
    status_code=status.HTTP_201_CREATED,
    response_model=TreasureMissionStartResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_200_OK: {
            "description": "이미 진행 중인 보물찾기 미션을 이어서 하는 경우",
            "model": TreasureMissionStartResponse,
        },
        status.HTTP_404_NOT_FOUND: _error_response(
            "보물찾기 미션을 찾을 수 없음", service.TREASURE_MISSION_NOT_FOUND
        ),
    },
)
def start_treasure_mission(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    treasure_mission_id: Annotated[
        int, Path(ge=1, description="진행도를 생성하거나 조회할 TREASURE_MISSION.id")
    ],
    latitude: Annotated[float, Query(ge=-90, le=90, description="사용자 현재 위치의 위도")],
    longitude: Annotated[float, Query(ge=-180, le=180, description="사용자 현재 위치의 경도")],
) -> TreasureMissionStartResponse:
    """POST /api/v1/treasure-missions/{treasureMissionId}/progress - 보물찾기 시작/이어하기."""
    result = service.start_treasure_mission(
        db=db,
        current_user_id=current_user_id,
        treasure_mission_id=treasure_mission_id,
        latitude=latitude,
        longitude=longitude,
    )
    if not result.is_created:
        response.status_code = status.HTTP_200_OK
    return result.response


@router.post(
    "/pictures-with-character",
    summary="ar 캐릭터와 사진 저장",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def save_picture_with_character(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    # File() 로 선언해야 Swagger 문서에도 multipart/form-data 로 나온다.
    request: Annotated[PictureWithCharacterSaveRequest, File()],
) -> None:
    """POST /api/v1/treasure-missions/pictures-with-character - ar 캐릭터와 사진 저장."""
    # UploadFile.file 은 동기 파일 객체라, DB 세션과 같은 동기 흐름에서 그대로 읽을 수 있다.
    service.save_picture_with_character(
        db=db,
        current_user_id=current_user_id,
        picture=request.picture.file,
        taken_at=request.taken_at,
    )


@router.patch(
    "/{treasure_mission_progress_id}/progress",
    summary="보물찾기 진행도 저장",
    status_code=status.HTTP_200_OK,
    response_model=TreasureMissionProgressSaveResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "진행 중인 진행도 또는 요청한 보물을 찾을 수 없음",
            f"{service.TREASURE_MISSION_PROGRESS_NOT_FOUND} | {service.TREASURE_ITEM_NOT_FOUND}",
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "이미 찾은 보물", service.TREASURE_ITEM_ALREADY_FOUND
        ),
    },
)
def save_treasure_mission_progress(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    treasure_mission_progress_id: Annotated[
        int, Path(ge=1, description="저장할 TREASURE_MISSION_PROGRESS.id")
    ],
    request: Annotated[TreasureMissionProgressSaveRequest, Body()],
    latitude: Annotated[float, Query(ge=-90, le=90, description="사용자 현재 위치의 위도")],
    longitude: Annotated[float, Query(ge=-180, le=180, description="사용자 현재 위치의 경도")],
) -> TreasureMissionProgressSaveResponse:
    """PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress - 보물찾기 진행도 저장."""
    return service.save_treasure_mission_progress(
        db=db,
        current_user_id=current_user_id,
        treasure_mission_progress_id=treasure_mission_progress_id,
        request=request,
        latitude=latitude,
        longitude=longitude,
    )


@router.patch(
    "/{treasure_mission_progress_id}/progress/stop",
    summary="보물찾기 중단",
    status_code=status.HTTP_200_OK,
    response_model=TreasureMissionStopResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "진행 중인 보물찾기 진행도를 찾을 수 없음",
            service.TREASURE_MISSION_PROGRESS_NOT_FOUND,
        ),
    },
)
def stop_treasure_mission(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    treasure_mission_progress_id: Annotated[
        int, Path(ge=1, description="중단할 TREASURE_MISSION_PROGRESS.id")
    ],
    latitude: Annotated[float, Query(ge=-90, le=90, description="사용자 현재 위치의 위도")],
    longitude: Annotated[float, Query(ge=-180, le=180, description="사용자 현재 위치의 경도")],
) -> TreasureMissionStopResponse:
    """PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress/stop - 보물찾기 중단."""
    return service.stop_treasure_mission(
        db=db,
        current_user_id=current_user_id,
        treasure_mission_progress_id=treasure_mission_progress_id,
        latitude=latitude,
        longitude=longitude,
    )


@completion_router.get(
    "/{mission_type}/{mission_id}/completion",
    summary="완료한 보물찾기 추천 화면",
    status_code=status.HTTP_200_OK,
    response_model=TreasureMissionCompletionResponse,
    response_model_by_alias=True,
    responses={
        status.HTTP_404_NOT_FOUND: _error_response(
            "보물찾기 미션 또는 현재 사용자의 완료 진행도를 찾을 수 없음",
            service.TREASURE_MISSION_NOT_FOUND,
        ),
        status.HTTP_409_CONFLICT: _error_response(
            "아직 찾지 않은 보물이 남아 있음", service.TREASURE_ITEMS_REMAINING
        ),
    },
)
def get_treasure_mission_completion(
    db: Annotated[Session, Depends(get_db)],
    current_user_id: Annotated[int, Depends(get_current_user_id)],
    mission_type: Annotated[
        MissionType, Path(description="조회할 미션 유형. 이 API 는 TREASURE 만 허용")
    ],
    mission_id: Annotated[int, Path(ge=1, description="완료한 TREASURE_MISSION.id")],
    latitude: Annotated[float, Query(ge=-90, le=90, description="사용자 현재 위치의 위도")],
    longitude: Annotated[float, Query(ge=-180, le=180, description="사용자 현재 위치의 경도")],
) -> TreasureMissionCompletionResponse:
    """GET /api/v1/missions/{missionType}/{missionId}/completion - 완료한 보물찾기 추천 화면."""
    return service.get_treasure_mission_completion(
        db=db,
        current_user_id=current_user_id,
        mission_type=mission_type,
        treasure_mission_id=mission_id,
        latitude=latitude,
        longitude=longitude,
    )
