"""미션 보상(`reward_detail`) 응답 스키마와 조합 로직.

`reward_detail` 은 문화/협동/보물 찾기 세 유형별 세부 미션 테이블이 모두 같은 형태로 갖는 컬럼이라
응답 형식과 조합 규칙을 세 도메인이 공유한다. 그래서 공용 모듈에 한 번만 두고 import해서 쓴다.

- `ar_character_id` 가 있으면 `AR_CHARACTER` 를 조회해 캐릭터 정보를 조합한다. 없으면 `null`
- 포인트 보상이 없으면 `0`
- 쿠폰 보상이 없으면 `null`
"""

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
        ar_character=_to_ar_character(db, reward.get("ar_character_id")),
        point=reward.get("point") or 0,
        coupon=_to_coupon(reward),
    )


def _to_ar_character(db: Session, ar_character_id: int | None) -> ArCharacterResponse | None:
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


def _to_coupon(reward: dict[str, Any]) -> CouponResponse | None:
    """쿠폰 보상 정보를 조합한다. 쿠폰 보상이 없으면 `None`."""
    coupon_location = reward.get("coupon_location")
    coupon_price = reward.get("coupon_price")
    if not coupon_location or coupon_price is None:
        return None

    return CouponResponse(coupon_location=coupon_location, coupon_price=coupon_price)
