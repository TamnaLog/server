"""문화 미션 도메인 비즈니스 로직.

기준 문서: app/culture_mission/docs/API_SPEC.md, app/culture_mission/docs/BUSINESS_RULES.md
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import rewards
from app.core.errors import NotFoundError
from app.culture_mission.models import CultureMission, CultureMissionProgress, MissionStatus
from app.culture_mission.schemas import CultureMissionStartResponse, QuizDetailResponse


CULTURE_MISSION_NOT_FOUND = "CULTURE_MISSION_NOT_FOUND"

# 신규 진행도 초기값
FIRST_QUIZ_INDEX = 1
INITIAL_CORRECT_NUMBER = 0


@dataclass(frozen=True)
class StartCultureMissionResult:
    """문화 미션 시작/이어하기 결과.

    응답 본문은 같지만 상태 코드가 달라서(신규 201 / 이어하기 200)
    진행도를 새로 만들었는지를 라우터에 함께 전달한다.
    """

    response: CultureMissionStartResponse
    is_created: bool


def start_culture_mission(
    db: Session, current_user_id: int, culture_mission_id: int
) -> StartCultureMissionResult:
    """문화 미션 시작/이어하기.

    - `IN_PROGRESS` 진행도가 있으면 새로 만들지 않고 그 진행도를 이어서 반환한다.
    - 없으면 새 진행도를 만든다. (최초 시작, 완료한 미션 재도전 모두 포함)
    - `isRewarded` 는 현재 진행도가 아니라 과거 `COMPLETED` 진행도 존재 여부로 정한다.
    """
    culture_mission = _get_culture_mission(db, culture_mission_id)

    is_rewarded = _has_completed_progress(db, current_user_id, culture_mission_id)
    progress = _find_in_progress(db, current_user_id, culture_mission_id)

    is_created = progress is None
    if progress is None:
        progress = _create_progress(db, current_user_id, culture_mission_id)
        db.commit()
        db.refresh(progress)

    return StartCultureMissionResult(
        response=CultureMissionStartResponse(
            culture_mission_progress_id=progress.id,
            quiz_count=culture_mission.quiz_total_count,
            current_quiz_number=progress.current_quiz_index,
            is_rewarded=is_rewarded,
            quiz_details=_to_quiz_details(culture_mission.quiz_detail),
            reward_detail=rewards.to_reward_detail(db, culture_mission.reward_detail),
        ),
        is_created=is_created,
    )


def _get_culture_mission(db: Session, culture_mission_id: int) -> CultureMission:
    """문화 미션을 조회한다. 없으면 진행도를 조회/생성하지 않고 404."""
    culture_mission = db.get(CultureMission, culture_mission_id)
    if culture_mission is None:
        raise NotFoundError(
            CULTURE_MISSION_NOT_FOUND,
            detail=f"문화 미션 {culture_mission_id} 을(를) 찾을 수 없습니다.",
        )
    return culture_mission


def _has_completed_progress(db: Session, current_user_id: int, culture_mission_id: int) -> bool:
    """과거에 이 문화 미션을 완료(=보상 지급)한 기록이 있는지 확인한다."""
    statement = (
        select(CultureMissionProgress.id)
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.culture_mission_id == culture_mission_id,
            CultureMissionProgress.mission_status == MissionStatus.COMPLETED.value,
        )
        .limit(1)
    )
    return db.scalar(statement) is not None


def _find_in_progress(
    db: Session, current_user_id: int, culture_mission_id: int
) -> CultureMissionProgress | None:
    """이어서 진행할 `IN_PROGRESS` 진행도를 찾는다.

    같은 사용자/미션에 `IN_PROGRESS` 진행도는 최대 하나만 있어야 하지만,
    데이터가 여러 건이어도 결과가 흔들리지 않도록 가장 먼저 만든 진행도를 사용한다.
    """
    statement = (
        select(CultureMissionProgress)
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.culture_mission_id == culture_mission_id,
            CultureMissionProgress.mission_status == MissionStatus.IN_PROGRESS.value,
        )
        .order_by(CultureMissionProgress.id)
    )
    return db.scalars(statement).first()


def _create_progress(
    db: Session, current_user_id: int, culture_mission_id: int
) -> CultureMissionProgress:
    """새 진행도를 만든다. 기존 `COMPLETED` 기록은 그대로 둔다."""
    progress = CultureMissionProgress(
        culture_mission_id=culture_mission_id,
        user_id=current_user_id,
        mission_status=MissionStatus.IN_PROGRESS.value,
        current_quiz_index=FIRST_QUIZ_INDEX,
        correct_number=INITIAL_CORRECT_NUMBER,
        completed_at=None,
    )
    db.add(progress)
    return progress


def _to_quiz_details(quiz_detail: list[dict[str, Any]] | None) -> list[QuizDetailResponse]:
    """문제 목록을 `quizIndex` 오름차순으로 반환한다."""
    quizzes = sorted(quiz_detail or [], key=lambda quiz: quiz["quiz_index"])
    return [
        QuizDetailResponse(
            quiz_index=quiz["quiz_index"],
            img_url=quiz.get("img_url"),
            question=quiz["question"],
            options=quiz.get("options"),
            answer=quiz["answer"],
            hint=quiz["hint"],
            explanation=quiz["explanation"],
        )
        for quiz in quizzes
    ]
