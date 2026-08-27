# 협동 미션 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `POST /api/v1/cooperative-missions/{cooperativeMissionId}/progress` (협동 미션 시작하기/이어하기) | `app/cooperative_mission/tests/test_start_cooperative_mission.py` |
| `POST /api/v1/cooperative-missions/join-requests` (URL로 참여 요청) | `app/cooperative_mission/tests/test_join_cooperative_mission.py` |

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
