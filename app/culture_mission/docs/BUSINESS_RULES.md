# 문화 미션 시작/이어하기 비즈니스 룰

## 1. 조회 기준

요청 Path의 `cultureMissionId`는 공통 `MISSION.id`가 아니라 `CULTURE_MISSION.id`를 의미한다.

현재 로그인한 사용자의 `userId`와 요청받은 `cultureMissionId`를 함께 사용하여 `CULTURE_MISSION_PROGRESS` 이력을 조회한다.

진행 이력은 상태에 따라 다음 두 종류로 구분한다.

- `IN_PROGRESS`: 현재 이어서 진행할 수 있는 진행도
- `COMPLETED`: 과거에 미션을 완료하고 보상을 받은 진행도

## 2. 처리 순서

1. `cultureMissionId`에 해당하는 `CULTURE_MISSION`을 조회한다.
2. 문화 미션이 존재하면 현재 사용자의 해당 문화 미션 진행 이력을 조회한다.
3. `COMPLETED` 진행도의 존재 여부로 `isRewarded`를 결정한다.
4. `IN_PROGRESS` 진행도가 있으면 기존 진행도를 반환한다.
5. `IN_PROGRESS` 진행도가 없으면 새로운 진행도를 생성하여 반환한다.

## 3. 진행 이력에 따른 분기

| `COMPLETED` 진행도 | `IN_PROGRESS` 진행도 | 처리 | `isRewarded` | Status Code |
| --- | --- | --- | --- | --- |
| 없음 | 없음 | 최초 진행도를 새로 생성 | `false` | `201` |
| 없음 | 있음 | 기존 진행도를 이어서 반환 | `false` | `200` |
| 있음 | 있음 | 기존 진행도를 이어서 반환 | `true` | `200` |
| 있음 | 없음 | 재도전 진행도를 새로 생성 | `true` | `201` |

### 3.1 최초 시작

현재 사용자와 문화 미션에 해당하는 진행도가 하나도 없으면 미션을 처음 시작하는 것으로 판단한다.

다음 값으로 `CULTURE_MISSION_PROGRESS`를 생성한다.

- `culture_mission_id`: 요청받은 `cultureMissionId`
- `user_id`: 현재 로그인한 사용자 id
- `mission_status`: `IN_PROGRESS`
- `current_quiz_index`: `1`
- `correct_number`: `0`
- `completed_at`: `null`

새로 생성한 진행도의 id를 `cultureMissionProgressId`로 반환하고, `isRewarded`는 `false`로 반환한다.

### 3.2 최초 도전 이어하기

`COMPLETED` 진행도는 없지만 `IN_PROGRESS` 진행도가 있으면 기존 진행도를 이어서 한다.

새로운 진행도를 생성하지 않고 기존 진행도의 다음 정보를 사용한다.

- `cultureMissionProgressId`: 기존 `IN_PROGRESS` 진행도의 id
- `currentQuizNumber`: 기존 진행도의 `current_quiz_index`
- `isRewarded`: `false`

### 3.3 보상을 받은 미션 이어하기

`COMPLETED` 진행도와 `IN_PROGRESS` 진행도가 모두 있으면 과거에 보상을 받은 후 다시 도전 중인 상태이다.

새로운 진행도를 생성하지 않고 기존 `IN_PROGRESS` 진행도를 반환한다.

- `cultureMissionProgressId`: 기존 `IN_PROGRESS` 진행도의 id
- `currentQuizNumber`: 기존 진행도의 `current_quiz_index`
- `isRewarded`: `true`

### 3.4 보상을 받은 미션 다시 시작하기

`COMPLETED` 진행도는 있지만 `IN_PROGRESS` 진행도가 없으면 과거에 완료한 미션을 다시 시작하는 것으로 판단한다.

기존 `COMPLETED` 진행도는 변경하거나 삭제하지 않고, 최초 시작과 동일한 초기값으로 새로운 `IN_PROGRESS` 진행도를 생성한다.

- `cultureMissionProgressId`: 새로 생성된 진행도의 id
- `currentQuizNumber`: `1`
- `isRewarded`: `true`

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

## 5. 보상 여부

`isRewarded`는 현재 진행도의 완료 여부가 아니라, 현재 사용자가 해당 문화 미션을 과거에 한 번이라도 완료하여 보상을 받은 적이 있는지를 나타낸다.

현재 사용자와 문화 미션에 해당하는 `COMPLETED` 진행도가 하나 이상 존재하면 `true`, 하나도 없으면 `false`이다.

서비스 정책상 `COMPLETED` 진행도가 존재하면 해당 문화 미션의 보상을 이미 받은 것으로 간주한다. 다만 문화 미션 진행도 저장 API는 보상을 직접 지급하지 않고 진행도 상태만 `COMPLETED`로 변경한다.

재도전 진행도를 완료하더라도 `isRewarded=true`이면 동일한 미션 보상을 다시 지급하지 않는다.

## 6. 진행도 생성 제한

동일한 사용자와 동일한 문화 미션에는 이어서 사용할 `IN_PROGRESS` 진행도가 최대 하나만 존재해야 한다.

기존 `IN_PROGRESS` 진행도가 있으면 시작 API를 다시 호출하더라도 새로운 진행도를 만들지 않고 기존 진행도를 반환한다.

## 7. 응답 데이터 구성

- `cultureMissionProgressId`: 반환 대상인 신규 또는 기존 `IN_PROGRESS` 진행도의 id
- `quizCount`: `CULTURE_MISSION.quiz_total_count`
- `currentQuizNumber`: 반환 대상 진행도의 `current_quiz_index`
- `isRewarded`: `COMPLETED` 진행도 존재 여부
- `quizDetails`: `CULTURE_MISSION.quiz_detail`을 `quizIndex` 오름차순으로 정렬한 목록
- `rewardDetail`: `CULTURE_MISSION.reward_detail`과 연결된 AR 캐릭터 정보

## 8. 오류 응답

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

이 API는 문화 미션 진행도만 완료 처리하며, 포인트·쿠폰·AR 캐릭터 등의 보상은 지급하지 않는다.

## 6. 다음 장소 추천

다음 장소 추천은 문화 미션 진행도 저장 로직 안에 직접 작성하지 않고 별도 함수로 분리한다.

현재는 실제 추천 기준이 정해지지 않았으므로 `LOCATION` 테이블에 존재하는 장소 중 하나를 무작위로 선택한다. 추후 추천 기준이 확정되면 별도 함수 내부의 무작위 선택 로직을 실제 추천 로직으로 교체한다.

진행 중인 응답에서는 장소를 추천하지 않고 `nextLocation`을 `null`로 반환한다. 마지막 퀴즈를 제출하여 미션을 완료한 경우에만 다음 장소를 조회한다.

추천할 수 있는 장소가 없으면 `nextLocation`은 `null`로 반환한다.

장소 정보는 다음 기준으로 조합한다.

- `nextLocation.id`: `LOCATION.id`
- `nextLocation.locationTitle`: `LOCATION.location_title`
- `nextLocation.locationImageUrl`: `LOCATION.content_id`를 사용하여 TourAPI에서 조회한 장소 이미지 URL
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
- `nextLocation`: 진행 중이면 `null`, 완료하면 거리 정보를 포함한 다음 장소 추천 결과

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
