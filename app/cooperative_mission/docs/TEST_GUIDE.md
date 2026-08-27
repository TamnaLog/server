# 협동 미션 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `POST /api/v1/cooperative-missions/{cooperativeMissionId}/progress` (협동 미션 시작하기/이어하기) | `app/cooperative_mission/tests/test_start_cooperative_mission.py` |
| `POST /api/v1/cooperative-missions/join-requests` (URL로 참여 요청) | `app/cooperative_mission/tests/test_join_cooperative_mission.py` |
| `PATCH /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/{participantId}/accept` (참여 요청 수락) | `app/cooperative_mission/tests/test_accept_join_request.py` |
| `DELETE /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/{participantId}` (참여 요청 거절) | `app/cooperative_mission/tests/test_reject_join_request.py` |
| 소프트 삭제(`deleted_at`) 공통 필터 — 위 API 전반 | `app/cooperative_mission/tests/test_soft_delete_filter.py` |

## 시작하기/이어하기 테스트 의도

이 API의 핵심은 **"이 요청이 새 방을 만들 상황인가, 기존 방을 돌려줄 상황인가"** 를 정확히 가르는 것이다.
같은 요청이라도 진행 이력에 따라 201과 200으로 갈리고, 잘못 판단하면
**방이 중복 생성되거나 남의 방을 이어받는** 사고가 난다.

그래서 "이어하기 대상이 아닌 경우"를 하나씩 따로 만들어 검증한다.

- 이미 **완료된** 방만 있는 경우 → 새 도전이므로 새 방
- 그 방에 **`MEMBER`로만** 참여 중인 경우 → 방장이 아니므로 새 방
- **다른 협동 미션**의 진행 중인 방 → 대상 아님
- **다른 사용자가 방장**인 방 → 대상 아님

두 번째 축은 **진행도와 방장 참여자가 항상 함께 존재하는 것**이다.
방장 없는 방이나 방 없는 참여자가 남으면 이후 API가 전부 어긋나므로,
저장이 실패하면 둘 다 저장되지 않아야 한다.

세 번째는 **역할 카드가 방에 복사되지 않는 것**이다.
역할 카드는 특정 미션에 속하지 않는 공통 마스터라, 방을 만들어도 카드 수가 늘면 안 된다.

## 주요 검증 항목

### 1. 신규 생성

- 처음 시작하면 **201**, 응답 필드가 명세와 일치한다.
  (`missionProgressId`, `missionProgressStatus`, `currentStep`, `teamToken`,
  `participants`, `roleCards`, `roleProgresses` / camelCase 확인)
- DB에 진행도가 `current_step=1` / `IN_PROGRESS` / `completed_at=null` 로 저장된다.
- 보상 지급 여부 3개 컬럼은 모두 `false` 로 남는다. (이 API는 보상을 다루지 않는다)
- 방장 참여자가 `HOST` / `ACCEPTED` / `joined_at` 기록과 함께 **함께** 생성된다.
- `roleProgresses` 는 `null` 이 아니라 **빈 배열**이다.

### 2. 팀 토큰

초대 URL 조합은 프론트 책임이라 백엔드는 토큰만 내려준다.

- `teamToken` 은 DB에 저장된 `team_token` 과 같다.
- 응답에 URL 형태(`http`, `/cooperative-missions/invite`)가 섞여 나오지 않는다.
- 방마다 다른 토큰이 생성된다.

### 3. 이어하기

- 방장으로 진행 중인 방이 있으면 **200**, 기존 `missionProgressId` / `currentStep` 을 반환하고
  **진행도와 참여자가 늘지 않는다.**
- 팀 토큰을 새로 만들지 않으므로 **프론트가 만드는 초대 링크도 그대로 유효**하다.
- 시작 API를 **연속 두 번 호출**하면 201 → 200이고 같은 방을 반환한다.

### 4. 목록 구성

- `participants` 는 **방장을 먼저** 두고 나머지는 참여한 순서로 정렬한다.
  (방장을 일부러 마지막 id로 넣어 두어, id 순으로 정렬하면 실패한다)
- 아직 수락 전인 `PENDING` 참여 요청도 목록에 포함한다.
- `roleProgresses` 는 참여자·역할 카드를 조인해 닉네임과 역할 이름까지 채운다.
- **다른 방의 역할 진행도는 포함하지 않는다.**

### 5. 역할 카드

- 공통 마스터 전체를 `id` 오름차순으로 반환한다.
- **미션이 달라도 같은 목록**이 나온다.
- 방을 만들어도 역할 카드가 복사되거나 늘지 않는다.
- 역할 카드 마스터가 비어 있으면 응답을 만들 수 없으므로 **500 `INTERNAL_SERVER_ERROR`**.

### 6. 오류

- 협동 미션이 없으면 **404 `COOPERATIVE_MISSION_NOT_FOUND`** 이고,
  이때 **진행도와 참여자를 만들지 않는다.**
- 저장이 실패하면 진행도도 참여자도 남지 않는다. (한 트랜잭션인지 확인)
- `cooperativeMissionId` 가 정수가 아니거나 1보다 작으면 **400 `INVALID_REQUEST`**.

## URL로 참여 요청 테스트 의도

이 API의 핵심은 **검증 순서**다.
"이미 참여자인가"를 **단계·인원 검증보다 먼저** 확인해야 한다.
순서를 뒤집으면 방장이 자기 초대 링크를 열었을 때, 또는 이미 요청한 사람이 링크를 다시 열었을 때
멀쩡한 사용자에게 `409`가 나간다. 그래서 "정원이 찼는데 기존 참여자", "단계가 지났는데 기존 참여자"를
따로 만들어 **200이 나오는지** 확인한다.

두 번째는 **인원 계산에 수락 대기(`PENDING`)도 포함**하는 것이다.
`ACCEPTED`만 세면 대기자가 쌓여 정원을 넘길 수 있다.

세 번째는 **요청자를 Body가 아니라 헤더로 식별**하는 것이다.
액세스 토큰을 바꾸면 저장되는 `user_id`도 따라 바뀌어야 한다.

### 주요 검증 항목

#### 1. 신규 참여 요청

- **201**, 응답은 `missionProgressId` / `participantId` / `participantStatus` 세 필드다.
- DB에 `PENDING` / `MEMBER` / `joined_at=null` 로 저장된다. (아직 수락 전이므로 참여 시각 없음)
- 헤더의 사용자가 그대로 `user_id` 로 저장된다.

#### 2. 기존 참여자

- 이미 요청한 사용자 → **200**, 같은 `participantId`, 참여자 수 그대로.
- 이미 수락된 사용자 → **200**, `ACCEPTED` 로 반환하고 **상태를 되돌리지 않는다.**
- **방장이 자기 링크를 열면** → 200, `HOST` 참여자 정보를 그대로 반환.
- 같은 요청을 두 번 보내면 201 → 200이고 참여자는 하나만 생긴다.
- **정원이 찼거나 단계가 지나도 기존 참여자는 409가 아니라 200**이다.

#### 3. 409 참여를 받을 수 없는 경우

- `current_step` 이 2 / 3 / 4 면 **`COOPERATIVE_MISSION_JOIN_CLOSED`**.
- 참여자가 6명이면 **`COOPERATIVE_MISSION_FULL`**.
- `PENDING` 참여자만으로 6명이어도 `FULL` 이다. (대기자도 인원에 포함)
- 5명이면 한 자리 남으므로 정상 참여된다. (경계값)
- 모두 참여자를 만들지 않는다.

#### 4. 404 `INVALID_INVITE_TOKEN`

- 없는 팀 토큰
- 토큰은 맞지만 이미 **완료된 방**인 경우

#### 5. 400 / 401

- `teamToken` 누락 · 빈 문자열 · `null` → **400 `INVALID_REQUEST`**
- 헤더의 사용자가 없으면 **401 `UNAUTHORIZED_USER`** 이고 참여자도 생기지 않는다.

## 참여 요청 수락 테스트 의도

이 API는 응답 본문이 없다(`204`). 그래서 확인할 것은 응답 형식이 아니라 **DB가 어떻게 바뀌었는가**와
**누가 이 요청을 할 수 있는가**다.

첫째는 **방장 권한**이다. 방장 여부를 요청 값이 아니라 토큰으로 식별한 사용자의 참여자 row로 판단하므로,
팀원 본인 / 방에 없는 사람 / 다른 방의 방장이 각각 `403`인지 본다.
특히 권한 검증이 단계 검증보다 **앞**이어서, 남의 방에 요청해도 그 방의 진행 단계를 알 수 없어야 한다.

둘째는 **두 Path id의 관계**다. `participantId`만 믿고 수락하면 다른 방 팀원을 수락할 수 있다.
그래서 "참여자는 있는데 다른 방 소속", "대상이 방장" 같은 경우를 `404`로 확인한다.

셋째는 **멱등성**이다. 프론트가 응답을 못 받아 재전송해도 상태와 `joined_at`이 다시 바뀌면 안 된다.
이미 `ACCEPTED`인 참여자를 다시 수락해도 `204`이고 수락 시각이 그대로인지 본다.

### 주요 검증 항목

#### 1. 수락 처리

- **204**이고 응답 본문이 비어 있다.
- 대상 참여자가 `PENDING → ACCEPTED` 로 바뀌고 `joined_at` 이 기록된다.
- 역할(`MEMBER`)과 소속 방은 그대로다.
- **새 참여자 row를 만들지 않는다.** (기존 row 갱신)

#### 2. 멱등 재요청

- 이미 `ACCEPTED` 인 참여자를 다시 수락해도 **204**, `joined_at` 은 기존 값 유지.
- 같은 요청을 연속 두 번 보내도 수락 시각과 참여자 수가 그대로다.

#### 3. 403 `COOPERATIVE_MISSION_HOST_ONLY`

- 수락 대기 중인 **팀원 본인**이 요청한 경우
- 방에 참여하지 않은 사용자가 요청한 경우
- **다른 방의 방장**이 요청한 경우 (자기 방에서만 방장이다)
- 모두 참여자 상태를 바꾸지 않는다.
- 단계가 지난 방이어도 방장이 아니면 **409보다 403이 먼저**다.

#### 4. 404

- 진행도가 없거나 **이미 완료된 방** → `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`
  (없는 방과 끝난 방을 구분해서 노출하지 않는다)
- 참여자가 없거나 **다른 방 소속**이거나 **대상이 방장**
  → `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`

#### 5. 409 `COOPERATIVE_MISSION_JOIN_CLOSED`

- `current_step` 이 2 / 3 이면 수락할 수 없고, 상태와 `joined_at` 도 그대로다.

#### 6. 400 / 401

- 두 Path id가 0 이하이거나 정수가 아니면 **400 `INVALID_REQUEST`**
- 헤더의 사용자가 없으면 **401 `UNAUTHORIZED_USER`** 이고 참여자 상태도 그대로다.

## 참여 요청 거절 테스트 의도

거절은 수락과 **권한·단계·대상 검증이 똑같고 마지막 한 걸음만 다르다.**
상태를 바꾸는 대신 참가자 row 를 **소프트 삭제한다.** 그래서 검증도 "무엇이 사라졌는가"에 맞춘다.

소프트 삭제라 확인할 것이 하나 늘어난다. **조회에서는 사라지지만 행은 남아 있어야 한다.**
그래서 "살아 있는 참가자 목록"과 "실제 row 목록"을 따로 조회해 둘 다 확인한다.

첫째, **`REJECTED` 상태를 남기지 않는다.** 거절하면 조회 결과에서 사라져야 하고,
그 결과로 **자리가 하나 비어 거절당한 사용자가 같은 초대 URL 로 다시 요청**할 수 있어야 한다.
그래서 거절 후 참여 요청 API 를 실제로 다시 호출해 201 이 나오는지까지 본다.

둘째, **이미 수락된 팀원은 이 API 로 지울 수 없다.** 수락된 팀원 내보내기는 다른 동작이라
`409 COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED` 이고 row 도 그대로여야 한다.
(수락이 먼저 커밋된 뒤 들어온 거절 요청이 이 경우다)

셋째, 거절은 되돌릴 수 없으므로 **막아야 할 요청에서 정말 아무것도 지워지지 않는지**를
모든 오류 케이스에서 참가자 목록으로 확인한다.

### 주요 검증 항목

#### 1. 거절 처리

- **204**이고 응답 본문이 비어 있다.
- 대상 참가자가 조회에서 빠지고 방장은 그대로 남는다.
- row 자체는 지우지 않는다. `deleted_at` 만 채워지고 `participant_status` 는 `PENDING` 그대로다.
- 거절당한 사용자는 같은 초대 URL 로 다시 요청해 새 `PENDING` 이 만들어진다.
  이때 삭제된 row 를 되살리지 않고 **새 `participantId`** 가 발급된다.
- 같은 `participantId` 로 다시 거절하면 **404** (삭제된 row 를 복원하지 않는다)

#### 2. 409 `COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED`

- 이미 `ACCEPTED` 인 팀원은 삭제하지 않고 409.

#### 3. 403 `COOPERATIVE_MISSION_HOST_ONLY`

- 팀원 본인 / 방에 없는 사용자 / **다른 방의 방장**이 요청한 경우
- 단계가 지난 방이어도 방장이 아니면 **409보다 403이 먼저**다.
- 모두 참가자를 지우지 않는다.

#### 4. 404

- 진행도가 없거나 **이미 완료된 방** → `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`
- 참여자가 없거나 **다른 방 소속**이거나 **대상이 방장**(방장은 자기 자신을 거절할 수 없다)
  → `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`

#### 5. 409 `COOPERATIVE_MISSION_JOIN_CLOSED`

- `current_step` 이 2 / 3 이면 거절할 수 없고 참가자도 그대로다.

#### 6. 400 / 401

- 두 Path id가 0 이하이거나 정수가 아니면 **400 `INVALID_REQUEST`**
- 헤더의 사용자가 없으면 **401 `UNAUTHORIZED_USER`**
- 두 경우 모두 참가자를 지우지 않는다.

## 소프트 삭제 필터 테스트 의도

`COOPERATIVE_MISSION_PROGRESS` / `COOPERATIVE_MISSION_PARTICIPANT` /
`COOPERATIVE_ROLE_PROGRESS` 세 테이블은 행을 지우지 않고 `deleted_at` 으로 삭제를 표현한다.
그래서 **조회할 때마다 `deleted_at IS NULL` 을 빠뜨리지 않았는지**가 이 도메인의 상시 위험 요소다.
한 곳만 빠져도 삭제된 참가자가 인원 수에 잡히거나, 끝난 방이 홈에 다시 뜨거나,
없는 역할이 배정된 것으로 처리된다.

이 테스트는 필터를 쿼리 단위로 확인하지 않는다.
**행 하나를 소프트 삭제한 뒤 API 응답이 실제로 달라지는지**로 확인한다.
필터가 빠지면 응답이 그대로라서 바로 실패한다.

### 주요 검증 항목

#### 1. 참여자 소프트 삭제

- 상태 조회의 `participants` 에서 빠진다.
- 삭제된 본인이 폴링하면 **404 `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`**
- 홈 조회의 진행 중 미션에서 빠진다.
- **인원 수에 들어가지 않는다.** 정원이 찬 방에서 한 명을 삭제하면 새 참여 요청이 201 로 통과한다.
- 삭제된 방장은 방장 권한을 잃는다. (**403 `COOPERATIVE_MISSION_HOST_ONLY`**)
  이어하기 대상도 아니라서 새 방이 만들어진다.
- 수락 대기(`PENDING`) 집계에서도 빠져 `1 → 2` 단계 변경을 막지 않는다.

#### 2. 진행도 소프트 삭제

- 상태 조회 / 단계 변경에서 **404 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`**
- 홈 조회의 진행 중 미션에서 빠진다.
- 그 방의 팀 토큰으로는 참여할 수 없다. (**404 `INVALID_INVITE_TOKEN`**)
- 이어하기 대상이 아니라서 새 방이 만들어진다.

#### 3. 역할 진행도 소프트 삭제

- 상태 조회의 `roleProgresses` 와 `totalRoleCount` 에서 빠진다.
- 역할이 삭제된 참가자는 **역할을 받지 않은 것으로 본다.**
  (`2 → 3` 이 **409 `COOPERATIVE_PARTICIPANT_ROLE_REQUIRED`** 로 막힌다.
  `OUTER JOIN` 의 `ON` 절에 필터를 두지 않으면 이 테스트가 깨진다)
- 사진 인증 대상이 아니다. (**404 `COOPERATIVE_ROLE_PROGRESS_NOT_FOUND`**)
- 그 역할 카드를 다시 배정할 수 있고, 삭제된 row 를 되살리지 않고 새 row 를 만든다.

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 협동 미션 도메인만
pytest app/cooperative_mission

# 특정 테스트만
pytest app/cooperative_mission/tests/test_start_cooperative_mission.py -k 이어하기
pytest app/cooperative_mission/tests/test_join_cooperative_mission.py -k 기존
pytest app/cooperative_mission/tests/test_accept_join_request.py -k 멱등
pytest app/cooperative_mission/tests/test_reject_join_request.py -k 거절
pytest app/cooperative_mission/tests/test_soft_delete_filter.py
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고,
협동 미션 / 역할 카드 6종 / 사용자 목업은 `cooperative_data` 픽스처에서 만든다.
진행도와 참여자는 조합이 테스트마다 달라서 `_add_progress()` / `_add_participant()` 헬퍼로 직접 만든다.

팀 토큰 충돌 재시도는 난수라 테스트로 재현하기 어렵다.
`app/cooperative_mission/service.py`의 `MAX_TEAM_TOKEN_ATTEMPTS` 안에서
중복이면 트랜잭션을 되돌리고 새 토큰으로 다시 시도하며, 계속 실패하면 공통 500으로 처리한다.

참여 요청 테스트는 `join_data` 픽스처로 방장 1명이 있는 방 하나와 참여 가능한 사용자들을 만든다.
동시 요청 시 인원 초과를 막는 진행도 행 잠금(`SELECT ... FOR UPDATE`)은 MySQL 에서만 걸리고
테스트 DB인 SQLite 에서는 무시되므로, 잠금 자체는 테스트로 검증하지 않는다.
