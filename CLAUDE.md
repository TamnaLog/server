# CLAUDE.md

## 1. Project Overview

### 1.1 Project Purpose
- 이 프로젝트는 제주 여행 앱 `잠깐, 제주`의 백엔드 API 서버이다.
- 백엔드는 홈, 온보딩, 지도, 미션, 방명록, 마이페이지 등 앱에서 필요한 API를 제공한다.

### 1.2 Tech Stack
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- MySQL
- Docker / Docker Compose

### 1.3 Authentication
- 별도의 로그인 화면 없이 익명 사용자 + 액세스 토큰으로 사용자를 식별한다.
- 프론트는 앱 실행 시 기기 보안 저장소의 토큰을 확인한다.
  - 토큰이 없으면 `POST /api/v1/auth/anonymous`로 익명 사용자와 토큰을 발급받아 저장한다.
  - 이후 모든 요청에 `Authorization: Bearer {accessToken}` 헤더를 넣는다.
- 토큰 원문은 발급 응답에서 한 번만 내려주고, DB에는 SHA-256 해시(`USER.access_token_hash`)만 저장한다.
  - 토큰 생성/해시는 `app/core/security.py`에 있고 발급(`app/auth`)과 식별(`app/core/deps.py`)이 같이 쓴다.
  - 토큰 원문과 해시는 로그/에러 응답/예외 메시지에 넣지 않는다.
- 현재 사용자 id가 필요한 API는 `get_current_user_id()` 의존성을 사용한다. (`app/core/deps.py`)
  - 헤더가 없거나 Bearer 형식이 아니면 401 `UNAUTHORIZED_USER`
  - 토큰 해시에 해당하는 `USER`가 없으면 401 `UNAUTHORIZED_USER`
  - 401은 `use_common_error_responses()`가 Bearer 인증을 쓰는 API에만 자동으로 문서에 넣는다.
- 목업 사용자(1~6번)의 토큰 원문은 `test-user-{id}-token`이다. (`scripts/sql/02-data-mock.sql`)
  - 테스트에서는 `conftest.py`의 `auth_headers(user_id)`를 쓴다.

### 1.4 Date and Time Policy
- 시간 정보는 한국시간(KST) 기준으로 처리한다.
- API 요청/응답은 offset 없는 ISO 8601 date-time 형식을 사용한다.
- 별도의 timezone 변환 없이 입력 값을 KST로 취급한다.
- DB에는 timezone 없는 `DATETIME`으로 저장한다.

### 1.5 API Base Convention
- 기본 API prefix는 `/api/v1`이다.
- API 요청/응답 필드명은 각 도메인의 `API_SPEC.md`를 기준으로 한다.

## 2. Project Structure
- 도메인별 패키지 구조: `app/<domain>/{router,service,schemas,models}.py`
- 도메인 문서: `app/<domain>/docs/API_SPEC.md`, `app/<domain>/docs/BUSINESS_RULES.md`
- 공통 코드
  - `app/core/`: 앱 인프라 (`config.py`, `database.py`, `deps.py`, `errors.py`, `models.py`, `security.py`)
  - `app/common/`: 도메인이 공유하는 계산/유틸과 공용 응답 스키마
    - `distance.py`: 좌표 거리·예상 소요 시간
    - `rewards.py`: 미션 보상(`reward_detail`) 응답 스키마 + 조합 로직 (문화/협동/보물 공용)
    - `next_location.py`: 미션 완료 후 다음 장소 추천 응답 스키마 + 추천 로직
    - `datetimes.py`: KST 기준 현재 시각(`now_kst()`)
  - `app/services/`: 외부 서비스 연동 (`kto.py`: TourAPI, `blob_storage.py`: Azure Blob 업로드,
    `openai_audio_title.py`: 방명록 오디오 제목 생성)
  - 보상을 실제로 지급하는 규칙(지급 순서/개수)은 미션 유형마다 다르므로 도메인 안에 둔다.
    (예: `app/culture_mission/reward_granter.py`)
- 테스트: 루트 `conftest.py` + `app/<domain>/tests/` (공통 규칙 테스트는 `app/core/tests/`)
- 라우터는 `app/main.py`의 `ROUTERS`에 등록한다.

## 3. Reference Documents
- API 명세: `app/<domain>/docs/API_SPEC.md` (노션 명세를 같은 형식으로 옮긴 파일)
- 비즈니스 룰: `app/<domain>/docs/BUSINESS_RULES.md`
- ERD: `docs/erd.md`, DDL: `scripts/sql/01-schema.sql`, 목업 데이터: `scripts/sql/02-data-mock.sql`
- 구현 전 해당 도메인의 두 문서를 먼저 읽고, 명세와 다르게 구현해야 하면 이유를 남긴다.

## 4. Development Principles
- 구현은 항상 명세 문서를 기준으로 한다. 명세에 없는 기능은 임의로 추가하지 않는다.
- 명세가 확정되지 않은 임시 로직은 `TODO` 주석으로 교체 지점을 남긴다.
- 주석과 docstring은 한국어로 작성한다.
- 공통 처리 정책, API 응답 규칙, DB 사용 방식, 테스트 방식 등 프로젝트 기준이 바뀌면 관련 코드와 문서를 함께 확인하고 필요한 변경 사항을 반영한다. 또한 반드시 이런 경우 공유한다.

## 5. Architecture Rules
- 계층 역할: router = 요청/응답 + 의존성, service = 비즈니스 로직, models = ORM, schemas = 검증/직렬화.
- router에는 비즈니스 로직을 두지 않고 service 함수만 호출한다.
- 배정/매칭처럼 교체 가능성이 큰 규칙은 별도 모듈로 분리한다. (예: `app/onboarding/onboarding_matcher.py`)
- ERD의 모든 테이블은 ORM 모델로 이미 정의되어 있다. API 구현 중에 모델을 새로 만들지 말고 소유 도메인에서 import해서 쓴다.
  - 모든 도메인 models 모듈은 `app/core/models.py`에서 한 번에 import한다. 새 모델 모듈을 추가하면 여기에도 추가한다.
  - `app/core/tests/test_models_registry.py`가 `scripts/sql/01-schema.sql`과 테이블/컬럼이 일치하는지 검증한다.
- 여러 도메인이 공유하는 테이블 모델은 소유 도메인에서 한 번만 정의하고 다른 도메인은 import한다.
  - `USER`, `USER_TRAVEL_STYLE` → `app/user/models.py`
  - `AR_CHARACTER` → `app/treasure_mission/models.py`

## 6. API Implementation Rules
- 요청/응답 필드명은 camelCase, 내부 코드/DB 컬럼은 snake_case를 사용한다.
  - 응답 스키마는 `app/onboarding/schemas.py`의 `CamelModel`처럼 `alias_generator=to_camel` + `populate_by_name=True`를 사용한다.
- 허용값이 정해진 필드는 `str, Enum`으로 정의해 검증을 스키마에 맡긴다.
- router에는 `response_model`과 명세의 `status_code`를 명시한다.
- 의존성은 `Annotated[Session, Depends(get_db)]` 형태로 선언한다.
- 현재 사용자 id가 필요하면 `Annotated[int, Depends(get_current_user_id)]`(`app/core/deps.py`)를 사용한다.

## 7. Database & Business Logic Rules
- 스키마 변경이 필요하면 `docs/erd.md`와 `scripts/sql/01-schema.sql`을 함께 수정한다. 이 경우에는 해당 수정 내용을 공유한다.
- 조회/저장은 SQLAlchemy 2.0 스타일(`select()`, `db.get()`)을 사용한다.
- 커밋은 service 계층에서 한 번만 수행한다.

## 8. Error Handling Rules
- 모든 에러 응답 형식은 `{ "code": ... }` 이다. (`app/core/errors.py`) 응답에 `message`는 넣지 않는다.
- 400 에러는 `INVALID_REQUEST`, 500 에러는 `INTERNAL_SERVER_ERROR` 코드 하나로 통일한다.
  - 두 에러는 공통 핸들러가 처리하므로 각 API에서 따로 정의하지 않는다.
  - 요청 검증 실패(FastAPI 기본 422)도 공통 핸들러가 400 `INVALID_REQUEST`로 변환한다.
- 404 등 명세에 정의된 도메인 에러는 `AppError`/`NotFoundError`를 발생시키고 명세의 `code`를 그대로 쓴다.
  - 원인 설명이 필요하면 `detail` 인자로 남긴다. 응답에는 나가지 않고 서버 로그 확인용이다.
- 예상치 못한 예외는 그대로 발생시키면 500 `INTERNAL_SERVER_ERROR`로 응답된다. (traceback은 서버 로그로 출력)
- Swagger 문서의 에러 응답도 `app/core/errors.py`의 `use_common_error_responses()`가 공통으로 맞춘다.
  - FastAPI 기본 422 응답과 관련 스키마는 문서에서 제거한다.
  - 요청 값(query/path/body)이 있는 API에는 400, 모든 API에는 500을 자동으로 문서에 넣는다.
  - 따라서 라우터에 400/500을 `responses`로 직접 적지 않는다. 404 등 도메인 에러만 적는다.

## 9. Testing Rules
- pytest + `TestClient` + SQLite 인메모리로 API 단위로 테스트한다. (`pip install -r requirements-dev.txt`, 실행: `pytest`)
- 공통 픽스처는 루트 `conftest.py`(`client`, `db_session`)에 있고, `get_db` 의존성만 교체해 라우터/서비스/모델을 그대로 태운다.
- 테스트 파일은 도메인 폴더 안에 둔다: `app/<domain>/tests/test_<api>.py`
  - 특정 도메인이 아니라 프로젝트 공통 규칙을 검증하는 테스트는 `app/core/tests/`에 둔다.
- API 하나당 최소 다음 케이스를 검증한다.
  1. 명세의 정상 케이스: status code + 응답 필드 + DB 저장 결과
  2. 명세의 분기 케이스(예: 빈 body, null 응답)
  3. 잘못된 요청 → 400 `INVALID_REQUEST`
  4. 명세에 정의된 도메인 에러(404 등)
- 테스트 함수명은 한국어로 검증 내용을 그대로 쓴다. (예: `test_나중에_할게요를_선택하면_...`)
- 랜덤 로직은 값 자체가 아니라 "DB에 존재하는 값 중 하나인지"로 검증한다.
- `db.get()`처럼 `X | None`을 반환하는 조회 결과는 속성 접근 전에 `assert result is not None`을 먼저 쓴다.
  (타입 체커가 None 가능성으로 경고하는 것을 막고, 조회 실패 시 원인도 명확해진다.)
- 테스트를 작성하거나 수정한 경우, 해당 도메인의 `docs/TEST_GUIDE.md`에 테스트 대상, 테스트 의도, 주요 검증 항목, 실행 방법을 작성한다.
- `TEST_GUIDE.md`는 테스트 코드를 그대로 설명하는 문서가 아니라, 해당 도메인 API에서 무엇을 검증하는지 사람이 빠르게 이해할 수 있게 정리한다.

## 10. Implementation Workflow & Definition of Done
1. 도메인의 `API_SPEC.md` / `BUSINESS_RULES.md` 확인
2. ERD/DDL과 필요한 컬럼 대조
3. models → schemas → service → router 순서로 구현
4. 명세의 정상/예외 케이스 동작 확인
5. 문서(ERD/DDL/CLAUDE.md) 변경 사항 반영
6. 논의가 필요한 상황이 존재하면 공유