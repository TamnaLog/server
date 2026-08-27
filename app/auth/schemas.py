"""인증 도메인 요청/응답 스키마.

필드명은 app/auth/docs/API_SPEC.md 기준(camelCase)이다.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """요청/응답에서 camelCase 필드명을 사용하는 기본 모델."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AnonymousUserResponse(CamelModel):
    """익명 사용자 발급 응답.

    토큰 원문은 이 응답에서만 확인할 수 있다.
    서버는 해시만 저장하므로 나중에 다시 알려줄 수 없다.
    """

    access_token: str
    token_type: str
