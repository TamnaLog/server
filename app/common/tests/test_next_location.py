"""app/common/next_location.py - 미션 완료 후 다음 장소 추천 로직 테스트.

API 를 거치지 않고 공용 추천 함수를 직접 호출해 추천 규칙만 검증한다.
(문화/보물/협동 미션 API 테스트는 각 도메인에서 응답 조합을 검증한다)
"""

import pytest
from sqlalchemy.orm import Session

from app.common import distance, next_location
from app.map.models import Location
from app.mission.models import Mission
from app.treasure_mission.models import TreasureMission


USER_LATITUDE = 33.4996
USER_LONGITUDE = 126.5312

TREASURE_TYPE_ID = 3
TREASURE_MISSION_ID = 21


@pytest.fixture(autouse=True)
def stub_location_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """장소 이미지 조회(TourAPI)를 막아 외부 네트워크를 타지 않게 한다."""
    monkeypatch.setattr(next_location, "get_location_image_url", lambda content_id: None)


def _location(location_id: int, *, lat_offset: float, lng_offset: float = 0.0) -> Location:
    """사용자 위치에서 위도/경도를 조금씩 옮긴 장소를 만든다."""
    return Location(
        id=location_id,
        content_id=100_000 + location_id,
        location_title=f"장소 {location_id}",
        location_address="제주특별자치도 제주시",
        location_category="관광지",
        radius=300,
        mx=USER_LONGITUDE + lng_offset,
        my=USER_LATITUDE + lat_offset,
    )


def test_사용자_위치에서_가장_가까운_장소를_추천한다(db_session: Session) -> None:
    db_session.add_all(
        [
            _location(1, lat_offset=0.05),
            _location(2, lat_offset=0.001),
            _location(3, lat_offset=0.01),
        ]
    )
    db_session.commit()

    result = next_location.recommend_next_location(db_session, USER_LATITUDE, USER_LONGITUDE)

    assert result is not None
    assert result.id == 2
    assert result.location_title == "장소 2"
    assert result.distance_meter == distance.calculate_distance_meter(
        USER_LATITUDE, USER_LONGITUDE, USER_LATITUDE + 0.001, USER_LONGITUDE
    )


def test_경도_차이도_거리에_반영해_가장_가까운_장소를_고른다(db_session: Session) -> None:
    # 위도 차이만 보면 1번이 가깝지만, 경도까지 따지면 2번이 가깝다.
    db_session.add_all(
        [
            _location(1, lat_offset=0.001, lng_offset=0.02),
            _location(2, lat_offset=0.003),
        ]
    )
    db_session.commit()

    result = next_location.recommend_next_location(db_session, USER_LATITUDE, USER_LONGITUDE)

    assert result is not None
    assert result.id == 2


def test_제외할_장소는_가장_가까워도_추천하지_않는다(db_session: Session) -> None:
    db_session.add_all([_location(1, lat_offset=0.0), _location(2, lat_offset=0.01)])
    db_session.commit()

    result = next_location.recommend_next_location(
        db_session, USER_LATITUDE, USER_LONGITUDE, exclude_location_id=1
    )

    assert result is not None
    assert result.id == 2


def test_거리가_같으면_id가_작은_장소를_추천한다(db_session: Session) -> None:
    # 사용자 위치를 기준으로 남/북으로 같은 거리에 둔다.
    db_session.add_all([_location(9, lat_offset=0.01), _location(4, lat_offset=-0.01)])
    db_session.commit()

    result = next_location.recommend_next_location(db_session, USER_LATITUDE, USER_LONGITUDE)

    assert result is not None
    assert result.id == 4


def test_추천할_장소가_없으면_None을_반환한다(db_session: Session) -> None:
    assert (
        next_location.recommend_next_location(db_session, USER_LATITUDE, USER_LONGITUDE) is None
    )


def test_제외한_장소_말고_장소가_없으면_None을_반환한다(db_session: Session) -> None:
    db_session.add(_location(1, lat_offset=0.0))
    db_session.commit()

    result = next_location.recommend_next_location(
        db_session, USER_LATITUDE, USER_LONGITUDE, exclude_location_id=1
    )

    assert result is None


def test_좌표_없는_추천은_기준_장소에서_가장_가까운_다른_장소를_고른다(
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            _location(1, lat_offset=0.0),
            _location(2, lat_offset=0.05),
            _location(3, lat_offset=0.002),
        ]
    )
    db_session.commit()
    base_location = db_session.get(Location, 1)
    assert base_location is not None

    result = next_location.recommend_next_location_summary(db_session, base_location)

    assert result is not None
    assert result.id == 3
    # 좌표 없는 추천은 거리를 내려주지 않는다.
    assert "distance_meter" not in result.model_dump()


def test_장소에_연결된_미션이_없으면_mission은_None이다(db_session: Session) -> None:
    db_session.add(_location(1, lat_offset=0.001))
    db_session.commit()

    result = next_location.recommend_next_location(db_session, USER_LATITUDE, USER_LONGITUDE)

    assert result is not None
    assert result.mission is None


def test_장소에_연결된_미션이_있으면_세부_미션_id와_유형을_반환한다(db_session: Session) -> None:
    db_session.add_all(
        [
            _location(1, lat_offset=0.001),
            Mission(
                id=TREASURE_TYPE_ID,
                mission_type="TREASURE",
                mission_title="보물 찾기",
                description="주변에 숨겨진 AR 보물을 찾아보세요.",
                step_detail=[{"step": 1, "step_title": "보물 찾기", "description": "설명"}],
            ),
        ]
    )
    db_session.flush()
    db_session.add(
        TreasureMission(
            id=TREASURE_MISSION_ID,
            mission_id=TREASURE_TYPE_ID,
            location_id=1,
            item_total_count=3,
            reward_detail={},
        )
    )
    db_session.commit()

    result = next_location.recommend_next_location(db_session, USER_LATITUDE, USER_LONGITUDE)

    assert result is not None
    assert result.mission is not None
    assert result.mission.id == TREASURE_MISSION_ID
    assert result.mission.mission_type == "TREASURE"
