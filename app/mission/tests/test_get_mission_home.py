"""GET /api/v1/missions/{missionType}/{missionId} - 미션 홈 조회 테스트.

기준 문서: app/mission/docs/API_SPEC.md, app/mission/docs/BUSINESS_RULES.md
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantRole,
    ParticipantStatus,
)
from app.core.deps import CURRENT_USER_ID
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.map.models import Location
from app.mission.models import Mission, MissionStatus
from app.user.models import User
from app.treasure_mission.models import ArCharacter, TreasureMission


# MISSION(유형 분류) id
CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TYPE_ID = 3

# 세부 미션 id. 유형이 달라도 같은 id 가 존재할 수 있다는 걸 드러내려고 일부러 겹쳐 둔다.
SHARED_DETAIL_ID = 5

AR_CHARACTER_ID = 7
CHARACTER_IMG_URL = "https://example.com/characters/stone-spirit.png"

LOCATION_ID = 1


def _endpoint(mission_type: str, mission_id: object) -> str:
    return f"/api/v1/missions/{mission_type}/{mission_id}"


def _step_detail() -> list[dict[str, object]]:
    # step 오름차순 정렬을 검증하려고 일부러 섞어서 저장한다.
    return [
        {"step": 3, "step_title": "정답 확인", "description": "문제를 다 풀면 결과를 확인할 수 있어요."},
        {"step": 1, "step_title": "퀴즈 시작하기", "description": "제주 방언에 대한 퀴즈를 풀어보세요."},
        {"step": 2, "step_title": "3문제 풀기", "description": "각 문제마다 보기 중 정답을 선택하세요."},
    ]


FULL_REWARD = {
    "ar_character_id": AR_CHARACTER_ID,
    "point": 100,
    "coupon_location": "종화네 막국수",
    "coupon_price": 1000,
}

# 현재 사용자가 아닌 다른 사용자
OTHER_USER_ID = CURRENT_USER_ID + 1


def _culture_progress(
    *,
    id: int,
    user_id: int = CURRENT_USER_ID,
    ar_character: bool = False,
    point: bool = False,
    coupon: bool = False,
) -> CultureMissionProgress:
    """보상 지급 여부만 지정하는 문화 미션 진행도 이력."""
    return CultureMissionProgress(
        id=id,
        culture_mission_id=SHARED_DETAIL_ID,
        user_id=user_id,
        mission_status=MissionStatus.COMPLETED.value,
        current_quiz_index=3,
        correct_number=3,
        ar_character_reward_granted=ar_character,
        point_reward_granted=point,
        coupon_reward_granted=coupon,
    )


def _cooperative_progress(
    *,
    id: int,
    team_token: str,
    ar_character: bool = False,
    point: bool = False,
    coupon: bool = False,
) -> CooperativeMissionProgress:
    """보상 지급 여부만 지정하는 협동 미션 진행도 이력."""
    return CooperativeMissionProgress(
        id=id,
        cooperative_mission_id=SHARED_DETAIL_ID,
        current_step=3,
        mission_status=MissionStatus.COMPLETED.value,
        team_token=team_token,
        ar_character_reward_granted=ar_character,
        point_reward_granted=point,
        coupon_reward_granted=coupon,
    )


def _participant(*, id: int, progress_id: int, user_id: int) -> CooperativeMissionParticipant:
    """협동 미션 진행도에 사용자를 연결하는 참여자."""
    return CooperativeMissionParticipant(
        id=id,
        cooperative_mission_progress_id=progress_id,
        user_id=user_id,
        participant_status=ParticipantStatus.ACCEPTED.value,
        participant_role=ParticipantRole.HOST.value,
    )


@pytest.fixture
def mission_data(db_session: Session) -> None:
    """유형별로 같은 id(5)를 갖는 세부 미션 목업 데이터."""
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
            User(id=CURRENT_USER_ID, nickname="몽글몽글파도", point=0),
            Location(
                id=LOCATION_ID,
                content_id=126508,
                location_title="종화네 과수원",
                location_address="제주특별자치도 제주시 조천읍 감귤밭길 12",
                location_category="농장",
                radius=400,
                mx=126.5707,
                my=33.4507,
            ),
            Mission(
                id=CULTURE_TYPE_ID,
                mission_type="CULTURE",
                mission_title="오늘의 제주 퀴즈",
                description="제주의 퀴즈를 맞춰보세요.",
                step_detail=_step_detail(),
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="일행과 역할을 나눠 귤나무를 완성해보세요!",
                step_detail=_step_detail(),
            ),
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title="보물 찾기",
                description="주변에 숨겨진 AR 보물을 찾아보세요.",
                step_detail=_step_detail(),
            ),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            CultureMission(
                id=SHARED_DETAIL_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=3,
                quiz_detail=[],
                reward_detail=FULL_REWARD,
            ),
            CooperativeMission(
                id=SHARED_DETAIL_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=LOCATION_ID,
                reward_detail={"ar_character_id": None, "point": 200},
            ),
        ]
    )
    db_session.commit()


# ---------------------------------------------------------------------
# 정상 조회
# ---------------------------------------------------------------------


def test_미션_홈을_조회하면_명세의_필드를_모두_반환한다(
    client: TestClient, mission_data: None
) -> None:
    response = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID))

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": SHARED_DETAIL_ID,
        "missionType": "CULTURE",
        "missionTitle": "오늘의 제주 퀴즈",
        "description": "제주의 퀴즈를 맞춰보세요.",
        "remainingReward": {
            "arCharacter": {
                "id": AR_CHARACTER_ID,
                "name": "돌담이",
                "imageUrl": CHARACTER_IMG_URL,
            },
            "point": 100,
            "coupon": {"couponLocation": "종화네 막국수", "couponPrice": 1000},
        },
        "steps": [
            {
                "step": 1,
                "stepTitle": "퀴즈 시작하기",
                "description": "제주 방언에 대한 퀴즈를 풀어보세요.",
            },
            {
                "step": 2,
                "stepTitle": "3문제 풀기",
                "description": "각 문제마다 보기 중 정답을 선택하세요.",
            },
            {
                "step": 3,
                "stepTitle": "정답 확인",
                "description": "문제를 다 풀면 결과를 확인할 수 있어요.",
            },
        ],
    }


def test_응답의_id는_공통_미션_id가_아니라_세부_미션_id다(
    client: TestClient, mission_data: None
) -> None:
    body = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()

    assert body["id"] == SHARED_DETAIL_ID
    assert body["id"] != CULTURE_TYPE_ID


def test_같은_id라도_요청한_유형의_세부_미션만_조회한다(
    client: TestClient, mission_data: None
) -> None:
    # id=5 인 문화 미션과 협동 미션이 둘 다 있다. 유형에 맞는 쪽만 나와야 한다.
    culture = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()
    cooperative = client.get(_endpoint("COOPERATIVE", SHARED_DETAIL_ID)).json()

    assert culture["missionType"] == "CULTURE"
    assert culture["missionTitle"] == "오늘의 제주 퀴즈"
    assert cooperative["missionType"] == "COOPERATIVE"
    assert cooperative["missionTitle"] == "함께 키우는 귤나무"


def test_단계_목록은_step_오름차순으로_반환한다(
    client: TestClient, mission_data: None
) -> None:
    # 목업은 3, 1, 2 순서로 저장돼 있다.
    body = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()

    assert [step["step"] for step in body["steps"]] == [1, 2, 3]


def test_보상은_공통_미션이_아니라_세부_미션의_값을_사용한다(
    client: TestClient, mission_data: None
) -> None:
    # 같은 유형이어도 세부 미션마다 보상이 다를 수 있다.
    culture = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()
    cooperative = client.get(_endpoint("COOPERATIVE", SHARED_DETAIL_ID)).json()

    assert culture["remainingReward"]["point"] == 100
    assert cooperative["remainingReward"]["point"] == 200


# ---------------------------------------------------------------------
# 보상 분기
# ---------------------------------------------------------------------


def test_캐릭터와_쿠폰_보상이_없으면_null로_반환한다(
    client: TestClient, mission_data: None
) -> None:
    body = client.get(_endpoint("COOPERATIVE", SHARED_DETAIL_ID)).json()

    assert body["remainingReward"]["arCharacter"] is None
    assert body["remainingReward"]["coupon"] is None
    assert body["remainingReward"]["point"] == 200


def test_포인트_보상이_없으면_null로_반환한다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    db_session.add(
        TreasureMission(
            id=1,
            mission_id=TREASURE_TYPE_ID,
            location_id=LOCATION_ID,
            item_total_count=3,
            reward_detail={},
        )
    )
    db_session.commit()

    body = client.get(_endpoint("TREASURE", 1)).json()

    assert body["remainingReward"] == {"arCharacter": None, "point": None, "coupon": None}


# ---------------------------------------------------------------------
# 남은 보상 (진행도 이력 기준)
# ---------------------------------------------------------------------


def test_진행도가_없으면_보상_3개를_모두_아직_지급되지_않은_것으로_본다(
    client: TestClient, mission_data: None
) -> None:
    body = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()

    assert body["remainingReward"]["arCharacter"] is not None
    assert body["remainingReward"]["point"] == 100
    assert body["remainingReward"]["coupon"] is not None


def test_과거_진행도에서_한_번이라도_지급된_보상은_null로_반환한다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    # 첫 시도에서 캐릭터를, 두 번째 시도에서 포인트를 받은 이력. 쿠폰만 아직 남아 있다.
    db_session.add_all(
        [
            _culture_progress(id=1, ar_character=True),
            _culture_progress(id=2, point=True),
        ]
    )
    db_session.commit()

    body = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()

    assert body["remainingReward"] == {
        "arCharacter": None,
        "point": None,
        "coupon": {"couponLocation": "종화네 막국수", "couponPrice": 1000},
    }


def test_보상을_모두_지급받았으면_남은_보상이_전부_null이다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    db_session.add(
        _culture_progress(id=1, ar_character=True, point=True, coupon=True)
    )
    db_session.commit()

    body = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()

    assert body["remainingReward"] == {"arCharacter": None, "point": None, "coupon": None}


def test_다른_사용자의_진행도는_남은_보상_판단에_포함하지_않는다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    db_session.add(
        _culture_progress(id=1, user_id=OTHER_USER_ID, ar_character=True, point=True, coupon=True)
    )
    db_session.commit()

    body = client.get(_endpoint("CULTURE", SHARED_DETAIL_ID)).json()

    assert body["remainingReward"]["arCharacter"] is not None
    assert body["remainingReward"]["point"] == 100
    assert body["remainingReward"]["coupon"] is not None


def test_협동_미션은_참여자로_연결된_진행도를_기준으로_판단한다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    # 협동 미션 진행도는 user_id 를 직접 갖지 않고 참여자 테이블로 연결된다.
    db_session.add_all(
        [
            _cooperative_progress(id=1, team_token="team-1", point=True),
            _cooperative_progress(id=2, team_token="team-2", point=True),
        ]
    )
    db_session.flush()
    db_session.add(_participant(id=1, progress_id=1, user_id=CURRENT_USER_ID))
    db_session.add(_participant(id=2, progress_id=2, user_id=OTHER_USER_ID))
    db_session.commit()

    body = client.get(_endpoint("COOPERATIVE", SHARED_DETAIL_ID)).json()

    assert body["remainingReward"]["point"] is None


def test_협동_미션에서_참여하지_않은_진행도는_판단에_포함하지_않는다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    db_session.add(_cooperative_progress(id=1, team_token="team-1", point=True))
    db_session.flush()
    db_session.add(_participant(id=1, progress_id=1, user_id=OTHER_USER_ID))
    db_session.commit()

    body = client.get(_endpoint("COOPERATIVE", SHARED_DETAIL_ID)).json()

    assert body["remainingReward"]["point"] == 200


# ---------------------------------------------------------------------
# 404 MISSION_NOT_FOUND
# ---------------------------------------------------------------------


def test_요청한_유형의_세부_미션이_없으면_404_MISSION_NOT_FOUND로_응답한다(
    client: TestClient, mission_data: None
) -> None:
    response = client.get(_endpoint("CULTURE", 999))

    assert response.status_code == 404
    assert response.json() == {"code": "MISSION_NOT_FOUND"}


def test_다른_유형에만_존재하는_id면_404_MISSION_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    # 보물찾기 미션에만 id=9 를 만들고 문화 미션으로 조회한다.
    db_session.add(
        TreasureMission(
            id=9,
            mission_id=TREASURE_TYPE_ID,
            location_id=LOCATION_ID,
            item_total_count=3,
            reward_detail={},
        )
    )
    db_session.commit()

    assert client.get(_endpoint("TREASURE", 9)).status_code == 200

    response = client.get(_endpoint("CULTURE", 9))

    assert response.status_code == 404
    assert response.json() == {"code": "MISSION_NOT_FOUND"}


def test_연결된_공통_미션의_유형이_다르면_404_MISSION_NOT_FOUND로_응답한다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    # 문화 미션인데 공통 미션은 보물찾기로 잘못 연결된 데이터
    db_session.add(
        CultureMission(
            id=77,
            mission_id=TREASURE_TYPE_ID,
            quiz_total_count=3,
            quiz_detail=[],
            reward_detail={},
        )
    )
    db_session.commit()

    response = client.get(_endpoint("CULTURE", 77))

    assert response.status_code == 404
    assert response.json() == {"code": "MISSION_NOT_FOUND"}


# ---------------------------------------------------------------------
# 400 INVALID_REQUEST
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mission_type", "mission_id"),
    [
        pytest.param("MUSIC", 1, id="정의되지_않은_미션_유형"),
        pytest.param("culture", 1, id="소문자_미션_유형"),
        pytest.param("CULTURE", "abc", id="정수가_아닌_미션_id"),
        pytest.param("CULTURE", 0, id="0인_미션_id"),
        pytest.param("CULTURE", -1, id="음수_미션_id"),
    ],
)
def test_요청_값이_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, mission_data: None, mission_type: str, mission_id: object
) -> None:
    # 유효하지 않은 미션 유형은 존재 여부를 조회할 수 없으므로 404가 아니라 400이다.
    response = client.get(_endpoint(mission_type, mission_id))

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
