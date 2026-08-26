"""GET /api/v1/missions/{missionType}/{missionId} - 미션 홈 조회 테스트.

기준 문서: app/mission/docs/API_SPEC.md, app/mission/docs/BUSINESS_RULES.md
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.cooperative_mission.models import CooperativeMission
from app.culture_mission.models import CultureMission
from app.map.models import Location
from app.mission.models import Mission
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
                role_total_count=4,
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
        "rewardDetail": {
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

    assert culture["rewardDetail"]["point"] == 100
    assert cooperative["rewardDetail"]["point"] == 200


# ---------------------------------------------------------------------
# 보상 분기
# ---------------------------------------------------------------------


def test_캐릭터와_쿠폰_보상이_없으면_null로_반환한다(
    client: TestClient, mission_data: None
) -> None:
    body = client.get(_endpoint("COOPERATIVE", SHARED_DETAIL_ID)).json()

    assert body["rewardDetail"]["arCharacter"] is None
    assert body["rewardDetail"]["coupon"] is None
    assert body["rewardDetail"]["point"] == 200


def test_포인트_보상이_없으면_0으로_반환한다(
    client: TestClient, db_session: Session, mission_data: None
) -> None:
    db_session.add(
        TreasureMission(
            id=1,
            mission_id=TREASURE_TYPE_ID,
            location_id=LOCATION_ID,
            item_total_count=3,
            item_detail=[],
            reward_detail={},
        )
    )
    db_session.commit()

    body = client.get(_endpoint("TREASURE", 1)).json()

    assert body["rewardDetail"] == {"arCharacter": None, "point": 0, "coupon": None}


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
            item_detail=[],
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
