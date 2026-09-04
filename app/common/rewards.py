"""미션 보상(`reward_detail`) 응답 스키마와 조합 로직.

`reward_detail` 은 문화/협동/보물 찾기 세 유형별 세부 미션 테이블이 모두 같은 형태로 갖는 컬럼이라
응답 형식과 조합 규칙을 세 도메인이 공유한다. 그래서 공용 모듈에 한 번만 두고 import해서 쓴다.

- `ar_character_id` 가 있으면 `AR_CHARACTER` 를 조회해 캐릭터 정보를 조합한다. 없으면 `null`
- 포인트 보상이 없으면 `0`
- 쿠폰 보상이 없으면 `null`

보상 3종을 항목별로 `null` 로 내려주는 응답은 `RewardItemsResponse` 를 상속해서 쓴다.

- `RemainingRewardResponse`: 아직 한 번도 지급되지 않은 보상 (미션 홈 조회)
- `GrantedRewardResponse`: 이번 요청으로 실제 지급된 보상 (미션 완료)

전체 보상(`RewardDetailResponse`)과 달리 두 응답은 해당 없는 항목이 포인트까지 `null` 이다.

보상 3종을 항목별 수령 여부와 함께 내려주는 응답은 `FullRewardDetailResponse` 를 쓴다.
(지도 미션 상세, 여행 마무리 엽서 요소 조회)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.orm import Session

from app.treasure_mission.models import ArCharacter


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ArCharacterResponse(CamelModel):
    """보상으로 획득할 AR 캐릭터."""

    id: int
    name: str
    image_url: str


class CouponResponse(CamelModel):
    """쿠폰 보상 정보."""

    coupon_location: str
    coupon_price: int


class RewardDetailResponse(CamelModel):
    """미션 완료 보상 정보.

    보상이 없는 항목은 캐릭터/쿠폰은 `null`, 포인트는 `0` 이다.
    """

    ar_character: ArCharacterResponse | None = None
    point: int = 0
    coupon: CouponResponse | None = None


def to_reward_detail(db: Session, reward_detail: dict[str, Any] | None) -> RewardDetailResponse:
    """세부 미션의 `reward_detail` 을 응답 형식으로 바꾼다."""
    reward = reward_detail or {}
    return RewardDetailResponse(
        ar_character=to_ar_character(db, reward.get("ar_character_id")),
        point=reward.get("point") or 0,
        coupon=to_coupon(reward),
    )


def to_ar_character(db: Session, ar_character_id: int | None) -> ArCharacterResponse | None:
    """보상 캐릭터 정보를 조합한다. 캐릭터 보상이 없으면 `None`."""
    if not ar_character_id:
        return None

    ar_character = db.get(ArCharacter, ar_character_id)
    if ar_character is None:
        # 보상에 적힌 캐릭터가 삭제된 경우. 미션 조회 자체를 실패시키지 않고 보상만 비운다.
        return None

    return ArCharacterResponse(
        id=ar_character.id,
        name=ar_character.character_name,
        image_url=ar_character.character_img_url,
    )


def to_coupon(reward: dict[str, Any]) -> CouponResponse | None:
    """쿠폰 보상 정보를 조합한다. 쿠폰 보상이 없으면 `None`."""
    coupon_location = reward.get("coupon_location")
    coupon_price = reward.get("coupon_price")
    if not coupon_location or coupon_price is None:
        return None

    return CouponResponse(coupon_location=coupon_location, coupon_price=coupon_price)


class ArCharacterRewardResponse(ArCharacterResponse):
    """AR 캐릭터 보상. 이미 받았어도 정보를 그대로 주고 `is_received` 로만 구분한다."""

    is_received: bool


class PointRewardResponse(CamelModel):
    """포인트 보상."""

    amount: int
    is_received: bool


class CouponRewardResponse(CouponResponse):
    """쿠폰 보상."""

    is_received: bool


class FullRewardDetailResponse(CamelModel):
    """미션의 **전체** 보상 정보와 현재 사용자의 수령 여부.

    아직 안 받은 보상만 주는 `RemainingRewardResponse` 와 달리 수령 여부와 관계없이
    세 종류를 모두 담고, 각 항목의 `is_received` 로 현재 사용자의 수령 여부를 구분한다.
    미션에 설정되지 않은 보상 항목만 `null` 이다.

    지도 미션 상세와 여행 마무리 엽서 요소 조회가 같은 형식을 쓴다.
    """

    ar_character: ArCharacterRewardResponse | None = None
    point: PointRewardResponse | None = None
    coupon: CouponRewardResponse | None = None


@dataclass(frozen=True)
class GrantedRewards:
    """미션의 과거 진행도 이력에서 한 번이라도 지급된 적이 있는 보상."""

    ar_character: bool = False
    point: bool = False
    coupon: bool = False


class RewardItemsResponse(CamelModel):
    """보상 3종을 항목별로 담는 응답 형태. 해당 없는 항목은 `null` 이다."""

    ar_character: ArCharacterResponse | None = None
    point: int | None = None
    coupon: CouponResponse | None = None


class RemainingRewardResponse(RewardItemsResponse):
    """아직 한 번도 지급되지 않은 미션 보상 정보.

    보상이 없거나 과거 진행도에서 한 번이라도 지급된 항목은 모두 `null` 이다.
    """


class GrantedRewardResponse(RewardItemsResponse):
    """이번 요청으로 실제 지급된 미션 보상 정보.

    지급하지 않은 항목은 모두 `null` 이다.
    """


class RewardItem(str, Enum):
    """보상 항목. 정의 순서가 곧 지급 순서다. (AR 캐릭터 → 포인트 → 쿠폰)"""

    AR_CHARACTER = "AR_CHARACTER"
    POINT = "POINT"
    COUPON = "COUPON"


def remaining_reward_items(
    db: Session, reward_detail: dict[str, Any] | None, granted: GrantedRewards
) -> list[RewardItem]:
    """아직 지급하지 않은 보상 항목을 지급 순서대로 반환한다.

    이미 지급된 항목과 `reward_detail` 에 없는 항목은 후보에서 뺀다.
    몇 개를 지급할지는 미션 유형마다 다르므로 각 도메인의 보상 지급 모듈에서 정한다.
    """
    reward = reward_detail or {}
    items = []
    if not granted.ar_character and to_ar_character(db, reward.get("ar_character_id")):
        items.append(RewardItem.AR_CHARACTER)
    if not granted.point and (reward.get("point") or 0) > 0:
        items.append(RewardItem.POINT)
    if not granted.coupon and to_coupon(reward):
        items.append(RewardItem.COUPON)
    return items


def to_remaining_reward(
    db: Session,
    reward_detail: dict[str, Any] | None,
    granted: GrantedRewards,
) -> RemainingRewardResponse:
    """세부 미션의 `reward_detail` 에서 아직 지급되지 않은 보상만 응답 형식으로 바꾼다."""
    reward = reward_detail or {}
    point = reward.get("point") or 0
    return RemainingRewardResponse(
        ar_character=(
            None if granted.ar_character else to_ar_character(db, reward.get("ar_character_id"))
        ),
        point=None if granted.point or point <= 0 else point,
        coupon=None if granted.coupon else to_coupon(reward),
    )


def to_full_reward_detail(
    db: Session, reward_detail: dict[str, Any] | None, granted: GrantedRewards
) -> FullRewardDetailResponse:
    """미션에 설정된 보상 전체와 현재 사용자의 수령 여부를 함께 담는다.

    이미 받은 보상도 정보를 지우지 않고 `is_received` 로만 구분한다.
    미션에 아예 없는 보상 항목만 `null` 이다.
    """
    reward = reward_detail or {}
    ar_character = to_ar_character(db, reward.get("ar_character_id"))
    coupon = to_coupon(reward)
    point = reward.get("point") or 0

    return FullRewardDetailResponse(
        ar_character=(
            ArCharacterRewardResponse(
                id=ar_character.id,
                name=ar_character.name,
                image_url=ar_character.image_url,
                is_received=granted.ar_character,
            )
            if ar_character
            else None
        ),
        point=(
            PointRewardResponse(amount=point, is_received=granted.point)
            if point > 0
            else None
        ),
        coupon=(
            CouponRewardResponse(
                coupon_location=coupon.coupon_location,
                coupon_price=coupon.coupon_price,
                is_received=granted.coupon,
            )
            if coupon
            else None
        ),
    )
