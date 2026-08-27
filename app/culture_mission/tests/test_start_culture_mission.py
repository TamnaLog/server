"""POST /api/v1/culture-missions/{cultureMissionId}/progress - 문화 미션 시작/이어하기 테스트.

기준 문서: app/culture_mission/docs/API_SPEC.md, app/culture_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.culture_mission.models import CultureMission, CultureMissionProgress, MissionStatus
from app.mission.models import Mission
from app.treasure_mission.models import ArCharacter
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash


CULTURE_TYPE_ID = 1
CULTURE_MISSION_ID = 12
AR_CHARACTER_ID = 7
CHARACTER_IMG_URL = "https://example.com/characters/stone-spirit.png"

OTHER_USER_ID = 2
OTHER_CULTURE_MISSION_ID = 13


def _endpoint(culture_mission_id: object) -> str:
    return f"/api/v1/culture-missions/{culture_mission_id}/progress"


def _quiz_detail() -> list[dict[str, object]]:
    # quizIndex 오름차순 정렬을 검증하려고 일부러 섞어서 저장한다.
    return [
        {
            "quiz_index": 3,
            "img_url": None,
            "question": "하영은 제주 방언으로 어떤 뜻일까요?",
            "options": None,
            "answer": "많이",
            "hint": "수량이 넉넉하다는 의미로 사용해요.",
            "explanation": "하영은 제주 방언으로 많이라는 뜻입니다.",
        },
        {
            "quiz_index": 1,
            "img_url": "https://example.com/images/quizzes/jeju-dialect-1.jpg",
            "question": "제주어로 할아버지는 무엇일까요?",
            "options": ["하르방", "하라범", "하르봉", "하르범"],
            "answer": "하르방",
            "hint": "제주의 돌하르방을 떠올려 보세요.",
            "explanation": "제주어에서 할아버지를 뜻하는 표현은 하르방입니다.",
        },
        {
            "quiz_index": 2,
            "img_url": None,
            "question": "제주를 배경으로 한 노희경 작가의 드라마는?",
            "options": ["우리들의 블루스", "우도의 봄", "갯마을 차차차", "도깨비"],
            "answer": "우리들의 블루스",
            "hint": "제목에 제주 바다를 연상시키는 색상이 들어가요.",
            "explanation": "우리들의 블루스는 제주를 배경으로 한 드라마입니다.",
        },
    ]


REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": 100,
    "coupon_location": "종화네 막국수",
    "coupon_price": 3000,
}


@pytest.fixture
def culture_mission_data(db_session: Session) -> None:
    """문화 미션 / 사용자 목업 데이터."""
    db_session.add_all(
        [
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name="돌담이",
                character_description="돌담을 지키는 캐릭터입니다.",
                acquire_condition="문화 미션을 완료하면 만날 수 있어요.",
                character_img_url=CHARACTER_IMG_URL,
                hashtags=["#돌담"],
            ),
            Mission(
                id=CULTURE_TYPE_ID,
                mission_type="CULTURE",
                mission_title="제주 문화 퀴즈",
                description="제주의 퀴즈를 맞춰보세요.",
                step_detail=[{"step": 1, "step_title": "퀴즈 풀기", "description": "설명"}],
            ),
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            CultureMission(
                id=CULTURE_MISSION_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=3,
                quiz_detail=_quiz_detail(),
                reward_detail=REWARD_DETAIL,
            ),
            # 사용자/미션 필터를 검증하기 위한 다른 문화 미션
            CultureMission(
                id=OTHER_CULTURE_MISSION_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=3,
                quiz_detail=_quiz_detail(),
                reward_detail={},
            ),
        ]
    )
    db_session.commit()


def _add_progress(
    db_session: Session,
    *,
    progress_id: int,
    status: MissionStatus,
    user_id: int = CURRENT_USER_ID,
    culture_mission_id: int = CULTURE_MISSION_ID,
    current_quiz_index: int = 1,
    correct_number: int = 0,
) -> None:
    db_session.add(
        CultureMissionProgress(
            id=progress_id,
            culture_mission_id=culture_mission_id,
            user_id=user_id,
            mission_status=status.value,
            current_quiz_index=current_quiz_index,
            correct_number=correct_number,
            completed_at=(
                datetime(2026, 8, 20, 12, 0, 0) if status is MissionStatus.COMPLETED else None
            ),
        )
    )
    db_session.commit()


def _progresses(db_session: Session) -> list[CultureMissionProgress]:
    return list(
        db_session.scalars(
            select(CultureMissionProgress)
            .where(
                CultureMissionProgress.user_id == CURRENT_USER_ID,
                CultureMissionProgress.culture_mission_id == CULTURE_MISSION_ID,
            )
            .order_by(CultureMissionProgress.id)
        ).all()
    )


# ---------------------------------------------------------------------
# 응답 형식
# ---------------------------------------------------------------------


def test_문화_미션을_처음_시작하면_명세의_필드를_모두_반환한다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    response = client.post(_endpoint(CULTURE_MISSION_ID))

    assert response.status_code == 201
    body = response.json()

    progresses = _progresses(db_session)
    assert len(progresses) == 1

    assert body == {
        "cultureMissionProgressId": progresses[0].id,
        "quizCount": 3,
        "currentQuizNumber": 1,
        "quizDetails": [
            {
                "quizIndex": 1,
                "imgUrl": "https://example.com/images/quizzes/jeju-dialect-1.jpg",
                "question": "제주어로 할아버지는 무엇일까요?",
                "options": ["하르방", "하라범", "하르봉", "하르범"],
                "answer": "하르방",
                "hint": "제주의 돌하르방을 떠올려 보세요.",
                "explanation": "제주어에서 할아버지를 뜻하는 표현은 하르방입니다.",
            },
            {
                "quizIndex": 2,
                "imgUrl": None,
                "question": "제주를 배경으로 한 노희경 작가의 드라마는?",
                "options": ["우리들의 블루스", "우도의 봄", "갯마을 차차차", "도깨비"],
                "answer": "우리들의 블루스",
                "hint": "제목에 제주 바다를 연상시키는 색상이 들어가요.",
                "explanation": "우리들의 블루스는 제주를 배경으로 한 드라마입니다.",
            },
            {
                "quizIndex": 3,
                "imgUrl": None,
                "question": "하영은 제주 방언으로 어떤 뜻일까요?",
                "options": None,
                "answer": "많이",
                "hint": "수량이 넉넉하다는 의미로 사용해요.",
                "explanation": "하영은 제주 방언으로 많이라는 뜻입니다.",
            },
        ],
    }


def test_문제_목록은_quizIndex_오름차순으로_반환한다(
    client: TestClient, culture_mission_data: None
) -> None:
    # 목업은 3, 1, 2 순서로 저장돼 있다.
    body = client.post(_endpoint(CULTURE_MISSION_ID)).json()

    assert [quiz["quizIndex"] for quiz in body["quizDetails"]] == [1, 2, 3]


# ---------------------------------------------------------------------
# 진행 이력에 따른 분기 (BUSINESS_RULES 3.)
# ---------------------------------------------------------------------


def test_진행_이력이_없으면_진행도를_새로_생성하고_201로_응답한다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    response = client.post(_endpoint(CULTURE_MISSION_ID))

    assert response.status_code == 201
    body = response.json()
    assert body["currentQuizNumber"] == 1

    progresses = _progresses(db_session)
    assert len(progresses) == 1
    saved = progresses[0]
    assert saved.id == body["cultureMissionProgressId"]
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.current_quiz_index == 1
    assert saved.correct_number == 0
    assert saved.completed_at is None


def test_진행_중인_기록이_있으면_새로_만들지_않고_200으로_이어서_반환한다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    _add_progress(
        db_session, progress_id=1, status=MissionStatus.IN_PROGRESS, current_quiz_index=2
    )

    response = client.post(_endpoint(CULTURE_MISSION_ID))

    assert response.status_code == 200
    body = response.json()
    assert body["cultureMissionProgressId"] == 1
    assert body["currentQuizNumber"] == 2
    # 진행도가 새로 생기지 않아야 한다.
    assert len(_progresses(db_session)) == 1


def test_완료_기록과_진행_중_기록이_모두_있으면_200으로_이어서_반환한다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    _add_progress(db_session, progress_id=1, status=MissionStatus.COMPLETED, current_quiz_index=4)
    _add_progress(
        db_session, progress_id=2, status=MissionStatus.IN_PROGRESS, current_quiz_index=3
    )

    response = client.post(_endpoint(CULTURE_MISSION_ID))

    assert response.status_code == 200
    body = response.json()
    assert body["cultureMissionProgressId"] == 2
    assert body["currentQuizNumber"] == 3
    assert len(_progresses(db_session)) == 2


def test_완료_기록만_있으면_재도전_진행도를_새로_만들고_201로_응답한다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    _add_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.COMPLETED,
        current_quiz_index=4,
        correct_number=3,
    )

    response = client.post(_endpoint(CULTURE_MISSION_ID))

    assert response.status_code == 201
    body = response.json()
    assert body["currentQuizNumber"] == 1

    progresses = _progresses(db_session)
    assert len(progresses) == 2

    # 기존 완료 기록은 그대로 남아 있어야 한다.
    completed = progresses[0]
    assert completed.id == 1
    assert completed.mission_status == MissionStatus.COMPLETED.value
    assert completed.current_quiz_index == 4
    assert completed.correct_number == 3

    created = progresses[1]
    assert created.id == body["cultureMissionProgressId"]
    assert created.mission_status == MissionStatus.IN_PROGRESS.value
    assert created.current_quiz_index == 1
    assert created.correct_number == 0


def test_시작_API를_두_번_호출해도_진행도는_하나만_생긴다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    first = client.post(_endpoint(CULTURE_MISSION_ID))
    second = client.post(_endpoint(CULTURE_MISSION_ID))

    assert first.status_code == 201
    assert second.status_code == 200
    assert (
        first.json()["cultureMissionProgressId"] == second.json()["cultureMissionProgressId"]
    )
    assert len(_progresses(db_session)) == 1


# ---------------------------------------------------------------------
# 사용자 / 미션 구분
# ---------------------------------------------------------------------


def test_다른_사용자의_진행도는_이어받지_않는다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    _add_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.IN_PROGRESS,
        user_id=OTHER_USER_ID,
        current_quiz_index=3,
    )

    response = client.post(_endpoint(CULTURE_MISSION_ID))

    assert response.status_code == 201
    assert response.json()["currentQuizNumber"] == 1
    assert response.json()["cultureMissionProgressId"] != 1


def test_다른_문화_미션의_완료_기록은_현재_미션_진행도에_영향을_주지_않는다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    _add_progress(
        db_session,
        progress_id=1,
        status=MissionStatus.COMPLETED,
        culture_mission_id=OTHER_CULTURE_MISSION_ID,
    )

    response = client.post(_endpoint(CULTURE_MISSION_ID))

    assert response.status_code == 201
    # 다른 미션의 기록을 이어받지 않고, 요청한 미션의 진행도를 새로 만든다.
    progresses = _progresses(db_session)
    assert len(progresses) == 1
    assert progresses[0].id == response.json()["cultureMissionProgressId"]


# ---------------------------------------------------------------------
# 오류
# ---------------------------------------------------------------------


def test_문화_미션이_없으면_404_CULTURE_MISSION_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, culture_mission_data: None
) -> None:
    response = client.post(_endpoint(999))

    assert response.status_code == 404
    assert response.json() == {"code": "CULTURE_MISSION_NOT_FOUND"}
    # 진행도를 만들지 않아야 한다.
    assert db_session.scalars(select(CultureMissionProgress)).all() == []


@pytest.mark.parametrize(
    "culture_mission_id",
    [
        pytest.param("abc", id="정수가_아닌_id"),
        pytest.param(0, id="0인_id"),
        pytest.param(-1, id="음수_id"),
    ],
)
def test_잘못된_id면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, culture_mission_data: None, culture_mission_id: object
) -> None:
    response = client.post(_endpoint(culture_mission_id))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
