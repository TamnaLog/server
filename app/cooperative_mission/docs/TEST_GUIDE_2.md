# 협동 미션 도메인 테스트 가이드 (2)

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `GET /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress` (협동 미션 상태 조회) | `app/cooperative_mission/tests/test_get_cooperative_mission_status.py` |
| `PATCH /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress` (협동 미션 진행도 저장) | `app/cooperative_mission/tests/test_save_cooperative_mission_progress.py` |
| `PUT /api/v1/cooperative-missions/{cooperativeMissionProgressId}/role-assignments/{roleCardId}` (협동 미션 역할 배정 저장) | `app/cooperative_mission/tests/test_save_role_assignment.py` |
| `POST /api/v1/cooperative-missions/{cooperativeMissionProgressId}/role-progresses/{roleProgressId}/verification` (협동 미션 역할 진행도 저장) | `app/cooperative_mission/tests/test_verify_role_progress.py` |
| `DELETE /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/me` (협동 미션 나가기) | `app/cooperative_mission/tests/test_leave_cooperative_mission.py` |

## 상태 조회 테스트 의도

이 API는 방장과 팀원이 **초대부터 완료까지 계속 폴링하는 하나의 창구**다.
그래서 응답이 단계마다 완전히 다르고, 검증도 "이 단계에서 무엇을 주고 무엇을 `null` 로 두는가"가 중심이다.

| 필드 | 1단계 | 2·3단계 | 4단계 |
| --- | --- | --- | --- |
| `currentParticipant` / `participants` | 값 | 값 | `null` |
| `roleCards` | `null` | 값 | `null` |
| `roleProgresses` / 역할 집계 | `null` | 값(없으면 빈 배열·0) | `null` |
| `reward` / `nextLocation` | `null` | `null` | 값 |

특히 **키를 생략하지 않고 `null` 로 내려주는지**를 본다. 프론트가 폴링하며 같은 구조를 기대하기 때문이다.
1단계 응답은 전체 body 를 통째로 비교해서 이 규칙이 깨지지 않는지 확인한다.

요청은 Query 로 사용자 현재 위치(`latitude`, `longitude`)를 항상 받는다.
좌표는 4단계 `nextLocation.distanceMeter` 계산에만 쓰지만 폴링 중 언제 4단계가 될지 알 수 없어
모든 단계 요청에서 필수다. 그래서 좌표가 없거나 범위를 벗어나는 요청도 검증 대상에 넣는다.

두 번째 축은 **호출자에 따라 달라지는 값**이다. `currentParticipant` 는 Bearer 토큰으로 정해지므로,
같은 방을 팀원이 조회하면 자신의 `PENDING/ACCEPTED` 상태가 나와야 한다.
거절당한 팀원은 참가자 row 가 사라져 `404 COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND` 를 받고,
프론트는 이 오류로 거절을 감지한다. 그래서 이 404 를 **정상 흐름의 일부로** 검증한다.

세 번째 축은 **4단계의 보상 정산**이다. 조회 API지만 4단계에서는 데이터를 바꾼다.

- 보상 등급은 **완료된 역할 수**로 정해진다. (0 / 1~2 / 3~4 / 5~6)
- 보상은 `ACCEPTED` 참가자 **전원**에게 지급한다. (`PENDING` 은 제외)
- 정산이 끝나면 등급에 못 든 보상까지 포함해 지급 여부 세 개를 모두 `TRUE` 로 마감한다.
- 여러 참가자가 동시에 폴링해도 **지급은 한 번뿐**이어야 한다.

역할 진행도는 `COOPERATIVE_ROLE_PROGRESS` 를 직접 만들어 상황을 재현한다.
한 참가자가 서로 다른 역할 카드를 여러 개 맡는 경우도 함께 만든다. (배정 규칙상 허용된다)

## 주요 검증 항목

### 1. 1단계 (초대)

- 응답 전체가 명세와 일치한다. 사용하지 않는 필드는 키를 지우지 않고 `null` 이다.
- `participants` 는 방장을 먼저 두고 `PENDING` 팀원도 포함한다.
- `currentParticipant` 는 토큰의 사용자 기준이다. 팀원이 조회하면 자기 `PENDING` 상태가 나온다.

### 2. 2·3단계 (역할 배정 / 수행)

- `roleCards` 는 공통 역할 카드 6종 전체를 id 오름차순으로 반환한다.
- `roleProgresses` 는 생성된 역할 진행도만 반환하고 `itemImgUrl` 은 없으면 `null`.
- 아직 배정이 없으면 `roleProgresses` 는 **`null` 이 아니라 빈 배열**, 집계는 둘 다 `0`.
- `totalRoleCount` 는 생성된 역할 수, `completedRoleCount` 는 그중 인증 완료 수다.
  (배정하지 않은 역할 카드는 집계에 넣지 않는다)
- 2·3단계에서는 `reward` / `nextLocation` 이 `null` 이다.

### 3. 4단계 (완료)

- 참가자·역할 정보는 모두 `null` 이고 `reward` / `nextLocation` 만 채운다.
- 완료 역할 수별 보상 등급 7가지(0~6)를 각각 확인한다.
- `ACCEPTED` 참가자 전원의 `USER.point` 와 `ACQUIRED_AR_CHARACTER` 가 갱신된다.
- `PENDING` 참가자에게는 지급하지 않는다.
- 정산 후 지급 여부 세 개가 모두 `TRUE` 다. (등급에 없어 소멸한 보상 포함)
- 여러 번 폴링해도 포인트·획득 기록이 늘지 않고 같은 보상 정보를 반환한다.
- `nextLocation.distanceMeter` 는 Query 좌표와 추천 장소 좌표로 계산한 직선거리(m)와 같다.
  (공통 `distance.calculate_distance_meter()` 결과와 비교한다)
- 추천할 장소가 하나도 없으면 `nextLocation` 만 `null` 이고 보상 정산은 정상 처리된다.

### 4. 404

- 진행도가 없으면 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`
- 방의 참가자가 아니거나 **거절로 참가자 row 가 삭제된 경우**
  → `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`
- 완료(4단계)된 방도 조회할 수 있어야 한다. (진행 중인 방으로 제한하면 완료 화면을 못 본다)

### 5. 400 / 401

- 진행도 id가 0 이하이거나 정수가 아니면 **400 `INVALID_REQUEST`**
- Query 좌표가 없거나(둘 중 하나만 보낸 경우 포함), 숫자가 아니거나,
  `latitude` `-90~90` / `longitude` `-180~180` 범위를 벗어나면 **400 `INVALID_REQUEST`**
- 헤더의 사용자가 없으면 **401 `UNAUTHORIZED_USER`**

## 진행도 저장 테스트 의도

이 API는 **단계를 한 칸 올리는 것만** 한다. 역할을 배정하지도, 보상을 주지도, 상태를 돌려주지도 않는다.
그래서 검증은 "언제 올릴 수 있고, 올릴 때 무엇이 바뀌는가" 두 가지에 집중한다.

첫째, **순차 이동만 허용**한다. 같은 단계·역행·건너뛰기는 전부 `409`다.
특히 같은 요청이 두 번 들어오면 두 번째는 409여야 한다. (단계가 이미 올라갔으므로)
이건 재전송 방어이기도 해서 별도 케이스로 확인한다.

둘째, **단계마다 통과 조건이 다르다.**

- `1 → 2`: 수락도 거절도 안 된 `PENDING` 참여 요청이 남아 있으면 막는다.
  이때 남은 요청을 자동으로 수락하거나 지우지 않는지도 확인한다.
- `2 → 3`: `ACCEPTED` 참가자 전원이 역할을 하나 이상 받아야 한다.
  반대로 **역할 카드가 남아 있거나 한 사람이 여러 역할을 맡은 것은 막지 않는다.**
- `3 → 4`: 인증이 안 끝난 역할이 남아 있어도 방장이 끝낼 수 있다.

셋째, **완료 처리 범위**다. `3 → 4`에서만 `mission_status`와 `completed_at`이 함께 바뀌고,
보상은 여기서 지급하지 않는다(상태 조회 4단계가 정산). 지급 여부 세 개가 그대로 `false`인지 확인한다.

막아야 할 요청에서는 항상 `current_step`이 그대로인지 함께 본다.

### 주요 검증 항목

#### 1. 단계 변경

- **204**이고 응답 본문이 비어 있다.
- `1 → 2`, `2 → 3` 은 `current_step` 만 바꾸고 완료 정보는 건드리지 않는다.
- `3 → 4` 는 `current_step=4` / `mission_status=COMPLETED` / `completed_at` 을 함께 저장한다.
- 완료해도 보상 지급 여부와 사용자 포인트는 그대로다.

#### 2. `1 → 2` 조건

- `PENDING` 참가자가 있으면 **409 `COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS`**,
  참가자 상태도 그대로 남는다.
- 방장 혼자여도 2단계로 올릴 수 있다.

#### 3. `2 → 3` 조건

- `ACCEPTED` 참가자 전원이 역할을 받았으면 통과.
- 한 명이라도 역할이 없거나 배정이 하나도 없으면 **409 `COOPERATIVE_PARTICIPANT_ROLE_REQUIRED`**.
- 미배정 역할 카드가 남아 있어도, 한 참가자가 여러 역할을 맡아도 막지 않는다.
- `PENDING` 참가자는 역할 검증 대상이 아니다.

#### 4. 409 순차/완료

- 건너뛰기 · 같은 단계 · 역행 5가지 조합 → **`COOPERATIVE_MISSION_STEP_NOT_ALLOWED`**
- 같은 요청 재전송 → 두 번째는 409
- 이미 완료된 방 → **`COOPERATIVE_MISSION_ALREADY_COMPLETED`**
  (없는 방으로 감추지 않고 완료됐다고 알려준다)

#### 5. 403 / 404 / 401

- 팀원이나 방 밖 사용자가 요청하면 **403 `COOPERATIVE_MISSION_HOST_ONLY`**
- 진행도가 없으면 **404 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`**
- 헤더의 사용자가 없으면 **401 `UNAUTHORIZED_USER`**

#### 6. 400 `INVALID_REQUEST`

- `currentStep` 누락 · `1` · `5` · `0` · 정수 아님 · `null`
- 진행도 id가 0 이하이거나 정수가 아님

## 역할 배정 저장 테스트 의도

이 API는 **역할 카드 하나를 단위로 하는 upsert**다. 같은 엔드포인트가 처음엔 생성, 다음엔 담당자 변경으로
동작하므로 검증의 중심은 "언제 새 row 를 만들고 언제 기존 row 를 고치는가"다.

- 처음 배정 → 역할 진행도 **생성**
- 이미 배정된 카드 → 새 row 없이 `participant_id` **만** 변경 (`roleProgressId`·역할 카드·인증 정보 유지)
- 같은 참가자로 재요청 → 아무것도 바꾸지 않음 (`updated_at` 도 그대로)

가장 틀리기 쉬운 지점은 **기존 배정을 찾는 범위**다. 역할 카드는 모든 방이 공유하는 마스터라
카드 id 만으로 찾으면 다른 방의 배정을 잡아서 남의 방 데이터를 고치게 된다.
그래서 다른 방에 같은 역할 카드가 배정된 상태를 만들어 두고, 그 row 를 건드리지 않는지 확인한다.

두 번째는 **배정 대상 자격**이다. 방장도 역할을 맡을 수 있지만, 아직 수락 전(`PENDING`)이거나
다른 방 참가자는 배정 대상이 아니다. 셋 다 `404 COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND` 로 통일된다.

세 번째는 **단계 제한**이다. 역할 배정은 2단계에서만 가능하고, 1·3단계는 409,
완료된 방은 `ALREADY_COMPLETED` 로 구분한다. 막히는 경우에는 역할 진행도가 하나도 안 생기는지 함께 본다.

### 주요 검증 항목

#### 1. 최초 배정

- **204**이고 응답 본문이 비어 있다.
- `participant_id` / `cooperative_role_card_id` 가 요청대로 저장되고,
  `progress_status=IN_PROGRESS` / `item_img_url=null` / `completed_at=null` 로 시작한다.
- 방장도 배정받을 수 있다.
- 한 참가자가 서로 다른 역할 카드를 여러 개 맡을 수 있다. (row 2개, 같은 `participant_id`)
- 요청하지 않은 역할 카드는 역할 진행도가 생기지 않는다.

#### 2. 담당자 변경 / 멱등

- 이미 배정된 카드에 다른 참가자를 요청하면 **row 수는 그대로**, 같은 `roleProgressId` 에서
  `participant_id` 만 바뀐다.
- 인증이 끝난 역할이어도 `item_img_url` / `progress_status` / `completed_at` 은 유지한다.
- 같은 참가자로 다시 요청하면 `updated_at` 까지 그대로다.
- **다른 방의 같은 역할 카드 배정은 건드리지 않는다.**

#### 3. 403 / 409

- 방장이 아니면 **403 `COOPERATIVE_MISSION_HOST_ONLY`**
- 1단계·3단계면 **409 `COOPERATIVE_MISSION_STEP_NOT_ALLOWED`**
- 완료된 방이면 **409 `COOPERATIVE_MISSION_ALREADY_COMPLETED`**
- 모두 역할 진행도를 만들지 않는다.

#### 4. 404

- 진행도 없음 → `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`
- 역할 카드 없음 → `COOPERATIVE_ROLE_CARD_NOT_FOUND`
- 참가자 없음 / `PENDING` 참가자 / 다른 방 참가자 → `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`

#### 5. 400 / 401

- `participantId` 누락 · 0 · 음수 · 정수 아님 · `null` → **400 `INVALID_REQUEST`**
- 두 Path id가 0 이하이거나 정수가 아니면 **400**
- 헤더의 사용자가 없으면 **401 `UNAUTHORIZED_USER`**
- 모두 역할 진행도를 만들지 않는다.

## 역할 진행도 저장(사진 인증) 테스트 의도

이 API는 **판정 → 업로드 → DB 저장** 세 단계가 이어져 있고, 각 단계가 실패했을 때 남는 흔적이 다르다.
그래서 검증의 축은 "성공/실패에 따라 무엇이 남고 무엇이 남지 않는가"다.

가장 중요한 건 **인증 실패가 오류가 아니라는 점**이다. `200` + `isVerified: false` 이고
사진을 올리지도, `item_img_url` / `progress_status` / `completed_at` 을 건드리지도 않는다.
지금은 임시 구현이 항상 `True` 라 실패 케이스는 `photo_verifier.verify_role_image` 를 가짜로 바꿔 만든다.
(인증 방식이 바뀌어도 이 테스트는 그대로 쓸 수 있다)

두 번째는 **권한이 방장이 아니라 담당자 기준**이라는 점이다. 방장이라도 남의 역할은 인증할 수 없고,
담당자여도 참가 상태가 `ACCEPTED` 가 아니면 막힌다. 둘 다 `403`이다.

세 번째는 **보상 작업(compensation)** 이다. Blob 업로드는 트랜잭션에 묶이지 않으므로
DB 저장이 실패하면 올린 사진을 지워 DB가 참조하지 않는 파일이 남지 않아야 한다.
Blob 호출은 실제 Azure 로 나가지 않도록 `uploads` / `deletes` 픽스처로 가로챈다.

마지막으로 이 API는 **협동 미션 단계를 바꾸지 않는다.** 마지막 역할까지 인증해도
`current_step` 은 3 그대로여야 한다. (4로 넘기는 건 방장의 진행도 저장 API)

### 주요 검증 항목

#### 1. 인증 성공

- **200 / `isVerified: true`**
- `item_img_url` / `progress_status=COMPLETED` / `completed_at` 이 저장된다.
- Blob 경로는 `cooperative_mission_role/{progressId}/{roleProgressId}` 이고
  확장자는 **파일 내용으로 판별한 실제 형식**을 따른다. 원본 파일명은 쓰지 않는다.
- JPEG / PNG / WebP 모두 인증되고, 확장자·Content-Type 이 내용과 달라도 실제 형식을 따른다.
- 팀원도 자기 역할을 인증할 수 있다.
- 모든 역할을 인증해도 미션 단계·상태·완료 시각은 그대로다.

#### 2. 인증 실패

- **200 / `isVerified: false`** 이고 업로드·DB 변경이 전혀 없다.
- 인증 모듈에는 이미지 bytes / MIME type 과 **역할 카드 정보**(이름·설명·찾을 장소)를 넘긴다.
  (프론트가 보낸 값이 아니라 역할 진행도 관계로 조회한 값이다)

#### 3. 실패 시 되돌리기

- Blob 업로드 실패 → **500**, 역할 진행도 그대로.
- DB 저장 실패 → **500**, 올린 Blob 을 삭제한다.

#### 4. 403 / 409

- 남의 역할을 인증하려 하면 **403 `COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED`** (방장도 예외 없음)
- 담당자가 `PENDING` 이면 403
- 이미 인증한 역할이면 **409 `COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED`**,
  기존 사진을 덮어쓰지 않는다.
- 1·2단계면 **409 `COOPERATIVE_MISSION_STEP_NOT_ALLOWED`**
- 완료된 방이면 **409 `COOPERATIVE_MISSION_ALREADY_COMPLETED`**

#### 5. 404 / 401

- 진행도 없음 → `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`
- 역할 진행도 없음 / **다른 방의 역할 진행도** → `COOPERATIVE_ROLE_PROGRESS_NOT_FOUND`
- 헤더의 사용자가 없으면 **401 `UNAUTHORIZED_USER`**

#### 6. 400 `INVALID_REQUEST`

- `itemImage` 누락 · 허용하지 않는 형식(GIF) · 빈 파일 · 10MB 초과
- 두 Path id가 0 이하이거나 정수가 아님
- 모두 업로드하지 않고 역할 진행도도 그대로다.

## 나가기 테스트 의도

나가기는 **누가 나가느냐에 따라 처리가 세 갈래로 갈린다.** 그래서 분기 자체가 검증 대상이다.

1. 일반 팀원 / 대기 참가자 → 본인과 본인의 역할만 빠지고 방은 그대로
2. 방장인데 남은 `ACCEPTED` 팀원이 있음 → 방장 승계
3. 마지막 `ACCEPTED` 참가자 → 방 전체 삭제

특히 **"마지막"의 기준이 `ACCEPTED` 수라는 점**이 틀리기 쉽다.
대기(`PENDING`) 참가자만 남은 방은 유지하지 않고, 반대로 대기 참가자가 나갔다고 방을 지워서도 안 된다.
그래서 방장 한 명 + 대기 참가자 한 명인 방에서 대기 참가자가 나가는 경우를 따로 확인한다.

또 하나는 **나가기가 완료가 아니라는 것**이다.
보상을 주지 않고 `mission_status` / `current_step` / `completed_at` / 보상 지급 여부를 건드리지 않는다.
응답의 `reward` 키는 유지하되 세 항목 값이 모두 `null`이어야 한다.

### 주요 검증 항목

#### 1. 정상 응답

- **200**이고 `missionProgressId`를 반환한다.
- `reward`는 `{arCharacter: null, point: null, coupon: null}` 이고,
  실제로도 `USER.point`가 늘지 않고 `ACQUIRED_AR_CHARACTER`가 생기지 않으며
  진행도의 보상 지급 여부도 그대로다.
- `nextLocation`은 공통 추천 로직 결과다. 추천할 장소가 없으면 `null`.

#### 2. 일반 팀원 / 대기 참가자 나가기

- 본인만 소프트 삭제된다. 행은 남고 `deleted_at`만 채워지며 상태·역할 값은 그대로다.
- 본인의 역할 진행도도 함께 소프트 삭제되고, **다른 참가자의 역할은 건드리지 않는다.**
- 진행도의 단계·상태·`team_token`은 변하지 않는다.
- 대기 참가자도 나가기로 참여 요청을 취소할 수 있다.
- **방장 한 명만 남은 방에서 대기 참가자가 나가도 방은 유지된다.**
- 역할 사진의 `item_img_url`과 Blob 이미지는 지우지 않는다. (`progress_status`도 그대로)

#### 3. 방장 나가기와 승계

- 남은 `ACCEPTED` 팀원 중 **먼저 참여한 사람**이 `HOST`가 된다.
- `joined_at`이 같으면 **참가자 id가 작은 쪽**이 승계한다.
- `PENDING` 참가자는 승계 대상이 아니다. 대기 참가자만 남으면 방 전체가 삭제된다.
- 승계해도 진행도의 단계·상태·`team_token`은 유지된다. 승계자의 `joined_at`도 바뀌지 않는다.
- 나간 방장의 역할 진행도도 함께 소프트 삭제된다.

#### 4. 마지막 참가자 나가기

- 진행도와 남은 참가자·역할 진행도가 **모두 같은 시각으로** 소프트 삭제된다.
- 남아 있던 `PENDING` 참가자도 함께 정리된다.
- **완료 처리하지 않는다.** `mission_status`는 `IN_PROGRESS`, `current_step`은 그대로,
  `completed_at`은 `null`, 보상 지급 여부도 `false` 그대로다.
- 삭제된 방은 상태 조회에서 404가 된다.

#### 5. 3단계에서 나가기

- 단계를 2로 되돌리지 않는다.
- 인증까지 마친 역할이어도 삭제되어 `totalRoleCount` / `completedRoleCount`에서 빠진다.
  (2/1 이던 집계가 나간 뒤 1/0 이 된다)

#### 6. 404 / 409

- 진행도가 없거나 **이미 삭제된 방** → `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`
- 방의 참가자가 아니거나 **이미 나간 사용자** → `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`
- `mission_status`가 `COMPLETED`이거나 `current_step`이 4이면
  **409 `COOPERATIVE_MISSION_ALREADY_COMPLETED`** 이고 아무도 나가지 않는다.

#### 7. 400 / 401

- Path id가 0 이하이거나 정수가 아니면 **400 `INVALID_REQUEST`**
- 토큰의 사용자가 없으면 **401 `UNAUTHORIZED_USER`**
- 두 경우 모두 참가자가 그대로 남는다.

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 협동 미션 도메인만
pytest app/cooperative_mission

# 특정 테스트만
pytest app/cooperative_mission/tests/test_get_cooperative_mission_status.py -k 보상
pytest app/cooperative_mission/tests/test_get_cooperative_mission_status.py -k 4단계
pytest app/cooperative_mission/tests/test_save_cooperative_mission_progress.py -k 단계
pytest app/cooperative_mission/tests/test_save_role_assignment.py -k 배정
pytest app/cooperative_mission/tests/test_verify_role_progress.py -k 인증
pytest app/cooperative_mission/tests/test_leave_cooperative_mission.py -k 승계
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고,
미션/장소/역할 카드/사용자와 방장·팀원 참가자는 `status_data` 픽스처에서 만든다.
단계 전환은 `_set_step()` / `_complete()`, 역할 진행도는 `_add_role_progress()` 헬퍼로 만든다.
TourAPI 호출은 `stub_location_image` 픽스처(autouse)로 막는다.
진행도 저장 테스트는 `progress_data` 픽스처로 초대 단계 방을 만들고, `_set_step()` / `_assign_role()` 로 각 단계 상황을 재현한다.
역할 배정 테스트는 `assignment_data` 픽스처로 2단계 방(방장/수락 팀원/대기 팀원)을 만들고, `_add_other_progress()` 로 다른 방 상황을 만든다.
사진 인증 테스트는 `verification_data` 픽스처로 3단계 방과 역할 배정을 만들고, Blob 호출은 `uploads` / `deletes` 픽스처로 가로챈다.
나가기 테스트는 `leave_data` 픽스처로 2단계 방(방장/수락 팀원)을 만들고, `_add_participant()` 로 승계 후보와 대기 참가자를 덧붙인다.
