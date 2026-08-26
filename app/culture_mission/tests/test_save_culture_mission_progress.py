"""PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress - 문화 미션 진행도 저장 테스트.

기준 문서: app/culture_mission/docs/API_SPEC.md, app/culture_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import distance, next_location
from app.cooperative_mission.models import CooperativeMission
from app.core.deps import CURRENT_USER_ID
from app.culture_mission.models import CultureMission, CultureMissionProgress, MissionStatus
from app.map.models import Location
from app.mission.models import Mission
from app.treasure_mission.models import AcquiredArCharacter, ArCharacter, TreasureMission
from app.user.models import User


CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2

CULTURE_MISSION_ID = 12
QUIZ_TOTAL_COUNT = 3

PROGRESS_ID = 31
OTHER_USER_ID = 2

LOCATION_ID = 5
COOPERATIVE_MISSION_ID = 41

USER_LATITUDE = 33.4996
USER_LONGITUDE = 126.5312

LOCATION_IMAGE_URL = "https://example.com/locations/handam.jpg"

AR_CHARACTER_ID = 7
OTHER_AR_CHARACTER_ID = 8
REWARD_POINT = 100
INITIAL_USER_POINT = 30

# 완료 시 지급할 보상. 쿠폰은 저장할 테이블이 없어 기록되지 않는다.
REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": REWARD_POINT,
    "coupon_location": "종화네 막국수",
    "coupon_price": 3000,
}


def _endpoint(progress_id: object) -> str:
    return f"/api/v1/culture-missions/{progress_id}/progress"


def _params() -> dict[str, float]:
    return {"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE}


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """장소 이미지 조회(TourAPI)를 막는다.

    실제 인증키가 설정돼 있으면 테스트가 외부 네트워크를 타서 느려지고 결과도 흔들린다.
    """
    monkeypatch.setattr(
        next_location, "get_location_image_url", lambda content_id: LOCATION_IMAGE_URL
    )


@pytest.fixture
def progress_data(db_session: Session) -> None:
    """문화 미션 / 진행 중 진행도 / 다음 장소 후보 목업 데이터."""
    db_session.add_all(
        [
            Mission(
                id=CULTURE_TYPE_ID,
                mission_type="CULTURE",
                mission_title="제주 문화 퀴즈",
                description="제주의 퀴즈를 맞춰보세요.",
                step_detail=[{"step": 1, "step_title": "퀴즈 풀기", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="일행과 역할을 나눠보세요.",
                step_detail=[{"step": 1, "step_title": "초대", "description": "설명"}],
            ),
            User(id=CURRENT_USER_ID, nickname="몽글몽글파도", point=INITIAL_USER_POINT),
            User(id=OTHER_USER_ID, nickname="한라봉주스", point=0),
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name="돌담이",
                character_description="돌담을 지키는 캐릭터입니다.",
                acquire_condition="문화 미션을 완료하면 만날 수 있어요.",
                character_img_url="https://example.com/characters/stone-spirit.png",
                hashtags=["#돌담"],
            ),
            ArCharacter(
                id=OTHER_AR_CHARACTER_ID,
                character_name="용암이",
                character_description="다른 미션 보상 캐릭터입니다.",
                acquire_condition="다른 미션을 완료하면 만날 수 있어요.",
                character_img_url="https://example.com/characters/yongami.png",
                hashtags=["#용암"],
            ),
            Location(
                id=LOCATION_ID,
                content_id=2686931,
                location_title="한담해안산책로",
                location_address="제주특별자치도 제주시 애월읍 애월리 2530",
                location_category="산책로",
                radius=300,
                mx=126.3760,
                my=33.4620,
            ),
        ]
    )
    db_session.flush()

    db_session.add(
        CultureMission(
            id=CULTURE_MISSION_ID,
            mission_id=CULTURE_TYPE_ID,
            quiz_total_count=QUIZ_TOTAL_COUNT,
            quiz_detail=[],
            reward_detail=REWARD_DETAIL,
        )
    )
    db_session.commit()


def _add_progress(
    db_session: Session,
    *,
    current_quiz_index: int,
    correct_number: int = 0,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
    user_id: int = CURRENT_USER_ID,
    progress_id: int = PROGRESS_ID,
) -> None:
    db_session.add(
        CultureMissionProgress(
            id=progress_id,
            culture_mission_id=CULTURE_MISSION_ID,
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


def _saved(db_session: Session) -> CultureMissionProgress:
    db_session.expire_all()
    progress = db_session.get(CultureMissionProgress, PROGRESS_ID)
    assert progress is not None
    return progress


# ---------------------------------------------------------------------
# 진행 중 처리 (BUSINESS_RULES 5.1)
# ---------------------------------------------------------------------


def test_마지막_퀴즈가_아니면_퀴즈_번호를_1_올리고_진행_중을_유지한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=1, correct_number=0)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"quizIndex": 1, "isCorrect": True}
    )

    assert response.status_code == 200
    assert response.json() == {
        "missionProgressStatus": "IN_PROGRESS",
        "quizCount": QUIZ_TOTAL_COUNT,
        "currentQuizNumber": 2,
        "correctNumber": 1,
        "nextLocation": None,
    }

    saved = _saved(db_session)
    assert saved.current_quiz_index == 2
    assert saved.correct_number == 1
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.completed_at is None


def test_오답이면_정답_수를_올리지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=2, correct_number=1)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"quizIndex": 2, "isCorrect": False}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correctNumber"] == 1
    assert body["currentQuizNumber"] == 3
    assert _saved(db_session).correct_number == 1


# ---------------------------------------------------------------------
# 완료 처리 (BUSINESS_RULES 5.2)
# ---------------------------------------------------------------------


def test_마지막_퀴즈를_제출하면_번호를_올리지_않고_완료로_바꾼다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT, correct_number=2)

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["missionProgressStatus"] == "COMPLETED"
    # 마지막 퀴즈는 번호를 올리지 않고 그대로 반환한다.
    assert body["currentQuizNumber"] == QUIZ_TOTAL_COUNT
    assert body["correctNumber"] == 3

    saved = _saved(db_session)
    assert saved.mission_status == MissionStatus.COMPLETED.value
    assert saved.current_quiz_index == QUIZ_TOTAL_COUNT
    assert saved.correct_number == 3
    assert saved.completed_at is not None


def test_완료하면_다음_장소를_거리와_함께_추천한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": False},
    )

    recommended = response.json()["nextLocation"]
    assert recommended is not None

    saved_location = db_session.get(Location, LOCATION_ID)
    assert saved_location is not None

    assert recommended["id"] == LOCATION_ID
    assert recommended["locationTitle"] == "한담해안산책로"
    assert recommended["locationImageUrl"] == LOCATION_IMAGE_URL
    # LOCATION 은 my=위도 / mx=경도로 저장한다.
    assert recommended["distanceMeter"] == distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, saved_location.my, saved_location.mx
    )
    # 장소에 연결된 세부 미션이 없으면 mission 은 null 이다.
    assert recommended["mission"] is None


def test_다음_장소에_연결된_미션이_있으면_유형과_세부_미션_id를_반환한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    db_session.add(
        CooperativeMission(
            id=COOPERATIVE_MISSION_ID,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=LOCATION_ID,
            role_total_count=4,
            reward_detail={},
        )
    )
    db_session.commit()
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )

    mission = response.json()["nextLocation"]["mission"]
    # 공통 MISSION.id 가 아니라 세부 미션 id 여야 한다.
    assert mission == {"id": COOPERATIVE_MISSION_ID, "missionType": "COOPERATIVE"}
    assert mission["id"] != COOPERATIVE_TYPE_ID


def test_추천할_장소가_없으면_nextLocation은_null이다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    db_session.query(Location).delete()
    db_session.commit()
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )

    assert response.status_code == 200
    assert response.json()["nextLocation"] is None


def test_장소_이미지를_조회하지_못하면_locationImageUrl은_null이다(
    client: TestClient,
    db_session: Session,
    progress_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        next_location, "get_location_image_url", lambda content_id: None
    )
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )

    assert response.json()["nextLocation"]["locationImageUrl"] is None


def test_추천되는_미션은_해당_장소에_연결된_미션_중_하나다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 추천이 랜덤이므로 값 자체가 아니라 DB에 있는 연결 미션인지로 검증한다.
    db_session.add_all(
        [
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=LOCATION_ID,
                role_total_count=4,
                reward_detail={},
            ),
            TreasureMission(
                id=51,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=LOCATION_ID,
                item_total_count=3,
                item_detail=[],
                reward_detail={},
            ),
        ]
    )
    db_session.commit()
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )

    mission = response.json()["nextLocation"]["mission"]
    assert (mission["missionType"], mission["id"]) in {
        ("COOPERATIVE", COOPERATIVE_MISSION_ID),
        ("TREASURE", 51),
    }


# ---------------------------------------------------------------------
# 보상 지급 (완료 시에만 / 중복 지급 금지)
# ---------------------------------------------------------------------


def _user_point(db_session: Session) -> int:
    db_session.expire_all()
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    return user.point


def _acquired(db_session: Session) -> list[AcquiredArCharacter]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(AcquiredArCharacter).where(AcquiredArCharacter.user_id == CURRENT_USER_ID)
        ).all()
    )


def _complete(client: TestClient) -> None:
    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )
    assert response.status_code == 200


def test_미션을_완료하면_포인트와_획득_캐릭터를_저장한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    _complete(client)

    assert _user_point(db_session) == INITIAL_USER_POINT + REWARD_POINT

    acquired = _acquired(db_session)
    assert len(acquired) == 1
    assert acquired[0].ar_character_id == AR_CHARACTER_ID
    # 획득 기록에는 세부 미션 id가 아니라 공통 MISSION.id 를 남긴다.
    assert acquired[0].acquired_mission_id == CULTURE_TYPE_ID


def test_진행_중이면_보상을_지급하지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=1)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"quizIndex": 1, "isCorrect": True}
    )

    assert response.status_code == 200
    assert _user_point(db_session) == INITIAL_USER_POINT
    assert _acquired(db_session) == []


def test_이미_완료한_적_있는_미션을_재도전해_완료해도_보상을_다시_주지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 과거 완료 기록 + 재도전 진행도
    _add_progress(
        db_session,
        progress_id=1,
        current_quiz_index=QUIZ_TOTAL_COUNT,
        status=MissionStatus.COMPLETED,
    )
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    _complete(client)

    assert _user_point(db_session) == INITIAL_USER_POINT
    assert _acquired(db_session) == []


def test_다른_미션에서_이미_획득한_캐릭터는_기록을_또_남기지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 같은 캐릭터를 다른 미션 보상으로 이미 획득한 상태
    db_session.add(
        AcquiredArCharacter(
            ar_character_id=AR_CHARACTER_ID,
            user_id=CURRENT_USER_ID,
            acquired_mission_id=COOPERATIVE_TYPE_ID,
        )
    )
    db_session.commit()
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    _complete(client)

    # 캐릭터 기록은 그대로 1건이지만 포인트는 정상 지급된다.
    assert len(_acquired(db_session)) == 1
    assert _user_point(db_session) == INITIAL_USER_POINT + REWARD_POINT


def test_보상이_없는_미션은_아무것도_지급하지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    culture_mission = db_session.get(CultureMission, CULTURE_MISSION_ID)
    assert culture_mission is not None
    culture_mission.reward_detail = {}
    db_session.commit()
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    _complete(client)

    assert _user_point(db_session) == INITIAL_USER_POINT
    assert _acquired(db_session) == []


def test_쿠폰만_있는_보상은_저장할_곳이_없어_기록되지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    culture_mission = db_session.get(CultureMission, CULTURE_MISSION_ID)
    assert culture_mission is not None
    culture_mission.reward_detail = {"coupon_location": "종화네 막국수", "coupon_price": 3000}
    db_session.commit()
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    _complete(client)

    assert _user_point(db_session) == INITIAL_USER_POINT
    assert _acquired(db_session) == []


def test_보상_지급에_실패하면_완료_처리도_저장되지_않는다(
    client: TestClient, db_session: Session, progress_data: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 완료 처리와 보상 지급은 한 트랜잭션이어야 한다.
    from app.culture_mission import service

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("보상 지급 실패")

    monkeypatch.setattr(service.reward_granter, "grant_mission_reward", boom)
    _add_progress(db_session, current_quiz_index=QUIZ_TOTAL_COUNT)

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )

    assert response.status_code == 500
    saved = _saved(db_session)
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.completed_at is None
    assert _user_point(db_session) == INITIAL_USER_POINT


# ---------------------------------------------------------------------
# 409 퀴즈 번호 불일치
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "quiz_index",
    [pytest.param(1, id="이전_퀴즈_번호"), pytest.param(3, id="다음_퀴즈_번호")],
)
def test_퀴즈_번호가_다르면_409로_응답하고_아무것도_바꾸지_않는다(
    client: TestClient, db_session: Session, progress_data: None, quiz_index: int
) -> None:
    _add_progress(db_session, current_quiz_index=2, correct_number=1)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"quizIndex": quiz_index, "isCorrect": True}
    )

    assert response.status_code == 409
    assert response.json() == {"code": "CULTURE_MISSION_QUIZ_INDEX_MISMATCH"}

    saved = _saved(db_session)
    assert saved.current_quiz_index == 2
    assert saved.correct_number == 1
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value


# ---------------------------------------------------------------------
# 404 진행도를 사용할 수 없음
# ---------------------------------------------------------------------


def test_진행도가_없으면_404로_응답한다(
    client: TestClient, progress_data: None
) -> None:
    response = client.patch(
        _endpoint(999), params=_params(), json={"quizIndex": 1, "isCorrect": True}
    )

    assert response.status_code == 404
    assert response.json() == {"code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"}


def test_다른_사용자의_진행도면_404로_응답하고_바꾸지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=1, user_id=OTHER_USER_ID)

    response = client.patch(
        _endpoint(PROGRESS_ID), params=_params(), json={"quizIndex": 1, "isCorrect": True}
    )

    assert response.status_code == 404
    assert response.json() == {"code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"}
    assert _saved(db_session).current_quiz_index == 1


def test_이미_완료된_진행도면_404로_응답하고_정답_수를_다시_반영하지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 완료 응답을 못 받아 같은 요청이 다시 들어와도 중복 반영되면 안 된다.
    _add_progress(
        db_session,
        current_quiz_index=QUIZ_TOTAL_COUNT,
        correct_number=3,
        status=MissionStatus.COMPLETED,
    )

    response = client.patch(
        _endpoint(PROGRESS_ID),
        params=_params(),
        json={"quizIndex": QUIZ_TOTAL_COUNT, "isCorrect": True},
    )

    assert response.status_code == 404
    assert response.json() == {"code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"}
    assert _saved(db_session).correct_number == 3


# ---------------------------------------------------------------------
# 400 잘못된 요청
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("progress_id", "params", "body"),
    [
        pytest.param(PROGRESS_ID, {}, {"quizIndex": 1, "isCorrect": True}, id="위치_누락"),
        pytest.param(
            PROGRESS_ID,
            {"latitude": 100, "longitude": USER_LONGITUDE},
            {"quizIndex": 1, "isCorrect": True},
            id="위도_범위_초과",
        ),
        pytest.param(
            PROGRESS_ID,
            {"latitude": USER_LATITUDE, "longitude": 200},
            {"quizIndex": 1, "isCorrect": True},
            id="경도_범위_초과",
        ),
        pytest.param(PROGRESS_ID, None, {"isCorrect": True}, id="퀴즈_번호_누락"),
        pytest.param(PROGRESS_ID, None, {"quizIndex": 0, "isCorrect": True}, id="0인_퀴즈_번호"),
        pytest.param(
            PROGRESS_ID, None, {"quizIndex": "일", "isCorrect": True}, id="정수가_아닌_퀴즈_번호"
        ),
        pytest.param(PROGRESS_ID, None, {"quizIndex": 1}, id="정답_여부_누락"),
        pytest.param(
            PROGRESS_ID, None, {"quizIndex": 1, "isCorrect": "네"}, id="boolean이_아닌_정답_여부"
        ),
        pytest.param(0, None, {"quizIndex": 1, "isCorrect": True}, id="0인_진행도_id"),
        pytest.param("abc", None, {"quizIndex": 1, "isCorrect": True}, id="정수가_아닌_진행도_id"),
    ],
)
def test_요청_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient,
    db_session: Session,
    progress_data: None,
    progress_id: object,
    params: dict[str, object] | None,
    body: dict[str, object],
) -> None:
    _add_progress(db_session, current_quiz_index=1)

    response = client.patch(
        _endpoint(progress_id), params=params if params is not None else _params(), json=body
    )

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
