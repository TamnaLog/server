# 협동 미션 시작하기/이어하기 비즈니스 룰

## 1. 요청 및 식별 기준

- HTTP 메서드: `POST`
- 엔드포인트: `/api/v1/cooperative-missions/{cooperativeMissionId}/progress`
- 요청 Path의 `cooperativeMissionId`는 공통 `MISSION.id`가 아니라 `COOPERATIVE_MISSION.id`를 의미한다.
- 요청 Body와 Query는 사용하지 않는다.
- 현재 로그인한 사용자는 협동 미션 방을 생성하거나 자신이 방장인 진행 중 방을 이어서 할 수 있다.

## 2. 처리 순서

1. `cooperativeMissionId`로 `COOPERATIVE_MISSION`을 조회한다.
2. 현재 사용자가 `HOST`로 참여하고 있는 해당 협동 미션의 `IN_PROGRESS` 진행도를 조회한다.
3. `IN_PROGRESS` 진행도가 없으면 새로운 진행도와 방장 참여자를 생성하고 `201 Created`를 반환한다.
4. `IN_PROGRESS` 진행도가 있으면 새로운 데이터를 생성하지 않고 기존 방 상태를 조합하여 `200 OK`를 반환한다.

과거의 `COMPLETED` 진행도는 이어하기 대상으로 사용하지 않는다. `COMPLETED` 진행도만 존재하면 새로운 도전으로 판단하여 새 `IN_PROGRESS` 진행도를 생성한다.

현재 사용자가 다른 방에 `MEMBER`로 참여하고 있는 기록은 이 API의 이어하기 대상으로 사용하지 않는다.

## 3. 신규 진행도 생성

현재 사용자가 방장인 해당 협동 미션의 `IN_PROGRESS` 진행도가 없으면 다음 값으로 `COOPERATIVE_MISSION_PROGRESS`를 생성한다.

- `cooperative_mission_id`: 요청받은 `cooperativeMissionId`
- `current_step`: `1`
- `mission_status`: `IN_PROGRESS`
- `team_token`: 새로 생성한 팀 토큰
- `ar_character_reward_granted`: `FALSE`
- `point_reward_granted`: `FALSE`
- `coupon_reward_granted`: `FALSE`
- `completed_at`: `NULL`

진행도와 함께 현재 사용자를 다음 값으로 `COOPERATIVE_MISSION_PARTICIPANT`에 생성한다.

- `cooperative_mission_progress_id`: 새로 생성한 진행도 id
- `user_id`: 현재 로그인한 사용자 id
- `participant_status`: `ACCEPTED`
- `participant_role`: `HOST`
- `joined_at`: 현재 시각

진행도 생성과 방장 참여자 생성은 하나의 트랜잭션으로 처리한다. 어느 한쪽이라도 저장에 실패하면 전체 작업을 롤백하여 방장 없는 진행도나 진행도 없는 참여자가 남지 않도록 한다.

신규 생성 응답은 다음 기준으로 구성한다.

- `missionProgressId`: 새로 생성한 진행도 id
- `missionProgressStatus`: `IN_PROGRESS`
- `currentStep`: `1`
- `teamToken`: 새로 생성하여 진행도에 저장한 팀 토큰
- `participants`: 새로 생성한 방장 참여자 1명
- `roleCards`: 공통 `COOPERATIVE_ROLE_CARD` 6종
- `roleProgresses`: 역할을 아직 배정하지 않았으므로 빈 배열

정상적으로 신규 생성한 경우 `201 Created`를 반환한다.

## 4. 진행 중인 미션 이어하기

현재 사용자가 `HOST`로 참여하고 있는 해당 협동 미션의 `IN_PROGRESS` 진행도가 있으면 새로운 진행도, 참여자 또는 팀 토큰을 생성하지 않는다.

기존 진행도에서 다음 값을 그대로 사용한다.

- `missionProgressId`: 기존 진행도 id
- `missionProgressStatus`: 기존 `mission_status`
- `currentStep`: 기존 `current_step`
- `teamToken`: 기존 진행도에 저장된 `team_token`

기존 진행도의 id로 `COOPERATIVE_MISSION_PARTICIPANT`를 조회하여 참여자와 참여 요청을 반환한다.

- `PENDING`: 초대 URL을 통해 참여를 요청했지만 방장이 아직 수락하지 않은 사용자
- `ACCEPTED`: 방장이거나 참여 요청이 수락된 사용자

`COOPERATIVE_ROLE_PROGRESS`는 해당 진행도의 참여자를 통해 조회한다. 역할 진행도가 존재하면 역할 카드와 참여자 정보를 조인하여 반환하고, 존재하지 않으면 빈 배열을 반환한다.

이어하기 응답은 현재 단계와 관계없이 전체 상태를 동일한 구조로 반환한다. 프론트는 `currentStep`을 기준으로 필요한 화면을 구성한다.

정상적으로 기존 진행도를 반환한 경우 `200 OK`를 반환한다.

## 5. 역할 카드 반환

`COOPERATIVE_ROLE_CARD`는 특정 협동 미션에 속하지 않고 모든 협동 미션에서 공통으로 사용하는 마스터 데이터이다.

시작하기와 이어하기 모두 역할 카드 6종 전체를 `roleCards`에 반환한다.

역할 카드는 `id` 오름차순으로 정렬하며 다음 값을 조합한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `roleCardId` | `COOPERATIVE_ROLE_CARD.id` |
| `roleName` | `COOPERATIVE_ROLE_CARD.role_name` |
| `roleDescription` | `COOPERATIVE_ROLE_CARD.role_description` |
| `locationToFind` | `COOPERATIVE_ROLE_CARD.location_to_find` |

역할 카드는 진행도 생성 시 복사하거나 새로 생성하지 않는다. 역할을 참여자에게 배정할 때만 별도의 `COOPERATIVE_ROLE_PROGRESS`를 생성하여 공통 역할 카드를 참조한다.

## 6. 팀 토큰 생성

팀 토큰은 예측하기 어려운 암호학적 난수로 생성한다.

Python에서는 `secrets.token_urlsafe(32)`를 사용한다.

```python
import secrets

team_token = secrets.token_urlsafe(32)
```

이 방식은 32바이트의 난수를 URL-safe Base64 문자열로 변환하며, 생성된 문자열은 약 43자이므로 `VARCHAR(100)` 범위에 들어간다.

`COOPERATIVE_MISSION_PROGRESS.team_token`의 `UNIQUE` 제약으로 토큰 중복을 방지한다. 매우 낮은 확률로 중복이 발생하여 저장에 실패하면 새로운 토큰을 생성하여 다시 시도한다. 정해진 재시도 횟수 안에 저장하지 못하면 트랜잭션을 롤백하고 공통 `500 INTERNAL_SERVER_ERROR`로 처리한다.

토큰은 로그에 원문으로 출력하지 않는다. 팀 토큰을 알면 해당 방의 참여 요청 화면에 접근할 수 있으므로 외부 노출에 주의한다.

## 7. 팀 토큰 반환 및 초대 URL 생성 책임

DB에는 완성된 초대 URL을 저장하지 않고 `team_token`만 저장한다.

백엔드는 시작하기와 이어하기 응답의 `teamToken`에 진행도의 `team_token`을 그대로 반환한다. 백엔드는 클라이언트 서버 기본 주소를 관리하거나 완성된 초대 URL을 조합하지 않는다.

신규 진행도를 생성한 경우 새 팀 토큰을 생성하여 DB에 저장하고 응답으로 반환한다.

기존 진행도를 이어서 하는 경우 기존 `team_token`을 새로 만들거나 변경하지 않고 그대로 반환한다. 따라서 프론트가 이전과 같은 클라이언트 주소에서 URL을 생성하면 기존에 공유한 초대 링크와 같은 URL이 만들어진다.

프론트는 현재 실행 중인 클라이언트 주소와 응답의 `teamToken`을 사용하여 다음 형식의 초대 URL을 생성한다.

```text
{현재 클라이언트 주소}/cooperative-missions/invite?token={URL 인코딩한 teamToken}
```

웹 클라이언트에서는 `window.location.origin`으로 현재 클라이언트 주소를 구하고 `encodeURIComponent(teamToken)`으로 토큰을 URL에 안전하게 넣을 수 있다.

```typescript
const inviteUrl =
  `${window.location.origin}/cooperative-missions/invite?token=${encodeURIComponent(teamToken)}`;
```

따라서 백엔드에는 초대 URL 생성을 위한 `CLIENT_BASE_URL` 환경변수가 필요하지 않다.

## 8. 응답 목록 구성

### 8.1 참여자 목록

`participants`에는 해당 진행도에 연결된 `PENDING`, `ACCEPTED` 참여자를 반환한다.

방장을 먼저 배치하고, 나머지 참여자는 `created_at` 오름차순으로 정렬한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `participantId` | `COOPERATIVE_MISSION_PARTICIPANT.id` |
| `name` | 연결된 `USER.nickname` |
| `participantRole` | `COOPERATIVE_MISSION_PARTICIPANT.participant_role` |
| `participantStatus` | `COOPERATIVE_MISSION_PARTICIPANT.participant_status` |

### 8.2 역할 진행도 목록

`roleProgresses`는 해당 진행도의 참여자에게 연결된 역할 진행도를 반환한다.

역할 진행도가 없으면 `null`이 아니라 빈 배열을 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `roleProgressId` | `COOPERATIVE_ROLE_PROGRESS.id` |
| `participantId` | `COOPERATIVE_ROLE_PROGRESS.participant_id` |
| `participantName` | 참여자와 연결된 `USER.nickname` |
| `roleCardId` | `COOPERATIVE_ROLE_PROGRESS.cooperative_role_card_id` |
| `roleName` | 연결된 `COOPERATIVE_ROLE_CARD.role_name` |
| `progressStatus` | `COOPERATIVE_ROLE_PROGRESS.progress_status` |
| `itemImgUrl` | `COOPERATIVE_ROLE_PROGRESS.item_img_url` |

역할 진행도는 `roleProgressId` 오름차순으로 정렬한다.

## 9. 중복 생성 방지

동일한 사용자와 동일한 협동 미션에는 그 사용자가 방장인 `IN_PROGRESS` 진행도가 최대 하나만 존재해야 한다.

같은 요청이 반복되면 첫 번째 요청만 진행도를 생성하고, 이후 요청은 생성된 진행도를 이어서 반환해야 한다.

진행도 조회, 중복 여부 재확인, 팀 토큰 생성, 진행도 생성과 방장 참여자 생성을 하나의 트랜잭션 범위에서 처리한다. 동시에 여러 요청이 들어온 경우에도 가능한 한 기존 진행도를 다시 조회하여 중복 방 생성을 방지한다.

현재 ERD에 사용자·협동 미션·상태를 묶은 `UNIQUE` 제약이 없으므로 최종적인 중복 방지 책임은 서비스 로직에 있다.

## 10. 보상 처리

이 API는 보상을 조회하거나 지급하지 않는다.

응답에도 `rewardDetail`이나 보상 지급 여부를 포함하지 않는다.

## 11. 오류 처리

### 400 `INVALID_REQUEST`

다음과 같이 요청 Path가 유효하지 않으면 진행도를 조회하거나 생성하지 않고 공통 `400` 오류를 반환한다.

- `cooperativeMissionId`가 정수가 아닌 경우
- `cooperativeMissionId`가 `1`보다 작은 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 404 `COOPERATIVE_MISSION_NOT_FOUND`

`cooperativeMissionId`에 해당하는 `COOPERATIVE_MISSION`이 존재하지 않으면 진행도와 참여자를 생성하지 않고 `404`를 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_NOT_FOUND"
}
```

### 500 `INTERNAL_SERVER_ERROR`

다음 오류는 진행도와 참여자 생성을 롤백하고 공통 `500` 오류로 처리한다.

- 팀 토큰 생성 또는 저장에 반복해서 실패한 경우
- 진행도는 생성됐지만 방장 참여자 생성에 실패한 경우
- 역할 카드 마스터 데이터가 정상적으로 구성되지 않아 응답을 만들 수 없는 경우
- 그 밖의 예상하지 못한 DB 또는 서버 오류

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```


# URL로 참여 요청 비즈니스 룰

## 1. 요청 및 사용자 식별

- HTTP 메서드: `POST`
- 엔드포인트: `/api/v1/cooperative-missions/join-requests`
- 요청 Body의 `teamToken`으로 참여할 협동 미션 방을 식별한다.
- 참여를 요청하는 사용자는 요청 Body로 받지 않고 공통 `Authorization: Bearer {accessToken}` 헤더로 식별한다.
- `get_current_user_id()`에서 토큰에 해당하는 `USER`가 실제로 존재하는지 먼저 검증한다.

## 2. 진행도 조회

요청받은 `teamToken`과 `COOPERATIVE_MISSION_PROGRESS.team_token`이 일치하고 `mission_status = IN_PROGRESS`인 진행도를 조회한다.

조회된 진행도의 `id`는 신규 또는 기존 참여 정보를 반환할 때 응답의 `missionProgressId`로 사용한다.

다음 경우에는 유효한 초대 링크가 아닌 것으로 판단한다.

- `teamToken`과 일치하는 진행도가 없는 경우
- 일치하는 진행도는 있지만 이미 `COMPLETED` 상태인 경우

## 3. 처리 순서

1. `teamToken`으로 진행 중인 협동 미션 진행도를 조회한다.
2. 진행도 id와 현재 사용자 id로 기존 참여자를 조회한다.
3. 기존 참여자가 있으면 새로운 참여자를 만들지 않고 기존 정보를 반환한다.
4. 기존 참여자가 없으면 현재 단계와 최대 인원을 검증한다.
5. 검증을 통과하면 현재 사용자를 `PENDING` 상태의 팀원으로 생성한다.

기존 참여자 조회를 새로운 참여 요청 검증보다 먼저 수행한다. 따라서 방장이나 이미 참여 요청을 보낸 사용자가 같은 링크를 다시 열어도 중복 데이터가 생성되지 않는다.

## 4. 기존 참여자가 있는 경우

다음 조건으로 `COOPERATIVE_MISSION_PARTICIPANT`를 조회한다.

```text
cooperative_mission_progress_id = 조회한 진행도 id
user_id = 현재 사용자 id
```

기존 참여자의 상태가 `PENDING`이면 참여 요청을 새로 생성하지 않고 기존 참여 정보를 `200 OK`로 반환한다.

기존 참여자의 상태가 `ACCEPTED`이면 참여자를 새로 생성하거나 상태를 변경하지 않고 기존 참여 정보를 `200 OK`로 반환한다. 방장이 자신의 초대 링크를 열었을 때도 방장은 이미 `HOST`, `ACCEPTED` 상태이므로 이 분기에 해당한다.

기존 참여자를 반환할 때는 현재 인원이 6명이거나 `current_step`이 2 이상이어도 `409`를 반환하지 않는다. 최대 인원과 참여 가능 단계 검증은 새로운 사용자의 참여 요청을 생성할 때만 적용한다.

## 5. 새로운 참여 요청 생성

현재 사용자가 해당 진행도의 참여자 명단에 없으면 새로운 참여 요청을 생성하기 전에 다음 조건을 검증한다.

### 5.1 참여 가능 단계

새로운 참여 요청은 `current_step = 1`인 초대 단계에서만 생성할 수 있다.

`current_step`이 `2`, `3`, `4`이면 새로운 팀원을 받을 수 없는 상태이므로 참여자를 생성하지 않는다.

### 5.2 최대 참여 인원

협동 미션 최대 참여 인원은 방장을 포함하여 6명으로 고정한다.

서비스 코드에는 다음 상수를 사용한다.

```python
COOPERATIVE_MISSION_MAX_PARTICIPANTS = 6
```

해당 진행도에 연결된 `COOPERATIVE_MISSION_PARTICIPANT` 행의 수를 조회한다. 인원 계산에는 `PENDING`과 `ACCEPTED` 참여자를 모두 포함한다.

```text
participant_count = PENDING 참여자 수 + ACCEPTED 참여자 수
```

`participant_count >= COOPERATIVE_MISSION_MAX_PARTICIPANTS`이면 새로운 참여자를 생성하지 않는다.

### 5.3 참여자 생성값

단계와 최대 인원 검증을 통과하면 다음 값으로 `COOPERATIVE_MISSION_PARTICIPANT`를 생성한다.

- `cooperative_mission_progress_id`: 팀 토큰으로 조회한 진행도 id
- `user_id`: 현재 사용자 id
- `participant_status`: `PENDING`
- `participant_role`: `MEMBER`
- `joined_at`: `NULL`

새로운 참여자를 정상적으로 생성하면 `201 Created`를 반환한다.

## 6. 응답 데이터

신규 참여 요청과 기존 참여 정보는 같은 응답 구조를 사용한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `missionProgressId` | `COOPERATIVE_MISSION_PROGRESS.id` |
| `participantId` | `COOPERATIVE_MISSION_PARTICIPANT.id` |
| `participantStatus` | `COOPERATIVE_MISSION_PARTICIPANT.participant_status` |

응답 상태 코드는 다음과 같이 구분한다.

| 조건 | Status Code |
| --- | --- |
| 새로운 `PENDING` 참여자를 생성함 | `201 Created` |
| 기존 `PENDING` 참여자를 반환함 | `200 OK` |
| 기존 `ACCEPTED` 참여자를 반환함 | `200 OK` |

프론트는 응답의 `missionProgressId`를 사용하여 자신의 참여 상태를 폴링한다.

- `PENDING`: 수락 대기 화면 유지
- `ACCEPTED`: 협동 미션 방으로 이동

## 7. 중복 생성 및 동시 요청 방지

동일한 진행도와 동일한 사용자에 대한 참여자 데이터는 최대 하나만 존재해야 한다.

같은 사용자가 참여 요청 API를 반복 호출하면 최초 요청에서만 참여자를 생성하고 이후 요청에는 기존 참여자를 반환한다.

진행도 조회, 기존 참여자 재확인, 현재 인원 확인과 참여자 생성을 하나의 트랜잭션 범위에서 처리한다. 동시에 여러 참여 요청이 들어오면 진행도 행을 잠근 뒤 기존 참여자와 현재 인원을 다시 조회하여 중복 참여자 생성과 6명 초과를 방지한다.

## 8. 오류 처리

### 400 `INVALID_REQUEST`

`teamToken`이 누락되거나 빈 문자열인 경우 참여자를 생성하지 않고 공통 `400` 오류를 반환한다.

```json
{
  "code": "INVALID_REQUEST"
}
```

### 404 `INVALID_INVITE_TOKEN`

`teamToken`에 해당하는 `IN_PROGRESS` 협동 미션 진행도를 찾을 수 없으면 `404`를 반환한다.

```json
{
  "code": "INVALID_INVITE_TOKEN"
}
```

### 409 `COOPERATIVE_MISSION_FULL`

기존 참여자가 아닌 사용자가 참여를 요청했고, 해당 진행도의 참여자 수가 이미 6명 이상이면 `409`를 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_FULL"
}
```

### 409 `COOPERATIVE_MISSION_JOIN_CLOSED`

기존 참여자가 아닌 사용자가 참여를 요청했고, 진행도의 `current_step`이 `2`, `3`, `4`이면 `409`를 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_JOIN_CLOSED"
}
```

### 500 `INTERNAL_SERVER_ERROR`

참여자 생성 또는 DB 처리 중 예상하지 못한 오류가 발생하면 트랜잭션을 롤백하고 공통 `500` 오류를 반환한다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```
