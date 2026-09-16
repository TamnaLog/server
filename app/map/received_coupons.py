"""지도 홈에서 현재 사용자가 받은 쿠폰을 장소별로 찾는 조회 로직."""

from collections import defaultdict
from collections.abc import Collection
from typing import Any

from sqlalchemy import literal, select, union_all
from sqlalchemy.orm import Session

from app.common import rewards
from app.cooperative_mission.models import (
    CooperativeMission,
    CooperativeMissionParticipant,
    CooperativeMissionProgress,
    ParticipantStatus,
)
from app.culture_mission.models import CultureMission, CultureMissionProgress
from app.treasure_mission.models import TreasureMission, TreasureMissionProgress


def find_received_coupon_prices_by_location(
    db: Session,
    current_user_id: int,
    location_titles: Collection[str],
) -> dict[str, list[int]]:
    """화면 안 장소에서 사용할 수 있는 수령 쿠폰 금액을 장소명별로 반환한다.

    쿠폰 테이블이 따로 없으므로 세 미션 유형의 `reward_detail`과 진행도의
    `coupon_reward_granted`를 조합한다. 세 조회를 `UNION ALL`로 묶어 DB 왕복은
    한 번만 하고, 화면 안 장소명과 완전히 같은 쿠폰만 DB에서 가져온다.

    같은 세부 미션을 여러 번 완료한 이력이 있으면 쿠폰 한 건으로 취급한다.
    서로 다른 미션에서 같은 장소의 쿠폰을 받았다면 각 쿠폰을 모두 유지한다.
    """
    titles = set(location_titles)
    if not titles:
        return {}

    culture = (
        select(
            literal("CULTURE").label("mission_type"),
            CultureMission.id.label("mission_id"),
            CultureMission.reward_detail.label("reward_detail"),
        )
        .join(
            CultureMissionProgress,
            CultureMissionProgress.culture_mission_id == CultureMission.id,
        )
        .where(
            CultureMissionProgress.user_id == current_user_id,
            CultureMissionProgress.coupon_reward_granted.is_(True),
            CultureMission.reward_detail["coupon_location"].as_string().in_(titles),
        )
    )
    treasure = (
        select(
            literal("TREASURE").label("mission_type"),
            TreasureMission.id.label("mission_id"),
            TreasureMission.reward_detail.label("reward_detail"),
        )
        .join(
            TreasureMissionProgress,
            TreasureMissionProgress.treasure_mission_id == TreasureMission.id,
        )
        .where(
            TreasureMissionProgress.user_id == current_user_id,
            TreasureMissionProgress.coupon_reward_granted.is_(True),
            TreasureMission.reward_detail["coupon_location"].as_string().in_(titles),
        )
    )
    cooperative = (
        select(
            literal("COOPERATIVE").label("mission_type"),
            CooperativeMission.id.label("mission_id"),
            CooperativeMission.reward_detail.label("reward_detail"),
        )
        .join(
            CooperativeMissionProgress,
            CooperativeMissionProgress.cooperative_mission_id == CooperativeMission.id,
        )
        .join(
            CooperativeMissionParticipant,
            CooperativeMissionParticipant.cooperative_mission_progress_id
            == CooperativeMissionProgress.id,
        )
        .where(
            CooperativeMissionParticipant.user_id == current_user_id,
            CooperativeMissionParticipant.participant_status
            == ParticipantStatus.ACCEPTED.value,
            CooperativeMissionParticipant.deleted_at.is_(None),
            CooperativeMissionProgress.coupon_reward_granted.is_(True),
            CooperativeMissionProgress.deleted_at.is_(None),
            CooperativeMission.reward_detail["coupon_location"].as_string().in_(titles),
        )
    )

    rows = sorted(
        db.execute(union_all(culture, treasure, cooperative)).all(),
        key=lambda row: (row.mission_type, row.mission_id),
    )
    prices_by_location: defaultdict[str, list[int]] = defaultdict(list)
    seen_missions: set[tuple[str, int]] = set()
    for mission_type, mission_id, reward_detail in rows:
        mission_key = (mission_type, mission_id)
        if mission_key in seen_missions:
            continue
        seen_missions.add(mission_key)

        coupon = rewards.to_coupon(_as_reward_detail(reward_detail))
        if coupon is not None:
            prices_by_location[coupon.coupon_location].append(coupon.coupon_price)

    return dict(prices_by_location)


def _as_reward_detail(value: Any) -> dict[str, Any]:
    """UNION 결과의 JSON 값을 보상 조합기가 기대하는 dict로 제한한다."""
    return value if isinstance(value, dict) else {}
