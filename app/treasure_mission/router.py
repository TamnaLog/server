"""보물 찾기 도메인 라우터.

노션 API 명세서 기준. 엔드포인트/HTTP 메서드/API 명은 확정값이며,
요청/응답 스키마는 아직 확정 전이라 TODO로 남겨둔다.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.treasure_mission import service


router = APIRouter(prefix="/api/v1/treasure-missions", tags=["treasure-mission"])


@router.post("/pictures-with-character", summary="ar 캐릭터와 사진 저장")
def save_picture_with_character(db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/treasure-missions/pictures-with-character - ar 캐릭터와 사진 저장."""
    # TODO: 요청/응답 스키마 연결 (app/treasure_mission/schemas.py)
    return service.save_picture_with_character(db)


@router.post("/{mission_id}/progress", summary="보물 찾기 시작/이어하기")
def start_treasure_mission(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """POST /api/v1/treasure-missions/{missionId}/progress - 보물 찾기 시작/이어하기."""
    # TODO: 요청/응답 스키마 연결 (app/treasure_mission/schemas.py)
    return service.start_treasure_mission(mission_id, db)


@router.patch("/{mission_id}/progress", summary="보물 찾기 진행도 저장")
def save_treasure_mission_progress(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/treasure-missions/{missionId}/progress - 보물 찾기 진행도 저장."""
    # TODO: 요청/응답 스키마 연결 (app/treasure_mission/schemas.py)
    return service.save_treasure_mission_progress(mission_id, db)


@router.patch("/{mission_id}/progress/stop", summary="보물 찾기 중단")
def stop_treasure_mission(mission_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """PATCH /api/v1/treasure-missions/{missionId}/progress/stop - 보물 찾기 중단."""
    # TODO: 요청/응답 스키마 연결 (app/treasure_mission/schemas.py)
    return service.stop_treasure_mission(mission_id, db)
