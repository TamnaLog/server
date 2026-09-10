## 걸음 수 저장

### 1. 사용자 식별과 요청값

- 현재 사용자는 `Authorization: Bearer {accessToken}`으로 식별하며 요청 Body에서 사용자 ID를 받지 않는다.
- 프론트는 `recordedAt`, `stepsCount`, `isGoalAchieved`를 모두 전달한다.
- `recordedAt`은 KST 기준 offset 없는 날짜·시간이며 `STEP_COUNT.saved_at`에 그대로 저장한다. 서버 수신 시각으로 교체하거나 KST 자정으로 정규화하지 않는다.
- `stepsCount`는 해당 시점의 누적 걸음 수이며 `STEP_COUNT.steps_count`에 그대로 저장한다. 서버에서 이전 기록과 더하거나 최댓값으로 보정하지 않는다.
- `isGoalAchieved`는 프론트가 목표 달성 여부를 판정해서 보낸 값이며 DB에 저장하지 않는다. 서버는 `stepsCount`와 목표 걸음 수를 다시 비교하여 이 값을 변경하지 않는다.

### 2. 걸음 수 기록 저장

다음 값으로 `STEP_COUNT`를 저장한다.

| 컬럼 | 저장값 |
| --- | --- |
| `user_id` | 액세스 토큰으로 식별한 현재 사용자 ID |
| `saved_at` | 요청의 `recordedAt` |
| `steps_count` | 요청의 `stepsCount` |

- `(user_id, saved_at)`이 처음 전달된 경우 새 기록을 생성한다.
- 동일 사용자와 동일 `recordedAt`으로 다시 요청하면 새 행을 만들지 않고 기존 행의 `steps_count`를 요청값으로 교체한다.
- 재요청의 `stepsCount`가 기존 값보다 작더라도 최신 요청값을 최종값으로 사용한다.
- 동시 요청으로 유니크 충돌이 발생하면 기존 행을 다시 조회해 요청값을 반영한다.

### 3. 목표 달성 캐릭터 추첨

- `isGoalAchieved = false`이면 캐릭터를 추첨하거나 `ACQUIRED_AR_CHARACTER`를 생성하지 않는다.
- `isGoalAchieved = true`이면 후보 ID `(1, 2, 3)` 중 하나를 균등한 확률로 무작위 선택한다.
- 후보 목록은 서비스 코드의 상수로 분리한다.

```python
STEP_GOAL_REWARD_CHARACTER_IDS = (1, 2, 3)
```

- 선택된 ID로 `AR_CHARACTER`를 조회하여 캐릭터 이름과 이미지 URL을 응답에 사용한다.
- 후보 ID에 해당하는 캐릭터가 존재하지 않으면 잘못된 목데이터 또는 마스터 데이터 상태이므로 전체 트랜잭션을 롤백하고 `500 INTERNAL_SERVER_ERROR`를 반환한다.
- 같은 요청에서 이미 보유한 캐릭터가 선택되더라도 다른 캐릭터를 다시 추첨하지 않는다.

### 4. 캐릭터 획득 저장

현재 사용자가 선택된 캐릭터를 보유했는지는 다음 조건의 `ACQUIRED_AR_CHARACTER` 존재 여부로 판단한다.

```text
ACQUIRED_AR_CHARACTER.user_id = current_user_id
AND ACQUIRED_AR_CHARACTER.ar_character_id = selected_character_id
```

- 기존 획득 기록이 없으면 다음 값으로 `ACQUIRED_AR_CHARACTER`에 새 행을 생성한다.

| 컬럼 | 저장값 |
| --- | --- |
| `user_id` | 현재 사용자 ID |
| `ar_character_id` | 무작위로 선택된 캐릭터 ID |
| `acquired_mission_id` | `NULL` |

- 기존 획득 기록이 있으면 중복 행을 생성하지 않는다.
- 중복 여부와 관계없이 이번 요청에서 무작위로 선택된 동일 캐릭터의 이름과 이미지 URL을 응답한다.
- 동시 요청으로 동일한 `(user_id, ar_character_id)` 획득이 경합하면 유니크 제약을 기준으로 한 행만 유지하고, 나머지 요청도 이미 보유한 경우와 동일하게 정상 응답한다.
- 걸음 수 달성 보상은 특정 미션에서 획득한 보상이 아니므로 `acquired_mission_id = NULL`로 저장한다.

### 5. 응답 조합

- `targetStep`은 현재 ERD에서 목표 걸음 수를 소유하는 `USER.target_step`으로 구성한다. `STEP_COUNT`에는 `target_step` 컬럼이 없다.
- `isGoalAchieved = true`이면 선택된 `AR_CHARACTER.character_name`을 `characterName`, `AR_CHARACTER.character_img_url`을 `characterImageUrl`로 반환한다.
- `isGoalAchieved = false`이면 `characterName`과 `characterImageUrl`을 모두 `null`로 반환한다.
- 캐릭터를 이미 보유하고 있어 획득 행을 생성하지 않은 경우에도 선택된 캐릭터 정보를 그대로 반환한다.

### 6. 트랜잭션

- 걸음 수 생성·갱신, 캐릭터 조회와 신규 획득 기록 생성은 하나의 트랜잭션으로 처리한다.
- 모든 DB 변경이 커밋된 뒤에만 `200 OK`로 응답한다.
- 처리 중 오류가 발생하면 걸음 수와 캐릭터 획득 변경을 모두 롤백한다.

## GPS 및 방문 장소 저장

- 현재 사용자는 인증 토큰으로 식별하며 클라이언트 입력으로 사용자 ID를 받지 않는다.
- 요청 좌표의 `longitude`는 `mx`, `latitude`는 `my`에 대응시키며, 요청의 `recordedAt`을 `GPS.saved_at`과 판정된 모든 `VISITED_LOCATION.visited_at`에 동일하게 사용한다. 서버 수신 시각은 방문 시각을 대신하지 않는다.
- 현재 방문 판정은 각 `LOCATION`의 중심 좌표와 `radius`를 기준으로 지표면 거리(m)를 계산해 `거리 <= radius`인 장소를 찾는다. 반경 경계는 방문으로 포함하며, 반경이 겹치면 일치한 장소를 모두 기록한다.
- 현재 단계에서는 진입·이탈 상태나 체류 시간을 추적하지 않는다. 따라서 주기적으로 수신한 좌표가 계속 반경 안에 있으면 요청마다 방문 기록이 생성된다.
- 방문 판정은 좌표와 장소 목록을 받아 방문 장소 ID 목록만 반환하는 독립 모듈로 분리한다. 영속화나 HTTP 처리에 의존하지 않게 하여 추후 진입 이벤트, 체류 시간, 위치 정확도 또는 공간 질의 기반 로직으로 교체할 수 있어야 한다.
- GPS 기록과 해당 좌표에서 판정된 방문 기록은 하나의 트랜잭션으로 저장한다. 하나라도 실패하면 전체를 롤백하고, 커밋이 끝난 뒤에만 성공으로 처리한다.
