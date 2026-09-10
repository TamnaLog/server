"""PUT /api/v1/users/me/step-counts - 걸음 수 저장 테스트.

기준 문서: app/others/docs/API_SPEC.md, app/others/docs/BUSINESS_RULES.md
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.others import service
from app.treasure_mission.models import AcquiredArCharacter, ArCharacter
from app.user.models import StepCount, User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me/step-counts"

OTHER_USER_ID = 2

RECORDED_AT = "2026-09-10T18:30:00"
RECORDED_DATETIME = datetime(2026, 9, 10, 18, 30, 0)
LATER_RECORDED_AT = "2026-09-10T19:00:00"
LATER_RECORDED_DATETIME = datetime(2026, 9, 10, 19, 0, 0)
CREATED_AT = datetime(2026, 9, 10, 18, 0, 0)

TARGET_STEP = 12000

# 보상 후보 캐릭터 id 와, 후보가 아닌 캐릭터 id
REWARD_CHARACTER_IDS = service.STEP_GOAL_REWARD_CHARACTER_IDS
NOT_REWARD_CHARACTER_ID = 4


@pytest.fixture
def step_data(db_session: Session) -> None:
    """사용자 2명 + 캐릭터 4개(후보 1~3, 후보가 아닌 4).

    걸음 수 기록과 획득 이력은 테스트마다 달라서 각 테스트에서 직접 만든다.
    """
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
                target_step=TARGET_STEP,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
        ]
    )
    db_session.add_all(
        [
            ArCharacter(
                id=character_id,
                character_name=f"캐릭터 {character_id}",
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="조건",
                character_img_url=f"https://example.com/ar-characters/{character_id}.png",
                hashtags=["#태그"],
            )
            for character_id in (*REWARD_CHARACTER_IDS, NOT_REWARD_CHARACTER_ID)
        ]
    )
    db_session.commit()


def _add_step_count(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    saved_at: datetime = RECORDED_DATETIME,
    steps_count: int = 5000,
    created_at: datetime = CREATED_AT,
) -> None:
    db_session.add(
        StepCount(
            user_id=user_id,
            saved_at=saved_at,
            steps_count=steps_count,
            created_at=created_at,
        )
    )
    db_session.commit()


def _add_acquired(
    db_session: Session,
    *,
    ar_character_id: int,
    user_id: int = CURRENT_USER_ID,
) -> None:
    db_session.add(
        AcquiredArCharacter(
            user_id=user_id,
            ar_character_id=ar_character_id,
            acquired_mission_id=None,
        )
    )
    db_session.commit()


def _put(
    client: TestClient,
    *,
    body: dict[str, object] | None = None,
    recorded_at: str = RECORDED_AT,
    steps_count: int = 8241,
    is_goal_achieved: bool = False,
    user_id: int = CURRENT_USER_ID,
) -> Any:
    payload = (
        {
            "recordedAt": recorded_at,
            "stepsCount": steps_count,
            "isGoalAchieved": is_goal_achieved,
        }
        if body is None
        else body
    )
    return client.put(ENDPOINT, json=payload, headers=auth_headers(user_id))


def _step_counts(db_session: Session) -> list[StepCount]:
    db_session.expire_all()
    return list(db_session.scalars(select(StepCount).order_by(StepCount.id)).all())


def _acquired(
    db_session: Session, user_id: int = CURRENT_USER_ID
) -> list[AcquiredArCharacter]:
    db_session.expire_all()
    statement = (
        select(AcquiredArCharacter)
        .where(AcquiredArCharacter.user_id == user_id)
        .order_by(AcquiredArCharacter.id)
    )
    return list(db_session.scalars(statement).all())


def _reward_characters(db_session: Session) -> list[ArCharacter]:
    """DB 에 있는 후보 캐릭터. 추첨 결과를 이 목록과 대조한다."""
    statement = (
        select(ArCharacter)
        .where(ArCharacter.id.in_(REWARD_CHARACTER_IDS))
        .order_by(ArCharacter.id)
    )
    return list(db_session.scalars(statement).all())


# ---------------------------------------------------------------------
# 저장 (신규)
# ---------------------------------------------------------------------


def test_걸음_수를_저장하면_200과_목표_걸음_수를_반환한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    response = _put(client)

    assert response.status_code == 200
    assert response.json() == {
        "characterName": None,
        "characterImageUrl": None,
        # 걸음 수 기록이 아니라 사용자 설정값(USER.target_step)이다.
        "targetStep": TARGET_STEP,
    }

    step_counts = _step_counts(db_session)
    assert len(step_counts) == 1
    assert step_counts[0].user_id == CURRENT_USER_ID
    assert step_counts[0].steps_count == 8241


def test_saved_at은_요청의_recordedAt을_그대로_저장한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _put(client, recorded_at=RECORDED_AT)

    # 서버 수신 시각으로 바꾸거나 KST 자정으로 정규화하지 않는다.
    assert _step_counts(db_session)[0].saved_at == RECORDED_DATETIME


def test_걸음_수가_0이어도_저장한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    response = _put(client, steps_count=0)

    assert response.status_code == 200
    assert _step_counts(db_session)[0].steps_count == 0


# ---------------------------------------------------------------------
# 저장 (갱신)
# ---------------------------------------------------------------------


def test_같은_시각으로_다시_보내면_행을_추가하지_않고_갱신한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _add_step_count(db_session, steps_count=5000)

    _put(client, steps_count=8241)

    step_counts = _step_counts(db_session)
    assert len(step_counts) == 1
    assert step_counts[0].steps_count == 8241
    # 처음 기록한 시각은 그대로 둔다.
    assert step_counts[0].created_at == CREATED_AT


def test_기존_값보다_작아도_요청값으로_덮어쓴다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _add_step_count(db_session, steps_count=9000)

    _put(client, steps_count=120)

    # 서버가 최댓값을 고르거나 누적해서 더하지 않는다.
    assert [item.steps_count for item in _step_counts(db_session)] == [120]


def test_측정_시각이_다르면_새_행을_만든다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _put(client, recorded_at=RECORDED_AT, steps_count=8241)
    _put(client, recorded_at=LATER_RECORDED_AT, steps_count=10500)

    step_counts = _step_counts(db_session)
    assert [item.saved_at for item in step_counts] == [
        RECORDED_DATETIME,
        LATER_RECORDED_DATETIME,
    ]
    assert [item.steps_count for item in step_counts] == [8241, 10500]


def test_다른_사용자의_같은_시각_기록은_건드리지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _add_step_count(db_session, user_id=OTHER_USER_ID, steps_count=5000)

    _put(client, steps_count=8241)

    step_counts = _step_counts(db_session)
    assert len(step_counts) == 2
    assert {(item.user_id, item.steps_count) for item in step_counts} == {
        (OTHER_USER_ID, 5000),
        (CURRENT_USER_ID, 8241),
    }


def test_토큰의_사용자로_저장한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    _put(client, user_id=OTHER_USER_ID)

    assert _step_counts(db_session)[0].user_id == OTHER_USER_ID


def test_한_사용자는_같은_시각에_기록을_하나만_가진다(
    db_session: Session, step_data: None
) -> None:
    """`(user_id, saved_at)` 유니크 제약이 DB 수준에서도 중복을 막는다."""
    _add_step_count(db_session, steps_count=5000)

    with pytest.raises(IntegrityError):
        _add_step_count(db_session, steps_count=8241)

    db_session.rollback()


def test_유니크_충돌이_나면_기존_행을_갱신하고_중복_행을_만들지_않는다(
    client: TestClient,
    db_session: Session,
    step_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 조회 직후 다른 요청이 같은 시각의 행을 먼저 만든 상황을 흉내 낸다.
    # (행은 이미 있는데 우리 쪽 조회 결과는 None 이라 INSERT 를 시도한다)
    _add_step_count(db_session, steps_count=5000)
    original_find = service._find_step_count
    calls: list[int] = []

    def find_once_missing(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            return None
        return original_find(*args, **kwargs)

    monkeypatch.setattr(service, "_find_step_count", find_once_missing)

    response = _put(client, steps_count=8241)

    assert response.status_code == 200
    step_counts = _step_counts(db_session)
    # 중복 행을 만들지 않고 기존 행을 갱신한다.
    assert len(step_counts) == 1
    assert step_counts[0].steps_count == 8241
    assert step_counts[0].created_at == CREATED_AT


# ---------------------------------------------------------------------
# 목표 달성 캐릭터 추첨과 획득
# ---------------------------------------------------------------------


def test_목표를_달성하면_후보_캐릭터_중_하나를_추첨해_응답한다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    body = _put(client, is_goal_achieved=True).json()

    # 값 자체가 아니라 DB 의 후보 캐릭터 중 하나인지로 확인한다.
    assert (body["characterName"], body["characterImageUrl"]) in [
        (character.character_name, character.character_img_url)
        for character in _reward_characters(db_session)
    ]
    assert body["targetStep"] == TARGET_STEP


def test_후보가_아닌_캐릭터는_추첨되지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    for minute in range(20):
        _put(client, recorded_at=f"2026-09-10T18:{minute:02d}:00", is_goal_achieved=True)

    assert {item.ar_character_id for item in _acquired(db_session)} <= set(
        REWARD_CHARACTER_IDS
    )


def test_목표를_달성하면_획득_기록을_만들고_acquired_mission_id는_NULL이다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    body = _put(client, is_goal_achieved=True).json()

    acquired = _acquired(db_session)
    assert len(acquired) == 1
    assert acquired[0].ar_character_id in REWARD_CHARACTER_IDS
    # 미션에서 받은 보상이 아니므로 출처 미션이 없다. (임의의 미션 id 를 넣지 않는다)
    assert acquired[0].acquired_mission_id is None

    character = db_session.get(ArCharacter, acquired[0].ar_character_id)
    assert character is not None
    assert body["characterName"] == character.character_name
    assert body["characterImageUrl"] == character.character_img_url


def test_이미_보유한_캐릭터가_뽑히면_중복_기록을_만들지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    # 후보 셋을 모두 보유한 상태라 무엇이 뽑혀도 이미 보유한 캐릭터다.
    for character_id in REWARD_CHARACTER_IDS:
        _add_acquired(db_session, ar_character_id=character_id)

    response = _put(client, is_goal_achieved=True)

    assert response.status_code == 200
    # 중복 저장하지 않아도 이번에 뽑힌 캐릭터 정보는 그대로 응답한다.
    assert response.json()["characterName"] is not None
    assert len(_acquired(db_session)) == len(REWARD_CHARACTER_IDS)


def test_다른_사용자의_획득_이력은_중복_판단에_쓰지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    for character_id in REWARD_CHARACTER_IDS:
        _add_acquired(db_session, ar_character_id=character_id, user_id=OTHER_USER_ID)

    _put(client, is_goal_achieved=True)

    assert len(_acquired(db_session)) == 1
    assert len(_acquired(db_session, user_id=OTHER_USER_ID)) == len(REWARD_CHARACTER_IDS)


def test_목표를_달성하지_못하면_추첨하지_않고_캐릭터가_null이다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    body = _put(client, is_goal_achieved=False).json()

    assert body == {
        "characterName": None,
        "characterImageUrl": None,
        "targetStep": TARGET_STEP,
    }
    assert _acquired(db_session) == []


def test_걸음_수와_목표_걸음_수를_다시_비교하지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    """달성 여부는 프론트 판정을 그대로 믿는다. 서버가 뒤집지 않는다."""
    body = _put(client, steps_count=1, is_goal_achieved=True).json()

    assert body["characterName"] is not None
    assert len(_acquired(db_session)) == 1


def test_후보_캐릭터가_없으면_500이고_걸음_수도_저장하지_않는다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    for character in _reward_characters(db_session):
        db_session.delete(character)
    db_session.commit()

    response = _put(client, is_goal_achieved=True)

    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_SERVER_ERROR"}
    # 전체 트랜잭션을 롤백한다.
    assert _step_counts(db_session) == []
    assert _acquired(db_session) == []


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            {"stepsCount": 8241, "isGoalAchieved": False}, id="측정_시각_누락"
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "isGoalAchieved": False}, id="걸음_수_누락"
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "stepsCount": 8241}, id="달성_여부_누락"
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "stepsCount": -1, "isGoalAchieved": False},
            id="음수_걸음_수",
        ),
        pytest.param(
            {"recordedAt": RECORDED_AT, "stepsCount": 1.5, "isGoalAchieved": False},
            id="정수가_아닌_걸음_수",
        ),
        pytest.param(
            {
                "recordedAt": "2026-09-10T18:30:00+09:00",
                "stepsCount": 8241,
                "isGoalAchieved": False,
            },
            id="offset이_붙은_시각",
        ),
        pytest.param(
            {"recordedAt": "어제", "stepsCount": 8241, "isGoalAchieved": False},
            id="형식이_아닌_시각",
        ),
        pytest.param(
            {
                "recordedAt": RECORDED_AT,
                "stepsCount": 8241,
                "isGoalAchieved": False,
                "userId": 2,
            },
            id="정의되지_않은_필드",
        ),
        pytest.param({}, id="빈_body"),
    ],
)
def test_요청_Body가_잘못되면_400이다(
    client: TestClient, db_session: Session, step_data: None, body: dict
) -> None:
    response = _put(client, body=body)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _step_counts(db_session) == []
    assert _acquired(db_session) == []


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


def test_인증_헤더가_없으면_401이다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.put(
        ENDPOINT,
        json={
            "recordedAt": RECORDED_AT,
            "stepsCount": 8241,
            "isGoalAchieved": True,
        },
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _step_counts(db_session) == []


def test_토큰의_사용자가_없으면_401이다(
    client: TestClient, db_session: Session, step_data: None
) -> None:
    response = _put(client, user_id=999)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _step_counts(db_session) == []


def test_문서에_401을_노출한다(client: TestClient) -> None:
    responses = client.get("/openapi.json").json()["paths"][ENDPOINT]["put"]["responses"]

    assert sorted(responses) == ["200", "400", "401", "500"]
