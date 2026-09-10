"""GET /api/v1/users/me/mypage - 마이페이지 조회 테스트.

기준 문서: app/mypage/docs/API_SPEC.md, app/mypage/docs/BUSINESS_RULES.md
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantRole,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.map.models import Location, VisitedLocation
from app.mission.models import Mission, MissionStatus
from app.treasure_mission.models import (
    AcquiredArCharacter,
    ArCharacter,
    TreasureMission,
    TreasureMissionProgress,
)
from app.user.models import User, UserTravelStyle
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


ENDPOINT = "/api/v1/users/me/mypage"

OTHER_USER_ID = 2

TRAVEL_STYLE_ID = 1
USER_TYPE = "기록 탐험가"
HASHTAGS = ["#인생샷", "#로컬탐방", "#자연"]

NICKNAME = "몽글몽글파도"
POINT = 1240
TARGET_STEP = 12000

# 공통 MISSION.id (유형별 세부 미션 id 와 일부러 다르게 둔다)
CULTURE_TYPE_ID = 1
COOPERATIVE_TYPE_ID = 2
TREASURE_TYPE_ID = 3

CULTURE_MISSION_ID = 11
COOPERATIVE_MISSION_ID = 12
TREASURE_MISSION_ID = 13

CULTURE_TITLE = "제주 문화 퀴즈"
COOPERATIVE_TITLE = "함께 키우는 귤나무"
TREASURE_TITLE = "성산일출봉 보물찾기"

LOCATION_ID = 39
LOCATION_TITLE = "성산일출봉"
OTHER_LOCATION_ID = 40
OTHER_LOCATION_TITLE = "귤림성"

CHARACTER_ID = 1
CHARACTER_NAME = "점박이 물범"
CHARACTER_IMG_URL = "https://example.com/ar-characters/1.png"
CHARACTER_STORY_TITLE = "제주 바다의 느긋한 안내자"
CHARACTER_DESCRIPTION = "제주 해안가에 살던 물범입니다."
CHARACTER_HASHTAGS = ["#제주바다", "#사진친구"]
CHARACTER_ACQUIRE_CONDITION = "보물찾기를 완료하면 만날 수 있어요."
CHARACTER_COLOR = "blue"

OTHER_CHARACTER_ID = 2
OTHER_CHARACTER_NAME = "귤나무 정령"

# 도감에 노출하는 캐릭터 id 범위(1~6) 밖의 캐릭터
OUT_OF_RANGE_CHARACTER_ID = 7

ACQUIRED_AT = datetime(2026, 8, 21, 14, 20, 0)


@pytest.fixture
def mypage_data(db_session: Session) -> None:
    """사용자 2명 + 장소 2곳 + 캐릭터 2개 + 유형별 미션 3개.

    진행도·획득 이력·방문 기록은 테스트마다 달라서 각 테스트에서 직접 만든다.
    """
    db_session.add_all(
        [
            UserTravelStyle(
                id=TRAVEL_STYLE_ID,
                user_type=USER_TYPE,
                type_description="설명",
                hashtags=HASHTAGS,
            ),
            ArCharacter(
                id=CHARACTER_ID,
                character_name=CHARACTER_NAME,
                character_description=CHARACTER_DESCRIPTION,
                character_story_title=CHARACTER_STORY_TITLE,
                acquire_condition=CHARACTER_ACQUIRE_CONDITION,
                character_img_url=CHARACTER_IMG_URL,
                character_color=CHARACTER_COLOR,
                hashtags=CHARACTER_HASHTAGS,
            ),
            ArCharacter(
                id=OTHER_CHARACTER_ID,
                character_name=OTHER_CHARACTER_NAME,
                character_description="귤밭을 지키는 정령입니다.",
                character_story_title="제주 귤밭의 작은 수호자",
                acquire_condition="협동 미션을 완료하면 만날 수 있어요.",
                character_img_url="https://example.com/ar-characters/2.png",
                # 색상이 없는 캐릭터도 있다. (character_color 는 nullable)
                hashtags=["#귤나무"],
            ),
            ArCharacter(
                id=OUT_OF_RANGE_CHARACTER_ID,
                character_name="범위 밖 캐릭터",
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="조건",
                character_img_url="https://example.com/ar-characters/7.png",
                character_color="grey",
                hashtags=["#범위밖"],
            ),
            Location(
                id=LOCATION_ID,
                content_id=126508,
                location_title=LOCATION_TITLE,
                location_address="제주특별자치도 서귀포시 성산읍",
                location_category="관광지",
                radius=300,
                mx=126.9331,
                my=33.4582,
            ),
            Location(
                id=OTHER_LOCATION_ID,
                content_id=126509,
                location_title=OTHER_LOCATION_TITLE,
                location_address="제주특별자치도 제주시",
                location_category="관광지",
                radius=300,
                mx=126.5312,
                my=33.5001,
            ),
            Mission(
                id=CULTURE_TYPE_ID,
                mission_type="CULTURE",
                mission_title=CULTURE_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "퀴즈", "description": "설명"}],
            ),
            Mission(
                id=COOPERATIVE_TYPE_ID,
                mission_type="COOPERATIVE",
                mission_title=COOPERATIVE_TITLE,
                description="설명",
                step_detail=[
                    {"step": 1, "step_title": "초대", "description": "설명"},
                    {"step": 2, "step_title": "역할", "description": "설명"},
                    {"step": 3, "step_title": "완성", "description": "설명"},
                    {"step": 4, "step_title": "정리", "description": "설명"},
                ],
            ),
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title=TREASURE_TITLE,
                description="설명",
                step_detail=[{"step": 1, "step_title": "탐색", "description": "설명"}],
            ),
        ]
    )
    db_session.add_all(
        [
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname=NICKNAME,
                point=POINT,
                target_step=TARGET_STEP,
                user_travel_style_id=TRAVEL_STYLE_ID,
                ar_character_id=CHARACTER_ID,
            ),
            User(
                id=OTHER_USER_ID,
                access_token_hash=access_token_hash(OTHER_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
        ]
    )
    db_session.commit()

    db_session.add_all(
        [
            CultureMission(
                id=CULTURE_MISSION_ID,
                mission_id=CULTURE_TYPE_ID,
                quiz_total_count=5,
                quiz_detail=[],
                reward_detail={"ar_character_id": CHARACTER_ID, "point": 100},
            ),
            CooperativeMission(
                id=COOPERATIVE_MISSION_ID,
                mission_id=COOPERATIVE_TYPE_ID,
                location_id=OTHER_LOCATION_ID,
                reward_detail={"ar_character_id": OTHER_CHARACTER_ID, "point": 150},
            ),
            TreasureMission(
                id=TREASURE_MISSION_ID,
                mission_id=TREASURE_TYPE_ID,
                location_id=LOCATION_ID,
                item_total_count=3,
                reward_detail={"ar_character_id": CHARACTER_ID, "point": 100},
            ),
        ]
    )
    db_session.commit()


def _add_visit(
    db_session: Session,
    *,
    location_id: int = LOCATION_ID,
    user_id: int = CURRENT_USER_ID,
    visited_at: datetime = datetime(2026, 8, 21, 10, 0, 0),
) -> None:
    db_session.add(
        VisitedLocation(
            user_id=user_id, location_id=location_id, visited_at=visited_at
        )
    )
    db_session.commit()


def _add_culture_progress(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.IN_PROGRESS,
    current_quiz_index: int = 2,
) -> None:
    db_session.add(
        CultureMissionProgress(
            culture_mission_id=CULTURE_MISSION_ID,
            user_id=user_id,
            mission_status=mission_status.value,
            current_quiz_index=current_quiz_index,
        )
    )
    db_session.commit()


def _add_treasure_progress(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.IN_PROGRESS,
    found_item_idx: list[int] | None = None,
) -> None:
    db_session.add(
        TreasureMissionProgress(
            treasure_mission_id=TREASURE_MISSION_ID,
            user_id=user_id,
            item_detail=[],
            current_found_item_idx=[1] if found_item_idx is None else found_item_idx,
            current_step=1,
            mission_status=mission_status.value,
        )
    )
    db_session.commit()


def _add_cooperative_progress(
    db_session: Session,
    *,
    user_id: int = CURRENT_USER_ID,
    mission_status: MissionStatus = MissionStatus.IN_PROGRESS,
    current_step: int = 2,
    participant_status: ParticipantStatus = ParticipantStatus.ACCEPTED,
    progress_deleted_at: datetime | None = None,
    participant_deleted_at: datetime | None = None,
) -> None:
    progress = CooperativeMissionProgress(
        cooperative_mission_id=COOPERATIVE_MISSION_ID,
        current_step=current_step,
        mission_status=mission_status.value,
        team_token=f"team-{user_id}-{mission_status.value}-{current_step}",
        deleted_at=progress_deleted_at,
    )
    db_session.add(progress)
    db_session.flush()
    db_session.add(
        CooperativeMissionParticipant(
            cooperative_mission_progress_id=progress.id,
            user_id=user_id,
            participant_status=participant_status.value,
            participant_role=ParticipantRole.HOST.value,
            joined_at=datetime(2026, 8, 20, 10, 0, 0),
            deleted_at=participant_deleted_at,
        )
    )
    db_session.commit()


def _add_acquired(
    db_session: Session,
    *,
    ar_character_id: int = CHARACTER_ID,
    user_id: int = CURRENT_USER_ID,
    acquired_mission_id: int = TREASURE_TYPE_ID,
    created_at: datetime = ACQUIRED_AT,
) -> None:
    db_session.add(
        AcquiredArCharacter(
            ar_character_id=ar_character_id,
            user_id=user_id,
            acquired_mission_id=acquired_mission_id,
            created_at=created_at,
        )
    )
    db_session.commit()


def _get(client: TestClient, user_id: int = CURRENT_USER_ID) -> dict:
    response = client.get(ENDPOINT, headers=auth_headers(user_id))
    assert response.status_code == 200
    return response.json()


def _character(body: dict, character_id: int = CHARACTER_ID) -> dict[str, Any]:
    found = [item for item in body["arCharacters"] if item["id"] == character_id]
    assert found, f"도감에 캐릭터 {character_id} 가 없습니다."
    return found[0]


# ---------------------------------------------------------------------
# 프로필
# ---------------------------------------------------------------------


def test_프로필에_닉네임_여행유형_대표캐릭터를_반환한다(
    client: TestClient, mypage_data: None
) -> None:
    assert _get(client)["profile"] == {
        "nickname": NICKNAME,
        "travelStyle": {"userType": USER_TYPE, "hashtags": HASHTAGS},
        "selectedArCharacter": {
            "id": CHARACTER_ID,
            "name": CHARACTER_NAME,
            "imageUrl": CHARACTER_IMG_URL,
            "characterColor": CHARACTER_COLOR,
        },
    }


def test_여행_유형이_없으면_travelStyle이_통째로_null이다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.user_travel_style_id = None
    db_session.commit()

    assert _get(client)["profile"]["travelStyle"] is None


def test_대표_캐릭터가_없으면_selectedArCharacter가_null이다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.ar_character_id = None
    db_session.commit()

    assert _get(client)["profile"]["selectedArCharacter"] is None


def test_닉네임이_없으면_null이다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.nickname = None
    db_session.commit()

    assert _get(client)["profile"]["nickname"] is None


def test_배정만_되고_획득하지_않은_캐릭터도_대표_캐릭터가_된다(
    client: TestClient, mypage_data: None
) -> None:
    # 획득 이력을 만들지 않았는데도 대표 캐릭터로 나온다.
    body = _get(client)

    assert body["profile"]["selectedArCharacter"]["id"] == CHARACTER_ID
    # 다만 도감에서는 미획득이다.
    assert _character(body)["isAcquired"] is False


# ---------------------------------------------------------------------
# 목표 걸음 수 / 요약 수치
# ---------------------------------------------------------------------


def test_목표_걸음_수는_USER의_설정값이다(
    client: TestClient, mypage_data: None
) -> None:
    assert _get(client)["dailyStep"] == {"targetStepCount": TARGET_STEP}


def test_포인트는_USER의_보유_포인트다(client: TestClient, mypage_data: None) -> None:
    assert _get(client)["summary"]["point"] == POINT


def test_방문_장소_수는_중복을_제외하고_센다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_visit(db_session, location_id=LOCATION_ID)
    _add_visit(db_session, location_id=LOCATION_ID, visited_at=datetime(2026, 8, 22, 9, 0, 0))
    _add_visit(db_session, location_id=OTHER_LOCATION_ID)

    # 같은 장소를 두 번 방문해도 한 곳이다.
    assert _get(client)["summary"]["visitedLocationCount"] == 2


def test_다른_사용자의_방문_기록은_세지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_visit(db_session, user_id=OTHER_USER_ID)

    assert _get(client)["summary"]["visitedLocationCount"] == 0


def test_완료_미션_수는_세_유형을_합산한다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_culture_progress(db_session, mission_status=MissionStatus.COMPLETED)
    _add_treasure_progress(db_session, mission_status=MissionStatus.COMPLETED)
    _add_cooperative_progress(db_session, mission_status=MissionStatus.COMPLETED)

    assert _get(client)["summary"]["completedMissionCount"] == 3


def test_진행_중인_미션은_완료_수에_넣지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_culture_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)
    _add_treasure_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)
    _add_cooperative_progress(db_session, mission_status=MissionStatus.IN_PROGRESS)

    assert _get(client)["summary"]["completedMissionCount"] == 0


def test_다른_사용자의_완료_미션은_세지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_culture_progress(
        db_session, user_id=OTHER_USER_ID, mission_status=MissionStatus.COMPLETED
    )
    _add_treasure_progress(
        db_session, user_id=OTHER_USER_ID, mission_status=MissionStatus.COMPLETED
    )
    _add_cooperative_progress(
        db_session, user_id=OTHER_USER_ID, mission_status=MissionStatus.COMPLETED
    )

    assert _get(client)["summary"]["completedMissionCount"] == 0


@pytest.mark.parametrize(
    ("participant_status", "progress_deleted_at", "participant_deleted_at", "reason"),
    [
        pytest.param(
            ParticipantStatus.PENDING, None, None, "수락하지_않은_참가", id="PENDING_참가"
        ),
        pytest.param(
            ParticipantStatus.ACCEPTED,
            datetime(2026, 8, 23, 9, 0, 0),
            None,
            "삭제된_방",
            id="삭제된_진행도",
        ),
        pytest.param(
            ParticipantStatus.ACCEPTED,
            None,
            datetime(2026, 8, 23, 9, 0, 0),
            "나간_참가자",
            id="삭제된_참가",
        ),
    ],
)
def test_협동_미션의_제외_대상은_완료_수에_넣지_않는다(
    client: TestClient,
    db_session: Session,
    mypage_data: None,
    participant_status: ParticipantStatus,
    progress_deleted_at: datetime | None,
    participant_deleted_at: datetime | None,
    reason: str,
) -> None:
    _add_cooperative_progress(
        db_session,
        mission_status=MissionStatus.COMPLETED,
        participant_status=participant_status,
        progress_deleted_at=progress_deleted_at,
        participant_deleted_at=participant_deleted_at,
    )

    assert _get(client)["summary"]["completedMissionCount"] == 0, reason


# ---------------------------------------------------------------------
# 진행 중인 미션
# ---------------------------------------------------------------------


def test_진행_중인_미션이_없으면_빈_배열이다(
    client: TestClient, mypage_data: None
) -> None:
    assert _get(client)["progressMissions"] == []


def test_문화_미션은_퀴즈_번호와_전체_퀴즈_수를_쓴다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_culture_progress(db_session, current_quiz_index=2)

    assert _get(client)["progressMissions"] == [
        {
            # 공통 MISSION.id 가 아니라 유형별 세부 미션 id 다.
            "missionId": CULTURE_MISSION_ID,
            "missionType": "CULTURE",
            "missionTitle": CULTURE_TITLE,
            "currentCount": 2,
            "totalCount": 5,
        }
    ]


def test_보물찾기_미션은_찾은_보물_수와_전체_보물_수를_쓴다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_treasure_progress(db_session, found_item_idx=[1, 3])

    assert _get(client)["progressMissions"] == [
        {
            "missionId": TREASURE_MISSION_ID,
            "missionType": "TREASURE",
            "missionTitle": TREASURE_TITLE,
            # 단계가 아니라 찾은 보물 목록의 길이다.
            "currentCount": 2,
            "totalCount": 3,
        }
    ]


def test_협동_미션은_현재_단계와_공통_미션의_전체_단계_수를_쓴다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_cooperative_progress(db_session, current_step=2)

    assert _get(client)["progressMissions"] == [
        {
            "missionId": COOPERATIVE_MISSION_ID,
            "missionType": "COOPERATIVE",
            "missionTitle": COOPERATIVE_TITLE,
            "currentCount": 2,
            # MISSION.step_detail 의 항목 수
            "totalCount": 4,
        }
    ]


def test_완료한_미션은_진행_중_목록에_넣지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_culture_progress(db_session, mission_status=MissionStatus.COMPLETED)
    _add_treasure_progress(db_session, mission_status=MissionStatus.COMPLETED)
    _add_cooperative_progress(db_session, mission_status=MissionStatus.COMPLETED)

    assert _get(client)["progressMissions"] == []


def test_다른_사용자의_진행_중인_미션은_넣지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_culture_progress(db_session, user_id=OTHER_USER_ID)
    _add_treasure_progress(db_session, user_id=OTHER_USER_ID)
    _add_cooperative_progress(db_session, user_id=OTHER_USER_ID)

    assert _get(client)["progressMissions"] == []


def test_협동_미션의_제외_대상은_진행_중_목록에도_넣지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_cooperative_progress(
        db_session, participant_deleted_at=datetime(2026, 8, 23, 9, 0, 0)
    )

    assert _get(client)["progressMissions"] == []


def test_세_유형이_모두_진행_중이면_모두_반환한다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_culture_progress(db_session)
    _add_treasure_progress(db_session)
    _add_cooperative_progress(db_session)

    types = [item["missionType"] for item in _get(client)["progressMissions"]]
    assert sorted(types) == ["COOPERATIVE", "CULTURE", "TREASURE"]


# ---------------------------------------------------------------------
# AR 캐릭터 도감
# ---------------------------------------------------------------------


def test_획득_여부와_관계없이_id_1_6_캐릭터를_id_오름차순으로_반환한다(
    client: TestClient, mypage_data: None
) -> None:
    assert [item["id"] for item in _get(client)["arCharacters"]] == [
        CHARACTER_ID,
        OTHER_CHARACTER_ID,
    ]


def test_id가_1_6_밖인_캐릭터는_도감에_넣지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    # 획득했고 보상 미션까지 설정돼 있어도 도감에는 넣지 않는다.
    _add_acquired(db_session, ar_character_id=OUT_OF_RANGE_CHARACTER_ID)
    mission = db_session.get(TreasureMission, TREASURE_MISSION_ID)
    assert mission is not None
    mission.reward_detail = {"ar_character_id": OUT_OF_RANGE_CHARACTER_ID, "point": 100}
    db_session.commit()

    body = _get(client)

    assert OUT_OF_RANGE_CHARACTER_ID not in [item["id"] for item in body["arCharacters"]]
    # 범위 밖 캐릭터를 보상으로 주는 미션도 도감의 다른 칸에 섞이지 않는다.
    assert [item["id"] for item in _character(body)["acquiredMissions"]] == [
        CULTURE_MISSION_ID
    ]


def test_id가_1_6_밖이어도_대표_캐릭터로는_반환한다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    """도감의 id 제한은 대표 캐릭터에 적용하지 않는다."""
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.ar_character_id = OUT_OF_RANGE_CHARACTER_ID
    db_session.commit()

    body = _get(client)

    assert body["profile"]["selectedArCharacter"]["id"] == OUT_OF_RANGE_CHARACTER_ID
    assert OUT_OF_RANGE_CHARACTER_ID not in [item["id"] for item in body["arCharacters"]]


def test_캐릭터_대표_색상을_대표_캐릭터와_도감에_모두_반환한다(
    client: TestClient, mypage_data: None
) -> None:
    body = _get(client)

    assert body["profile"]["selectedArCharacter"]["characterColor"] == CHARACTER_COLOR
    assert _character(body)["characterColor"] == CHARACTER_COLOR


def test_색상이_없는_캐릭터는_characterColor가_null이다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    user.ar_character_id = OTHER_CHARACTER_ID
    db_session.commit()

    body = _get(client)

    # 필드를 생략하지 않고 null 로 준다. (획득 여부와도 무관하다)
    assert body["profile"]["selectedArCharacter"]["characterColor"] is None
    assert _character(body, OTHER_CHARACTER_ID)["characterColor"] is None


def test_획득한_캐릭터는_획득_날짜와_장소를_함께_반환한다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_acquired(db_session, acquired_mission_id=TREASURE_TYPE_ID)

    assert _character(_get(client)) == {
        "id": CHARACTER_ID,
        "name": CHARACTER_NAME,
        "imageUrl": CHARACTER_IMG_URL,
        "characterColor": CHARACTER_COLOR,
        "isAcquired": True,
        "acquiredAt": "2026-08-21",
        "acquiredLocation": LOCATION_TITLE,
        "storyTitle": CHARACTER_STORY_TITLE,
        "storyContent": CHARACTER_DESCRIPTION,
        "hashtags": CHARACTER_HASHTAGS,
        "acquireCondition": CHARACTER_ACQUIRE_CONDITION,
        "acquiredMissions": [
            {
                "id": CULTURE_MISSION_ID,
                "missionType": "CULTURE",
                "missionTitle": CULTURE_TITLE,
            },
            {
                "id": TREASURE_MISSION_ID,
                "missionType": "TREASURE",
                "missionTitle": TREASURE_TITLE,
            },
        ],
    }


def test_미획득_캐릭터도_이름과_이미지와_이야기를_그대로_반환한다(
    client: TestClient, mypage_data: None
) -> None:
    character = _character(_get(client))

    assert character["isAcquired"] is False
    # 실루엣 처리는 프론트가 하므로 서버는 실제 값을 그대로 준다.
    assert character["name"] == CHARACTER_NAME
    assert character["imageUrl"] == CHARACTER_IMG_URL
    assert character["storyTitle"] == CHARACTER_STORY_TITLE
    assert character["storyContent"] == CHARACTER_DESCRIPTION
    assert character["hashtags"] == CHARACTER_HASHTAGS
    assert character["acquireCondition"] == CHARACTER_ACQUIRE_CONDITION
    assert character["acquiredMissions"] != []


def test_미획득_캐릭터는_획득_날짜와_장소가_null이다(
    client: TestClient, mypage_data: None
) -> None:
    character = _character(_get(client))

    assert character["acquiredAt"] is None
    assert character["acquiredLocation"] is None


def test_다른_사용자의_획득_이력은_반영되지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_acquired(db_session, user_id=OTHER_USER_ID)

    assert _character(_get(client))["isAcquired"] is False


def test_장소가_없는_문화_미션으로_획득했으면_장소가_null이다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_acquired(db_session, acquired_mission_id=CULTURE_TYPE_ID)

    character = _character(_get(client))
    assert character["isAcquired"] is True
    assert character["acquiredAt"] == "2026-08-21"
    # 문화 미션은 장소를 갖지 않는다.
    assert character["acquiredLocation"] is None


def test_협동_미션으로_획득했으면_그_미션의_장소를_반환한다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_acquired(
        db_session,
        ar_character_id=OTHER_CHARACTER_ID,
        acquired_mission_id=COOPERATIVE_TYPE_ID,
    )

    assert _character(_get(client), OTHER_CHARACTER_ID)["acquiredLocation"] == (
        OTHER_LOCATION_TITLE
    )


def test_획득_가능_미션은_공통_MISSION_id_오름차순이다(
    client: TestClient, mypage_data: None
) -> None:
    missions = _character(_get(client))["acquiredMissions"]

    # 문화(공통 1) → 보물찾기(공통 3) 순서다. 세부 미션 id 순서(11, 13)와는 별개다.
    assert [item["missionType"] for item in missions] == ["CULTURE", "TREASURE"]


def test_획득_가능_미션은_최대_3개다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    # 같은 캐릭터를 보상으로 주는 문화 미션을 3개 더 만든다. (총 5개)
    for index, mission_id in enumerate((4, 5, 6), start=1):
        db_session.add(
            Mission(
                id=mission_id,
                mission_type="CULTURE",
                mission_title=f"추가 퀴즈 {index}",
                description="설명",
                step_detail=[{"step": 1, "step_title": "퀴즈", "description": "설명"}],
            )
        )
        db_session.flush()
        db_session.add(
            CultureMission(
                id=100 + mission_id,
                mission_id=mission_id,
                quiz_total_count=3,
                quiz_detail=[],
                reward_detail={"ar_character_id": CHARACTER_ID},
            )
        )
    db_session.commit()

    missions = _character(_get(client))["acquiredMissions"]

    # 공통 MISSION.id 1, 3, 4 만 남는다. (5, 6 은 잘린다)
    assert len(missions) == 3
    assert [item["id"] for item in missions] == [
        CULTURE_MISSION_ID,
        TREASURE_MISSION_ID,
        104,
    ]


def test_보상으로_설정되지_않은_캐릭터는_획득_가능_미션이_빈_배열이다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    # 협동 미션의 보상 캐릭터를 없애면 2번 캐릭터를 주는 미션이 사라진다.
    mission = db_session.get(CooperativeMission, COOPERATIVE_MISSION_ID)
    assert mission is not None
    mission.reward_detail = {"point": 150}
    db_session.commit()

    assert _character(_get(client), OTHER_CHARACTER_ID)["acquiredMissions"] == []


def test_획득_여부는_획득_가능_미션_유무로_추론하지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    mission = db_session.get(CooperativeMission, COOPERATIVE_MISSION_ID)
    assert mission is not None
    mission.reward_detail = {"point": 150}
    db_session.commit()
    # 획득 가능 미션이 없어도 획득 이력이 있으면 획득 상태다.
    _add_acquired(db_session, ar_character_id=OTHER_CHARACTER_ID)

    character = _character(_get(client), OTHER_CHARACTER_ID)
    assert character["acquiredMissions"] == []
    assert character["isAcquired"] is True


# ---------------------------------------------------------------------
# N+1 / 읽기 전용
# ---------------------------------------------------------------------


def test_캐릭터가_늘어도_쿼리_수가_늘지_않는다(
    client: TestClient, db_session: Session, mypage_data: None, executed_queries: list[str]
) -> None:
    """도감·미션·획득 이력을 캐릭터마다 다시 조회하면 여기서 걸린다."""
    _add_acquired(db_session)

    executed_queries.clear()
    _get(client)
    before = len(executed_queries)

    # 도감에 나오는 id 범위(1~6) 안에서 캐릭터를 늘린다.
    for character_id in range(3, 7):
        db_session.add(
            ArCharacter(
                id=character_id,
                character_name=f"캐릭터 {character_id}",
                character_description="설명",
                character_story_title="이야기 제목",
                acquire_condition="조건",
                character_img_url=f"https://example.com/{character_id}.png",
                hashtags=["#태그"],
            )
        )
    db_session.commit()

    executed_queries.clear()
    body = _get(client)

    assert len(body["arCharacters"]) == 6
    assert len(executed_queries) == before


def test_조회는_데이터를_바꾸지_않는다(
    client: TestClient, db_session: Session, mypage_data: None
) -> None:
    _add_acquired(db_session)
    _add_visit(db_session)
    _add_culture_progress(db_session)

    _get(client)

    db_session.expire_all()
    user = db_session.get(User, CURRENT_USER_ID)
    assert user is not None
    assert (user.point, user.target_step) == (POINT, TARGET_STEP)
    assert len(list(db_session.scalars(select(AcquiredArCharacter)))) == 1
    assert len(list(db_session.scalars(select(VisitedLocation)))) == 1
    assert len(list(db_session.scalars(select(CultureMissionProgress)))) == 1


# ---------------------------------------------------------------------
# 401 UNAUTHORIZED_USER
# ---------------------------------------------------------------------


def test_인증_헤더가_없으면_401이다(client: TestClient, mypage_data: None) -> None:
    client.headers.pop("Authorization", None)

    response = client.get(ENDPOINT)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_토큰의_사용자가_없으면_401이다(
    client: TestClient, mypage_data: None
) -> None:
    response = client.get(ENDPOINT, headers=auth_headers(999))

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}


def test_문서에_401을_노출한다(client: TestClient) -> None:
    responses = client.get("/openapi.json").json()["paths"][ENDPOINT]["get"]["responses"]

    assert sorted(responses) == ["200", "401", "500"]
