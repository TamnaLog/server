# 온보딩 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `PATCH /api/v1/users/me` (사용자 온보딩 정보 저장) | `app/onboarding/tests/test_save_onboarding_info.py` |

## 테스트 의도

온보딩 API는 두 가지를 동시에 책임진다.

1. 사용자가 온보딩에서 고른 값(여행 기대 항목 / 주 이동 수단 / 자투리 시간 여행 방식)을 저장하는 것
2. 그 결과로 여행 유형과 AR 캐릭터를 배정해서 돌려주는 것

그래서 테스트는 **응답 형식이 명세와 같은지**와 **DB에 실제로 저장됐는지**를 항상 같이 본다.
응답만 맞고 저장이 안 되는 경우, 반대로 저장은 됐는데 응답 필드명이 다른 경우를 모두 잡기 위해서다.

배정 로직은 아직 기획이 확정되지 않아 랜덤이므로(`onboarding_matcher.py`), 어떤 값이 나오는지는 검증하지 않는다.
대신 **DB에 존재하는 값 중 하나가 배정되고, 그 값이 그대로 저장/응답되는지**만 검증한다.
매칭 기준이 확정돼서 랜덤이 실제 로직으로 바뀌어도 이 테스트는 그대로 쓸 수 있다.

## 주요 검증 항목

### 1. 온보딩을 정상 진행한 경우

- 201로 응답한다.
- 응답 `user.arCharacter`는 `id`, `name`, `imageUrl`, `user.userTravelStyle`은 `id`, `userType`, `typeDescription`, `hashtags`로 이루어진다. (camelCase 명세 확인)
- 요청으로 보낸 선택값이 `USER`의 `expectation` / `transportation` / `travel_style`에 그대로 저장된다.
- 응답에 실린 여행 유형·AR 캐릭터 id가 `USER`의 `user_travel_style_id` / `ar_character_id`와 일치한다. (배정 결과가 응답과 저장에 동일하게 반영되는지)

### 2. 배정 결과의 유효성

- 배정된 여행 유형과 AR 캐릭터는 DB에 존재하는 값 중 하나다. (임의 값이나 하드코딩된 값이 아님)

### 3. **나중에 할게요**를 선택한 경우 (빈 body `{}`)

- 201로 응답한다.
- `user.userTravelStyle`이 `null`이다.
- 기본 캐릭터 **돌멍이**가 배정된다.
- 선택값 3개와 `user_travel_style_id`는 DB에 `null`로 남는다. (이전 값이 남거나 빈 배열로 저장되지 않는지)

### 4. 현재 사용자

- 현재 사용자는 `X-Test-User-Id` 헤더로 정한다. **이 API는 사용자를 새로 만들지 않는다.**
- 헤더의 사용자가 존재하지 않으면 **401 `UNAUTHORIZED_USER`** 로 응답하고 사용자도 생기지 않는다.
  (사용자 없이 온보딩만 먼저 하는 흐름은 없다)

### 5. 잘못된 요청

- 허용값 밖의 값(`categories`, `transportation`, `travelStyle`)이나 타입이 다른 값을 보내면
  **400 `INVALID_REQUEST`** 로 응답한다.
  (FastAPI 기본 422가 아니라 공통 에러 형식 `{ "code": ... }` 으로 나가는지 확인)

### 6. 배정할 데이터가 없는 경우

- 여행 유형 / AR 캐릭터 마스터 데이터가 비어 있으면 **500 `INTERNAL_SERVER_ERROR`** 로 응답한다.
  (서버 내부 예외가 traceback이 아니라 공통 에러 형식 `{ "code": ... }` 으로 나가는지 확인)

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 온보딩 도메인만
pytest app/onboarding

# 특정 테스트만
pytest app/onboarding/tests/test_save_onboarding_info.py -k 나중에
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고, 목업 데이터는 각 테스트의 `onboarding_data` 픽스처에서 만든다.
