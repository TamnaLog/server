"""GET /api/v1/users/me/home - 홈 조회 테스트.

기준 문서: app/home/docs/API_SPEC.md, app/home/docs/BUSINESS_RULES.md

미션 구조상 실제 미션 한 건은 미션 유형별 테이블의 행이므로,
응답의 `missionId` 는 `MISSION.id` 가 아니라 유형별 테이블의 id다.
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.common import distance
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantRole,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.guestbook.models import Guestbook, RoadGuestbook
from app.home.models import ArCharacter, Location, Mission, MissionStatus, User
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress
from conftest import CURRENT_USER_ID, access_token_hash


ENDPOINT = "/api/v1/users/me/home"

# 요청 기준 위치 (제주시청 근처)
USER_LATITUDE = 33.4996
USER_LONGITUDE = 126.5312

CHARACTER_IMG_URL = "https://example.com/images/characters/jacheongbi.png"

# MISSION(유형 분류) id
CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TYPE_ID = 3

# 미션 유형별 테이블 id = 응답의 missionId
CULTURE_MISSION_ID = 11
COOPERATIVE_MISSION_ID = 21
TREASURE_MISSION_ID = 31

# 추천 후보를 늘릴 때 쓰는 id
SECOND_CULTURE_MISSION_ID = 12
NEAR_COOPERATIVE_MISSION_ID = 22
NEAR_TREASURE_MISSION_ID = 32

# 장소 id
SEONGSAN_LOCATION_ID = 1
SAEBYEOL_LOCATION_ID = 2
# 사용자 요청 위치와 같은 좌표의 장소 (가장 가까운 미션 검증용)
NEAR_LOCATION_ID = 3

OTHER_USER_ID = 2

REWARD_DETAIL = {
    "ar_character_id": 1,
    "point": 100,
    "coupon_location": "제주 기념품숍",
    "coupon_price": 1000,
}

# 보물 좌표는 미션이 아니라 진행도가 가진다. [{index, mx, my}]
TREASURE_ITEM_DETAIL = [
    {"index": 1, "mx": 126.9410, "my": 33.4580},
    {"index": 2, "mx": 126.9415, "my": 33.4585},
]


def _step_detail(count: int) -> list[dict[str, object]]:
    return [
        {"step": index, "step_title": f"{index}단계", "description": "설명"}
        for index in range(1, count + 1)
    ]


def _mission(mission_id: int, mission_type: str, title: str, step_count: int) -> Mission:
    """MISSION - 미션 유형 분류 행."""
    return Mission(
        id=mission_id,
        mission_type=mission_type,
        mission_title=title,
        description=f"{title} 미션입니다.",
        step_detail=_step_detail(step_count),
    )


@pytest.fixture
def home_data(db_session: Session) -> None:
    """홈 조회에 필요한 장소 / 미션 / 사용자 목업 데이터.

    미션은 유형별로 1건씩만 둔다. (추천 후보가 하나뿐이면 선정 결과가 정해진다)
    추천 후보를 늘려야 하는 테스트는 `_add_near_missions()` 로 미션을 더 넣는다.
    진행도와 방명록은 각 테스트에서 필요한 만큼 따로 추가한다.
    """
    db_session.add_all(
        [
            ArCharacter(
                id=1,
                character_name="자청비 모티브 탐험가",
                character_description="기록 탐험가 캐릭터입니다.",
                character_story_title="이야기 제목",
                acquire_condition="온보딩에서 기록형 여행 스타일을 선택하면 만날 수 있어요.",
                character_img_url=CHARACTER_IMG_URL,
                hashtags=["#인생사진"],
            ),
            Location(
                id=SEONGSAN_LOCATION_ID,
                content_id=126508,
                location_title="성산일출봉",
                location_address="제주특별자치도 서귀포시 성산읍 일출로 284-12",
                location_category="자연",
                radius=300,
                mx=126.9410,
                my=33.4580,
            ),
            Location(
                id=SAEBYEOL_LOCATION_ID,
                content_id=126454,
                location_title="새별 오름",
                location_address="제주특별자치도 제주시 애월읍 봉성리 산59-8",
                location_category="오름",
                radius=500,
                mx=126.3577,
                my=33.3663,
            ),
            _mission(CULTURE_TYPE_ID, "CULTURE", "제주 문화 퀴즈", step_count=3),
            _mission(COOPERATIVE_TYPE_ID, "COOPERATIVE", "함께 키우는 귤나무", step_count=4),
            _mission(TREASURE_TYPE_ID, "TREASURE", "보물 찾기", step_count=3),
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
                ar_character_id=1,
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
            # 문화 미션은 장소를 갖지 않는다.
            CultureMission(
                id=CULTURE_MISSION_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=5,
                quiz_detail=[],
                reward_detail=REWARD_DETAIL,
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=SAEBYEOL_LOCATION_ID,
                reward_detail=REWARD_DETAIL,
            ),
            TreasureMission(
                id=TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=SEONGSAN_LOCATION_ID,
                item_total_count=5,
                reward_detail=REWARD_DETAIL,
            ),
        ]
    )
    db_session.commit()


def _add_near_missions(db_session: Session) -> None:
    """사용자 요청 위치와 같은 좌표의 장소에 협동 / 보물 찾기 미션을 한 건씩 추가한다.

    기본 목업의 미션(새별 오름 / 성산일출봉)보다 항상 가까우므로,
    "가장 가까운 미션을 고른다"를 거리 계산 없이 검증할 수 있다.
    """
    db_session.add(
        Location(
            id=NEAR_LOCATION_ID,
            content_id=126501,
            location_title="제주목 관아",
            location_address="제주특별자치도 제주시 관덕로 25",
            location_category="역사",
            radius=200,
            mx=USER_LONGITUDE,
            my=USER_LATITUDE,
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            CooperativeMission(
                id=NEAR_COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=NEAR_LOCATION_ID,
                reward_detail=REWARD_DETAIL,
            ),
            TreasureMission(
                id=NEAR_TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=NEAR_LOCATION_ID,
                item_total_count=5,
                reward_detail=REWARD_DETAIL,
            ),
        ]
    )
    db_session.commit()


def _complete_cooperative_mission(
    db_session: Session,
    cooperative_mission_id: int,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
) -> None:
    """협동 미션을 해당 사용자가 완료한 이력으로 만든다."""
    db_session.add(
        CooperativeMissionProgress(
            id=progress_id,
            cooperative_mission_id=cooperative_mission_id,
            current_step=4,
            mission_status=MissionStatus.COMPLETED.value,
            team_token=f"team-token-{progress_id}",
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=progress_id,
            cooperative_mission_progress_id=progress_id,
            user_id=user_id,
            participant_status=ParticipantStatus.ACCEPTED.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
    )
    db_session.commit()


def _complete_treasure_mission(
    db_session: Session,
    treasure_mission_id: int,
    progress_id: int,
    user_id: int = CURRENT_USER_ID,
) -> None:
    """보물 찾기 미션을 해당 사용자가 완료한 이력으로 만든다."""
    db_session.add(
        TreasureMissionProgress(
            id=progress_id,
            treasure_mission_id=treasure_mission_id,
            user_id=user_id,
            item_detail=TREASURE_ITEM_DETAIL,
            current_found_item_idx=[1, 2],
            current_step=3,
            mission_status=MissionStatus.COMPLETED.value,
        )
    )
    db_session.commit()


def _request_home(client: TestClient) -> dict:
    response = client.get(
        ENDPOINT, params={"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE}
    )
    assert response.status_code == 200
    return response.json()


def _expected_distance(location: Location) -> tuple[int, int]:
    meter = distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, location.my, location.mx
    )
    return meter, distance.calculate_duration_minutes(meter)


# ---------------------------------------------------------------------
# 응답 형식
# ---------------------------------------------------------------------


def test_홈을_조회하면_명세의_필드를_모두_반환한다(
    client: TestClient, home_data: None
) -> None:
    body = _request_home(client)

    assert set(body) == {
        "missionRecommend",
        "progressMission",
        "guestbookCount",
        "characterImgUrl",
    }
    assert body["characterImgUrl"] == CHARACTER_IMG_URL
    assert body["progressMission"] == []
    assert body["guestbookCount"] == 0

    assert len(body["missionRecommend"]) == 3
    for mission in body["missionRecommend"]:
        assert set(mission) == {
            "missionId",
            "missionType",
            "missionTitle",
            "locationTitle",
            "location",
            "distanceMeter",
            "durationMinutes",
        }


# ---------------------------------------------------------------------
# 추천 미션
# ---------------------------------------------------------------------


def test_추천_미션의_missionId는_미션_유형별_테이블의_id다(
    client: TestClient, home_data: None
) -> None:
    # MISSION(유형 분류) id가 아니라 유형별 테이블의 id가 나가야 한다.
    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    assert by_type["CULTURE"]["missionId"] == CULTURE_MISSION_ID
    assert by_type["COOPERATIVE"]["missionId"] == COOPERATIVE_MISSION_ID
    assert by_type["TREASURE"]["missionId"] == TREASURE_MISSION_ID


def test_추천_미션의_유형과_이름은_공통_미션_정보를_따른다(
    client: TestClient, home_data: None
) -> None:
    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    assert by_type["CULTURE"]["missionTitle"] == "제주 문화 퀴즈"
    assert by_type["COOPERATIVE"]["missionTitle"] == "함께 키우는 귤나무"
    assert by_type["TREASURE"]["missionTitle"] == "보물 찾기"


def test_추천_미션은_문화_협동_보물_유형을_한_건씩_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 유형별 후보가 여러 건이어도 유형마다 한 건씩만 추천한다.
    _add_near_missions(db_session)

    body = _request_home(client)

    assert [mission["missionType"] for mission in body["missionRecommend"]] == [
        "CULTURE",
        "COOPERATIVE",
        "TREASURE",
    ]


def test_추천_문화_미션은_DB의_문화_미션_중_하나로_선정된다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 문화 미션은 장소가 없어 랜덤으로 고르므로 값 자체가 아니라 DB에 있는 미션인지로 검증한다.
    db_session.add(
        CultureMission(
            id=SECOND_CULTURE_MISSION_ID,
            mission_id=CULTURE_TYPE_ID,
            quiz_total_count=5,
            quiz_detail=[],
            reward_detail=REWARD_DETAIL,
        )
    )
    db_session.commit()
    saved = {row.id for row in db_session.query(CultureMission).all()}

    for _ in range(10):
        by_type = {
            mission["missionType"]: mission
            for mission in _request_home(client)["missionRecommend"]
        }
        assert by_type["CULTURE"]["missionId"] in saved


def test_협동과_보물찾기는_장소가_가장_가까운_미션을_추천한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    _add_near_missions(db_session)

    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    assert by_type["COOPERATIVE"]["missionId"] == NEAR_COOPERATIVE_MISSION_ID
    assert by_type["TREASURE"]["missionId"] == NEAR_TREASURE_MISSION_ID
    assert by_type["COOPERATIVE"]["distanceMeter"] == 0
    assert by_type["TREASURE"]["distanceMeter"] == 0


def test_이미_완료한_협동_미션은_추천하지_않는다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 가장 가까운 협동 미션을 완료해 두면 그다음으로 가까운 미션이 추천된다.
    _add_near_missions(db_session)
    _complete_cooperative_mission(db_session, NEAR_COOPERATIVE_MISSION_ID, progress_id=1)

    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    assert by_type["COOPERATIVE"]["missionId"] == COOPERATIVE_MISSION_ID


def test_이미_완료한_보물찾기_미션은_추천하지_않는다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    _add_near_missions(db_session)
    _complete_treasure_mission(db_session, NEAR_TREASURE_MISSION_ID, progress_id=1)

    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    assert by_type["TREASURE"]["missionId"] == TREASURE_MISSION_ID


def test_다른_사용자의_완료_이력은_추천에서_제외하지_않는다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 완료 이력은 현재 사용자 기준으로만 판단한다.
    _add_near_missions(db_session)
    _complete_treasure_mission(
        db_session, NEAR_TREASURE_MISSION_ID, progress_id=1, user_id=OTHER_USER_ID
    )
    _complete_cooperative_mission(
        db_session, NEAR_COOPERATIVE_MISSION_ID, progress_id=1, user_id=OTHER_USER_ID
    )

    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    assert by_type["TREASURE"]["missionId"] == NEAR_TREASURE_MISSION_ID
    assert by_type["COOPERATIVE"]["missionId"] == NEAR_COOPERATIVE_MISSION_ID


def test_추천할_후보가_없는_유형은_추천_목록에서_제외한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 협동/보물 찾기 미션을 모두 완료하면 문화 미션만 추천된다.
    _complete_cooperative_mission(db_session, COOPERATIVE_MISSION_ID, progress_id=1)
    _complete_treasure_mission(db_session, TREASURE_MISSION_ID, progress_id=1)

    body = _request_home(client)

    assert [mission["missionType"] for mission in body["missionRecommend"]] == ["CULTURE"]


def test_장소가_있는_추천_미션은_좌표와_거리_예상_소요_시간을_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    saved_location = db_session.get(Location, SAEBYEOL_LOCATION_ID)
    assert saved_location is not None
    expected_meter, expected_minutes = _expected_distance(saved_location)

    cooperative = by_type["COOPERATIVE"]
    assert cooperative["locationTitle"] == "새별 오름"
    # DB는 my=위도 / mx=경도로 저장하고 응답은 lat / lng 로 나간다.
    assert cooperative["location"] == {"lat": saved_location.my, "lng": saved_location.mx}
    assert cooperative["distanceMeter"] == expected_meter
    assert cooperative["durationMinutes"] == expected_minutes


def test_문화_미션은_장소가_없어_장소_관련_필드가_모두_null이다(
    client: TestClient, home_data: None
) -> None:
    body = _request_home(client)
    by_type = {mission["missionType"]: mission for mission in body["missionRecommend"]}

    culture = by_type["CULTURE"]
    assert culture["locationTitle"] is None
    assert culture["location"] is None
    assert culture["distanceMeter"] is None
    assert culture["durationMinutes"] is None


# ---------------------------------------------------------------------
# 진행 중인 미션
# ---------------------------------------------------------------------


def test_진행_중인_문화_미션을_퀴즈_단계와_함께_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    db_session.add(
        CultureMissionProgress(
            id=1,
            culture_mission_id=CULTURE_MISSION_ID,
            user_id=CURRENT_USER_ID,
            mission_status=MissionStatus.IN_PROGRESS.value,
            current_quiz_index=2,
            correct_number=1,
        )
    )
    db_session.commit()

    body = _request_home(client)

    assert len(body["progressMission"]) == 1
    progress = body["progressMission"][0]
    assert set(progress) == {
        "missionId",
        "missionType",
        "missionTitle",
        "locationTitle",
        "distanceMeter",
        "durationMinutes",
        "totalStep",
        "currentStep",
    }
    assert progress["missionId"] == CULTURE_MISSION_ID
    assert progress["missionType"] == "CULTURE"
    # 문화 미션의 전체 단계는 step_detail(3)이 아니라 퀴즈 총 개수(5)를 쓴다.
    assert progress["totalStep"] == 5
    assert progress["currentStep"] == 2
    # 문화 미션은 장소가 없다.
    assert progress["locationTitle"] is None
    assert progress["distanceMeter"] is None
    assert progress["durationMinutes"] is None


def test_진행_중인_보물찾기_미션을_장소와_현재_단계와_함께_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 보물 찾기 진행 단계는 1 | 2 | 3 이고 3이 완료 단계다.
    db_session.add(
        TreasureMissionProgress(
            id=1,
            treasure_mission_id=TREASURE_MISSION_ID,
            user_id=CURRENT_USER_ID,
            item_detail=TREASURE_ITEM_DETAIL,
            current_found_item_idx=[1],
            current_step=2,
            mission_status=MissionStatus.IN_PROGRESS.value,
        )
    )
    db_session.commit()

    saved_location = db_session.get(Location, SEONGSAN_LOCATION_ID)
    assert saved_location is not None
    expected_meter, expected_minutes = _expected_distance(saved_location)

    body = _request_home(client)

    assert len(body["progressMission"]) == 1
    progress = body["progressMission"][0]
    assert progress["missionId"] == TREASURE_MISSION_ID
    assert progress["missionType"] == "TREASURE"
    assert progress["locationTitle"] == "성산일출봉"
    assert progress["distanceMeter"] == expected_meter
    assert progress["durationMinutes"] == expected_minutes
    # 보물 찾기는 공통 미션 단계 정보(step_detail 개수)를 쓴다.
    assert progress["totalStep"] == 3
    assert progress["currentStep"] == 2


def test_참여자로_등록된_협동_미션을_진행_중_미션으로_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 협동 미션 진행도에는 user_id 가 없으므로 참여자를 통해 찾아야 한다.
    db_session.add(
        CooperativeMissionProgress(
            id=1,
            cooperative_mission_id=COOPERATIVE_MISSION_ID,
            current_step=3,
            mission_status=MissionStatus.IN_PROGRESS.value,
            team_token="team-token-1",
        )
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=1,
            cooperative_mission_progress_id=1,
            user_id=CURRENT_USER_ID,
            participant_status=ParticipantStatus.ACCEPTED.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
    )
    db_session.commit()

    body = _request_home(client)

    assert len(body["progressMission"]) == 1
    progress = body["progressMission"][0]
    assert progress["missionId"] == COOPERATIVE_MISSION_ID
    assert progress["missionType"] == "COOPERATIVE"
    assert progress["locationTitle"] == "새별 오름"
    assert progress["totalStep"] == 4
    assert progress["currentStep"] == 3


def test_세_유형의_진행_중_미션을_모두_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    db_session.add_all(
        [
            CultureMissionProgress(
                id=1,
                culture_mission_id=CULTURE_MISSION_ID,
                user_id=CURRENT_USER_ID,
                mission_status=MissionStatus.IN_PROGRESS.value,
                current_quiz_index=1,
                correct_number=0,
            ),
            TreasureMissionProgress(
                id=1,
                treasure_mission_id=TREASURE_MISSION_ID,
                user_id=CURRENT_USER_ID,
                item_detail=TREASURE_ITEM_DETAIL,
                current_found_item_idx=[],
                current_step=1,
                mission_status=MissionStatus.IN_PROGRESS.value,
            ),
            CooperativeMissionProgress(
                id=1,
                cooperative_mission_id=COOPERATIVE_MISSION_ID,
                current_step=1,
                mission_status=MissionStatus.IN_PROGRESS.value,
                team_token="team-token-1",
            ),
        ]
    )
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            id=1,
            cooperative_mission_progress_id=1,
            user_id=CURRENT_USER_ID,
            participant_status=ParticipantStatus.ACCEPTED.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
    )
    db_session.commit()

    body = _request_home(client)

    assert {progress["missionType"] for progress in body["progressMission"]} == {
        "CULTURE",
        "TREASURE",
        "COOPERATIVE",
    }


def test_완료된_미션과_다른_사용자의_미션은_진행_중_미션에_포함하지_않는다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    db_session.add_all(
        [
            # 현재 사용자지만 이미 완료한 미션
            CultureMissionProgress(
                id=1,
                culture_mission_id=CULTURE_MISSION_ID,
                user_id=CURRENT_USER_ID,
                mission_status=MissionStatus.COMPLETED.value,
                current_quiz_index=5,
                correct_number=5,
                completed_at=datetime(2026, 8, 20, 12, 0, 0),
            ),
            # 진행 중이지만 다른 사용자의 미션
            TreasureMissionProgress(
                id=1,
                treasure_mission_id=TREASURE_MISSION_ID,
                user_id=OTHER_USER_ID,
                item_detail=TREASURE_ITEM_DETAIL,
                current_found_item_idx=[],
                current_step=1,
                mission_status=MissionStatus.IN_PROGRESS.value,
            ),
        ]
    )
    db_session.commit()

    body = _request_home(client)

    assert body["progressMission"] == []


# ---------------------------------------------------------------------
# 방명록 개수 / 캐릭터 / 사용자 없음
# ---------------------------------------------------------------------


def test_방명록_개수는_전체_방명록에서_삭제된_것을_뺀_값이다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    db_session.add_all(
        [
            Guestbook(
                id=1,
                user_id=CURRENT_USER_ID,
                location_id=SEONGSAN_LOCATION_ID,
                visited_at=date(2026, 8, 19),
                saved_at=datetime(2026, 8, 19, 8, 30, 0),
            ),
            # 다른 사용자의 방명록도 개수에 포함된다. (서비스에 쌓인 전체 수)
            Guestbook(
                id=2,
                user_id=OTHER_USER_ID,
                location_id=SEONGSAN_LOCATION_ID,
                visited_at=date(2026, 8, 20),
                saved_at=datetime(2026, 8, 20, 9, 0, 0),
            ),
            # 삭제된 방명록은 제외된다.
            Guestbook(
                id=3,
                user_id=CURRENT_USER_ID,
                location_id=SEONGSAN_LOCATION_ID,
                visited_at=date(2026, 8, 21),
                saved_at=datetime(2026, 8, 21, 9, 0, 0),
                deleted_at=datetime(2026, 8, 21, 20, 0, 0),
            ),
            RoadGuestbook(
                id=1,
                user_id=CURRENT_USER_ID,
                location_id=None,
                location_alias="이름 모를 돌담길",
                visited_at=date(2026, 8, 18),
                mx=126.5312,
                my=33.5001,
                saved_at=datetime(2026, 8, 18, 10, 25, 0),
            ),
            RoadGuestbook(
                id=2,
                user_id=CURRENT_USER_ID,
                location_id=None,
                location_alias="구좌 당근밭 앞",
                visited_at=date(2026, 8, 18),
                mx=126.7550,
                my=33.5410,
                saved_at=datetime(2026, 8, 18, 14, 10, 0),
                deleted_at=datetime(2026, 8, 18, 21, 0, 0),
            ),
        ]
    )
    db_session.commit()

    body = _request_home(client)

    # 일반 방명록 2건 + 길 위의 방명록 1건
    assert body["guestbookCount"] == 3


def test_배정된_캐릭터가_없으면_characterImgUrl은_null이다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.ar_character_id = None
    db_session.commit()

    body = _request_home(client)

    assert body["characterImgUrl"] is None


def test_토큰의_사용자가_없으면_401_UNAUTHORIZED_USER로_응답한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 현재 사용자는 액세스 토큰으로 정하고, 토큰의 사용자가 없으면 조회 자체를 막는다.
    db_session.query(User).filter(User.id == CURRENT_USER_ID).delete()
    db_session.commit()

    response = client.get(ENDPOINT, params={"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE})

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


# ---------------------------------------------------------------------
# 잘못된 요청
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"longitude": USER_LONGITUDE}, id="위도_누락"),
        pytest.param({"latitude": USER_LATITUDE}, id="경도_누락"),
        pytest.param({"latitude": "제주", "longitude": USER_LONGITUDE}, id="위도_타입_오류"),
        pytest.param({"latitude": 100, "longitude": USER_LONGITUDE}, id="위도_범위_초과"),
        pytest.param({"latitude": USER_LATITUDE, "longitude": 200}, id="경도_범위_초과"),
    ],
)
def test_위치_정보가_잘못되면_400_INVALID_REQUEST로_응답한다(
    client: TestClient, home_data: None, params: dict[str, object]
) -> None:
    response = client.get(ENDPOINT, params=params)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
