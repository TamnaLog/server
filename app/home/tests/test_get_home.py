"""GET /api/v1/users/me/home - 홈 조회 테스트.

기준 문서: app/home/docs/API_SPEC.md, app/home/docs/BUSINESS_RULES.md
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import CURRENT_USER_ID
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantStatus,
    ParticipantType,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.guestbook.models import Guestbook, RoadGuestbook
from app.home import distance
from app.home.models import ArCharacter, Location, Mission, MissionStatus, User
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress


ENDPOINT = "/api/v1/users/me/home"

# 요청 기준 위치 (제주시청 근처)
USER_LATITUDE = 33.4996
USER_LONGITUDE = 126.5312

CHARACTER_IMG_URL = "https://example.com/images/characters/jacheongbi.png"

# 미션 id
CULTURE_MISSION_ID = 1
COOPERATIVE_MISSION_ID = 2
TREASURE_MISSION_ID = 3
NO_LOCATION_MISSION_ID = 4

OTHER_USER_ID = 2


def _step_detail(count: int) -> list[dict[str, object]]:
    return [
        {"step": index, "step_title": f"{index}단계", "description": "설명"}
        for index in range(1, count + 1)
    ]


REWARD_DETAIL = {
    "ar_character_id": 1,
    "point": 100,
    "coupon_location": "성산 해맞이 카페",
    "coupon_price": 2000,
}


@pytest.fixture
def home_data(db_session: Session) -> None:
    """홈 조회에 필요한 장소 / 미션 / 사용자 목업 데이터.

    진행도와 방명록은 각 테스트에서 필요한 만큼 따로 추가한다.
    """
    db_session.add_all(
        [
            ArCharacter(
                id=1,
                character_name="자청비 모티브 탐험가",
                character_description="기록 탐험가 캐릭터입니다.",
                acquire_condition="온보딩에서 기록형 여행 스타일을 선택하면 만날 수 있어요.",
                character_img_url=CHARACTER_IMG_URL,
                hashtags=["#인생사진"],
            ),
            Location(
                id=1,
                content_id=126508,
                location_title="성산일출봉",
                location_address="제주특별자치도 서귀포시 성산읍 일출로 284-12",
                location_category="자연",
                radius=300,
                mx=126.9410,
                my=33.4580,
            ),
            Location(
                id=2,
                content_id=126454,
                location_title="새별 오름",
                location_address="제주특별자치도 제주시 애월읍 봉성리 산59-8",
                location_category="오름",
                radius=500,
                mx=126.3577,
                my=33.3663,
            ),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            Mission(
                id=CULTURE_MISSION_ID,
                mission_type="CULTURE",
                mission_title="성산일출봉 화산 이야기",
                description="성산일출봉 문화 퀴즈 미션입니다.",
                location_id=1,
                reward_detail=REWARD_DETAIL,
                step_detail=_step_detail(3),
            ),
            Mission(
                id=COOPERATIVE_MISSION_ID,
                mission_type="COOPERATIVE",
                mission_title="함께 키우는 귤나무",
                description="팀원과 함께하는 협동 미션입니다.",
                location_id=2,
                reward_detail=REWARD_DETAIL,
                step_detail=_step_detail(4),
            ),
            Mission(
                id=TREASURE_MISSION_ID,
                mission_type="TREASURE",
                mission_title="보물 찾기",
                description="숨은 보물을 찾는 미션입니다.",
                location_id=2,
                reward_detail=REWARD_DETAIL,
                step_detail=_step_detail(3),
            ),
            Mission(
                id=NO_LOCATION_MISSION_ID,
                mission_type="CULTURE",
                mission_title="오늘의 제주 퀴즈",
                description="장소와 상관없이 푸는 퀴즈 미션입니다.",
                location_id=None,
                reward_detail=REWARD_DETAIL,
                step_detail=_step_detail(2),
            ),
            User(id=CURRENT_USER_ID, nickname="몽글몽글파도", point=0, ar_character_id=1),
            User(id=OTHER_USER_ID, nickname="한라봉주스", point=0),
        ]
    )
    db_session.flush()

    db_session.add_all(
        [
            CultureMission(mission_id=CULTURE_MISSION_ID, quiz_total_count=5, quiz_detail=[]),
            CultureMission(mission_id=NO_LOCATION_MISSION_ID, quiz_total_count=5, quiz_detail=[]),
            CooperativeMission(mission_id=COOPERATIVE_MISSION_ID, role_total_count=4),
            TreasureMission(
                mission_id=TREASURE_MISSION_ID, item_total_count=5, item_detail=[]
            ),
        ]
    )
    db_session.commit()


def _request_home(client: TestClient) -> dict[str, object]:
    response = client.get(
        ENDPOINT, params={"latitude": USER_LATITUDE, "longitude": USER_LONGITUDE}
    )
    assert response.status_code == 200
    return response.json()


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


def test_추천_미션은_DB에_존재하는_미션_중에서_선정된다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 추천 로직이 랜덤이므로 값 자체가 아니라 DB에 있는 미션인지로 검증한다.
    saved_missions = {
        mission.id: mission for mission in db_session.query(Mission).all()
    }

    body = _request_home(client)
    recommended = body["missionRecommend"]

    recommended_ids = [mission["missionId"] for mission in recommended]
    assert len(set(recommended_ids)) == len(recommended_ids)

    for mission in recommended:
        saved = saved_missions.get(mission["missionId"])
        assert saved is not None
        assert mission["missionTitle"] == saved.mission_title
        assert mission["missionType"] == saved.mission_type


def test_장소가_있는_추천_미션은_좌표와_거리_예상_소요_시간을_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    body = _request_home(client)

    located = [
        mission for mission in body["missionRecommend"] if mission["location"] is not None
    ]
    assert located, "장소가 있는 추천 미션이 하나도 없습니다."

    for mission in located:
        saved_location = db_session.get(Mission, mission["missionId"]).location
        assert saved_location is not None

        assert mission["locationTitle"] == saved_location.location_title
        assert mission["location"] == {
            "lat": saved_location.my,
            "lng": saved_location.mx,
        }

        expected_distance = distance.calculate_distance_meter(
            USER_LATITUDE, USER_LONGITUDE, saved_location.my, saved_location.mx
        )
        assert mission["distanceMeter"] == expected_distance
        assert mission["durationMinutes"] == distance.calculate_duration_minutes(
            expected_distance
        )


def test_장소가_없는_미션은_장소_관련_필드가_모두_null이다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 추천이 랜덤이므로 장소 없는 미션만 남겨서 반드시 추천되게 한다.
    db_session.query(CultureMission).filter(
        CultureMission.mission_id == CULTURE_MISSION_ID
    ).delete()
    db_session.query(CooperativeMission).delete()
    db_session.query(TreasureMission).delete()
    db_session.query(Mission).filter(Mission.id != NO_LOCATION_MISSION_ID).delete()
    db_session.commit()

    body = _request_home(client)

    assert len(body["missionRecommend"]) == 1
    mission = body["missionRecommend"][0]
    assert mission["missionId"] == NO_LOCATION_MISSION_ID
    assert mission["locationTitle"] is None
    assert mission["location"] is None
    assert mission["distanceMeter"] is None
    assert mission["durationMinutes"] is None


def test_진행_중인_문화_미션을_현재_퀴즈_단계와_함께_반환한다(
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
    assert progress["locationTitle"] == "성산일출봉"
    # 문화 미션의 전체 단계는 MISSION.step_detail이 아니라 퀴즈 총개수를 사용한다.
    assert progress["totalStep"] == 5
    assert progress["currentStep"] == 2


def test_진행_중인_보물찾기_미션을_현재_단계와_함께_반환한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    # 보물 찾기 진행 단계는 1 | 2 | 3 이고 3이 완료 단계다.
    db_session.add(
        TreasureMissionProgress(
            id=1,
            treasure_mission_id=TREASURE_MISSION_ID,
            user_id=CURRENT_USER_ID,
            current_found_item_idx=[1],
            current_step=2,
            mission_status=MissionStatus.IN_PROGRESS.value,
        )
    )
    db_session.commit()

    body = _request_home(client)

    assert len(body["progressMission"]) == 1
    progress = body["progressMission"][0]
    assert progress["missionId"] == TREASURE_MISSION_ID
    assert progress["missionType"] == "TREASURE"
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
            participant_type=ParticipantType.USER.value,
            user_id=CURRENT_USER_ID,
            participant_status=ParticipantStatus.ACCEPTED.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
        )
    )
    db_session.commit()

    body = _request_home(client)

    assert len(body["progressMission"]) == 1
    progress = body["progressMission"][0]
    assert progress["missionId"] == COOPERATIVE_MISSION_ID
    assert progress["missionType"] == "COOPERATIVE"
    assert progress["totalStep"] == 4
    assert progress["currentStep"] == 3


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
                current_found_item_idx=[],
                current_step=1,
                mission_status=MissionStatus.IN_PROGRESS.value,
            ),
        ]
    )
    db_session.commit()

    body = _request_home(client)

    assert body["progressMission"] == []


def test_방명록_개수는_전체_방명록에서_삭제된_것을_뺀_값이다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    db_session.add_all(
        [
            Guestbook(
                id=1,
                user_id=CURRENT_USER_ID,
                location_id=1,
                visited_at=date(2026, 8, 19),
                saved_at=datetime(2026, 8, 19, 8, 30, 0),
            ),
            # 다른 사용자의 방명록도 개수에 포함된다. (서비스에 쌓인 전체 수)
            Guestbook(
                id=2,
                user_id=OTHER_USER_ID,
                location_id=1,
                visited_at=date(2026, 8, 20),
                saved_at=datetime(2026, 8, 20, 9, 0, 0),
            ),
            # 삭제된 방명록은 제외된다.
            Guestbook(
                id=3,
                user_id=CURRENT_USER_ID,
                location_id=1,
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


def test_사용자_데이터가_없어도_홈_조회는_정상_동작한다(
    client: TestClient, db_session: Session, home_data: None
) -> None:
    db_session.query(User).filter(User.id == CURRENT_USER_ID).delete()
    db_session.commit()

    body = _request_home(client)

    assert body["characterImgUrl"] is None
    assert body["progressMission"] == []


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
