"""협동 미션 역할 사진 인증.

참가자가 올린 사진이 자신이 맡은 역할 카드의 조건에 맞는지 판단한다.
(app/cooperative_mission/docs/BUSINESS_RULES_2.md - 8. 사진 인증 모듈 분리 / 9. 임시 인증 구현)

인증 방식은 바뀔 수 있으므로 service 에 직접 쓰지 않고 이 모듈로 분리한다.
router/service 는 판단 방법(외부 API 호출, 프롬프트, 응답 형식)을 알지 않고 `bool` 만 받는다.

현재는 이미지 인증 기획과 프롬프트가 확정되지 않아 **유효한 이미지면 항상 성공**으로 본다.
확정되면 함수 시그니처는 그대로 두고 이 함수 안에서 역할 카드 정보와 이미지를 담아 판단하도록 바꾼다.
(형식/크기/단계/담당자/중복 완료 검증은 임시 구현에서도 그대로 수행한다)
"""


def verify_role_image(
    *,
    image_bytes: bytes,
    content_type: str,
    role_name: str,
    role_description: str,
    location_to_find: list[str],
) -> bool:
    """역할 카드 조건에 맞는 사진인지 판단한다. 인증에 성공하면 `True`."""
    # TODO: 이미지 인증 기획 확정 시 역할 카드 정보와 이미지를 사용해 실제로 판단하도록 교체
    return True
