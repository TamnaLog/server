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

### 1.3 Authentication Assumption
- 현재 로그인 기능은 구현되어 있지 않다.
- 현재 사용자는 항상 `id=1`로 처리한다.
- DB에는 항상 1번 사용자에 대한 목업 데이터가 존재해야 한다.
- 현재 사용자 id가 필요한 API는 `get_current_user_id()` 의존성을 사용한다.

### 1.4 Date and Time Policy
- 시간 정보는 한국시간(KST) 기준으로 처리한다.
- API 요청/응답은 offset 없는 ISO 8601 date-time 형식을 사용한다.
- 별도의 timezone 변환 없이 입력 값을 KST로 취급한다.
- DB에는 timezone 없는 `DATETIME`으로 저장한다.

### 1.5 API Base Convention
- 기본 API prefix는 `/api/v1`이다.
- API 요청/응답 필드명은 각 도메인의 `API_SPEC.md`를 기준으로 한다.



## 2. Reference Documents

구현 전에 반드시 관련 문서를 먼저 확인한다.

우선순위는 다음과 같다.

1. 해당 도메인의 `app/{domain}/docs/API_SPEC.md`
2. 해당 도메인의 `app/{domain}/docs/BUSINESS_RULES.md`
3. DB 구조가 필요한 경우 `docs/erd.md`
4. 실제 테이블/컬럼 확인이 필요한 경우 `scripts/sql/01-schema.sql`
5. 목업 데이터 확인이 필요한 경우 `scripts/sql/02-data-mock.sql`
6. API 문서 형식 확인이 필요한 경우 `docs/api_example.md`

Claude는 Notion을 직접 참고하지 않는다. API 구현 기준은 각 도메인에 존재하는 `API_SPEC.md`와 `BUSINESS_RULES.md`이다.

`API_SPEC.md`와 구현이 충돌하면 구현을 임의로 바꾸지 말고, 먼저 명세를 기준으로 판단한다. 명세 자체가 이상하면 사용자에게 확인하거나, 수정 사유를 명확히 남긴다.



## 4. Development Principles

- 명세에 없는 기능을 임의로 추가하지 않는다.
- 명세에 있는 요청 필드명, 응답 필드명, 상태 코드, 에러 코드를 그대로 사용한다.
- 추측으로 필드명을 바꾸지 않는다.
- 기존 코드 스타일과 도메인 구조를 우선한다.
- 한 번에 큰 리팩터링을 하지 말고, 요청받은 API 구현에 필요한 범위만 수정한다.
- 한국어 문자열은 UTF-8로 그대로 유지한다.
- SQL, Markdown, Python 파일은 UTF-8 without BOM 기준으로 작성한다.
- 날짜/시간 응답은 offset 없는 ISO 8601 문자열로 반환한다.
- 배열 응답은 데이터가 없으면 빈 배열 `[]`로 반환한다.
- 명세에서 `null`이라고 정한 값은 빈 객체 `{}`나 빈 문자열 `""`로 대체하지 않는다.

## 5. Architecture Rules

- FastAPI의 라우터, 서비스, 스키마, 모델 분리 구조를 유지한다.
- `router.py`는 요청 파라미터 수집, 의존성 주입, service 호출, 응답 반환만 담당한다.
- 비즈니스 로직은 `service.py`에 둔다.
- 요청/응답 모델은 `schemas.py`에 둔다.
- SQLAlchemy 모델은 `models.py`에 둔다.
- 공통 설정, DB 세션, 공통 의존성은 `app/core` 구조를 따른다.
- DB 컬럼명이 snake_case이고 API 응답 필드명이 camelCase이면, service 또는 schema 계층에서 명세 기준 camelCase로 변환한다.
- 도메인 간 참조가 필요하더라도 순환 import가 생기지 않도록 주의한다.

## 6. API Implementation Rules

- API 구현 전 해당 도메인의 `API_SPEC.md`를 먼저 읽는다.
- 비즈니스 조건이 있으면 같은 도메인의 `BUSINESS_RULES.md`를 함께 읽는다.
- HTTP 메서드와 endpoint는 `API_SPEC.md`에 적힌 값을 그대로 사용한다.
- 요청 Query, Path, Body는 명세의 필수 여부와 타입을 따른다.
- 응답 Body는 명세의 JSON 구조와 필드명을 그대로 따른다.
- `204 No Content` 응답은 Body를 반환하지 않는다.
- Pydantic schema의 필드명은 API 명세 기준으로 작성한다.
- DB 저장값과 응답값의 이름이 다르면 service에서 명확히 매핑한다.
- 구현 후 Swagger에서 보이는 요청/응답 모델이 명세와 어긋나지 않는지 확인한다.

## 7. Database & Business Logic Rules

- DB 구조는 `docs/erd.md`를 기준으로 판단한다.
- 실제 SQL 컬럼 정의가 필요하면 `scripts/sql/01-schema.sql`을 확인한다.
- 목업 데이터는 `scripts/sql/02-data-mock.sql`을 확인한다.
- JSON 배열 컬럼은 배열 의미의 값이면 가능하면 `[]`를 사용한다.
- `NULL`과 빈 배열 `[]`의 의미를 구분해서 사용한다.
- API 응답 예시와 실제 목업 데이터는 서로 맞아야 한다.
- 명세 응답을 만들기 위한 데이터가 부족하면 `scripts/sql/02-data-mock.sql`을 수정할 수 있다.
- 테이블 구조 변경이 필요하면 `scripts/sql/01-schema.sql`과 `docs/erd.md`를 함께 수정해야 하는지 확인한다.

SQL을 수정한 경우에는 최종 응답에 반드시 아래 내용을 작성한다.

- 어떤 SQL 파일을 수정했는지
- 어떤 테이블/컬럼/데이터를 수정했는지
- 왜 수정했는지
- 기존 DB 볼륨에는 자동 반영되지 않는다는 점

SQL 수정 후 기존 로컬 DB에 반영하려면 볼륨을 삭제하고 다시 기동해야 한다.

```powershell
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build
```

초기화 SQL은 MySQL 최초 기동 시 아래 순서로 실행된다.

```text
scripts/sql/01-schema.sql
scripts/sql/02-data-mock.sql
```

## 8. Error Handling Rules

- 에러 코드는 반드시 API 명세에 적힌 세부 코드만 사용한다.
- 명세에 없는 세부 에러 코드를 임의로 만들지 않는다.
- 400 에러는 `INVALID_REQUEST` 코드 하나로 통일해서 전송한다.
- 500 에러는 `INTERNAL_SERVER_ERROR` 코드 하나로 통일해서 전송한다.
- 400과 500 에러 응답은 각 API 명세에 따로 명시하지 않는다.
- 404, 409 등 비즈니스 상황별 에러는 `API_SPEC.md`에 적힌 코드가 있을 때만 해당 코드를 사용한다.
- 동일한 상황에 대해 도메인마다 다른 에러 코드가 필요하면 해당 도메인의 `API_SPEC.md`를 따른다.

## 9. Testing Rules

- 테스트는 기본적으로 API 단위로 작성한다.
- API 1개당 테스트 1개만 작성하는 것이 아니라, 정상 케이스와 중요한 실패 케이스를 나누어 작성한다.
- 조회 API는 status code, 응답 필드명, 응답 구조, null/빈 배열 처리, 정렬/페이지네이션 조건을 확인한다.
- 저장/수정/삭제 API는 status code와 DB 반영 여부를 함께 확인한다.
- 저장/수정 API가 `204 No Content`를 반환하는 경우 응답 Body가 없는지 확인한다.
- Service 테스트는 비즈니스 로직 검증에 사용한다.
- API 테스트는 `TestClient` 등을 사용해 실제 HTTP 요청/응답 흐름을 검증한다.
- 구현 후 최소한 import 오류가 없는지 확인한다.
- 가능하면 해당 API를 직접 호출해서 응답 구조를 확인한다.
- DB 조회가 필요한 API는 목업 데이터 기준으로 정상 응답이 나오는지 확인한다.
- 에러 케이스가 명세에 있으면 최소한 주요 에러 조건을 확인한다.
- 에러 응답 테스트에서는 `API_SPEC.md`에 명시된 세부 에러 코드만 검증한다.
- 테스트 또는 수동 검증을 실행하지 못했다면 최종 응답에 실행하지 못했다고 명시한다.
- SQL 목업 데이터를 수정한 경우, 기존 DB 볼륨을 유지한 상태에서는 수정 데이터가 자동 반영되지 않는다는 점을 검증 결과에 포함한다.

## 10. Implementation Workflow & Definition of Done

구현은 아래 순서로 진행한다.

1. 해당 도메인의 `API_SPEC.md` 확인
2. 해당 도메인의 `BUSINESS_RULES.md` 확인
3. 필요한 경우 `docs/erd.md`, `01-schema.sql`, `02-data-mock.sql` 확인
4. 요청/응답 schema 작성
5. 필요한 SQLAlchemy model 작성 또는 수정
6. service 로직 구현
7. router 연결
8. 명세와 응답 필드명/구조 비교
9. 가능한 검증 실행
10. 수정 내용과 검증 결과 보고

완료 기준은 아래와 같다.

- endpoint가 명세와 일치한다.
- 요청 Query, Path, Body가 명세와 일치한다.
- 정상 응답 구조가 명세와 일치한다.
- 에러 코드는 명세에 있는 코드만 사용한다.
- DB 조회/저장 로직이 ERD와 SQL 스키마에 맞다.
- 필요한 목업 데이터가 존재한다.
- SQL을 수정했다면 수정 위치, 수정 내용, 수정 이유, DB 륨 재생성 필요 여부를 보고했다.
- 실행한 검증과 실행하지 못한 검증을 명확히 보고했다.
