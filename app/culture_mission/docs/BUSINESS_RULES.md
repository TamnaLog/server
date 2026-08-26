# 문화 미션 시작/이어하기 비즈니스 룰

## 1. 조회 기준

요청 Path의 `cultureMissionId`는 공통 `MISSION.id`가 아니라 `CULTURE_MISSION.id`를 의미한다.

현재 로그인한 사용자의 `userId`와 요청받은 `cultureMissionId`를 함께 사용하여 `CULTURE_MISSION_PROGRESS` 이력을 조회한다.

진행 이력은 상태에 따라 다음 두 종류로 구분한다.

- `IN_PROGRESS`: 현재 이어서 진행할 수 있는 진행도
- `COMPLETED`: 과거에 미션을 완료한 진행도

## 2. 처리 순서

1. `cultureMissionId`에 해당하는 `CULTURE_MISSION`을 조회한다.
2. 문화 미션이 존재하면 현재 사용자의 해당 문화 미션 진행 이력을 조회한다.
3. `IN_PROGRESS` 진행도가 있으면 기존 진행도를 반환한다.
4. `IN_PROGRESS` 진행도가 없으면 새로운 진행도를 생성하여 반환한다.

## 3. 진행 이력에 따른 분기

| `COMPLETED` 진행도 | `IN_PROGRESS` 진행도 | 처리 | Status Code |
| --- | --- | --- | --- |
| 없음 | 없음 | 최초 진행도를 새로 생성 | `201` |
| 없음 | 있음 | 기존 진행도를 이어서 반환 | `200` |
| 있음 | 있음 | 기존 진행도를 이어서 반환 | `200` |
| 있음 | 없음 | 재도전 진행도를 새로 생성 | `201` |

### 3.1 최초 시작

현재 사용자와 문화 미션에 해당하는 진행도가 하나도 없으면 미션을 처음 시작하는 것으로 판단한다.

다음 값으로 `CULTURE_MISSION_PROGRESS`를 생성한다.

- `culture_mission_id`: 요청받은 `cultureMissionId`
- `user_id`: 현재 로그인한 사용자 id
- `mission_status`: `IN_PROGRESS`
- `current_quiz_index`: `1`
- `correct_number`: `0`
- `completed_at`: `null`

새로 생성한 진행도의 id를 `cultureMissionProgressId`로 반환한다.

### 3.2 최초 도전 이어하기

`COMPLETED` 진행도는 없지만 `IN_PROGRESS` 진행도가 있으면 기존 진행도를 이어서 한다.

새로운 진행도를 생성하지 않고 기존 진행도의 다음 정보를 사용한다.

- `cultureMissionProgressId`: 기존 `IN_PROGRESS` 진행도의 id
- `currentQuizNumber`: 기존 진행도의 `current_quiz_index`

### 3.3 완료 이력이 있는 미션 이어하기

`COMPLETED` 진행도와 `IN_PROGRESS` 진행도가 모두 있으면 과거에 완료한 미션을 다시 도전 중인 상태이다.

새로운 진행도를 생성하지 않고 기존 `IN_PROGRESS` 진행도를 반환한다.

- `cultureMissionProgressId`: 기존 `IN_PROGRESS` 진행도의 id
- `currentQuizNumber`: 기존 진행도의 `current_quiz_index`

### 3.4 완료 이력이 있는 미션 다시 시작하기

`COMPLETED` 진행도는 있지만 `IN_PROGRESS` 진행도가 없으면 과거에 완료한 미션을 다시 시작하는 것으로 판단한다.

기존 `COMPLETED` 진행도는 변경하거나 삭제하지 않고, 최초 시작과 동일한 초기값으로 새로운 `IN_PROGRESS` 진행도를 생성한다.

- `cultureMissionProgressId`: 새로 생성된 진행도의 id
- `currentQuizNumber`: `1`

## 4. 퀴즈 진행 위치

`CULTURE_MISSION_PROGRESS.current_quiz_index`는 사용자가 다음에 풀 퀴즈 번호를 의미한다.

- 신규 진행도의 `current_quiz_index`: `1`
- 1번 퀴즈까지 완료한 경우: `2`
- 2번 퀴즈까지 완료한 경우: `3`

응답의 `currentQuizNumber`에는 진행도의 `current_quiz_index`를 그대로 반환한다.

```text
currentQuizNumber = current_quiz_index
```

따라서 신규 진행도의 `current_quiz_index`와 응답의 `currentQuizNumber`는 모두 `1`이다.

## 5. 진행도 생성 제한

동일한 사용자와 동일한 문화 미션에는 이어서 사용할 `IN_PROGRESS` 진행도가 최대 하나만 존재해야 한다.

기존 `IN_PROGRESS` 진행도가 있으면 시작 API를 다시 호출하더라도 새로운 진행도를 만들지 않고 기존 진행도를 반환한다.

## 6. 응답 데이터 구성

- `cultureMissionProgressId`: 반환 대상인 신규 또는 기존 `IN_PROGRESS` 진행도의 id
- `quizCount`: `CULTURE_MISSION.quiz_total_count`
- `currentQuizNumber`: 반환 대상 진행도의 `current_quiz_index`
- `quizDetails`: `CULTURE_MISSION.quiz_detail`을 `quizIndex` 오름차순으로 정렬한 목록

## 7. 오류 응답

### 404 `CULTURE_MISSION_NOT_FOUND`

`cultureMissionId`에 해당하는 `CULTURE_MISSION`이 존재하지 않으면 진행도를 조회하거나 생성하지 않고 `404`를 반환한다.

```json
{
  "code": "CULTURE_MISSION_NOT_FOUND"
}
```



# 문화 미션 진행도 저장 비즈니스 룰

## 1. 요청 기준

요청 Path의 `cultureMissionProgressId`는 `CULTURE_MISSION_PROGRESS.id`를 의미한다.

요청 Body로 다음 정보를 전달받는다.

- `quizIndex`: 사용자가 제출한 퀴즈 번호
- `isCorrect`: 프론트에서 판정한 정답 여부

요청 Query로 다음 사용자 위치 정보를 전달받는다.

- `latitude`: 사용자 현재 위치의 위도
- `longitude`: 사용자 현재 위치의 경도

사용자 위치는 미션 완료 후 추천된 다음 장소까지의 거리를 계산하는 데 사용한다. 현재 임시 추천 로직에서는 장소를 선정하는 기준으로 사용하지 않는다.

정답 여부는 프론트의 판정 결과를 신뢰한다. 백엔드는 사용자가 선택한 답을 다시 비교하거나 정답을 재검증하지 않고 `isCorrect`를 그대로 진행도에 반영한다.

## 2. 진행도 조회

`cultureMissionProgressId`와 현재 로그인한 사용자 id를 함께 사용하여 `IN_PROGRESS` 상태의 `CULTURE_MISSION_PROGRESS`를 조회한다.

다른 사용자의 진행도이거나 이미 `COMPLETED` 상태인 진행도는 갱신 대상으로 사용하지 않는다.

진행도를 찾으면 `culture_mission_id`를 사용하여 연결된 `CULTURE_MISSION`을 조회하고, 다음 값을 사용한다.

- `current_quiz_index`: 현재 제출해야 하는 퀴즈 번호
- `correct_number`: 현재까지 맞힌 문제 수
- `quiz_total_count`: 문화 미션의 전체 퀴즈 수

## 3. 퀴즈 번호 검증

요청 Body의 `quizIndex`는 진행도의 `current_quiz_index`와 일치해야 한다.

```text
quizIndex = current_quiz_index
```

두 값이 일치하지 않으면 진행도를 변경하지 않고 `409 CULTURE_MISSION_QUIZ_INDEX_MISMATCH`를 반환한다.

## 4. 정답 수 반영

퀴즈 번호 검증을 통과하면 프론트가 전달한 `isCorrect`를 다음과 같이 반영한다.

- `isCorrect=true`: `correct_number`를 `1` 증가
- `isCorrect=false`: `correct_number`를 변경하지 않음

정답 여부는 진행 중인 경우와 마지막 퀴즈를 완료하는 경우 모두 동일하게 반영한다.

## 5. 진행 중과 완료 분기

퀴즈 번호와 전체 퀴즈 수를 비교하여 진행 중 처리와 완료 처리를 구분한다.

| 조건 | 처리 결과 |
| --- | --- |
| `current_quiz_index < quiz_total_count` | 진행 중 처리 |
| `current_quiz_index = quiz_total_count` | 완료 처리 |

### 5.1 진행 중 처리

현재 퀴즈 번호가 전체 퀴즈 수보다 작으면 아직 풀어야 할 문제가 남아 있는 상태이다.

정답 여부를 반영한 후 다음과 같이 진행도를 변경한다.

- `current_quiz_index`: `1` 증가
- `mission_status`: `IN_PROGRESS` 유지
- `completed_at`: `null` 유지

응답은 갱신된 값을 기준으로 조합한다.

- `missionProgressStatus`: `IN_PROGRESS`
- `currentQuizNumber`: `1` 증가한 `current_quiz_index`
- `correctNumber`: 정답 여부를 반영한 `correct_number`
- `nextLocation`: `null`
- `reward`: `null`

### 5.2 완료 처리

현재 퀴즈 번호와 전체 퀴즈 수가 같으면 이번 요청으로 마지막 퀴즈를 제출한 것이다.

정답 여부를 반영한 후 다음과 같이 진행도를 변경한다.

- `current_quiz_index`: 증가시키지 않음
- `mission_status`: `COMPLETED`로 변경
- `completed_at`: 완료 시각 기록

응답은 완료된 값을 기준으로 조합한다.

- `missionProgressStatus`: `COMPLETED`
- `currentQuizNumber`: 증가시키지 않은 마지막 퀴즈 번호
- `correctNumber`: 마지막 정답 여부까지 반영한 `correct_number`
- `nextLocation`: 다음 장소 추천 결과
- `reward`: 이번 완료 요청으로 실제 지급된 보상 정보

미션을 완료하면 정답 수에 따라 `CULTURE_MISSION.reward_detail`의 보상을 실제 데이터에 반영한다.

보상 지급 로직은 문화 미션 진행도 저장 로직 안에 직접 작성하지 않고 별도 모듈 `app/culture_mission/reward_granter.py`의 `grant_culture_mission_reward()`를 사용한다. 지급 순서와 개수 계산은 문화 미션의 정답 수 규칙을 따르므로 도메인 안에 둔다. 보상 응답 형식과 조합 규칙은 미션 유형과 무관하게 같으므로 공용 모듈 `app/common/rewards.py`를 사용한다.

| 보상 | 저장 위치 |
| --- | --- |
| 포인트 | `USER.point`에 누적 |
| AR 캐릭터 | `ACQUIRED_AR_CHARACTER`에 획득 기록 추가 |
| 쿠폰 | 별도 보관 테이블이 없으므로 진행도 지급 여부만 기록하고 응답에 쿠폰 정보를 반환 |

`ACQUIRED_AR_CHARACTER.acquired_mission_id`에는 유형별 세부 미션 id가 아니라 연결된 공통 `MISSION.id`를 저장한다.

`(user_id, ar_character_id)`는 UNIQUE이므로, 같은 캐릭터를 다른 미션 보상으로 이미 획득했다면 획득 기록을 추가하지 않는다. 이때도 포인트는 정상 지급한다.

미션 완료 처리와 보상 지급은 하나의 트랜잭션으로 처리한다. 보상 지급 중 오류가 발생하면 완료 처리도 저장되지 않는다.

### 5.3 보상 지급 순서와 중복 지급 방지

보상은 같은 사용자와 같은 문화 미션 기준으로 각 보상 항목을 한 번만 지급할 수 있다.

문화 미션은 여러 번 재시도할 수 있으므로, 보상 지급 여부는 현재 진행도 하나만 보지 않고 같은 사용자와 같은 문화 미션의 모든 진행도 이력을 기준으로 판단한다.

보상 지급 전 같은 사용자와 같은 문화 미션의 모든 진행도에서 아래 컬럼을 조회한다.

- `ar_character_reward_granted`
- `point_reward_granted`
- `coupon_reward_granted`

각 컬럼 중 하나라도 `true`인 이력이 있으면 해당 보상 항목은 이미 지급된 것으로 보고 이번 요청에서 다시 지급하지 않는다.

지급 가능한 보상은 아래 순서로 계산한다.

1. AR 캐릭터
2. 포인트
3. 쿠폰

이미 지급된 보상과 `reward_detail`에 존재하지 않는 보상은 지급 후보에서 제외한다.

이번 요청에서 지급할 수 있는 보상 개수는 `correct_number`와 남은 지급 후보 수 중 더 작은 값이다. 즉 정답 1개당 보상 항목 1개를 지급하되, 남은 보상보다 더 많이 지급하지 않는다.

예를 들어 전체 퀴즈 3개 중 첫 완료 시 정답이 1개이면 AR 캐릭터만 지급한다. 이후 같은 문화 미션을 다시 완료했고 정답이 1개이면 과거에 지급된 AR 캐릭터는 제외하고 포인트만 지급한다. 남은 보상이 포인트와 쿠폰 2개뿐인데 정답이 3개이면 포인트와 쿠폰 2개만 지급한다.

이번 요청으로 실제 지급한 보상 항목은 현재 `CULTURE_MISSION_PROGRESS` row의 지급 여부 컬럼을 `true`로 변경한다. 지급하지 않은 항목은 `false`로 둔다.

### 5.4 보상 응답 구성

진행 중인 응답에서는 `reward`를 `null`로 반환한다.

완료 응답에서는 `reward` 객체를 반환하고, 이번 요청으로 실제 지급된 보상만 채운다.

- `reward.arCharacter`: 이번 요청으로 AR 캐릭터를 지급했으면 캐릭터 정보, 아니면 `null`
- `reward.point`: 이번 요청으로 포인트를 지급했으면 지급 포인트, 아니면 `null`
- `reward.coupon`: 이번 요청으로 쿠폰을 지급했으면 쿠폰 정보, 아니면 `null`

미션을 완료했더라도 정답 수가 `0`이거나 모든 보상 항목이 이미 지급된 상태이면 `reward` 객체 안의 모든 항목을 `null`로 반환한다.

## 6. 다음 장소 추천

다음 장소 추천은 문화 미션 진행도 저장 로직 안에 직접 작성하지 않고 별도 함수로 분리한다.

현재는 실제 추천 기준이 정해지지 않았으므로 `LOCATION` 테이블에 존재하는 장소 중 하나를 무작위로 선택한다. 추후 추천 기준이 확정되면 별도 함수 내부의 무작위 선택 로직을 실제 추천 로직으로 교체한다.

진행 중인 응답에서는 장소를 추천하지 않고 `nextLocation`을 `null`로 반환한다. 마지막 퀴즈를 제출하여 미션을 완료한 경우에는 `nextLocation`을 반드시 객체로 반환한다.

완료 응답을 만들기 위해 추천 가능한 장소 데이터는 최소 1개 이상 존재해야 한다. 추천 가능한 장소가 없는 상태는 정상 완료 응답으로 처리하지 않는다.

장소 이미지 URL은 외부 API(TourAPI)에 의존하므로 조회 실패를 미션 완료 실패로 취급하지 않는다. 인증키 미설정, 통신 오류, 응답에 이미지가 없는 경우 모두 `locationImageUrl`을 `null`로 반환하고 나머지 응답은 정상으로 처리한다.

장소 정보는 다음 기준으로 조합한다.

- `nextLocation.id`: `LOCATION.id`
- `nextLocation.locationTitle`: `LOCATION.location_title`
- `nextLocation.locationImageUrl`: `LOCATION.content_id`를 사용하여 TourAPI에서 조회한 장소 이미지 URL. 조회하지 못하면 `null`
- `nextLocation.distanceMeter`: 사용자 위치에서 추천 장소까지의 직선거리(m)

`distanceMeter`는 별도의 거리 계산 로직을 새로 작성하지 않고 공통 거리 모듈인 `app/common/distance.py`의 `calculate_distance_meter()`를 사용하여 계산한다.

`LOCATION` 좌표에서 `my`는 위도, `mx`는 경도를 의미하므로 다음 순서로 전달한다.

```python
distance.calculate_distance_meter(
    latitude,
    longitude,
    next_location.my,
    next_location.mx,
)
```

계산 결과는 정수 미터 단위로 `nextLocation.distanceMeter`에 반환한다.

## 7. 다음 장소의 미션 정보

추천된 장소에 연결된 세부 미션이 있으면 `nextLocation.mission`에 미션 정보를 포함한다. 연결된 세부 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.

`nextLocation.mission.id`는 공통 `MISSION.id`가 아니라 `missionType`에 해당하는 유형별 세부 미션 테이블의 id이다.

현재 ERD에서 문화 미션은 장소를 갖지 않으므로 다음 장소에 연결된 미션으로 반환할 수 있는 유형은 협동 미션과 보물찾기 미션이다.

| `missionType` | `nextLocation.mission.id`의 출처 |
| --- | --- |
| `COOPERATIVE` | `COOPERATIVE_MISSION.id` |
| `TREASURE` | `TREASURE_MISSION.id` |

추천된 장소에 여러 세부 미션이 연결되어 있으면 다음 장소 추천 함수가 응답에 포함할 미션 하나를 선택한다. 현재 임시 추천 로직에서는 연결된 세부 미션 중 하나를 무작위로 선택한다.

프론트는 `nextLocation.mission.missionType`과 `nextLocation.mission.id`를 함께 사용하여 미션 홈 조회 API를 호출한다.

## 8. 완료된 진행도 재요청

이미 `COMPLETED` 상태인 진행도에는 추가 저장을 허용하지 않는다.

완료 요청의 응답을 받지 못해 같은 요청이 다시 전달되더라도 완료 결과를 다시 반환하거나 정답 수를 다시 반영하지 않는다. `IN_PROGRESS` 진행도를 찾지 못한 것으로 처리하여 `404 CULTURE_MISSION_PROGRESS_NOT_FOUND`를 반환한다.

## 9. 응답 데이터 구성

- `missionProgressStatus`: 갱신 후 `mission_status`
- `quizCount`: `CULTURE_MISSION.quiz_total_count`
- `currentQuizNumber`: 갱신 후 `current_quiz_index`
- `correctNumber`: 요청의 정답 여부를 반영한 `correct_number`
- `nextLocation`: 진행 중이면 `null`, 완료하면 거리 정보를 포함한 다음 장소 추천 결과 객체
- `reward`: 진행 중이면 `null`, 완료하면 이번 요청으로 실제 지급된 보상 정보

## 10. 오류 응답

### 400 `INVALID_REQUEST`

요청 Path 또는 Body의 형식이나 값 자체가 유효하지 않은 경우 반환한다.

- `quizIndex`가 정수가 아닌 경우
- `quizIndex`가 `1`보다 작은 경우
- `isCorrect`가 boolean이 아닌 경우
- `cultureMissionProgressId`가 정수가 아니거나 `1`보다 작은 경우
- `latitude` 또는 `longitude`가 누락되거나 숫자가 아닌 경우
- `latitude`가 `-90~90` 범위를 벗어난 경우
- `longitude`가 `-180~180` 범위를 벗어난 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 404 `CULTURE_MISSION_PROGRESS_NOT_FOUND`

요청한 진행도를 현재 사용자의 진행 중인 문화 미션 진행도로 사용할 수 없는 경우 반환한다.

- `cultureMissionProgressId`에 해당하는 진행도가 없는 경우
- 해당 진행도가 다른 사용자의 진행도인 경우
- 해당 진행도가 이미 `COMPLETED` 상태인 경우

```json
{
  "code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"
}
```

### 409 `CULTURE_MISSION_QUIZ_INDEX_MISMATCH`

요청의 `quizIndex`가 진행도의 `current_quiz_index`와 일치하지 않는 경우 반환한다.

```json
{
  "code": "CULTURE_MISSION_QUIZ_INDEX_MISMATCH"
}
```



# 문화 미션 중단 비즈니스 룰

## 1. 요청 기준

문화 미션을 끝까지 진행하지 않고 현재까지의 결과로 종료할 때 호출한다. 문화 미션 중단은 실패가 아닌 완료로 취급한다.

- Path의 `cultureMissionProgressId`로 중단할 문화 미션 진행도를 식별한다.
- Query의 `latitude`, `longitude`는 다음 장소까지의 거리를 계산하는 데 사용한다.
- 별도의 Request Body는 받지 않는다.
- 현재 사용자의 `IN_PROGRESS` 상태인 진행도만 중단할 수 있다.

## 2. 처리 순서

1. `cultureMissionProgressId`, `latitude`, `longitude`의 형식과 범위를 검증한다.
2. `cultureMissionProgressId`에 해당하는 현재 사용자의 `IN_PROGRESS` 문화 미션 진행도를 조회한다.
3. 진행도에 저장된 현재 `correct_number`를 기준으로 지급할 보상을 계산한다.
4. 문화 미션 진행도 저장의 완료 처리와 동일한 방식으로 다음 장소를 추천한다.
5. 진행도의 `mission_status`를 즉시 `COMPLETED`로 변경하고 `completed_at`을 현재 시각으로 저장한다.
6. 이번 요청에서 실제 지급한 보상에 해당하는 지급 여부 컬럼을 갱신한다.
7. 상태 변경과 보상 지급을 하나의 트랜잭션으로 저장한 뒤 응답을 반환한다.

## 3. 진행도 완료 처리

중단 요청이 유효하면 남은 퀴즈 수와 관계없이 진행도를 즉시 완료 처리한다.

- `mission_status`: `COMPLETED`로 변경
- `completed_at`: 중단 처리 시각으로 저장
- `current_quiz_index`: 기존 값을 유지
- `correct_number`: 기존 값을 유지

중단 API는 `quizIndex`와 `isCorrect`를 받지 않는다. 따라서 퀴즈 인덱스와 정답 수를 증가시키지 않으며, DB에 이미 반영된 진행 결과만 사용한다.

## 4. 보상 지급

보상 지급 방식은 문화 미션 진행도 저장 API의 완료 처리와 동일하다. 별도의 중단 전용 보상 계산을 만들지 않고 `app/culture_mission/reward_granter.py`의 `grant_culture_mission_reward()`를 동일하게 사용한다.

- 지급 개수는 DB에 저장된 현재 진행도의 `correct_number`를 기준으로 계산한다.
- 정답 1개당 보상 아이템 1개를 지급한다.
- 지급 순서는 AR 캐릭터, 포인트, 쿠폰 순서이다.
- 같은 사용자와 같은 문화 미션의 모든 진행도 이력을 조회하여 이미 한 번이라도 지급된 보상 유형은 제외한다.
- 중복 지급 여부는 모든 진행도의 `ar_character_reward_granted`, `point_reward_granted`, `coupon_reward_granted`를 기준으로 판단한다.
- 해당 문화 미션의 `reward_detail`에 존재하지 않는 보상 유형은 지급 대상에서 제외한다.
- 실제 지급 개수는 `min(correct_number, 아직 지급되지 않은 보상 개수)`이다.
- 이번 요청에서 실제 지급한 보상에 대해서만 현재 진행도의 지급 여부 컬럼을 `true`로 변경한다.

`correct_number`가 `0`이거나 지급 가능한 보상이 남아 있지 않아도 중단 처리는 정상 완료한다. 이 경우 `reward`는 객체로 반환하되 내부의 `arCharacter`, `point`, `coupon`을 모두 `null`로 반환한다.

보상 지급과 진행도 완료 처리는 하나의 트랜잭션으로 처리한다. 보상 지급 중 오류가 발생하면 `mission_status` 변경을 포함한 중단 처리 전체를 롤백한다.

## 5. 다음 장소 추천

다음 장소 추천 방식은 문화 미션 진행도 저장 API의 완료 처리와 동일하다. 동일한 추천 함수와 거리 계산 함수를 사용한다.

- 사용자 위치는 Query의 `latitude`, `longitude`를 사용한다.
- `distanceMeter`는 `app/common/distance.py`의 `calculate_distance_meter()`로 계산한다.
- 중단은 미션 완료로 처리되므로 `nextLocation`은 항상 객체로 반환한다.
- 추천 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.
- TourAPI 조회 실패 또는 이미지가 없는 경우 `nextLocation.locationImageUrl`만 `null`로 반환하고 중단 처리는 정상 완료한다.

## 6. 응답 데이터 구성

- `missionProgressStatus`: 항상 `COMPLETED`
- `quizCount`: `CULTURE_MISSION.quiz_total_count`
- `correctNumber`: 중단 시점에 진행도에 저장된 `correct_number`
- `nextLocation`: 거리 정보를 포함한 다음 장소 추천 결과 객체
- `reward`: 이번 중단 요청에서 실제 지급된 보상 정보. 지급된 보상이 없으면 내부 필드가 모두 `null`인 객체

중단 응답에는 `currentQuizNumber`, `rewardDetail`, 보상 지급 여부 컬럼을 포함하지 않는다.

## 7. 오류 응답

### 400 `INVALID_REQUEST`

요청 Path 또는 Query의 형식이나 값 자체가 유효하지 않은 경우 반환한다.

- `cultureMissionProgressId`가 정수가 아니거나 `1`보다 작은 경우
- `latitude` 또는 `longitude`가 누락되거나 숫자가 아닌 경우
- `latitude`가 `-90~90` 범위를 벗어난 경우
- `longitude`가 `-180~180` 범위를 벗어난 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 404 `CULTURE_MISSION_PROGRESS_NOT_FOUND`

요청한 진행도를 현재 사용자의 진행 중인 문화 미션 진행도로 사용할 수 없는 경우 반환한다.

- `cultureMissionProgressId`에 해당하는 진행도가 없는 경우
- 해당 진행도가 다른 사용자의 진행도인 경우
- 해당 진행도가 이미 `COMPLETED` 상태인 경우

이미 완료된 진행도도 외부에 존재 여부나 소유권을 구분해서 노출하지 않고 동일하게 `404 CULTURE_MISSION_PROGRESS_NOT_FOUND`로 처리한다. 별도의 `CULTURE_MISSION_ALREADY_COMPLETED` 오류는 사용하지 않는다.

```json
{
  "code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"
}
```
