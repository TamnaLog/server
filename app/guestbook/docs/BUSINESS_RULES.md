# 방명록 도메인 비즈니스 룰

## A. 방명록 작성 가능 여부 조회

### 1. 적용 범위

이 문서는 `방명록 작성 가능 여부 조회` API의 구현 규칙만 정의한다.
엔드포인트, 요청 필드, 응답 필드와 JSON 예시는 노션 API 명세를 기준으로 하며 여기서 반복하지 않는다.

이 API가 판단하는 것은 **현재 사용자가 요청한 장소를 방문한 기록이 있는지**뿐이다. 다음 항목은 판단 조건에 포함하지 않는다.

- 해당 장소에 방명록을 이미 작성했는지 여부
- 해당 장소에서 미션을 수행하거나 완료했는지 여부
- 다른 사용자의 방문 기록
- 방문 이후 경과 시간

### 2. 사용자 식별

- 현재 사용자는 `get_current_user_id()` 의존성으로 식별한다.
- 클라이언트가 사용자 id를 Query, Path 또는 Body로 전달하게 만들지 않는다.
- 다른 사용자의 `VISITED_LOCATION` 기록으로 현재 사용자의 작성 가능 여부를 판단하면 안 된다.
- 인증 실패는 프로젝트 공통 401 처리 정책을 사용하며 이 도메인에서 별도 인증 코드를 정의하지 않는다.

### 3. 조회 순서

서비스는 다음 순서로 조회한다.

1. 요청받은 `locationId`로 `LOCATION`을 조회한다.
2. 장소가 없으면 방문 기록을 조회하지 않고 `404 LOCATION_NOT_FOUND`를 발생시킨다.
3. 장소가 있으면 현재 사용자와 장소가 모두 일치하는 `VISITED_LOCATION`을 조회한다.
4. 방문 기록의 존재 여부와 최신 기록을 기준으로 응답을 구성한다.

장소 존재 여부를 먼저 확인해야 한다. 존재하지 않는 장소와 존재하지만 방문하지 않은 장소가 모두 `canWrite=false`로 합쳐지면 안 된다.

### 4. 방문 기록 조회 조건

방문 기록은 반드시 다음 조건을 모두 만족해야 한다.

```text
VISITED_LOCATION.user_id = current_user_id
AND VISITED_LOCATION.location_id = locationId
```

같은 사용자가 같은 장소를 여러 번 방문할 수 있으므로 단일 방문만 존재한다고 가정하거나 중복 오류를 발생시키지 않는다.

가장 최근 기록 한 건은 다음 순서로 결정한다.

```text
ORDER BY VISITED_LOCATION.visited_at DESC,
         VISITED_LOCATION.id DESC
LIMIT 1
```

- `visited_at`이 가장 늦은 기록을 우선한다.
- `visited_at`이 같으면 id가 큰 기록을 우선한다.
- Python에서 전체 목록을 정렬하지 말고 DB 조회 단계에서 정렬하고 한 건만 가져온다.

### 5. 응답 구성

#### 방문 기록이 있는 경우

- `canWrite`는 `true`다.
- `visitedLocation.locationId`는 조회한 `LOCATION.id`다.
- `visitedLocation.locationName`은 조회한 `LOCATION.location_title`이다.
- `visitedLocation.visitedAt`은 4절에서 선택한 `VISITED_LOCATION.visited_at`이다.
- `visitedAt`은 프로젝트 시간 정책에 따라 KST 기준 offset 없는 ISO 8601 date-time으로 직렬화한다.

#### 방문 기록이 없는 경우

- `canWrite`는 `false`다.
- `visitedLocation`은 객체를 부분적으로 만들지 않고 반드시 `null`이다.
- 방문하지 않은 것은 정상적인 조회 결과이므로 404나 다른 오류를 발생시키지 않는다.

응답 필드는 조건에 따라 생략하지 않는다. 두 경우 모두 `canWrite`와 `visitedLocation` 키를 포함한다.

### 6. 데이터 변경 금지

이 API는 읽기 전용이다.

- `VISITED_LOCATION`을 생성하거나 수정하지 않는다.
- `GUESTBOOK` 또는 `ROAD_GUESTBOOK`을 생성하거나 조회하지 않는다.
- 조회 결과를 캐시한다는 이유로 사용자나 장소 데이터를 수정하지 않는다.
- 서비스에서 `db.commit()` 또는 `db.flush()`를 호출하지 않는다.

방문 기록 생성은 실제 장소 방문을 판정하는 별도 기능의 책임이다. 이 API에서 좌표나 장소 반경을 다시 검증하지 않는다.

### 7. 구현 위치

- 라우터: `app/guestbook/router.py`
  - Query와 현재 사용자 의존성을 받고 서비스 함수를 호출한다.
  - 비즈니스 조건이나 SQL 조회를 작성하지 않는다.
- 스키마: `app/guestbook/schemas.py`
  - Query 검증과 응답 모델을 정의한다.
  - 응답 alias는 프로젝트 규칙에 따라 camelCase를 사용한다.
- 서비스: `app/guestbook/service.py`
  - 장소 존재 확인, 최신 방문 기록 조회와 응답 조합을 담당한다.
- 모델:
  - `Location`과 `VisitedLocation`은 소유 도메인인 `app.map.models`에서 import한다.
  - 이 API를 위해 방명록 도메인에 중복 ORM 모델을 만들지 않는다.

요청 값 누락이나 타입·범위 오류는 공통 요청 검증 처리에 맡기고, 라우터나 서비스에서 `INVALID_REQUEST` 응답을 직접 만들지 않는다.

### 8. 필수 테스트

최소한 다음 동작을 API 단위 테스트로 검증한다.

1. 현재 사용자의 방문 기록이 있으면 `canWrite=true`와 장소 정보가 반환된다.
2. 같은 장소를 여러 번 방문했으면 가장 늦은 `visited_at`이 반환된다.
3. `visited_at`이 같은 기록이 여러 개면 id가 가장 큰 기록이 반환된다.
4. 장소는 존재하지만 현재 사용자의 방문 기록이 없으면 `canWrite=false`, `visitedLocation=null`이다.
5. 다른 사용자만 방문한 장소는 현재 사용자에게 작성 가능으로 처리되지 않는다.
6. 장소가 존재하지 않으면 `404 LOCATION_NOT_FOUND`다.
7. `locationId`가 누락되거나 유효하지 않으면 공통 `400 INVALID_REQUEST`다.
8. 인증 헤더가 없거나 사용자 토큰이 유효하지 않으면 공통 `401 UNAUTHORIZED_USER`다.
9. 정상 조회와 오류 조회 모두 DB 데이터를 변경하지 않는다.

테스트 구현 후 검증 의도와 실행 방법을 `app/guestbook/docs/TEST_GUIDE.md`에 정리한다.

---

## B. 방명록 작성

### 1. 적용 범위

이 절은 일반 방명록과 길바닥 방명록을 생성하는 `방명록 작성` API의 내부 구현 규칙을 정의한다.
요청 필드, 응답 필드, HTTP 상태 코드와 예시는 노션 API 명세를 기준으로 하며 여기서 반복하지 않는다.

두 유형은 같은 API에서 `guestbookType`으로 구분하지만 저장 테이블은 다르다.

| `guestbookType` | 저장 테이블 | 의미 |
| --- | --- | --- |
| `GENERAL` | `GUESTBOOK` | 등록된 `LOCATION`에 작성하는 일반 방명록 |
| `ROAD` | `ROAD_GUESTBOOK` | 특정 `LOCATION`에 귀속되지 않고 지도 좌표에 작성하는 길바닥 방명록 |

현재 사용자는 `get_current_user_id()`로 식별한다. 요청에서 사용자 id를 받거나 다른 사용자의 방문·미션 진행도를 사용하면 안 된다.

### 2. 유형별 요청 검증

multipart에서 선택 필드를 전송하지 않은 경우 Python에서는 `None`으로 처리한다.

`GENERAL`은 다음 조건을 적용한다.

- `locationId`는 반드시 값이 있어야 한다.
- `locationAlias`, `latitude`, `longitude`는 `None`이어야 한다.
- `missionId`는 `None` 또는 양의 정수다.

`ROAD`는 다음 조건을 적용한다.

- `locationAlias`, `latitude`, `longitude`는 반드시 값이 있어야 한다.
- `locationId`와 `missionId`는 `None`이어야 한다.
- 위도는 -90 이상 90 이하, 경도는 -180 이상 180 이하만 허용한다.

유형별 미사용 필드에 실제 값이 전달되거나 필수 필드가 빠지면 도메인 로직을 실행하지 않고 공통 `400 INVALID_REQUEST`로 처리한다. 이 검증은 가능한 한 요청 스키마 또는 명시적인 요청 검증 함수 한 곳에 모으고 서비스 곳곳에 분산하지 않는다.

글, 이미지, 오디오, 날씨와 색상은 모두 선택 값이다. 콘텐츠 다섯 종류가 전부 `None`이어도 빈 방명록 생성을 허용한다.

### 3. 공통 처리 순서

서비스는 다음 순서를 지킨다.

1. `guestbookType`과 유형별 조건부 필드를 검증한다.
2. `GENERAL`이면 장소 존재, 방문 이력, 미션 존재와 완료 여부를 순서대로 판정한다.
3. 유형에 맞는 ORM 객체를 만들고 `db.add()` 후 `db.flush()`하여 방명록 id를 얻는다.
4. 파일을 요청 순서대로 하나씩 읽고 크기·실제 형식을 검증한 직후, 방명록 id가 포함된 경로로 Blob Storage에 업로드한다.
5. 반환된 Blob URL 목록을 ORM 객체의 JSON 컬럼에 저장한다.
6. DB 변경을 한 번만 `commit()`한다.
7. 저장된 ORM 값을 1-depth 응답 모델로 변환해 반환한다.

장소·방문·미션 검증이 끝나기 전에 Blob 업로드를 시작하지 않는다. 뒤쪽 파일의 검증이나 업로드가 실패하면 앞서 업로드한 파일은 10절의 보상 삭제로 모두 정리한다.

### 4. 일반 방명록 장소와 방문 검증

`GENERAL` 요청은 다음 순서로 검증한다.

1. `LOCATION.id = locationId`인 장소를 조회한다.
2. 장소가 없으면 `404 LOCATION_NOT_FOUND`를 발생시킨다.
3. 장소가 있으면 현재 사용자의 방문 이력 존재 여부를 조회한다.
4. 방문 이력이 없으면 `409 LOCATION_NOT_VISITED`를 발생시킨다.
5. 방문 이력이 있으면 기존 방명록 존재 여부와 관계없이 생성을 계속한다.

방문 이력 조건은 다음 두 값만 사용한다.

```text
VISITED_LOCATION.user_id = current_user_id
AND VISITED_LOCATION.location_id = locationId
```

- 방문 기록은 한 건 이상 존재하는지만 확인하며 가장 최근 기록을 가져올 필요가 없다.
- 요청의 `visitedAt`과 `VISITED_LOCATION.visited_at` 날짜가 같은지 비교하지 않는다.
- 다른 사용자의 방문 이력은 작성 권한으로 인정하지 않는다.
- 같은 사용자가 같은 장소에 이미 일반 방명록을 작성했어도 다시 작성할 수 있다.
- 작성 횟수 제한, `(user_id, location_id)` 중복 검사와 기존 행 갱신은 하지 않는다.

### 5. 일반 방명록 미션 처리

`missionId`는 공통 `MISSION.id`다. 유형별 세부 미션 id나 미션 진행도 id로 해석하지 않는다.

`missionId`가 `None`이면 미션 조회 없이 `GUESTBOOK.mission_id = NULL`로 저장한다.

값이 전달되면 다음 순서로 처리한다.

1. `MISSION.id = missionId`인 공통 미션을 조회한다.
2. 미션이 없으면 `404 MISSION_NOT_FOUND`를 발생시킨다.
3. 미션의 `mission_type`에 맞는 완료 이력을 현재 사용자 기준으로 조회한다.
4. 완료 이력이 하나 이상이면 요청받은 `MISSION.id`를 저장한다.
5. 미션은 존재하지만 완료 이력이 없으면 오류를 발생시키지 않고 `mission_id = NULL`로 저장한다.

완료 여부는 보상 지급 여부가 아니라 `mission_status = COMPLETED` 이력으로 판단한다. 여러 번 도전한 미션은 완료 이력이 하나라도 있으면 완료한 것으로 본다.

#### 문화 미션 완료 조건

```text
CULTURE_MISSION.mission_id = missionId
AND CULTURE_MISSION_PROGRESS.culture_mission_id = CULTURE_MISSION.id
AND CULTURE_MISSION_PROGRESS.user_id = current_user_id
AND CULTURE_MISSION_PROGRESS.mission_status = COMPLETED
```

#### 보물찾기 미션 완료 조건

```text
TREASURE_MISSION.mission_id = missionId
AND TREASURE_MISSION_PROGRESS.treasure_mission_id = TREASURE_MISSION.id
AND TREASURE_MISSION_PROGRESS.user_id = current_user_id
AND TREASURE_MISSION_PROGRESS.mission_status = COMPLETED
```

#### 협동 미션 완료 조건

```text
COOPERATIVE_MISSION.mission_id = missionId
AND COOPERATIVE_MISSION_PROGRESS.cooperative_mission_id = COOPERATIVE_MISSION.id
AND COOPERATIVE_MISSION_PROGRESS.mission_status = COMPLETED
AND COOPERATIVE_MISSION_PROGRESS.deleted_at IS NULL
AND COOPERATIVE_MISSION_PARTICIPANT.cooperative_mission_progress_id
    = COOPERATIVE_MISSION_PROGRESS.id
AND COOPERATIVE_MISSION_PARTICIPANT.user_id = current_user_id
AND COOPERATIVE_MISSION_PARTICIPANT.participant_status = ACCEPTED
AND COOPERATIVE_MISSION_PARTICIPANT.deleted_at IS NULL
```

미션 완료 판정은 별도 함수로 분리한다. 예를 들어 `is_mission_completed(db, current_user_id, mission)`처럼 호출부가 미션 유형별 JOIN 구조를 몰라도 되게 한다.

### 6. 일반 방명록 저장값

`GUESTBOOK`에는 다음 기준으로 저장한다.

| 컬럼 | 값 |
| --- | --- |
| `user_id` | `current_user_id` |
| `location_id` | 검증이 끝난 `LOCATION.id` |
| `visited_at` | 요청의 `visitedAt` |
| `content_img_url` | 업로드된 이미지 URL 목록. 파일이 없으면 `NULL` |
| `content_writing` | 요청의 글. 없으면 `NULL` |
| `content_audio_url` | 업로드된 오디오 URL 목록. 파일이 없으면 `NULL` |
| `content_weather` | 요청의 날씨. 없으면 `NULL` |
| `content_color_code` | 요청의 색상. 없으면 `NULL` |
| `saved_at` | `now_kst()` |
| `mission_id` | 5절에서 결정한 `MISSION.id` 또는 `NULL` |
| `deleted_at` | `NULL` |

### 7. 길바닥 방명록 저장값

`ROAD`는 `LOCATION`과 `VISITED_LOCATION`, 미션 완료 여부를 조회하지 않는다. 전달받은 좌표는 프론트가 정한 작성 위치로 신뢰하며 장소 반경이나 현재 GPS와의 거리를 다시 검증하지 않는다.

`ROAD_GUESTBOOK`에는 다음 기준으로 저장한다.

| 컬럼 | 값 |
| --- | --- |
| `user_id` | `current_user_id` |
| `location_id` | `NULL` |
| `location_alias` | 요청의 `locationAlias` |
| `visited_at` | 요청의 `visitedAt` |
| `content_img_url` | 업로드된 이미지 URL 목록. 파일이 없으면 `NULL` |
| `content_writing` | 요청의 글. 없으면 `NULL` |
| `content_audio_url` | 업로드된 오디오 URL 목록. 파일이 없으면 `NULL` |
| `content_weather` | 요청의 날씨. 없으면 `NULL` |
| `content_color_code` | 요청의 색상. 없으면 `NULL` |
| `mx` | 요청의 `longitude` |
| `my` | 요청의 `latitude` |
| `saved_at` | `now_kst()` |
| `deleted_at` | `NULL` |

길바닥 방명록도 같은 사용자가 같은 별칭이나 좌표에 여러 번 작성할 수 있다. 좌표·별칭 중복 검사와 기존 행 갱신은 하지 않는다.

### 8. 이미지 검증과 저장

이미지는 기존 `app/common/images.py`를 그대로 사용한다.

- 파일당 최대 10MB다.
- JPEG, PNG, WebP만 허용한다.
- 원본 파일명과 multipart Content-Type을 신뢰하지 않고 파일 시그니처로 실제 형식을 판별한다.
- JPEG 저장 확장자는 `.jpg`로 통일한다.
- 이미지가 여러 장이면 요청 순서를 URL 배열 순서로 유지한다.
- 이미지가 없으면 빈 배열이 아니라 DB와 응답 모두 `NULL`을 사용한다.

Blob prefix는 유형과 생성된 방명록 id로 만든다.

```text
guestbook/general/{guestbook_id}/images
guestbook/road/{guestbook_id}/images
```

`blob_storage.upload_file()`에는 판별된 실제 확장자와 Content-Type을 전달한다. 원본 파일명은 Blob 이름에 포함하지 않는다.

### 9. 오디오 검증과 저장

오디오 검증은 서비스에 직접 구현하지 않고 `app/common/audios.py` 같은 공통 모듈로 분리한다. 모듈은 파일 읽기, 크기 제한과 실제 형식 판별을 담당하고 서비스에는 `(data, audio_format)`을 반환한다.

- 파일당 최대 30MB다.
- MP3, M4A, AAC, WAV, OGG, WebM을 허용한다.
- 원본 파일명과 multipart Content-Type만으로 허용 여부를 판단하지 않는다.
- 파일 시그니처와 컨테이너 헤더로 실제 형식을 판별하고 그 형식의 확장자와 Content-Type으로 저장한다.
- 빈 파일과 형식을 판별할 수 없는 파일은 공통 `400 INVALID_REQUEST`로 처리한다.
- 오디오가 여러 개면 요청 순서를 URL 배열 순서로 유지한다.
- 오디오가 없으면 빈 배열이 아니라 DB와 응답 모두 `NULL`을 사용한다.

Blob prefix는 다음과 같다.

```text
guestbook/general/{guestbook_id}/audios
guestbook/road/{guestbook_id}/audios
```

파일 개수는 비즈니스 규칙으로 제한하지 않는다. 단, 파일을 모두 동시에 무제한 메모리에 올리지 말고 파일별 크기 제한을 적용하면서 순서대로 검증·처리한다.

### 10. 트랜잭션과 Blob 정리

MySQL 트랜잭션과 Blob Storage 업로드는 하나의 원자적 트랜잭션이 될 수 없으므로 보상 삭제를 적용한다.

1. DB 행을 `flush()`하여 id를 얻되 아직 `commit()`하지 않는다.
2. 파일을 하나씩 업로드하며 성공한 URL을 별도 목록에 기록한다.
3. 모든 URL을 ORM 객체에 반영한 뒤 한 번만 `commit()`한다.
4. 업로드 또는 DB 저장 중 하나라도 실패하면 `rollback()`한다.
5. 실패 전에 업로드된 모든 파일을 `blob_storage.delete_file()`로 삭제한다.
6. Blob 삭제 중 일부가 실패해도 원래 발생한 예외를 바꾸지 않는다. 삭제 실패는 로그로 남긴다.

파일이 없는 요청도 동일한 DB 트랜잭션 흐름을 사용하되 Blob 함수를 호출하지 않는다.

### 11. 재호출과 중복 생성

이 API는 멱등 API가 아니다. 정상 요청을 호출할 때마다 새로운 `GUESTBOOK` 또는 `ROAD_GUESTBOOK` 행을 생성한다.

- 동일한 사용자, 장소, 방문 날짜와 콘텐츠 조합도 다시 저장할 수 있다.
- 동일한 길바닥 좌표와 장소 별칭도 다시 저장할 수 있다.
- 기존 방명록을 찾아 덮어쓰거나 소프트 삭제하지 않는다.
- 네트워크 재시도로 같은 요청이 두 번 도착하면 두 건이 생성될 수 있다.

향후 중복 방지 요구가 생기면 별도의 idempotency key 정책으로 추가해야 하며 현재 구현에서 콘텐츠 비교로 임의 중복 제거를 하면 안 된다.

### 12. 응답 구성

응답은 저장이 끝난 ORM 값만 사용해 1-depth 구조로 구성한다. 요청 파일명이나 업로드 전 값을 응답에 사용하지 않는다.

- `GENERAL`은 `locationAlias`, `latitude`, `longitude`를 `null`로 둔다.
- `ROAD`는 `locationId`, `missionId`를 `null`로 둔다.
- 이미지와 오디오가 없으면 각각의 URL 필드는 `null`이다.
- 존재하지만 미완료인 미션 id가 요청되었으면 `missionId`는 실제 저장값과 같은 `null`이다.
- 응답 필드는 유형이나 값에 따라 생략하지 않는다.
- DB commit 이후 저장된 `saved_at`을 KST 기준 offset 없는 ISO 8601로 직렬화한다.

### 13. 구현 위치

- `app/guestbook/router.py`
  - multipart Form/File 파라미터와 현재 사용자 의존성을 선언하고 서비스만 호출한다.
  - 정상 상태 코드는 201, 응답 모델은 통합 1-depth 모델을 사용한다.
- `app/guestbook/schemas.py`
  - `guestbookType` Enum, 조건부 요청 검증과 통합 응답 모델을 정의한다.
- `app/guestbook/service.py`
  - 장소·방문·미션 검증, ORM 생성, Blob 업로드, commit과 실패 정리를 조정한다.
- `app/common/images.py`
  - 기존 이미지 읽기와 실제 형식 판별을 재사용한다.
- `app/common/audios.py`
  - 오디오 읽기, 크기 제한과 실제 형식 판별을 구현한다.
- `app/services/blob_storage.py`
  - 기존 `upload_file()`과 `delete_file()`을 재사용한다.

이 API를 위해 `Location`, `VisitedLocation`, `Mission` 또는 유형별 미션 진행도 ORM을 방명록 도메인에 중복 정의하지 않는다. 각 소유 도메인 모델을 import한다.

### 14. 오류 판정 순서

`GENERAL` 요청의 도메인 오류는 다음 순서로 판정한다.

1. 장소가 없으면 `404 LOCATION_NOT_FOUND`
2. 현재 사용자의 방문 이력이 없으면 `409 LOCATION_NOT_VISITED`
3. `missionId`가 전달됐지만 미션이 없으면 `404 MISSION_NOT_FOUND`

미션이 존재하지만 미완료인 경우는 오류가 아니다. `mission_id = NULL`로 저장하고 정상 응답한다.

요청 형식, 유형별 필수 필드, 문자열 길이, 좌표 범위, 파일 크기와 파일 형식 오류는 공통 `400 INVALID_REQUEST`로 처리한다. 인증 실패와 예상하지 못한 저장·Blob 오류는 각각 프로젝트 공통 401, 500 정책을 사용한다. 공통 오류를 위한 방명록 전용 코드는 만들지 않는다.

### 15. 필수 테스트

최소한 다음 동작을 API 단위 테스트로 검증한다.

1. 방문 이력이 있는 사용자가 일반 방명록을 작성하면 201과 저장된 1-depth 응답을 받는다.
2. 같은 장소에 여러 번 작성하면 기존 행을 바꾸지 않고 매번 새 행이 생성된다.
3. 방문 기록의 날짜와 요청 `visitedAt`이 달라도 방문 이력이 존재하면 작성된다.
4. 다른 사용자만 방문한 장소는 `409 LOCATION_NOT_VISITED`다.
5. 장소가 없으면 `404 LOCATION_NOT_FOUND`이고 Blob과 DB에 아무것도 남지 않는다.
6. 미션이 없으면 `404 MISSION_NOT_FOUND`이고 Blob과 DB에 아무것도 남지 않는다.
7. 문화·보물·협동 미션 각각 현재 사용자의 완료 이력이 있으면 `mission_id`가 저장된다.
8. 미션이 존재하지만 미완료이면 작성은 성공하고 DB와 응답의 `missionId`가 `null`이다.
9. 다른 사용자만 완료한 미션은 현재 사용자에게 미완료로 처리되어 `mission_id`가 `NULL`이다.
10. 길바닥 방명록은 장소·방문 이력 없이 저장되고 `location_id = NULL`이다.
11. 같은 길바닥 좌표에 여러 번 작성해도 매번 새 행이 생성된다.
12. 콘텐츠를 전부 생략한 일반·길바닥 방명록도 생성된다.
13. 여러 이미지와 오디오의 Blob URL 및 DB 배열 순서가 요청 순서와 같다.
14. 파일이 없으면 URL 컬럼과 응답 필드가 빈 배열이 아니라 `null`이다.
15. 허용 파일 형식별 확장자와 Content-Type이 실제 파일 내용 기준으로 결정된다.
16. 빈 파일, 허용하지 않는 형식과 파일당 크기 초과는 공통 400이고 DB·Blob에 데이터가 남지 않는다.
17. 일부 파일 업로드 후 다음 업로드가 실패하면 앞서 업로드된 Blob을 모두 삭제하고 DB를 rollback한다.
18. 파일 업로드 후 DB commit이 실패하면 업로드된 Blob을 모두 삭제한다.
19. 유형별 미사용 필드에 값이 오거나 필수 필드가 빠지면 공통 400이다.
20. 인증되지 않은 요청은 공통 401이고 DB·Blob에 데이터가 남지 않는다.

테스트에서 Blob Storage는 실제로 호출하지 않고 업로드·삭제 함수를 monkeypatch하여 호출 순서, 경로, URL 저장과 실패 정리를 검증한다. 구현 후 테스트 의도와 실행 방법을 `app/guestbook/docs/TEST_GUIDE.md`에 정리한다.

---

## C. 방명록 조회

### 1. 적용 범위

이 절은 현재 사용자가 작성한 일반 방명록과 길바닥 방명록 전체를 조회하는 API의 내부 구현 규칙을 정의한다.
응답 필드와 JSON 구조는 노션 API 명세를 기준으로 하며 여기서 반복하지 않는다.

이 API는 사용자 본인의 방명록 보관함 조회다. 지도 화면에 노출할 다른 사용자의 방명록이나 특정 장소의 방명록을 조회하는 용도로 재사용하지 않는다.

### 2. 사용자 식별과 조회 범위

현재 사용자는 `get_current_user_id()`로 식별한다. 클라이언트에서 사용자 id를 받지 않는다.

일반 방명록은 다음 조건을 모두 만족하는 행만 조회한다.

```text
GUESTBOOK.user_id = current_user_id
AND GUESTBOOK.deleted_at IS NULL
```

길바닥 방명록은 다음 조건을 모두 만족하는 행만 조회한다.

```text
ROAD_GUESTBOOK.user_id = current_user_id
AND ROAD_GUESTBOOK.deleted_at IS NULL
```

- 다른 사용자의 데이터는 포함하지 않는다.
- 소프트 삭제된 행은 일반·길바닥 목록 모두에서 제외한다.
- 조회 결과가 없어도 오류가 아니며 해당 배열을 빈 배열로 반환한다.

### 3. 페이지네이션과 정렬

페이지네이션을 적용하지 않는다.

- `page`, `size`, cursor 등의 Query를 받지 않는다.
- SQL에 `LIMIT`과 `OFFSET`을 적용하지 않는다.
- 전체 개수, 전체 페이지, 다음 페이지 여부를 계산하지 않는다.
- 응답에 `pageInfo`를 만들지 않는다.

두 테이블의 결과는 합친 뒤 다시 나누지 않고 각각 독립적으로 조회하고 정렬한다.

```text
ORDER BY saved_at DESC, id DESC
```

- 저장 시각이 최신인 방명록이 배열 앞에 온다.
- `saved_at`이 같으면 id가 큰 행이 앞에 온다.
- 일반·길바닥 목록 사이의 전역 순서는 정의하지 않는다.
- Python에서 다시 정렬하지 않고 DB 쿼리에 정렬 조건을 둔다.

전체 조회는 현재 확정된 요구사항이다. 임의로 최대 건수를 두거나 일부만 잘라 반환하면 안 된다. 향후 데이터 증가로 페이지네이션이 필요해지면 API 계약을 별도로 변경한다.

### 4. 일반 방명록 연관 데이터 조회

일반 방명록은 각 행의 장소 정보와 선택적인 미션 정보를 함께 반환한다.

#### 장소

`GUESTBOOK.location_id = LOCATION.id`로 장소를 조회한다.

- `GUESTBOOK.location_id`는 NOT NULL FK이므로 응답의 `location`은 항상 객체다.
- 위도는 `LOCATION.my`, 경도는 `LOCATION.mx`를 사용한다.
- 장소 정보는 방명록별 추가 쿼리로 가져오지 않는다.

#### 미션

`GUESTBOOK.mission_id = MISSION.id`로 공통 미션을 조회한다.

- `mission_id`가 `NULL`이면 응답의 `mission`은 `null`이다.
- 값이 있으면 공통 `MISSION`의 id, 유형과 제목으로 응답을 구성한다.
- 조회 시점에 미션 완료 여부를 다시 검사하지 않는다. 작성 API가 저장한 `mission_id`를 기준으로만 반환한다.
- 미션 보상, 세부 미션 id와 진행도 정보는 추가 조회하지 않는다.

일반 방명록 목록은 `LOCATION`을 필수 JOIN하고 `MISSION`을 선택적 OUTER JOIN하여 한 번의 목록 쿼리로 필요한 데이터를 가져온다. 방명록 개수만큼 장소나 미션을 개별 조회하는 N+1 쿼리를 만들지 않는다.

### 5. 길바닥 방명록 데이터 조회

길바닥 방명록은 `ROAD_GUESTBOOK`에 저장된 값만으로 응답을 구성한다.

- 장소 별칭은 `location_alias`다.
- 위도는 `my`, 경도는 `mx`다.
- `location_id`는 응답에 사용하지 않는다.
- `LOCATION`이나 `MISSION`을 JOIN하지 않는다.
- 지도 좌표의 유효성이나 현재 사용자 GPS와의 거리를 다시 검증하지 않는다.

### 6. 콘텐츠 값 보존

일반·길바닥 방명록 모두 콘텐츠를 조회 시점에 가공하지 않고 DB 저장값 그대로 반환한다.

- `content_img_url = NULL`이면 `contentImageUrls = null`
- `content_img_url = []`이면 `contentImageUrls = []`
- `content_audio_url = NULL`이면 `contentAudioUrls = null`
- `content_audio_url = []`이면 `contentAudioUrls = []`
- 글, 날씨와 색상 값이 `NULL`이면 각각 `null`
- URL 배열의 순서를 변경하거나 중복 URL을 제거하지 않는다.
- Blob 파일을 다시 읽거나 URL 유효성을 검사하지 않는다.

`visited_at`은 `yyyy-MM-dd`, `saved_at`은 KST 기준 offset 없는 ISO 8601 date-time으로 직렬화한다.

### 7. 응답 조합

서비스는 일반 방명록 조회 결과를 `generalGuestbooks`, 길바닥 방명록 조회 결과를 `roadGuestbooks`로 각각 변환한다.

- 두 최상위 배열 키는 항상 포함한다.
- 한 유형의 결과만 없어도 해당 배열만 빈 배열로 둔다.
- 일반 방명록의 `location`과 선택적 `mission` 중첩 구조를 길바닥 응답에 억지로 맞추지 않는다.
- 목록 항목에 `guestbookType`을 추가하지 않는다. 최상위 배열 이름으로 유형이 구분된다.
- 페이지 정보나 전체 개수 필드를 추가하지 않는다.

### 8. 읽기 전용 처리

이 API는 읽기 전용이다.

- 방명록, 장소와 미션 데이터를 생성·수정·삭제하지 않는다.
- `db.flush()` 또는 `db.commit()`을 호출하지 않는다.
- Blob Storage의 업로드·삭제·조회 함수를 호출하지 않는다.
- 조회 과정에서 소프트 삭제 상태를 되돌리거나 콘텐츠 값을 정규화하여 저장하지 않는다.

### 9. 구현 위치

- `app/guestbook/router.py`
  - DB와 현재 사용자 의존성을 받고 서비스 함수만 호출한다.
  - Query 모델을 받지 않는다.
- `app/guestbook/schemas.py`
  - 일반 방명록, 장소, 미션, 길바닥 방명록과 최상위 응답 모델을 정의한다.
  - 모든 응답 alias는 camelCase를 사용한다.
- `app/guestbook/service.py`
  - 두 목록 쿼리, 정렬과 응답 변환을 담당한다.

장소와 미션 ORM은 각 소유 도메인에서 import하고 방명록 도메인에 중복 모델을 만들지 않는다.

### 10. 오류 처리

이 API에는 별도의 도메인 오류가 없다.

- 결과 없음은 404가 아니라 빈 배열을 포함한 200 응답이다.
- 미션이 연결되지 않은 일반 방명록은 오류가 아니라 `mission=null`이다.
- 공통 401과 500은 프로젝트 공통 처리 정책을 사용하며 API 명세에 별도로 적지 않는다.

### 11. 필수 테스트

최소한 다음 동작을 API 단위 테스트로 검증한다.

1. 현재 사용자의 일반·길바닥 방명록이 각각 올바른 배열로 반환된다.
2. 다른 사용자의 일반·길바닥 방명록은 반환되지 않는다.
3. 소프트 삭제된 일반·길바닥 방명록은 반환되지 않는다.
4. 두 목록이 각각 `saved_at DESC, id DESC` 순서다.
5. 두 유형 모두 없으면 200과 두 개의 빈 배열을 반환한다.
6. 일반 방명록이 없거나 길바닥 방명록만 없는 경우에도 두 배열 키를 모두 반환한다.
7. 일반 방명록의 장소 필드는 `LOCATION` 값과 좌표 방향에 맞게 구성된다.
8. 연결된 미션이 있으면 공통 `MISSION` 정보가 반환되고 없으면 `mission=null`이다.
9. 길바닥 방명록은 별칭과 `my → latitude`, `mx → longitude`로 반환된다.
10. 콘텐츠의 `NULL`, 빈 배열과 URL 배열 순서가 DB 저장값 그대로 유지된다.
11. 응답에 `pageInfo`가 없고 Query 없이 전체 데이터가 반환된다.
12. 조회 전후 DB 데이터가 변경되지 않고 Blob 함수가 호출되지 않는다.
13. 인증되지 않은 요청은 공통 `401 UNAUTHORIZED_USER`다.

목록 쿼리 테스트에서는 SQL 쿼리 개수가 방명록 건수에 따라 증가하지 않는지도 확인하여 장소·미션 N+1 회귀를 막는다. 구현 후 테스트 의도와 실행 방법을 `app/guestbook/docs/TEST_GUIDE.md`에 정리한다.
