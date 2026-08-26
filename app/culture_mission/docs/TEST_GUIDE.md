# 문화 미션 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `POST /api/v1/culture-missions/{cultureMissionId}/progress` (문화 미션 시작/이어하기) | `app/culture_mission/tests/test_start_culture_mission.py` |
| `PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress` (문화 미션 진행도 저장) | `app/culture_mission/tests/test_save_culture_mission_progress.py` |
| `PATCH /api/v1/culture-missions/{cultureMissionProgressId}/progress/stop` (문화 미션 중단) | `app/culture_mission/tests/test_stop_culture_mission_progress.py` |

## 시작/이어하기 테스트 의도

이 API는 **같은 요청이 상황에 따라 전혀 다르게 동작한다.** 진행 이력에 따라
새 진행도를 만들 수도, 기존 진행도를 그대로 돌려줄 수도 있고 상태 코드도 201 / 200으로 갈린다.
그래서 테스트의 중심은 BUSINESS_RULES 3번의 **분기표 네 줄을 그대로 재현**하는 것이다.

| `COMPLETED` | `IN_PROGRESS` | 처리 | Status |
| --- | --- | --- | --- |
| 없음 | 없음 | 새로 생성 | `201` |
| 없음 | 있음 | 이어서 반환 | `200` |
| 있음 | 있음 | 이어서 반환 | `200` |
| 있음 | 없음 | 재도전 생성 | `201` |

특히 헷갈리기 쉬운 두 가지를 **응답만이 아니라 DB 상태까지** 확인한다.

- 이어서 하는 경우에 **진행도가 늘어나지 않는지** (같은 미션에 `IN_PROGRESS` 는 최대 하나)
- 재도전으로 새로 만들 때 **기존 `COMPLETED` 기록이 그대로 남는지** (덮어쓰거나 지우면 안 된다)

### 주요 검증 항목

#### 1. 응답 형식

- 처음 시작하면 201로 응답하고, 응답 전체가 명세와 정확히 일치한다.
  (`cultureMissionProgressId`, `quizCount`, `currentQuizNumber`, `quizDetails` / camelCase 확인)
- `quizDetails` 는 `quizIndex` 오름차순으로 반환한다.
  (목업은 3 → 1 → 2 순서로 저장해 두어, 정렬을 빠뜨리면 바로 드러난다)
- 주관식 문제는 `options` 가 `null`, 이미지가 없는 문제는 `imgUrl` 이 `null` 이다.

#### 2. 진행 이력에 따른 분기

- **이력 없음** → 201, 새 진행도 1건 생성. DB에 `IN_PROGRESS` / `current_quiz_index=1` /
  `correct_number=0` / `completed_at=null` 로 저장된다.
- **진행 중 있음** → 200, 진행도 개수 그대로, 기존 진행도의 `current_quiz_index` 를 반환한다.
- **완료 + 진행 중** → 200, 진행도 개수 그대로.
- **완료만 있음** → 201, `currentQuizNumber=1`,
  기존 완료 기록(`current_quiz_index` / `correct_number`)은 변경되지 않는다.
- 시작 API를 **연속 두 번 호출**하면 첫 번째는 201, 두 번째는 200이고
  같은 진행도 id를 반환하며 진행도는 하나만 남는다.

#### 3. 사용자 / 미션 구분

- 다른 사용자의 `IN_PROGRESS` 진행도는 이어받지 않고 새로 만든다.
- 다른 문화 미션의 `COMPLETED` 기록은 현재 문화 미션의 재도전 판단에 영향을 주지 않는다.

#### 4. 오류

- 문화 미션이 없으면 **404 `CULTURE_MISSION_NOT_FOUND`**.
  이때 **진행도를 만들지 않는다**는 것도 함께 확인한다. (조회 실패인데 데이터가 생기면 안 된다)
- `cultureMissionId` 가 정수가 아니거나 1보다 작으면 **400 `INVALID_REQUEST`**.

## 진행도 저장 테스트 의도

이 API는 **퀴즈 하나를 제출할 때마다 진행도를 바꾸는** API라, 잘못 동작하면 사용자의 기록이 틀어진다.
그래서 테스트는 응답만 보지 않고 **DB에 저장된 값까지 매번 확인**한다.

가장 헷갈리는 지점은 **마지막 퀴즈의 처리**다.
진행 중이면 퀴즈 번호를 1 올리지만, 마지막 퀴즈는 번호를 **올리지 않고** 완료로 바꾼다.
그래서 목업의 전체 퀴즈 수를 3으로 두고 1→2번(진행 중), 3번(완료)을 나눠서 검증한다.

보상 지급도 같은 맥락이다. 완료 처리와 보상 지급이 한 트랜잭션이어야 하고,
재도전으로 두 번째 완료를 하더라도 이미 지급된 보상 항목은 다시 지급되면 안 된다.

또 하나는 **중복 요청 방어**다. 완료 응답을 못 받아 같은 요청이 다시 들어와도
정답 수가 두 번 반영되면 안 되므로, 완료된 진행도는 404로 처리되고 값이 그대로인지 확인한다.

다음 장소 추천(`app/common/next_location.py`)은 아직 랜덤이라
**어떤 장소가 뽑혔는지**가 아니라 **DB에 있는 장소/연결 미션인지**로 검증한다.
장소 이미지 URL은 TourAPI에서 가져오므로, 테스트가 외부 네트워크를 타지 않도록
`stub_location_image` 픽스처(autouse)로 조회 함수를 대체한다.

### 주요 검증 항목

#### 1. 진행 중 처리

- 마지막 퀴즈가 아니면 `current_quiz_index` 를 1 올리고 `IN_PROGRESS` / `completed_at=null` 을 유지한다.
- `isCorrect=true` 면 정답 수 +1, `false` 면 그대로. (응답과 DB 양쪽 확인)
- 진행 중이면 `nextLocation` 은 `null` 이다.

#### 2. 완료 처리

- 마지막 퀴즈를 제출하면 `missionProgressStatus` 가 `COMPLETED` 로 바뀌고
  **`currentQuizNumber` 는 올라가지 않고 마지막 번호 그대로**다.
- `completed_at` 이 기록된다.
- 마지막 퀴즈의 정답 여부도 정답 수에 반영된다.

#### 3. 다음 장소 추천 (완료 시에만)

- `id` / `locationTitle` 은 DB의 장소 값과 일치한다.
- `distanceMeter` 는 `app/common/distance.py` 의 계산 결과와 일치한다.
  (`my`=위도 / `mx`=경도 순서를 뒤집지 않았는지 확인)
- 장소에 연결된 세부 미션이 없으면 `mission` 은 `null`.
- 연결된 미션이 있으면 **공통 `MISSION.id` 가 아니라 세부 미션 id** 와 유형을 반환한다.
- 여러 미션이 연결돼 있으면 그중 하나가 나온다.
- 완료 응답에서는 `nextLocation` 이 반드시 객체로 내려온다.
- 추천할 장소 데이터가 하나도 없으면 완료 응답을 만들지 않고 **500 `INTERNAL_SERVER_ERROR`** 로 응답하며,
  완료 처리도 저장되지 않는다.
- 이미지 조회에 실패하면 `locationImageUrl` 은 `null` (미션 완료 응답 자체는 성공)

#### 4. 보상 지급과 응답 (완료 시에만)

보상은 사용자 데이터를 실제로 바꾸면서 응답에도 포함되므로 **응답과 DB를 함께 검증**한다.

- 진행 중이면 응답의 `reward` 는 `null` 이고 아무 보상도 지급하지 않는다.
- 완료하면 응답의 `reward` 에 이번 요청으로 실제 지급된 보상만 포함한다.
- 지급되지 않은 항목은 `reward.arCharacter`, `reward.point`, `reward.coupon` 각각 `null` 로 반환한다.
- 완료하면 `USER.point` 가 실제 지급 포인트만큼 늘고 `ACQUIRED_AR_CHARACTER` 에 획득 기록이 생긴다.
- 획득 기록의 `acquired_mission_id` 는 세부 미션 id가 아니라 **공통 `MISSION.id`** 다.
- 같은 사용자와 같은 문화 미션의 모든 진행도 이력을 보고 이미 지급된 보상 항목은 다시 지급하지 않는다.
- 보상은 AR 캐릭터, 포인트, 쿠폰 순서로 지급한다.
- 정답 1개당 보상 항목 1개를 지급하되, 남은 보상 수보다 많이 지급하지 않는다.
- 이번 요청으로 지급한 항목은 현재 진행도의 `ar_character_reward_granted`, `point_reward_granted`, `coupon_reward_granted` 중 해당 컬럼이 `true` 로 저장된다.
- 같은 캐릭터를 다른 미션에서 이미 획득했으면 기록을 또 남기지 않는다. 이때도 **포인트는 지급**된다.
- 쿠폰은 별도 보관 테이블이 없으므로 진행도 지급 여부 컬럼과 응답으로 검증한다.
- 보상 지급 중 오류가 나면 **완료 처리도 저장되지 않는다.** (한 트랜잭션인지 확인)

#### 5. 409 `CULTURE_MISSION_QUIZ_INDEX_MISMATCH`

- 제출한 `quizIndex` 가 현재 퀴즈 번호와 다르면(앞 번호든 뒤 번호든) 409로 응답하고
  **진행도를 전혀 바꾸지 않는다.**

#### 6. 404 `CULTURE_MISSION_PROGRESS_NOT_FOUND`

- 진행도가 없는 경우
- **다른 사용자의 진행도**인 경우 (남의 기록을 바꾸면 안 된다)
- **이미 완료된 진행도**인 경우 (중복 반영 방지)

#### 7. 400 `INVALID_REQUEST`

- 위치(`latitude` / `longitude`) 누락·범위 초과
- `quizIndex` 누락·0 이하·정수 아님
- `isCorrect` 누락·boolean 아님
- 진행도 id가 0 이하이거나 정수가 아님

## 중단 테스트 의도

중단은 **실패가 아니라 완료**다. 그래서 "그만두면 아무 일도 없어야 한다"가 아니라
**진행도 저장의 완료 처리와 같은 결과가 나오는지**를 확인하는 게 핵심이다.

진행도 저장과 다른 점은 두 가지뿐이다.

- 요청으로 `quizIndex` / `isCorrect` 를 받지 않는다. 그래서 **퀴즈 번호와 정답 수를 건드리면 안 된다.**
  (DB에 이미 저장된 값만 사용한다)
- 응답에 `currentQuizNumber` 가 없고, `nextLocation` 과 `reward` 는 **항상 객체**다.
  지급된 보상이 없으면 `reward` 를 `null` 로 두는 게 아니라 내부 항목 3개가 모두 `null` 인 객체다.

보상 계산은 진행도 저장과 같은 모듈(`app/culture_mission/reward_granter.py`)을 쓰므로
계산 규칙 전체를 다시 검증하지는 않고, **저장된 정답 수를 기준으로 지급되는지**와
**과거 이력의 지급분이 제외되는지**를 중심으로 본다.

중복 요청 방어도 같은 맥락이다. 이미 완료된 진행도로 중단을 다시 요청해도
404로 막히고 보상이 두 번 나가지 않아야 한다.

### 주요 검증 항목

#### 1. 중단 처리

- 응답 전체가 명세와 일치한다. (`missionProgressStatus`, `quizCount`, `correctNumber`,
  `nextLocation`, `reward` / camelCase 확인) 응답에 `currentQuizNumber` 는 없다.
- `mission_status` 가 `COMPLETED` 로 바뀌고 `completed_at` 이 기록된다.
- **`current_quiz_index` 와 `correct_number` 는 그대로**다. (중단이 진행 결과를 바꾸면 안 된다)
- 첫 퀴즈를 풀기 전(정답 0개)에 중단해도 완료로 처리한다.

#### 2. 보상 지급

- DB에 저장된 정답 수만큼 AR 캐릭터 → 포인트 → 쿠폰 순서로 지급하고,
  지급한 항목만 진행도의 지급 여부 컬럼이 `true` 로 저장된다.
- 정답이 0개면 아무것도 지급하지 않고 `reward` 항목 3개가 모두 `null` 이다.
- 같은 미션의 과거 진행도에서 이미 지급된 항목은 제외한다.
- 남은 보상보다 정답이 많아도 남은 보상만 지급한다.
- 보상 지급 중 오류가 나면 **완료 처리(상태 변경)도 저장되지 않는다.** (한 트랜잭션인지 확인)

#### 3. 다음 장소 추천

- 연결된 미션이 있으면 **공통 `MISSION.id` 가 아니라 세부 미션 id** 와 유형을 반환한다.
- 이미지 조회에 실패하면 `locationImageUrl` 만 `null` 이고 중단 처리는 정상 완료한다.
- 추천할 장소 데이터가 하나도 없으면 중단 응답을 만들지 않고 **500 `INTERNAL_SERVER_ERROR`**,
  상태 변경도 저장되지 않는다.

#### 4. 404 `CULTURE_MISSION_PROGRESS_NOT_FOUND`

- 진행도가 없는 경우
- **다른 사용자의 진행도**인 경우 (남의 미션을 끝내면 안 된다)
- **이미 완료된 진행도**인 경우. 이때 보상이 다시 지급되지 않는 것도 함께 확인한다.

#### 5. 400 `INVALID_REQUEST`

- 위치(`latitude` / `longitude`) 누락·범위 초과·숫자 아님
- 진행도 id가 0 이하이거나 정수가 아님
- 이 경우 진행도 상태가 그대로인지도 확인한다.

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 문화 미션 도메인만
pytest app/culture_mission

# 특정 테스트만
pytest app/culture_mission/tests/test_start_culture_mission.py -k 재도전
pytest app/culture_mission/tests/test_save_culture_mission_progress.py -k 마지막
pytest app/culture_mission/tests/test_stop_culture_mission_progress.py -k 중단
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고,
캐릭터/공통 미션/문화 미션/사용자 목업 데이터는 각 테스트의 `culture_mission_data` 픽스처에서 만든다.
진행 이력은 테스트마다 조합이 달라서 `_add_progress()` 헬퍼로 각 테스트에서 직접 만든다.
진행도 저장/중단 테스트는 `progress_data` 픽스처로 미션/장소를 만들고, TourAPI 호출은 픽스처로 막는다.
