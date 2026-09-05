# 협동 미션 상태 조회 비즈니스 룰

## 1. 요청 및 사용자 식별

- HTTP 메서드: `GET`
- 엔드포인트: `/api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress`
- Path의 `cooperativeMissionProgressId`로 조회할 `COOPERATIVE_MISSION_PROGRESS`를 식별한다.
- Request Query로 사용자 현재 위치의 `latitude`, `longitude`를 받는다. 두 값 모두 필수이다.
- Request Body는 받지 않는다.
- 현재 사용자는 Authorization Bearer 토큰의 `get_current_user_id()`로 식별한다.

프론트는 현재 사용자의 참가자 id, 참가자 역할 또는 참여 상태를 요청으로 전달하지 않는다. 백엔드가 현재 사용자 id와 진행도 id로 `COOPERATIVE_MISSION_PARTICIPANT`를 조회하여 호출 권한과 현재 참가자 정보를 판단한다.

Query의 사용자 좌표는 4단계 응답의 다음 장소까지 직선거리를 계산하는 데만 사용한다. 1~3단계 응답에서는 좌표를 사용하지 않지만, 폴링 중 어느 시점에 4단계로 넘어갈지 알 수 없으므로 모든 폴링 요청에서 동일하게 전달받는다.

## 2. API 용도와 폴링

방장과 팀원은 초대 단계인 `current_step = 1`부터 이 API를 주기적으로 호출하여 협동 미션의 최신 상태를 확인한다.

상태 조회는 다음 변경 사항을 프론트에 전달한다.

- 참여 요청 생성, 수락 및 거절 결과
- 협동 미션 단계 변경
- 역할 카드 배정 결과
- 역할별 사진 인증 결과
- 협동 미션 완료 결과

1~3단계 조회에서는 진행도, 참가자 또는 역할 진행도를 변경하지 않는다. 단, 4단계 조회에서는 아직 보상 정산이 수행되지 않았다면 보상 지급 로직을 실행할 수 있다.

## 3. 처리 순서

1. `cooperativeMissionProgressId`와 Query의 `latitude`, `longitude` 형식과 범위를 검증한다.
2. 진행도 id로 `COOPERATIVE_MISSION_PROGRESS`와 연결된 협동 미션 정보를 조회한다.
3. 현재 사용자가 해당 진행도의 참가자인지 확인한다.
4. 현재 사용자의 참가자 row로 `currentParticipant`를 구성한다.
5. 진행도의 `current_step`에 따라 필요한 데이터만 조회한다.
6. 4단계이면 보상 지급 여부를 확인하고 필요한 경우 보상 지급 로직을 실행한다.
7. 4단계이면 `common`의 다음 장소 추천 로직을 현재 사용자 기준으로 실행하고, Query의 좌표로 추천 장소까지의 직선거리를 계산한다.
8. 단계별 응답 구조를 조합하여 `200 OK`를 반환한다.

## 4. 진행도와 참가자 검증

`COOPERATIVE_MISSION_PROGRESS.id = cooperativeMissionProgressId`인 진행도를 조회한다.

상태 조회는 진행 중인 진행도뿐 아니라 완료된 4단계 진행도도 조회해야 하므로 `mission_status = IN_PROGRESS` 조건만으로 제한하지 않는다.

진행도가 존재하지 않으면 `404 COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`를 반환한다.

현재 사용자가 다음 조건을 만족하는 참가자인지 조회한다.

```text
cooperative_mission_progress_id = cooperativeMissionProgressId
user_id = current_user_id
```

참가자 row가 없으면 `404 COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`를 반환한다. 참여 요청 거절로 `PENDING` 참가자 row가 삭제된 경우도 이 오류에 포함한다.

## 5. 단계 정의

`current_step`은 다음 네 단계만 사용한다.

| 단계 | 의미 | 진행 상태 |
| --- | --- | --- |
| `1` | 초대 | `IN_PROGRESS` |
| `2` | 역할 카드 배정 | `IN_PROGRESS` |
| `3` | 미션 수행 및 사진 인증 | `IN_PROGRESS` |
| `4` | 미션 완료 | `COMPLETED` |

미션이 완료되는 순간 다음 값을 함께 변경한다.

- `current_step`: `4`
- `mission_status`: `COMPLETED`
- `completed_at`: 완료 처리 시각

완료 상태를 `current_step = 3`으로 유지하지 않는다.

## 6. 공통 응답 데이터

모든 단계에서 다음 값을 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `missionProgressId` | `COOPERATIVE_MISSION_PROGRESS.id` |
| `missionId` | `COOPERATIVE_MISSION.id` |
| `missionTitle` | 협동 미션과 연결된 `MISSION.title` |
| `missionProgressStatus` | `COOPERATIVE_MISSION_PROGRESS.mission_status` |
| `currentStep` | `COOPERATIVE_MISSION_PROGRESS.current_step` |

그 밖의 필드는 현재 단계에 필요한 데이터만 반환하고 사용하지 않는 필드는 키를 생략하지 않고 `null`로 반환한다.

## 7. 1단계 응답

1단계는 초대 및 참여 요청 처리 화면이다.

- `currentParticipant`: 현재 호출자의 참가자 정보
- `participants`: 해당 진행도의 `PENDING`, `ACCEPTED` 참가자 목록
- `roleCards`: `null`
- `roleProgresses`: `null`
- `completedRoleCount`: `null`
- `totalRoleCount`: `null`
- `reward`: `null`
- `nextLocation`: `null`

`currentParticipant`는 다음 값으로 구성한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `participantId` | 현재 사용자의 참가자 `id` |
| `participantRole` | `participant_role`. `HOST \| MEMBER` |
| `participantStatus` | `participant_status`. `PENDING \| ACCEPTED` |

참여 요청을 보낸 팀원은 `PENDING`으로 반환한다. 방장이 수락한 뒤 다음 폴링부터 `ACCEPTED`로 반환한다.

방장이 참여 요청을 거절하면 참가자 row가 삭제되므로 이후 폴링에는 `404 COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`를 반환한다. 프론트는 1단계 대기 화면에서 이 오류를 받으면 참여 요청이 거절된 것으로 처리한다.

## 8. 2단계와 3단계 응답

2단계와 3단계에서는 다음 값을 반환한다.

- `currentParticipant`: 현재 호출자의 참가자 정보
- `participants`: 참가자 목록
- `roleCards`: 공통 역할 카드 6종 전체
- `roleProgresses`: 현재까지 생성된 역할 진행도 목록
- `completedRoleCount`: 완료된 역할 진행도 수
- `totalRoleCount`: 실제 생성된 역할 진행도 수
- `reward`: `null`
- `nextLocation`: `null`

2단계에서 역할 카드 하나를 배정할 때마다 별도의 역할 배정 저장 API를 호출한다. 저장이 완료되면 다음 상태 조회 폴링부터 생성된 역할 진행도를 `roleProgresses`에 반영한다.

2단계에서 아직 역할이 하나도 배정되지 않았다면 `roleProgresses`는 `null`이 아니라 빈 배열을 반환하고 역할 집계값은 모두 `0`을 반환한다.

## 9. 참가자 목록 구성

`participants`에는 해당 진행도에 존재하는 `PENDING`, `ACCEPTED` 참가자를 반환한다.

방장을 먼저 배치하고 나머지 참가자는 `created_at` 오름차순으로 정렬한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `participantId` | `COOPERATIVE_MISSION_PARTICIPANT.id` |
| `name` | 참가자와 연결된 `USER.nickname` |
| `participantRole` | `COOPERATIVE_MISSION_PARTICIPANT.participant_role` |
| `participantStatus` | `COOPERATIVE_MISSION_PARTICIPANT.participant_status` |

## 10. 역할 카드 배정 규칙

`COOPERATIVE_ROLE_CARD`에는 모든 협동 미션이 공통으로 사용하는 역할 카드 6종이 존재한다.

역할 배정에는 다음 규칙을 적용한다.

- 하나의 역할 카드는 최대 한 명의 참가자에게만 배정한다.
- 같은 역할 카드를 여러 참가자에게 중복 배정하지 않는다.
- 한 참가자는 서로 다른 여러 역할 카드를 배정받을 수 있다.
- 역할 카드 6종을 모두 배정할 필요는 없다.
- 참여 인원이 적으면 일부 역할 카드는 미배정 상태로 남길 수 있다.
- 미배정 역할 카드는 `COOPERATIVE_ROLE_PROGRESS`를 생성하지 않는다.

따라서 역할 진행도 수는 `0` 이상 `6` 이하이다.

`roleCards`는 `COOPERATIVE_ROLE_CARD.id` 오름차순으로 정렬하며 다음 값을 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `roleCardId` | `COOPERATIVE_ROLE_CARD.id` |
| `roleName` | `COOPERATIVE_ROLE_CARD.role_name` |
| `roleDescription` | `COOPERATIVE_ROLE_CARD.role_description` |
| `locationToFind` | `COOPERATIVE_ROLE_CARD.location_to_find` |

## 11. 역할 진행도와 집계

`roleProgresses`는 해당 협동 미션 진행도의 `COOPERATIVE_ROLE_PROGRESS`를 `id` 오름차순으로 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `roleProgressId` | `COOPERATIVE_ROLE_PROGRESS.id` |
| `participantId` | `COOPERATIVE_ROLE_PROGRESS.participant_id` |
| `participantName` | 참가자와 연결된 `USER.nickname` |
| `roleCardId` | `COOPERATIVE_ROLE_PROGRESS.cooperative_role_card_id` |
| `roleName` | 연결된 `COOPERATIVE_ROLE_CARD.role_name` |
| `progressStatus` | `COOPERATIVE_ROLE_PROGRESS.progress_status` |
| `itemImgUrl` | `COOPERATIVE_ROLE_PROGRESS.item_img_url` |

집계값은 다음 기준으로 계산한다.

```text
totalRoleCount = 현재 진행도에 생성된 전체 역할 진행도 row 수
completedRoleCount = progress_status가 COMPLETED인 역할 진행도 row 수
```

미배정 역할 카드는 두 집계값에 포함하지 않는다. 역할 카드 중복 배정을 허용하지 않으므로 각 역할 진행도는 서로 다른 역할 카드를 참조한다.

## 12. 4단계 응답

4단계는 협동 미션 완료 화면이다.

- `currentParticipant`: `null`
- `participants`: `null`
- `roleCards`: `null`
- `roleProgresses`: `null`
- `completedRoleCount`: `null`
- `totalRoleCount`: `null`
- `reward`: 현재 사용자에게 제공할 보상 정보
- `nextLocation`: 현재 사용자에게 추천할 다음 장소 정보. Query의 사용자 위치에서의 직선거리 `distanceMeter`를 포함한다

4단계 응답을 구성할 때 내부적으로 현재 사용자의 참가자 row는 권한과 보상 대상을 확인하는 데 사용하지만 응답의 `currentParticipant`에는 포함하지 않는다.

## 13. 완료 역할 수에 따른 보상

보상 등급은 진행도에 생성된 역할 진행도 중 `COMPLETED` 상태인 개수로 결정한다.

| 완료 역할 수 | 지급 대상 보상 |
| --- | --- |
| `0` | 없음 |
| `1~2` | AR 캐릭터 |
| `3~4` | AR 캐릭터, 포인트 |
| `5~6` | AR 캐릭터, 포인트, 쿠폰 |

역할 카드는 최대 한 번만 배정되므로 완료 역할 수는 최대 6이다.

협동 미션 보상은 완료 시점에 `ACCEPTED` 상태인 참가자 전원에게 같은 등급으로 지급한다. 최초로 4단계 상태 조회가 호출되었을 때 아직 보상 정산이 끝나지 않았다면 보상 지급 로직을 실행한다.

## 14. 보상 정산과 지급 여부 마감

보상 정산은 다음 순서로 처리한다.

1. 완료된 진행도 row를 잠금 조회한다.
2. 완료된 역할 진행도 수로 보상 등급을 계산한다.
3. 보상 정산이 아직 수행되지 않았다면 `ACCEPTED` 참가자 전원에게 해당 등급의 보상을 지급한다.
4. 지급 등급에 포함되지 않아 받지 못한 보상은 소멸 처리한다.
5. 지급 대상 보상이 정상적으로 처리되면, 등급에 포함되지 않아 소멸한 보상까지 포함하여 진행도의 세 보상 지급 여부를 모두 `TRUE`로 변경한다.
6. 참가자 전원의 보상 처리와 지급 여부 변경을 하나의 트랜잭션으로 커밋한다.

정산 완료 후 저장값은 다음과 같다.

```text
ar_character_reward_granted = TRUE
point_reward_granted = TRUE
coupon_reward_granted = TRUE
```

예를 들어 완료 역할이 2개이면 AR 캐릭터만 지급한다. 포인트와 쿠폰은 지급하지 않고 소멸시키지만 세 지급 여부는 모두 `TRUE`로 변경한다.

세 지급 여부가 이미 모두 `TRUE`이면 이후 폴링에서는 사용자 보상을 추가 지급하지 않는다. 응답의 `reward`는 완료 역할 수에 해당하는 보상 정보를 조합하여 반환한다.

`reward` 객체의 각 항목은 실제 보상 구성에 따라 `null`일 수 있다.

- `reward.arCharacter`: AR 캐릭터 보상이 없으면 `null`
- `reward.point`: 포인트 보상이 없으면 `null`
- `reward.coupon`: 쿠폰 보상이 없으면 `null`

## 15. 다음 장소 추천

4단계 상태 조회에서는 `common`에 존재하는 다음 장소 추천 로직을 호출한다.

- 현재 호출 사용자를 기준으로 추천 로직을 실행한다.
- 참가자마다 서로 다른 장소가 추천될 수 있다.
- 이전 폴링에서 반환한 장소와 같은 장소를 유지할 의무는 없다.
- 상태 조회 API는 별도의 다음 장소 추천 로직을 중복 구현하지 않는다.
- 문화 미션, 보물찾기 미션 완료와 같이 거리를 포함하는 `recommend_next_location()`을 사용한다.
- Query로 전달받은 사용자 위치에서 추천 장소까지의 직선거리를 `nextLocation.distanceMeter`에 미터 단위로 반환한다.
- 추천 결과는 명세의 `nextLocation` 형식으로 변환하여 반환한다.
- 추천할 장소가 없으면 `nextLocation: null`을 반환한다.
- 추천 장소에 연결된 미션이 없으면 `nextLocation.mission: null`을 반환한다.

1~3단계에서는 추천 로직을 실행하지 않고 `nextLocation: null`을 반환한다.

## 16. 조회와 동시 요청 처리

1~3단계의 일반 상태 조회는 읽기 작업으로 처리하며 DB 데이터를 변경하지 않는다.

4단계에서 보상 정산이 필요한 경우에는 진행도 row를 잠그고 지급 여부를 다시 확인한다. 여러 참가자가 동시에 폴링하더라도 한 요청만 보상 정산을 수행하고 나머지 요청은 정산 완료 상태를 조회하도록 한다.

보상 지급 중 일부 참가자 처리에 실패하면 참가자 보상과 세 지급 여부 변경을 모두 롤백한다. 일부 참가자에게만 보상이 지급된 상태로 지급 여부가 마감되지 않도록 한다.

## 17. 정상 응답

현재 사용자가 해당 진행도의 참가자이고 단계별 상태를 정상적으로 조회한 경우 `200 OK`를 반환한다.

응답 필드는 단계에 따라 다음과 같이 구성한다.

| 필드 | 1단계 | 2단계 | 3단계 | 4단계 |
| --- | --- | --- | --- | --- |
| 공통 미션 정보 | 값 | 값 | 값 | 값 |
| `currentParticipant` | 값 | 값 | 값 | `null` |
| `participants` | 값 | 값 | 값 | `null` |
| `roleCards` | `null` | 값 | 값 | `null` |
| `roleProgresses` | `null` | 배열 | 배열 | `null` |
| 역할 집계 | `null` | 값 | 값 | `null` |
| `reward` | `null` | `null` | `null` | 값 |
| `nextLocation` | `null` | `null` | `null` | 값 |

## 18. 오류 처리

### 400 `INVALID_REQUEST`

다음 중 하나에 해당하면 공통 요청 오류를 반환한다.

- `cooperativeMissionProgressId`가 정수가 아니거나 `1`보다 작은 경우
- Query의 `latitude` 또는 `longitude`가 없거나 숫자가 아닌 경우
- `latitude`가 `-90~90`, `longitude`가 `-180~180` 범위를 벗어난 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 404 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`

`cooperativeMissionProgressId`에 해당하는 진행도가 존재하지 않으면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

### 404 `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`

현재 사용자가 해당 진행도의 참가자가 아니면 반환한다. 참여 요청 거절로 참가자 row가 삭제된 경우도 포함한다.

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```

### 500 `INTERNAL_SERVER_ERROR`

상태 조회, 보상 정산 또는 다음 장소 추천 처리 중 예상하지 못한 서버 오류가 발생하면 공통 `500` 오류를 반환한다. 보상 정산 트랜잭션이 진행 중이었다면 전체 작업을 롤백한다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```

# 협동 미션 나가기 비즈니스 룰

## 1. 요청 및 사용자 식별

- HTTP 메서드: `DELETE`
- 엔드포인트: `/api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/me`
- Path의 `cooperativeMissionProgressId`로 나갈 `COOPERATIVE_MISSION_PROGRESS`를 식별한다.
- Request Query와 Body는 받지 않는다.
- 현재 사용자는 Authorization Bearer 토큰의 `get_current_user_id()`로 식별한다.

프론트는 사용자 id와 참가자 id를 전달하지 않는다. 백엔드가 현재 사용자 id와 진행도 id로 삭제되지 않은 `COOPERATIVE_MISSION_PARTICIPANT`를 조회한다.

## 2. 호출 가능 대상과 범위

삭제되지 않은 협동 미션 진행도에 속한 `PENDING | ACCEPTED` 참가자는 미션 진행 중 언제든 나가기를 호출할 수 있다.

- `PENDING` 팀원이 호출하면 대기 중인 참여 요청을 취소하는 것으로 처리한다.
- `ACCEPTED` 일반 팀원이 호출하면 방에서 나가는 것으로 처리한다.
- `ACCEPTED` 방장이 호출하면 남은 참가자에 따라 방장을 승계하거나 진행도 전체를 삭제한다.
- 이미 완료된 진행도에서는 나가기를 허용하지 않는다.
- 소프트 딜리트된 진행도나 참가자는 존재하지 않는 대상으로 취급한다.

## 3. 공통 소프트 딜리트 규칙

이 API에서 삭제는 모두 하드 딜리트가 아니라 `deleted_at`을 현재 한국시간으로 저장하는 소프트 딜리트다.

현재 참가자가 나가면 다음 데이터를 같은 시각으로 소프트 딜리트한다.

1. 현재 사용자의 `COOPERATIVE_MISSION_PARTICIPANT`
2. 해당 참가자를 참조하는 모든 `COOPERATIVE_ROLE_PROGRESS`

소프트 딜리트된 데이터는 이후 참가자 목록, 역할 진행도 목록, 역할 개수, 완료 역할 개수, 최대 인원 계산, 방장 권한 및 보상 대상에서 제외한다. 모든 일반 조회에는 `deleted_at IS NULL` 조건을 적용한다.

## 4. 일반 팀원 및 대기 참가자 나가기

현재 참가자의 `participant_role`이 `MEMBER`이면 참가자와 연결된 역할 진행도를 소프트 딜리트한다.

- `PENDING` 참가자는 역할 진행도가 없더라도 동일하게 참가자를 소프트 딜리트한다.
- `ACCEPTED` 참가자가 역할을 배정받았다면 해당 역할 진행도를 함께 소프트 딜리트한다.
- 일반 팀원이 나가도 진행도의 `current_step`과 `mission_status`는 변경하지 않는다.
- 나간 팀원의 역할 카드는 미배정 상태가 된다.

## 5. 방장 나가기와 방장 승계

방장이 나갈 때 다른 삭제되지 않은 `ACCEPTED` 참가자가 남아 있으면 방을 삭제하지 않고 방장을 승계한다.

차기 방장은 다음 조건과 순서로 선정한다.

```text
deleted_at IS NULL
participant_status = ACCEPTED
현재 방장 참가자 제외
ORDER BY joined_at ASC, id ASC
LIMIT 1
```

- `PENDING` 참가자는 방장 승계 대상이 아니다.
- 가장 먼저 방에 들어온 `ACCEPTED` 팀원을 우선한다.
- `joined_at`이 같으면 `id`가 작은 참가자를 우선한다.
- 선정된 참가자의 `participant_role`을 `MEMBER`에서 `HOST`로 변경한다.
- 기존 방장 참가자와 기존 방장의 역할 진행도는 소프트 딜리트한다.
- 진행도의 `current_step`, `mission_status`, `team_token`은 유지한다.

## 6. 마지막 참가자 나가기

마지막 참가자 여부는 `PENDING`을 제외한 삭제되지 않은 `ACCEPTED` 참가자 수로 판단한다.

```text
현재 사용자를 포함한 deleted_at IS NULL AND participant_status = ACCEPTED 참가자 수 = 1
```

현재 사용자가 마지막 `ACCEPTED` 참가자이면 다음 데이터를 모두 같은 시각으로 소프트 딜리트한다.

1. `COOPERATIVE_MISSION_PROGRESS`
2. 해당 진행도에 속한 모든 `COOPERATIVE_MISSION_PARTICIPANT`
3. 해당 참가자들을 참조하는 모든 `COOPERATIVE_ROLE_PROGRESS`

이때 남아 있던 `PENDING` 참가자와 그 하위 데이터도 함께 소프트 딜리트한다.

진행도는 완료 처리하지 않으므로 다음 값은 변경하지 않는다.

- `mission_status`를 `COMPLETED`로 변경하지 않는다.
- `current_step`을 `4`로 변경하지 않는다.
- `completed_at`을 저장하지 않는다.
- 보상 지급 여부를 변경하지 않는다.

## 7. 3단계에서 참가자가 나가는 경우

`current_step = 3`에서 역할을 가진 참가자가 나가면 해당 역할 진행도도 소프트 딜리트되어 그 역할은 비어 있는 상태가 된다.

- 진행도를 2단계로 되돌리지 않는다.
- 삭제된 역할을 다른 참가자에게 자동으로 재배정하지 않는다.
- 3단계에서는 역할 배정 API를 다시 호출하지 않는다.
- 남은 참가자와 남아 있는 역할 진행도만으로 미션을 계속한다.
- 소프트 딜리트된 역할 진행도는 `totalRoleCount`와 `completedRoleCount`에서 제외한다.
- 소프트 딜리트 전에 사진 인증을 완료했더라도 완료 역할 수와 보상 계산에서 제외한다.

## 8. Blob 이미지 보존

역할 진행도를 소프트 딜리트하더라도 `item_img_url`이 참조하는 Azure Blob 이미지는 삭제하지 않는다.

- DB의 `item_img_url`도 그대로 유지한다.
- 소프트 딜리트된 데이터의 복구와 이력 확인이 가능하도록 Blob을 보존한다.
- 나가기 API는 `blob_storage.delete_file()`을 호출하지 않는다.

## 9. 보상 미지급

협동 미션 나가기는 미션 완료가 아니므로 어떤 보상도 지급하지 않는다.

- `ACQUIRED_AR_CHARACTER`를 생성하지 않는다.
- `USER.point`를 증가시키지 않는다.
- 쿠폰을 지급하지 않는다.
- 진행도의 보상 지급 여부를 변경하지 않는다.

응답에는 보상 객체의 키를 유지하고 값을 모두 `null`로 반환한다.

```json
{
  "arCharacter": null,
  "point": null,
  "coupon": null
}
```

## 10. 다음 장소 추천

나가기 처리가 성공하면 `app/common/next_location.py`의 공통 다음 장소 추천 로직을 호출한다.

- 나가기 서비스에 별도의 추천 로직을 중복 구현하지 않는다.
- 현재 API는 사용자 위도·경도를 받지 않으므로 거리 없는 `recommend_next_location_summary()`를 사용한다.
- 추천할 장소가 없으면 `nextLocation: null`을 반환한다.
- 추천 장소에 연결된 미션이 없으면 `nextLocation.mission: null`을 반환한다.

## 11. 처리 순서와 트랜잭션

나가기 전체 처리는 하나의 트랜잭션으로 처리한다.

1. Path 형식과 범위를 검증한다.
2. 삭제되지 않은 진행도 row를 잠금 조회한다.
3. 진행도가 완료 상태인지 확인한다.
4. 현재 사용자의 삭제되지 않은 참가자 row를 조회한다.
5. 삭제되지 않은 `ACCEPTED` 참가자 목록을 잠금 범위 안에서 다시 조회한다.
6. 현재 참가자의 역할과 남은 `ACCEPTED` 참가자 수에 따라 일반 나가기, 방장 승계 또는 진행도 전체 삭제를 결정한다.
7. 대상 참가자, 역할 진행도 및 필요한 경우 진행도의 `deleted_at`을 저장한다.
8. 방장 승계가 필요하면 차기 참가자의 `participant_role`을 `HOST`로 변경한다.
9. DB 변경을 한 번에 커밋한다.
10. 공통 다음 장소 추천 결과와 보상이 없는 응답을 조합하여 `200 OK`를 반환한다.

진행도 row를 먼저 잠가 방장과 다른 참가자가 동시에 나가더라도 방장이 두 명이 되거나 방장이 없는 진행 중 방이 남지 않도록 한다. 잠금을 획득한 뒤 참가자 수와 승계 대상을 다시 계산한다.

DB 처리 중 오류가 발생하면 참가자 삭제, 역할 진행도 삭제, 진행도 삭제 및 방장 승계를 모두 롤백한다.

## 12. 정상 응답

나가기를 정상 처리하면 `200 OK`를 반환한다.

```json
{
  "missionProgressId": 10,
  "reward": {
    "arCharacter": null,
    "point": null,
    "coupon": null
  },
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
    "mission": {
      "id": 3,
      "missionType": "TREASURE"
    }
  }
}
```

## 13. 오류 처리

### 400 `INVALID_REQUEST`

`cooperativeMissionProgressId`가 정수가 아니거나 `1`보다 작으면 공통 요청 오류를 반환한다.

```json
{
  "code": "INVALID_REQUEST"
}
```

### 404 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`

다음 경우 반환한다.

- `cooperativeMissionProgressId`에 해당하는 진행도가 존재하지 않는 경우
- 해당 진행도가 이미 소프트 딜리트된 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

### 404 `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`

다음 경우 반환한다.

- 현재 사용자가 해당 진행도의 참가자가 아닌 경우
- 현재 사용자의 참가자 데이터가 이미 소프트 딜리트된 경우

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```

### 409 `COOPERATIVE_MISSION_ALREADY_COMPLETED`

진행도의 `mission_status`가 `COMPLETED`이거나 `current_step = 4`이면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```

### 500 `INTERNAL_SERVER_ERROR`

DB 변경 또는 다음 장소 추천 중 예상하지 못한 오류가 발생하면 공통 `500` 오류를 반환한다. DB 트랜잭션이 진행 중이었다면 모든 변경을 롤백한다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```

# 협동 미션 역할 배정 저장 비즈니스 룰

## 1. 요청 및 사용자 식별

- HTTP 메서드: `PUT`
- 엔드포인트: `/api/v1/cooperative-missions/{cooperativeMissionProgressId}/role-assignments/{roleCardId}`
- Path의 `cooperativeMissionProgressId`로 역할을 배정할 `COOPERATIVE_MISSION_PROGRESS`를 식별한다.
- Path의 `roleCardId`로 배정하거나 담당자를 변경할 `COOPERATIVE_ROLE_CARD`를 식별한다.
- Request Body의 `participantId`로 역할 카드를 맡을 참가자를 식별한다.
- Request Query는 받지 않는다.
- 현재 사용자는 Authorization Bearer 토큰의 `get_current_user_id()`로 식별한다.

프론트에서 방장 id, 역할 진행도 id 또는 현재 담당자 id를 전달받지 않는다. 방장 여부와 기존 역할 진행도는 백엔드가 DB를 기준으로 판단한다.

## 2. API 책임

이 API는 협동 미션 2단계에서 역할 카드 하나의 담당자를 저장한다.

역할 카드 기준 upsert 방식으로 처리한다.

- 해당 역할 카드의 역할 진행도가 없으면 새 역할 진행도를 생성한다.
- 해당 역할 카드의 역할 진행도가 이미 있으면 기존 row의 참가자만 변경한다.
- 역할 진행도 id를 새로 발급하지 않고 기존 `roleProgressId`를 유지한다.
- 역할 카드 id도 변경하지 않는다.
- 같은 배정 요청이 반복되면 추가 변경 없이 정상 처리한다.

역할 배정 결과는 이 API에서 반환하지 않는다. 프론트는 협동 미션 상태 조회 API의 다음 polling 응답에서 갱신된 `roleProgresses`를 확인한다.

정상 처리 시 응답 Body 없이 `204 No Content`를 반환한다.

## 3. 처리 순서

1. Path와 Request Body의 형식 및 범위를 검증한다.
2. `cooperativeMissionProgressId`에 해당하는 진행도를 잠금 조회한다.
3. 진행도가 이미 완료되었는지 확인한다.
4. 현재 사용자가 해당 진행도의 `HOST`이자 `ACCEPTED` 참가자인지 확인한다.
5. 진행도의 `current_step`이 역할 배정 단계인 `2`인지 확인한다.
6. `roleCardId`에 해당하는 역할 카드를 조회한다.
7. `participantId`에 해당하는 같은 진행도의 `ACCEPTED` 참가자를 조회한다.
8. 해당 진행도와 역할 카드에 연결된 기존 역할 진행도를 조회한다.
9. 기존 역할 진행도가 없으면 새로 생성하고, 존재하면 담당 참가자를 변경한다.
10. 트랜잭션을 커밋하고 `204 No Content`를 반환한다.

## 4. 진행도 조회

다음 조건으로 `COOPERATIVE_MISSION_PROGRESS`를 조회한다.

```text
id = cooperativeMissionProgressId
```

진행도가 존재하지 않으면 `404 COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`를 반환한다.

진행도를 id로 조회한 뒤 완료 상태를 별도로 확인한다. `mission_status = COMPLETED`이거나 `current_step = 4`이면 `409 COOPERATIVE_MISSION_ALREADY_COMPLETED`를 반환한다.

## 5. 방장 권한과 단계 검증

현재 사용자가 다음 조건을 모두 만족하는 참가자인지 확인한다.

- `cooperative_mission_progress_id = cooperativeMissionProgressId`
- `user_id = current_user_id`
- `participant_role = HOST`
- `participant_status = ACCEPTED`

조건을 만족하지 않으면 `403 COOPERATIVE_MISSION_HOST_ONLY`를 반환한다.

역할 배정은 다음 단계에서만 허용한다.

```text
COOPERATIVE_MISSION_PROGRESS.current_step = 2
```

현재 단계가 `1`, `3` 또는 `4`이면 역할 진행도를 생성하거나 변경하지 않고 `409 COOPERATIVE_MISSION_STEP_NOT_ALLOWED`를 반환한다.

## 6. 역할 카드 검증

`COOPERATIVE_ROLE_CARD.id = roleCardId`인 역할 카드를 조회한다.

역할 카드는 모든 협동 미션이 공통으로 사용하는 마스터 데이터이므로 특정 협동 미션 id로 추가 필터링하지 않는다.

역할 카드가 존재하지 않으면 `404 COOPERATIVE_ROLE_CARD_NOT_FOUND`를 반환한다.

## 7. 배정 대상 참가자 검증

다음 조건으로 배정 대상 참가자를 조회한다.

- `id = participantId`
- `cooperative_mission_progress_id = cooperativeMissionProgressId`
- `participant_status = ACCEPTED`

다음 경우에는 `404 COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`를 반환한다.

- `participantId`에 해당하는 참가자가 없는 경우
- 참가자가 다른 협동 미션 진행도에 속하는 경우
- 참가자가 아직 `PENDING` 상태인 경우

방장과 팀원 모두 역할 카드를 배정받을 수 있다. `participant_role`은 `HOST | MEMBER`를 모두 허용한다.

## 8. 기존 역할 진행도 조회 기준

기존 역할 진행도는 역할 카드 id만으로 전역 조회하지 않는다. 반드시 요청한 협동 미션 진행도 범위에서 조회한다.

`COOPERATIVE_ROLE_PROGRESS`에는 진행도 id가 직접 존재하지 않으므로 참가자 테이블을 통해 다음 관계를 확인한다.

```text
COOPERATIVE_ROLE_PROGRESS.cooperative_role_card_id = roleCardId
COOPERATIVE_ROLE_PROGRESS.participant_id = COOPERATIVE_MISSION_PARTICIPANT.id
COOPERATIVE_MISSION_PARTICIPANT.cooperative_mission_progress_id = cooperativeMissionProgressId
```

이 조건으로 해당 방에서 같은 역할 카드를 참조하는 역할 진행도가 존재하는지 조회한다.

## 9. 최초 역할 배정

해당 진행도에 `roleCardId`를 참조하는 역할 진행도가 없으면 다음 값으로 `COOPERATIVE_ROLE_PROGRESS`를 생성한다.

- `participant_id`: Request Body의 `participantId`
- `cooperative_role_card_id`: Path의 `roleCardId`
- `progress_status`: `IN_PROGRESS`
- `item_img_url`: `NULL`
- `completed_at`: `NULL`

역할 진행도 생성 이후 해당 역할 카드는 요청한 참가자에게 배정된 것으로 처리한다.

## 10. 기존 역할 담당자 변경

해당 진행도와 `roleCardId`에 연결된 역할 진행도가 이미 존재하면 새로운 row를 생성하지 않는다.

기존 역할 진행도에서 다음 값만 변경한다.

```text
participant_id = 요청받은 participantId
```

다음 값은 그대로 유지한다.

- `COOPERATIVE_ROLE_PROGRESS.id`
- `cooperative_role_card_id`
- `progress_status`
- `item_img_url`
- `completed_at`

역할 배정은 2단계에서만 변경할 수 있으므로 정상 흐름에서는 기존 역할 진행도가 아직 `IN_PROGRESS`이고 인증 데이터가 존재하지 않는다.

예를 들어 역할 카드 1이 종화에게 배정된 상태에서 같은 역할 카드 1과 지민의 참가자 id로 요청하면 기존 역할 진행도의 `participant_id`만 지민으로 변경한다.

## 11. 동일 배정 재요청

기존 역할 진행도의 `participant_id`가 요청받은 `participantId`와 이미 같으면 멱등 요청으로 처리한다.

- 역할 진행도를 새로 생성하지 않는다.
- `updated_at`을 불필요하게 변경하지 않는다.
- 기존 역할 배정 데이터를 그대로 유지한다.
- 오류 없이 `204 No Content`를 반환한다.

네트워크 재시도나 중복 버튼 입력으로 같은 요청이 반복되어도 역할 진행도가 중복 생성되지 않아야 한다.

## 12. 역할 배정 관계 규칙

하나의 협동 미션 진행도에서는 역할 카드 하나에 참가자 한 명만 배정할 수 있다.

```text
진행도 + roleCardId당 COOPERATIVE_ROLE_PROGRESS 최대 1개
```

한 참가자는 서로 다른 여러 역할 카드를 배정받을 수 있다. 따라서 `participant_id`는 역할 진행도 전체에서 고유값이 아니다.

예를 들어 지민이 역할 카드 1과 역할 카드 2를 모두 맡으면 서로 다른 두 역할 진행도가 같은 `participant_id`를 참조한다.

역할 카드 6종을 모두 배정할 필요는 없다. 한 번도 요청하지 않은 역할 카드는 역할 진행도가 생성되지 않은 미배정 상태로 남는다.

## 13. 상태 조회 반영

역할 진행도 생성 또는 담당자 변경 트랜잭션이 커밋된 뒤 협동 미션 상태 조회 API는 변경된 역할 배정을 `roleProgresses`에 반환해야 한다.

- 최초 배정이면 새 `roleProgressId`가 목록에 추가된다.
- 담당자 변경이면 같은 `roleProgressId`에서 `participantId`와 `participantName`이 변경된다.
- 역할 카드 id와 역할 이름은 그대로 유지된다.

역할 배정 저장 API 자체는 갱신된 역할 진행도를 응답하지 않는다.

## 14. 트랜잭션과 동시 요청

진행도 조회, 방장 검증, 역할 카드와 참가자 검증, 기존 역할 진행도 조회 및 upsert를 하나의 트랜잭션으로 처리한다.

- 진행도 row를 잠가 같은 방의 역할 배정 요청을 직렬화한다.
- 잠금을 획득한 뒤 같은 진행도와 역할 카드의 기존 역할 진행도를 다시 조회한다.
- 기존 row가 없을 때만 새 역할 진행도를 생성한다.
- 동시에 같은 역할 카드 배정 요청이 들어와도 역할 진행도는 하나만 남아야 한다.
- 처리 중 오류가 발생하면 생성 또는 담당자 변경을 롤백한다.

현재 `COOPERATIVE_ROLE_PROGRESS`에는 `cooperative_mission_progress_id`가 직접 없으므로 진행도와 역할 카드의 복합 `UNIQUE` 제약을 단순하게 걸 수 없다. 최종적인 중복 방지 책임은 진행도 잠금과 서비스 로직에 있다.

## 15. 정상 응답

다음 경우 모두 `204 No Content`를 반환한다.

- 역할 카드를 참가자에게 처음 배정하여 역할 진행도를 생성한 경우
- 이미 배정된 역할 카드의 담당 참가자를 변경한 경우
- 같은 역할 카드와 같은 참가자의 배정을 다시 요청한 경우

응답 Body는 반환하지 않는다.

## 16. 오류 처리

### 400 `INVALID_REQUEST`

다음과 같이 Path 또는 Request Body가 유효하지 않으면 반환한다.

- `cooperativeMissionProgressId`가 정수가 아니거나 `1`보다 작은 경우
- `roleCardId`가 정수가 아니거나 `1`보다 작은 경우
- `participantId`가 정수가 아니거나 `1`보다 작은 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 403 `COOPERATIVE_MISSION_HOST_ONLY`

현재 사용자가 해당 진행도의 `HOST`이자 `ACCEPTED` 참가자가 아니면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_HOST_ONLY"
}
```

### 404 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`

`cooperativeMissionProgressId`에 해당하는 진행도가 존재하지 않으면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

### 404 `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`

`participantId`에 해당하는 같은 진행도의 `ACCEPTED` 참가자가 존재하지 않으면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```

### 404 `COOPERATIVE_ROLE_CARD_NOT_FOUND`

`roleCardId`에 해당하는 역할 카드가 존재하지 않으면 반환한다.

```json
{
  "code": "COOPERATIVE_ROLE_CARD_NOT_FOUND"
}
```

### 409 `COOPERATIVE_MISSION_ALREADY_COMPLETED`

진행도가 이미 `COMPLETED` 상태이거나 `current_step = 4`이면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```

### 409 `COOPERATIVE_MISSION_STEP_NOT_ALLOWED`

진행도의 `current_step`이 역할 배정 단계인 `2`가 아니면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"
}
```

### 500 `INTERNAL_SERVER_ERROR`

역할 진행도 생성, 담당자 변경 또는 DB 처리 중 예상하지 못한 오류가 발생하면 변경 사항을 롤백하고 공통 `500` 오류를 반환한다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```

# 협동 미션 진행도 저장 비즈니스 룰

## 1. 요청 및 사용자 식별

- HTTP 메서드: `PATCH`
- 엔드포인트: `/api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress`
- Path의 `cooperativeMissionProgressId`로 단계를 변경할 `COOPERATIVE_MISSION_PROGRESS`를 식별한다.
- 요청 Body의 `currentStep`으로 변경할 다음 단계를 전달받는다.
- Request Query는 받지 않는다.
- 현재 사용자는 Authorization Bearer 토큰의 `get_current_user_id()`로 식별한다.

프론트에서 방장 id, 현재 단계 또는 역할 배정 정보를 전달받지 않는다. 현재 단계와 방장 여부는 DB를 기준으로 검증한다.

## 2. API 책임

이 API는 협동 미션의 단계를 다음 단계로 변경하는 역할만 담당한다.

- 역할 카드를 배정하거나 `COOPERATIVE_ROLE_PROGRESS`를 생성하지 않는다.
- 역할 배정 목록을 Request Body로 받지 않는다.
- 보상을 지급하거나 다음 장소를 추천하지 않는다.
- 변경된 협동 미션 전체 상태를 응답하지 않는다.
- 단계 변경 이후 화면 갱신은 협동 미션 상태 조회 API의 polling 결과를 사용한다.

정상적으로 단계를 변경하면 응답 Body 없이 `204 No Content`를 반환한다.

## 3. 처리 순서

1. Path와 Request Body의 형식 및 범위를 검증한다.
2. `cooperativeMissionProgressId`에 해당하는 진행도를 잠금 조회한다.
3. 진행도가 이미 완료되었는지 확인한다.
4. 현재 사용자가 해당 진행도의 `HOST`이자 `ACCEPTED` 참가자인지 확인한다.
5. 현재 단계와 요청한 `currentStep`이 순차적인 다음 단계인지 확인한다.
6. 단계별 추가 조건을 검증한다.
7. 진행도의 `current_step`을 요청한 단계로 변경한다.
8. `3 → 4`이면 완료 상태와 완료 시각을 함께 저장한다.
9. 트랜잭션을 커밋하고 `204 No Content`를 반환한다.

## 4. 진행도 조회

다음 조건으로 `COOPERATIVE_MISSION_PROGRESS`를 조회한다.

```text
id = cooperativeMissionProgressId
```

진행도가 존재하지 않으면 `404 COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`를 반환한다.

진행도 조회 시 `mission_status = IN_PROGRESS` 조건을 먼저 적용하여 완료된 진행도를 찾을 수 없는 진행도로 처리하지 않는다. 진행도를 id로 조회한 뒤 완료 상태를 별도로 확인하여 `409 COOPERATIVE_MISSION_ALREADY_COMPLETED`를 반환한다.

## 5. 방장 권한 검증

현재 사용자가 다음 조건을 모두 만족하는 참가자인지 확인한다.

- `cooperative_mission_progress_id = cooperativeMissionProgressId`
- `user_id = current_user_id`
- `participant_role = HOST`
- `participant_status = ACCEPTED`

조건을 만족하지 않으면 진행도를 변경하지 않고 `403 COOPERATIVE_MISSION_HOST_ONLY`를 반환한다.

방장 권한은 Request Body나 Path의 별도 사용자 id로 판단하지 않는다. 반드시 Bearer 토큰으로 식별한 현재 사용자의 참가자 row를 조회하여 판단한다.

## 6. 순차 단계 변경

단계는 다음 순서로 한 단계씩만 변경할 수 있다.

```text
1 → 2 → 3 → 4
```

허용되는 요청은 다음과 같다.

| 현재 단계 | 요청 `currentStep` | 처리 |
| --- | --- | --- |
| `1` | `2` | 초대 단계 종료 |
| `2` | `3` | 역할 카드 배정 단계 종료 |
| `3` | `4` | 협동 미션 완료 |

다음 요청은 `409 COOPERATIVE_MISSION_STEP_NOT_ALLOWED`로 처리한다.

- 현재 단계와 같은 단계 요청
- 이전 단계로 돌아가는 요청
- 두 단계 이상 건너뛰는 요청
- `currentStep`이 `2 | 3 | 4`가 아닌 요청

## 7. 1단계에서 2단계 변경

`1 → 2`에서는 해당 진행도에 `PENDING` 상태인 참가자가 남아 있는지 확인한다.

```text
cooperative_mission_progress_id = cooperativeMissionProgressId
participant_status = PENDING
```

`PENDING` 참가자가 한 명이라도 존재하면 `409 COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS`를 반환한다.

방장은 모든 참여 요청을 수락하거나 거절한 뒤 다시 단계 변경을 요청해야 한다. `PENDING` 참가자를 자동으로 수락하거나 삭제하지 않는다.

검증을 통과하면 `current_step`만 `2`로 변경한다.

## 8. 2단계에서 3단계 변경

`2 → 3`에서는 해당 진행도의 모든 `ACCEPTED` 참가자가 역할 카드를 최소 1개 이상 배정받았는지 확인한다.

검증 대상에는 다음 참가자를 포함한다.

- `HOST`, `ACCEPTED` 상태인 방장
- `MEMBER`, `ACCEPTED` 상태인 팀원

`PENDING` 참가자는 검증 대상에 포함하지 않는다. 정상 흐름에서는 `1 → 2` 검증으로 `PENDING` 참가자가 남아 있지 않아야 한다.

역할 진행도가 하나도 연결되지 않은 `ACCEPTED` 참가자가 존재하면 `409 COOPERATIVE_PARTICIPANT_ROLE_REQUIRED`를 반환한다.

다음 상황은 단계 변경을 막지 않는다.

- 역할 카드 6종 중 일부가 미배정으로 남아 있는 경우
- 한 참가자가 서로 다른 여러 역할 카드를 배정받은 경우

검증을 통과하면 `current_step`만 `3`으로 변경한다. 역할 진행도를 새로 만들거나 기존 역할 배정을 수정하지 않는다.

## 9. 3단계에서 4단계 변경

`3 → 4`는 방장이 협동 미션을 현재 인증 결과대로 종료할 때 사용한다.

인증하지 않은 역할 진행도가 남아 있거나 완료 역할 수가 `0`이어도 단계 변경을 허용한다.

다음 값을 하나의 트랜잭션에서 변경한다.

- `current_step`: `4`
- `mission_status`: `COMPLETED`
- `completed_at`: `now_kst()`로 구한 완료 처리 시각

이 API에서는 보상 지급과 다음 장소 추천을 수행하지 않는다. 완료 후 참가자들이 호출하는 협동 미션 상태 조회 API의 4단계 처리에서 보상과 다음 장소 정보를 구성한다.

## 10. 역할 배정 데이터 검증 범위

이 API는 `2 → 3` 변경 시 참가자별 역할 보유 여부만 검증한다.

역할 카드 하나가 최대 한 명에게만 배정되는지, 요청한 참가자와 역할 카드가 유효한지 등의 저장 검증은 별도의 협동 미션 역할 배정 저장 API가 담당한다.

진행도 저장 API는 이미 저장된 `COOPERATIVE_ROLE_PROGRESS`를 조회하여 다음 조건만 확인한다.

```text
모든 ACCEPTED 참가자에 대해 연결된 역할 진행도 수 >= 1
```

## 11. 트랜잭션과 동시 요청

진행도 조회, 권한 검증, 단계별 조건 검증과 단계 변경을 하나의 트랜잭션으로 처리한다.

- 진행도 row를 잠가 동일한 단계 변경 요청이 동시에 처리되지 않도록 한다.
- 잠금을 획득한 뒤 현재 단계와 완료 상태를 다시 확인한다.
- `1 → 2`에서는 잠금 범위 안에서 `PENDING` 참가자 존재 여부를 확인한다.
- `2 → 3`에서는 잠금 범위 안에서 `ACCEPTED` 참가자와 역할 진행도를 다시 조회한다.
- 처리 중 오류가 발생하면 단계, 상태 및 완료 시각 변경을 모두 롤백한다.

첫 번째 요청이 단계를 변경한 뒤 같은 요청이 다시 처리되면 현재 단계와 요청 단계가 일치하므로 `409 COOPERATIVE_MISSION_STEP_NOT_ALLOWED`를 반환한다.

## 12. 정상 응답

단계별 검증을 통과하고 진행도를 정상적으로 변경하면 `204 No Content`를 반환한다.

응답 Body는 반환하지 않는다. 프론트는 다음 polling 응답에서 변경된 `currentStep`과 협동 미션 상태를 확인한다.

## 13. 오류 처리

### 400 `INVALID_REQUEST`

다음과 같이 Path 또는 Request Body가 유효하지 않으면 반환한다.

- `cooperativeMissionProgressId`가 정수가 아니거나 `1`보다 작은 경우
- `currentStep`이 정수가 아닌 경우
- `currentStep`이 `2 | 3 | 4`가 아닌 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 403 `COOPERATIVE_MISSION_HOST_ONLY`

현재 사용자가 해당 진행도의 `HOST`이자 `ACCEPTED` 참가자가 아니면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_HOST_ONLY"
}
```

### 404 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`

`cooperativeMissionProgressId`에 해당하는 진행도가 존재하지 않으면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

### 409 `COOPERATIVE_MISSION_ALREADY_COMPLETED`

진행도의 `mission_status`가 이미 `COMPLETED`이거나 `current_step`이 이미 `4`이면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```

### 409 `COOPERATIVE_MISSION_STEP_NOT_ALLOWED`

현재 단계에서 요청한 `currentStep`으로 순차 변경할 수 없으면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"
}
```

### 409 `COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS`

`1 → 2` 변경 시 `PENDING` 참가자가 한 명 이상 존재하면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS"
}
```

### 409 `COOPERATIVE_PARTICIPANT_ROLE_REQUIRED`

`2 → 3` 변경 시 역할 진행도가 하나도 없는 `ACCEPTED` 참가자가 존재하면 반환한다.

```json
{
  "code": "COOPERATIVE_PARTICIPANT_ROLE_REQUIRED"
}
```

### 500 `INTERNAL_SERVER_ERROR`

진행도 조회, 검증 또는 저장 중 예상하지 못한 오류가 발생하면 변경 사항을 롤백하고 공통 `500` 오류를 반환한다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```

# 협동 미션 역할 진행도 저장 비즈니스 룰

## 1. 요청 및 사용자 식별

- HTTP 메서드: `POST`
- 엔드포인트: `/api/v1/cooperative-missions/{cooperativeMissionProgressId}/role-progresses/{roleProgressId}/verification`
- Path의 `cooperativeMissionProgressId`로 `COOPERATIVE_MISSION_PROGRESS`를 식별한다.
- Path의 `roleProgressId`로 사진을 인증할 `COOPERATIVE_ROLE_PROGRESS`를 식별한다.
- Request Body는 `multipart/form-data` 형식으로 받는다.
- 현재 사용자는 Authorization Bearer 토큰의 `get_current_user_id()`로 식별한다.

프론트에서 참가자 id, 역할 카드 id, 인증 성공 여부 또는 변경할 진행 상태를 전달받지 않는다. 역할 담당자와 역할 카드 정보는 역할 진행도 관계를 통해 백엔드가 조회하고, 인증 성공 여부도 백엔드가 결정한다.

## 2. 요청 이미지

프론트는 다음 필드로 사진 파일을 전송한다.

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `itemImage` | file | O | 역할 카드 조건에 맞는지 인증할 이미지 |

이미지는 AR 캐릭터와 사진 저장 API와 동일한 정책을 사용한다.

- 허용 형식: JPEG, PNG, WebP
- 최대 크기: 10MB
- HEIC/HEIF는 직접 받지 않고 프론트에서 JPEG로 변환한 후 전송한다.
- 파일 확장자만 신뢰하지 않고 실제 파일의 MIME type과 이미지 형식을 검증한다.
- 원본 파일명은 Blob 경로 생성에 사용하지 않는다.
- 실제 이미지 형식에 맞는 확장자로 정규화한다.

`itemImage`가 누락되거나 허용하지 않는 이미지이거나 10MB를 초과하면 사진 인증과 Blob 업로드를 수행하지 않고 `400 INVALID_REQUEST`를 반환한다.

## 3. API 책임

이 API는 현재 사용자가 자신에게 배정된 역할의 사진을 제출했을 때 다음 작업을 수행한다.

1. 진행도, 역할 진행도, 담당 참가자와 현재 단계를 검증한다.
2. 별도 사진 인증 모듈을 호출하여 인증 성공 여부를 판단한다.
3. 인증에 실패하면 DB를 변경하지 않고 `isVerified: false`를 반환한다.
4. 인증에 성공하면 사진을 Azure Blob Storage에 저장한다.
5. Blob URL과 역할 진행도 완료 상태를 DB에 저장한다.
6. `isVerified: true`를 반환한다.

이 API는 협동 미션 전체의 `current_step`과 `mission_status`를 변경하지 않는다. 마지막 역할 인증이 완료되어도 방장이 협동 미션 진행도 저장 API를 호출하여 `3 → 4`로 변경해야 한다.

## 4. 처리 순서

1. Path와 `itemImage`의 형식 및 크기를 검증한다.
2. `cooperativeMissionProgressId`에 해당하는 진행도를 조회한다.
3. 진행도가 이미 완료되었는지 확인한다.
4. 진행도의 `current_step`이 미션 수행 단계인 `3`인지 확인한다.
5. `roleProgressId`에 해당하며 요청한 진행도에 속하는 역할 진행도를 잠금 조회한다.
6. 현재 사용자가 해당 역할 진행도의 담당자이면서 `ACCEPTED` 참가자인지 확인한다.
7. 역할 진행도가 이미 완료되었는지 확인한다.
8. 연결된 역할 카드 정보를 조회한다.
9. 사진 인증 모듈을 호출한다.
10. 인증 성공 시 Blob 업로드와 역할 진행도 갱신을 수행한다.
11. 인증 결과를 `200 OK`로 반환한다.

## 5. 진행도와 단계 검증

`COOPERATIVE_MISSION_PROGRESS.id = cooperativeMissionProgressId`인 진행도를 조회한다.

진행도가 존재하지 않으면 `404 COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`를 반환한다.

진행도의 `mission_status`가 이미 `COMPLETED`이거나 `current_step = 4`이면 `409 COOPERATIVE_MISSION_ALREADY_COMPLETED`를 반환한다.

사진 인증은 다음 단계에서만 허용한다.

```text
COOPERATIVE_MISSION_PROGRESS.current_step = 3
```

현재 단계가 `1` 또는 `2`이면 `409 COOPERATIVE_MISSION_STEP_NOT_ALLOWED`를 반환한다.

## 6. 역할 진행도 조회

다음 관계를 모두 만족하는 역할 진행도를 조회한다.

```text
COOPERATIVE_ROLE_PROGRESS.id = roleProgressId
COOPERATIVE_ROLE_PROGRESS.participant_id = COOPERATIVE_MISSION_PARTICIPANT.id
COOPERATIVE_MISSION_PARTICIPANT.cooperative_mission_progress_id = cooperativeMissionProgressId
```

역할 진행도가 존재하지 않거나 다른 협동 미션 진행도에 속하면 `404 COOPERATIVE_ROLE_PROGRESS_NOT_FOUND`를 반환한다.

역할 진행도의 `progress_status`가 이미 `COMPLETED`이면 사진을 다시 인증하거나 기존 사진을 덮어쓰지 않고 `409 COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED`를 반환한다.

## 7. 담당 참가자 권한

현재 사용자는 다음 조건을 모두 만족해야 한다.

- 역할 진행도의 `participant_id`와 연결된 참가자의 사용자 id가 `current_user_id`와 같다.
- 참가자의 `participant_status`가 `ACCEPTED`이다.

조건을 만족하지 않으면 `403 COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED`를 반환한다.

방장도 해당 역할이 자신에게 배정된 경우에만 사진을 인증할 수 있다. 방장이라는 이유만으로 다른 참가자의 역할을 대신 인증할 수 없다.

한 참가자가 여러 역할을 맡았다면 각 `roleProgressId`에 대해 사진 인증 API를 별도로 호출한다.

## 8. 사진 인증 모듈 분리

사진 인증 판단은 `service.py`에 직접 구현하지 않고 다음 별도 모듈로 분리한다.

```text
app/cooperative_mission/photo_verifier.py
```

서비스는 사진 인증 모듈에 다음 정보를 전달한다.

- 이미지 파일의 bytes 또는 검증된 파일 객체
- 이미지 MIME type
- `COOPERATIVE_ROLE_CARD.role_name`
- `COOPERATIVE_ROLE_CARD.role_description`
- `COOPERATIVE_ROLE_CARD.location_to_find`

모듈은 서비스에 인증 여부인 `bool`만 반환한다.

```python
def verify_role_image(
    *,
    image_bytes: bytes,
    content_type: str,
    role_name: str,
    role_description: str,
    location_to_find: list[str],
) -> bool:
    ...
```

라우터와 서비스는 OpenAI API 호출 방법, 프롬프트 또는 응답 형식을 알지 않아야 한다. 이후 인증 방식이 변경되어도 `photo_verifier.py` 내부 구현만 교체할 수 있어야 한다.

## 9. 임시 인증 구현

현재는 OpenAI API 기반 이미지 인증 기획과 프롬프트가 확정되지 않았으므로 실제 외부 API를 호출하지 않는다.

`photo_verifier.py`의 `verify_role_image()`는 유효한 이미지 입력에 대해 항상 `True`를 반환하도록 구현한다.

```python
def verify_role_image(
    *,
    image_bytes: bytes,
    content_type: str,
    role_name: str,
    role_description: str,
    location_to_find: list[str],
) -> bool:
    return True
```

항상 인증 성공을 반환하더라도 파일 형식, 파일 크기, 진행 단계, 담당자 권한과 중복 완료 검증은 생략하지 않는다.

향후에는 동일한 함수 인터페이스를 유지한 채 함수 내부에서 OpenAI API를 호출하고 역할 카드 정보와 이미지를 프롬프트에 포함하여 인증 여부를 판단한다.

## 10. 인증 실패 처리

사진 인증 모듈이 `False`를 반환하면 인증 실패로 처리한다.

- Blob Storage에 사진을 업로드하지 않는다.
- `item_img_url`을 변경하지 않는다.
- `progress_status`를 변경하지 않는다.
- `completed_at`을 변경하지 않는다.
- `200 OK`와 `isVerified: false`를 반환한다.

인증 실패는 정상적인 판정 결과이므로 4xx 오류로 처리하지 않는다.

## 11. Blob Storage 저장

사진 인증 모듈이 `True`를 반환한 경우에만 Azure Blob Storage에 사진을 업로드한다.

컨테이너는 환경변수 `AZURE_STORAGE_CONTAINER`로 지정한다.

Blob 경로는 다음 형식을 사용한다.

```text
cooperative_mission_role/{cooperativeMissionProgressId}/{roleProgressId}/{uuid}.{extension}
```

경로 구성 규칙은 다음과 같다.

- `cooperativeMissionProgressId`: 요청 Path의 진행도 id
- `roleProgressId`: 요청 Path의 역할 진행도 id
- `uuid`: 서버에서 생성한 충돌 가능성이 낮은 UUID
- `extension`: 실제 이미지 형식에 따라 정규화한 `jpg | png | webp`

사진 파일은 App Service 또는 Docker 컨테이너의 로컬 파일 시스템이나 MySQL BLOB 컬럼에 저장하지 않는다.

## 12. 인증 성공 시 DB 갱신

Blob 업로드가 성공하면 다음 값을 하나의 트랜잭션에서 변경한다.

- `item_img_url`: 업로드된 Blob URL
- `progress_status`: `COMPLETED`
- `completed_at`: `now_kst()`로 구한 인증 완료 시각

인증 성공 시 기존 역할 진행도 row를 갱신하며 새로운 역할 진행도를 생성하지 않는다.

이 API에서는 다음 값을 변경하지 않는다.

- `COOPERATIVE_MISSION_PROGRESS.current_step`
- `COOPERATIVE_MISSION_PROGRESS.mission_status`
- `COOPERATIVE_MISSION_PROGRESS.completed_at`

## 13. Blob과 DB 저장 실패 처리

Blob 업로드에 실패하면 역할 진행도를 변경하지 않고 공통 `500 INTERNAL_SERVER_ERROR`를 반환한다.

Blob 업로드는 성공했지만 DB 갱신 또는 커밋에 실패하면 업로드한 Blob을 삭제하는 보상 작업을 시도하고 DB 변경을 롤백한다.

보상 삭제까지 실패하면 삭제 대상 Blob 경로를 오류 로그에 남기되 이미지 bytes, 인증 토큰 또는 전체 사용자 정보는 로그에 기록하지 않는다.

DB 커밋이 완료된 이후에는 역할 진행도에 저장된 Blob을 삭제하지 않는다.

## 14. 상태 조회 반영

인증 성공 트랜잭션이 커밋된 뒤 협동 미션 상태 조회 API의 다음 polling 응답에는 다음 값이 반영되어야 한다.

- `roleProgresses[].progressStatus`: `COMPLETED`
- `roleProgresses[].itemImgUrl`: 저장된 Blob URL
- `completedRoleCount`: 이전 값보다 1 증가

인증 실패이면 polling 응답의 역할 진행도와 완료 개수는 변경되지 않는다.

## 15. 정상 응답

사진 인증 모듈이 정상적으로 결과를 반환하면 성공 여부와 관계없이 `200 OK`를 반환한다.

인증 성공:

```json
{
  "isVerified": true
}
```

인증 실패:

```json
{
  "isVerified": false
}
```

다른 응답 필드는 포함하지 않는다.

## 16. 트랜잭션과 동시 요청

진행도와 역할 진행도 검증, 사진 인증 성공 후 Blob 업로드 및 DB 갱신은 하나의 요청 흐름에서 처리한다.

- 역할 진행도 row를 잠가 같은 역할에 대한 동시 인증 요청을 직렬화한다.
- 잠금을 획득한 뒤 `progress_status`를 다시 확인한다.
- 먼저 성공한 요청만 역할 진행도를 `COMPLETED`로 변경한다.
- 이후 요청은 `409 COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED`를 반환한다.
- DB 갱신 중 오류가 발생하면 변경 사항을 롤백한다.

외부 이미지 인증이 도입되면 긴 OpenAI API 호출 동안 DB 잠금을 유지하지 않도록 인증 전 조회와 인증 성공 후 잠금 재조회 단계를 분리한다. 인증 성공 후에는 역할 진행도와 담당자가 요청 시작 시점과 동일한지 다시 검증한 뒤 저장한다.

## 17. 오류 처리

### 400 `INVALID_REQUEST`

다음 경우 반환한다.

- `itemImage`가 누락된 경우
- JPEG, PNG, WebP가 아닌 경우
- 이미지 크기가 10MB를 초과한 경우
- Path id가 정수가 아니거나 `1`보다 작은 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 403 `COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED`

현재 사용자가 역할 진행도의 담당자가 아니거나 담당 참가자가 `ACCEPTED` 상태가 아니면 반환한다.

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED"
}
```

### 404 `COOPERATIVE_MISSION_PROGRESS_NOT_FOUND`

`cooperativeMissionProgressId`에 해당하는 진행도가 존재하지 않으면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

### 404 `COOPERATIVE_ROLE_PROGRESS_NOT_FOUND`

`roleProgressId`에 해당하는 역할 진행도가 존재하지 않거나 요청한 협동 미션 진행도에 속하지 않으면 반환한다.

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_NOT_FOUND"
}
```

### 409 `COOPERATIVE_MISSION_STEP_NOT_ALLOWED`

진행도의 `current_step`이 미션 수행 단계인 `3`이 아니면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"
}
```

### 409 `COOPERATIVE_MISSION_ALREADY_COMPLETED`

진행도가 이미 `COMPLETED` 상태이거나 `current_step = 4`이면 반환한다.

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```

### 409 `COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED`

역할 진행도가 이미 `COMPLETED` 상태이면 반환한다.

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED"
}
```

### 500 `INTERNAL_SERVER_ERROR`

사진 인증 모듈, Blob Storage 또는 DB 처리 중 예상하지 못한 오류가 발생하면 공통 `500` 오류를 반환한다. 이미 업로드된 Blob이 있으면 보상 삭제를 시도한다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```
