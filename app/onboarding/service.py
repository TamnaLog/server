"""온보딩 도메인 비즈니스 로직."""

from sqlalchemy.orm import Session

from app.onboarding import onboarding_matcher
from app.onboarding.models import ArCharacter, User, UserTravelStyle
from app.onboarding.schemas import (
    ArCharacterResponse,
    OnboardingSaveRequest,
    OnboardingSaveResponse,
    UserResponse,
    UserTravelStyleResponse,
)


def save_onboarding_info(
    db: Session, current_user_id: int, request: OnboardingSaveRequest
) -> OnboardingSaveResponse:
    """사용자 온보딩 정보 저장.

    - 온보딩을 진행한 경우: 선택값을 저장하고 여행 유형/AR 캐릭터를 배정한다.
    - **나중에 할게요**를 선택한 경우: 선택값과 여행 유형은 `null`로 두고
      기본 캐릭터(돌멍이)를 배정한다.
    """
    user = _get_or_create_user(db, current_user_id)

    if request.is_skipped:
        user.expectation = None
        user.transportation = None
        user.travel_style = None
        travel_style: UserTravelStyle | None = None
        ar_character = onboarding_matcher.get_default_ar_character(db)
    else:
        user.expectation = [value.value for value in request.categories]
        user.transportation = [value.value for value in request.transportation]
        user.travel_style = [value.value for value in request.travel_style]
        travel_style = onboarding_matcher.assign_travel_style(db, request)
        ar_character = onboarding_matcher.assign_ar_character(db, request)

    user.user_travel_style_id = travel_style.id if travel_style else None
    user.ar_character_id = ar_character.id

    db.commit()
    db.refresh(user)

    return _to_response(user, ar_character, travel_style)


def _get_or_create_user(db: Session, user_id: int) -> User:
    """사용자를 조회하고, 없으면 해당 id로 생성한다."""
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        db.add(user)
        db.flush()
    return user


def _to_response(
    user: User, ar_character: ArCharacter, travel_style: UserTravelStyle | None
) -> OnboardingSaveResponse:
    return OnboardingSaveResponse(
        user=UserResponse(
            id=user.id,
            ar_character=ArCharacterResponse(
                id=ar_character.id,
                name=ar_character.character_name,
                image_url=ar_character.character_img_url,
            ),
            user_travel_style=(
                UserTravelStyleResponse(
                    id=travel_style.id,
                    user_type=travel_style.user_type,
                    type_description=travel_style.type_description,
                    hashtags=travel_style.hashtags,
                )
                if travel_style
                else None
            ),
        )
    )
