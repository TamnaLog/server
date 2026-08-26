"""문화 미션 도메인 비즈니스 로직.

기준 문서: app/culture_mission/docs/API_SPEC.md, app/culture_mission/docs/BUSINESS_RULES.md
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import next_location
from app.common.datetimes import now_kst
from app.common.next_location import NextLocationResponse
from app.core.errors import ConflictError, NotFoundError
from app.culture_mission import reward_granter
from app.culture_mission.models import CultureMission, CultureMissionProgress, MissionStatus
from app.culture_mission.schemas import (
    CultureMissionProgressSaveRequest,
    CultureMissionProgressSaveResponse,
    CultureMissionStartResponse,
    QuizDetailResponse,
)


CULTURE_MISSION_NOT_FOUND = "CULTURE_MISSION_NOT_FOUND"
CULTURE_MISSION_PROGRESS_NOT_FOUND = "CULTURE_MISSION_PROGRESS_NOT_FOUND"
CULTURE_MISSION_QUIZ_INDEX_MISMATCH = "CULTURE_MISSION_QUIZ_INDEX_MISMATCH"

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
    """
    culture_mission = _get_culture_mission(db, culture_mission_id)

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
            quiz_details=_to_quiz_details(culture_mission.quiz_detail),
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


# ---------------------------------------------------------------------
# 진행도 저장
# ---------------------------------------------------------------------


def save_culture_mission_progress(
    db: Session,
    current_user_id: int,
    culture_mission_progress_id: int,
    request: CultureMissionProgressSaveRequest,
    latitude: float,
    longitude: float,
) -> CultureMissionProgressSaveResponse:
    """문화 미션 진행도 저장.

    - 제출한 퀴즈 번호가 진행도의 현재 퀴즈 번호와 다르면 아무것도 바꾸지 않고 409.
    - 마지막 퀴즈가 아니면 퀴즈 번호를 1 올리고 `IN_PROGRESS` 를 유지한다.
    - 마지막 퀴즈면 퀴즈 번호를 올리지 않고 `COMPLETED` 로 바꾼 뒤
      정답 수만큼 보상을 지급하고 다음 장소를 추천한다.

    보상 지급과 완료 처리는 같은 트랜잭션으로 커밋한다.
    """
    progress = _get_in_progress_by_id(db, current_user_id, culture_mission_progress_id)
    culture_mission = _get_culture_mission(db, progress.culture_mission_id)

    if request.quiz_index != progress.current_quiz_index:
        raise ConflictError(
            CULTURE_MISSION_QUIZ_INDEX_MISMATCH,
            detail=(
                f"제출한 퀴즈 번호 {request.quiz_index} 가 "
                f"현재 퀴즈 번호 {progress.current_quiz_index} 와 다릅니다."
            ),
        )

    if request.is_correct:
        progress.correct_number += 1

    is_last_quiz = progress.current_quiz_index >= culture_mission.quiz_total_count
    if is_last_quiz:
        # 마지막 퀴즈는 번호를 올리지 않고 그대로 두고 완료 처리한다.
        progress.mission_status = MissionStatus.COMPLETED.value
        progress.completed_at = now_kst()
        # 정답 수 반영 이후에 지급해야 이번 요청의 정답까지 보상 개수에 들어간다.
        reward = reward_granter.grant_culture_mission_reward(db, progress, culture_mission)
        recommended_location = _recommend_next_location(db, latitude, longitude)
    else:
        progress.current_quiz_index += 1
        reward = None
        recommended_location = None

    db.commit()
    db.refresh(progress)

    return CultureMissionProgressSaveResponse(
        mission_progress_status=MissionStatus(progress.mission_status),
        quiz_count=culture_mission.quiz_total_count,
        current_quiz_number=progress.current_quiz_index,
        correct_number=progress.correct_number,
        next_location=recommended_location,
        reward=reward,
    )


def _recommend_next_location(
    db: Session, latitude: float, longitude: float
) -> NextLocationResponse:
    """완료 응답에 넣을 다음 장소를 추천한다.

    완료 응답의 `nextLocation` 은 반드시 객체여야 하므로, 추천할 장소 데이터가 하나도 없으면
    정상 완료로 처리하지 않고 예외를 발생시킨다. (공통 처리기가 500 으로 응답)
    """
    recommended = next_location.recommend_next_location(db, latitude, longitude)
    if recommended is None:
        raise RuntimeError("추천할 수 있는 장소 데이터가 없어 미션 완료 응답을 만들 수 없습니다.")
    return recommended


def _get_in_progress_by_id(
    db: Session, current_user_id: int, culture_mission_progress_id: int
) -> CultureMissionProgress:
    """현재 사용자의 진행 중인 진행도를 조회한다.

    다른 사용자의 진행도이거나 이미 완료된 진행도면 갱신 대상이 아니므로 404로 처리한다.
    (완료 요청이 중복으로 들어와도 정답 수가 다시 반영되지 않는다)
    """
    progress = db.get(CultureMissionProgress, culture_mission_progress_id)
    if (
        progress is None
        or progress.user_id != current_user_id
        or progress.mission_status != MissionStatus.IN_PROGRESS.value
    ):
        raise NotFoundError(
            CULTURE_MISSION_PROGRESS_NOT_FOUND,
            detail=(
                f"사용자 {current_user_id} 의 진행 중인 문화 미션 진행도 "
                f"{culture_mission_progress_id} 을(를) 찾을 수 없습니다."
            ),
        )
    return progress
