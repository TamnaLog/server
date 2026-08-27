# 인증 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `POST /api/v1/auth/anonymous` (익명 사용자 발급) | `app/auth/tests/test_issue_anonymous_user.py` |
| 공통 현재 사용자 식별 (`Authorization: Bearer`) | `app/core/tests/test_current_user_token.py` |

현재 사용자 식별은 인증 도메인이 아니라 모든 API에 공통으로 걸리는 규칙이라
`app/core/tests/`에 둔다.

## 테스트 의도

익명 사용자 발급은 "토큰을 만들어 응답한다"로 끝나지 않는다.
발급 결과가 이후 모든 API의 인증 근거가 되므로 다음 세 가지를 함께 확인한다.

1. 발급 결과가 DB에 제대로 남는가 (사용자 + 사용자 설정)
2. 저장한 값이 토큰 원문이 아니라 해시인가
3. 발급받은 토큰으로 실제로 다른 API를 호출할 수 있는가

## 주요 검증 항목

### 익명 사용자 발급

- **정상 응답**: 201, 응답 필드는 `accessToken` / `tokenType`(항상 `Bearer`) 두 개뿐이다.
  사용자 id와 토큰 해시는 응답하지 않는다.
- **DB 저장**: `USER` 1행 + `USER_SETTING` 1행이 함께 생긴다.
  - 온보딩 정보(`expectation`, `transportation`, `travel_style`)와
    `user_travel_style_id`, `ar_character_id`는 아직 `NULL`이다. (온보딩 API가 채운다)
  - `point`는 0, `nickname`은 익명 닉네임 5개 중 하나다.
  - 닉네임은 무작위라서 값 자체가 아니라 후보 안에 있는지로 검증한다.
  - `USER_SETTING`의 두 알림 값은 모두 `TRUE`다.
- **토큰 원문 미저장**: `USER.access_token_hash`가 토큰 원문과 다르고,
  `hash_access_token(원문)`과 같으며 길이가 64자다.
- **발급 토큰의 실제 사용**: 발급받은 토큰을 `Authorization` 헤더에 넣어
  현재 사용자가 필요한 API(홈 조회)를 호출하면 200이 나온다.
- **중복 호출**: 호출할 때마다 새 사용자와 새 토큰을 만든다. 기존 사용자를 재사용하지 않는다.
- **토큰 충돌 재시도**: `generate_access_token`을 교체해 같은 토큰이 연속으로 나오게 만든다.
  - 충돌하면 새 토큰으로 다시 시도하고, 충돌한 토큰은 응답하지 않는다.
  - 계속 충돌하면 `MAX_TOKEN_ATTEMPTS`번만 시도하고 500 `INTERNAL_SERVER_ERROR`로 응답한다.
    이때 사용자도 추가로 생기지 않는다.
- **트랜잭션**: 사용자 설정 저장이 실패하면 사용자도 남지 않는다.
  (설정 없는 사용자나 사용자 없는 설정이 생기면 안 된다)
- **인증 불필요**: `Authorization` 헤더 없이 호출해도 201이고, 문서에 401을 넣지 않는다.

### 공통 현재 사용자 식별

- **토큰의 주인이 현재 사용자**: 서로 다른 캐릭터를 가진 사용자 두 명을 만들고,
  토큰을 바꿔가며 호출해 응답의 `characterImgUrl`로 누구로 처리됐는지 확인한다.
- **401 `UNAUTHORIZED_USER`**: 다음 경우 모두 같은 코드로 응답한다.
  - `Authorization` 헤더가 없음
  - 형식이 잘못됨 (토큰만 보냄 / `Basic` 등 다른 방식 / 토큰이 비어 있음)
  - 형식은 맞지만 토큰에 해당하는 사용자가 없음
- **Swagger 문서**: 현재 사용자가 필요한 API는 `AccessToken` 보안 스키마를 쓰고
  401 응답 예시가 붙는다. 인증이 필요 없는 API(`/health`)에는 401이 붙지 않는다.

## 실행 방법

```bash
pip install -r requirements-dev.txt

# 인증 도메인만
pytest app/auth

# 공통 사용자 식별까지
pytest app/auth app/core/tests/test_current_user_token.py

# 전체
pytest
```

## 테스트에서 사용자 인증하기

`conftest.py`의 헬퍼를 쓴다. 목업 데이터와 같은 규칙(`test-user-{id}-token`)이라
Swagger나 curl로 직접 호출할 때도 같은 값을 쓸 수 있다.

```python
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers

# 픽스처에서 사용자를 만들 때
User(id=2, access_token_hash=access_token_hash(2), ...)

# 그 사용자로 요청할 때
client.get(ENDPOINT, headers=auth_headers(2))
```

`client` 픽스처는 기본으로 `CURRENT_USER_ID`(=1)의 인증 헤더를 넣어 두므로,
다른 사용자로 호출하는 테스트만 `auth_headers()`로 덮어쓰면 된다.
