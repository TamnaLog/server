"""PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress/stop - 문화 미션 중단 테스트.

기준 문서: app/culture_mission/docs/API_SPEC.md, app/culture_mission/docs/BUSINESS_RULES.md
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common import distance, next_location
from app.cooperative_mission.models import CooperativeMission
from app.culture_mission.models import CultureMission, CultureMissionProgress, MissionStatus
from app.map.models import Location
from app.mission.models import Mission
from app.treasure_mission.models import AcquiredArCharacter, ArCharacter
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash


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
CHARACTER_IMG_URL = "https://example.com/characters/stone-spirit.png"
REWARD_POINT = 100
INITIAL_USER_POINT = 30

COUPON_LOCATION = "종화네 막국수"
COUPON_PRICE = 3000

REWARD_DETAIL = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": REWARD_POINT,
    "coupon_location": COUPON_LOCATION,
    "coupon_price": COUPON_PRICE,
}


def _endpoint(progress_id: object) -> str:
    return f"/api/v1/culture-missions/{progress_id}/progress/stop"


def _params(**overrides: object) -> dict[str, object]:
    return {"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE, **overrides}


def _ar_character_reward() -> dict[str, object]:
    return {"id": AR_CHARACTER_ID, "name": "돌담이", "imageUrl": CHARACTER_IMG_URL}


def _coupon_reward() -> dict[str, object]:
    return {"couponLocation": COUPON_LOCATION, "couponPrice": COUPON_PRICE}


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """장소 이미지 조회(TourAPI)를 막아 외부 네트워크를 타지 않게 한다."""
    monkeypatch.setattr(
        next_location, "get_location_image_url", lambda content_id: LOCATION_IMAGE_URL
    )


@pytest.fixture
def progress_data(db_session: Session) -> None:
    """문화 미션 / 사용자 / 보상 캐릭터 / 다음 장소 후보 목업 데이터."""
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
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=INITIAL_USER_POINT,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
            ArCharacter(
                id=AR_CHARACTER_ID,
                character_name="돌담이",
                character_description="돌담을 지키는 캐릭터입니다.",
                acquire_condition="문화 미션을 완료하면 만날 수 있어요.",
                character_img_url=CHARACTER_IMG_URL,
                hashtags=["#돌담"],
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
    current_quiz_index: int = 2,
    correct_number: int = 1,
    status: MissionStatus = MissionStatus.IN_PROGRESS,
    user_id: int = CURRENT_USER_ID,
    progress_id: int = PROGRESS_ID,
    ar_character_granted: bool = False,
    point_granted: bool = False,
    coupon_granted: bool = False,
) -> None:
    db_session.add(
        CultureMissionProgress(
            id=progress_id,
            culture_mission_id=CULTURE_MISSION_ID,
            user_id=user_id,
            mission_status=status.value,
            current_quiz_index=current_quiz_index,
            correct_number=correct_number,
            ar_character_reward_granted=ar_character_granted,
            point_reward_granted=point_granted,
            coupon_reward_granted=coupon_granted,
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


def _stop(client: TestClient) -> dict:
    response = client.patch(_endpoint(PROGRESS_ID), params=_params())
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------
# 중단 처리 (BUSINESS_RULES 3.)
# ---------------------------------------------------------------------


def test_중단하면_명세의_필드를_모두_반환한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=2, correct_number=1)

    body = _stop(client)

    saved_location = db_session.get(Location, LOCATION_ID)
    assert saved_location is not None
    assert body == {
        "missionProgressStatus": "COMPLETED",
        "quizCount": QUIZ_TOTAL_COUNT,
        "correctNumber": 1,
        "nextLocation": {
            "id": LOCATION_ID,
            "locationTitle": "한담해안산책로",
            "locationImageUrl": LOCATION_IMAGE_URL,
            "distanceMeter": distance.calculate_distance_meter(
                USER_LATITUDE, USER_LONGITUDE, saved_location.my, saved_location.mx
            ),
            "mission": None,
        },
        # 정답 1개이므로 지급 순서상 첫 보상인 AR 캐릭터만 지급된다.
        "reward": {"arCharacter": _ar_character_reward(), "point": None, "coupon": None},
    }
    # 중단 응답에는 퀴즈 번호를 넣지 않는다.
    assert "currentQuizNumber" not in body


def test_중단하면_퀴즈_번호와_정답_수는_그대로_두고_완료로_바꾼다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=2, correct_number=1)

    _stop(client)

    saved = _saved(db_session)
    assert saved.mission_status == MissionStatus.COMPLETED.value
    assert saved.completed_at is not None
    # 남은 퀴즈가 있어도 진행 결과는 그대로 둔다.
    assert saved.current_quiz_index == 2
    assert saved.correct_number == 1


def test_첫_퀴즈를_풀기_전에_중단해도_완료로_처리한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=1, correct_number=0)

    body = _stop(client)

    assert body["missionProgressStatus"] == "COMPLETED"
    assert body["correctNumber"] == 0
    assert _saved(db_session).mission_status == MissionStatus.COMPLETED.value


# ---------------------------------------------------------------------
# 보상 지급 (BUSINESS_RULES 4.)
# ---------------------------------------------------------------------


def test_저장된_정답_수만큼_AR캐릭터_포인트_쿠폰_순으로_지급한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=3, correct_number=2)

    body = _stop(client)

    assert body["reward"] == {
        "arCharacter": _ar_character_reward(),
        "point": REWARD_POINT,
        "coupon": None,
    }
    assert _user_point(db_session) == INITIAL_USER_POINT + REWARD_POINT
    assert len(_acquired(db_session)) == 1

    saved = _saved(db_session)
    assert saved.ar_character_reward_granted is True
    assert saved.point_reward_granted is True
    assert saved.coupon_reward_granted is False


def test_정답이_0개면_보상을_지급하지_않고_reward_항목이_모두_null이다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, current_quiz_index=1, correct_number=0)

    body = _stop(client)

    assert body["reward"] == {"arCharacter": None, "point": None, "coupon": None}
    assert _user_point(db_session) == INITIAL_USER_POINT
    assert _acquired(db_session) == []


def test_과거_진행도에서_지급된_보상은_중단해도_다시_지급하지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 과거 완료에서 AR 캐릭터를 이미 받았으므로 정답 1개는 포인트로 간다.
    _add_progress(
        db_session,
        progress_id=1,
        current_quiz_index=QUIZ_TOTAL_COUNT,
        status=MissionStatus.COMPLETED,
        ar_character_granted=True,
    )
    _add_progress(db_session, current_quiz_index=2, correct_number=1)

    body = _stop(client)

    assert body["reward"] == {"arCharacter": None, "point": REWARD_POINT, "coupon": None}
    assert _user_point(db_session) == INITIAL_USER_POINT + REWARD_POINT
    assert _acquired(db_session) == []


def test_남은_보상보다_정답이_많아도_남은_보상만_지급한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(
        db_session,
        progress_id=1,
        current_quiz_index=QUIZ_TOTAL_COUNT,
        status=MissionStatus.COMPLETED,
        ar_character_granted=True,
        point_granted=True,
    )
    _add_progress(db_session, current_quiz_index=3, correct_number=3)

    body = _stop(client)

    assert body["reward"] == {"arCharacter": None, "point": None, "coupon": _coupon_reward()}
    assert _user_point(db_session) == INITIAL_USER_POINT


def test_보상_지급에_실패하면_중단_처리도_저장되지_않는다(
    client: TestClient, db_session: Session, progress_data: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 상태 변경과 보상 지급은 한 트랜잭션이어야 한다.
    from app.culture_mission import service

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("보상 지급 실패")

    monkeypatch.setattr(service.reward_granter, "grant_culture_mission_reward", boom)
    _add_progress(db_session, current_quiz_index=2, correct_number=1)

    response = client.patch(_endpoint(PROGRESS_ID), params=_params())

    assert response.status_code == 500
    saved = _saved(db_session)
    assert saved.mission_status == MissionStatus.IN_PROGRESS.value
    assert saved.completed_at is None
    assert _user_point(db_session) == INITIAL_USER_POINT


# ---------------------------------------------------------------------
# 다음 장소 추천 (BUSINESS_RULES 5.)
# ---------------------------------------------------------------------


def test_다음_장소에_연결된_미션이_있으면_유형과_세부_미션_id를_반환한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    db_session.add(
        CooperativeMission(
            id=COOPERATIVE_MISSION_ID,
            mission_id=COOPERATIVE_TYPE_ID,
            location_id=LOCATION_ID,
            reward_detail={},
        )
    )
    db_session.commit()
    _add_progress(db_session)

    mission = _stop(client)["nextLocation"]["mission"]

    # 공통 MISSION.id 가 아니라 세부 미션 id 여야 한다.
    assert mission == {"id": COOPERATIVE_MISSION_ID, "missionType": "COOPERATIVE"}


def test_장소_이미지를_조회하지_못하면_locationImageUrl은_null이다(
    client: TestClient,
    db_session: Session,
    progress_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(next_location, "get_location_image_url", lambda content_id: None)
    _add_progress(db_session)

    body = _stop(client)

    assert body["nextLocation"]["locationImageUrl"] is None
    # 이미지 조회 실패는 중단 처리 실패가 아니다.
    assert body["missionProgressStatus"] == "COMPLETED"


def test_추천할_장소가_없으면_중단_응답을_만들지_않고_500으로_응답한다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    db_session.query(Location).delete()
    db_session.commit()
    _add_progress(db_session)

    response = client.patch(_endpoint(PROGRESS_ID), params=_params())

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}
    assert _saved(db_session).mission_status == MissionStatus.IN_PROGRESS.value


# ---------------------------------------------------------------------
# 404 CULTURE_MISSION_PROGRESS_NOT_FOUND
# ---------------------------------------------------------------------


def test_진행도가_없으면_404로_응답한다(client: TestClient, progress_data: None) -> None:
    response = client.patch(_endpoint(999), params=_params())

    assert response.status_code == 404
    assert response.json() == {"code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"}


def test_다른_사용자의_진행도면_404로_응답하고_바꾸지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    _add_progress(db_session, user_id=OTHER_USER_ID)

    response = client.patch(_endpoint(PROGRESS_ID), params=_params())

    assert response.status_code == 404
    assert response.json() == {"code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"}
    assert _saved(db_session).mission_status == MissionStatus.IN_PROGRESS.value


def test_이미_완료된_진행도면_404로_응답하고_보상을_다시_지급하지_않는다(
    client: TestClient, db_session: Session, progress_data: None
) -> None:
    # 중단 요청이 중복으로 들어와도 보상이 두 번 나가면 안 된다.
    _add_progress(
        db_session,
        current_quiz_index=2,
        correct_number=1,
        status=MissionStatus.COMPLETED,
        ar_character_granted=True,
    )

    response = client.patch(_endpoint(PROGRESS_ID), params=_params())

    assert response.status_code == 404
    assert response.json() == {"code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"}
    assert _user_point(db_session) == INITIAL_USER_POINT
    assert _acquired(db_session) == []


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"longitude": USER_LONGITUDE}, id="위도_누락"),
        pytest.param({"latitude": USER_LATITUDE}, id="경도_누락"),
        pytest.param(_params(latitude=90.1), id="위도_범위_초과"),
        pytest.param(_params(longitude=-180.1), id="경도_범위_초과"),
        pytest.param(_params(latitude="abc"), id="숫자가_아닌_위도"),
    ],
)
def test_위치_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, db_session: Session, progress_data: None, params: dict
) -> None:
    _add_progress(db_session)

    response = client.patch(_endpoint(PROGRESS_ID), params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _saved(db_session).mission_status == MissionStatus.IN_PROGRESS.value


@pytest.mark.parametrize(
    "progress_id",
    [pytest.param(0, id="0인_진행도_id"), pytest.param("abc", id="정수가_아닌_진행도_id")],
)
def test_진행도_id가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, progress_data: None, progress_id: object
) -> None:
    response = client.patch(_endpoint(progress_id), params=_params())

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
