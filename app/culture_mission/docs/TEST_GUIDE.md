# 문화 미션 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `POST /api/v1/culture-missions/{cultureMissionId}/progress` (문화 미션 시작/이어하기) | `app/culture_mission/tests/test_start_culture_mission.py` |

## 테스트 의도

이 API는 **같은 요청이 상황에 따라 전혀 다르게 동작한다.** 진행 이력에 따라
새 진행도를 만들 수도, 기존 진행도를 그대로 돌려줄 수도 있고 상태 코드도 201 / 200으로 갈린다.
그래서 테스트의 중심은 BUSINESS_RULES 3번의 **분기표 네 줄을 그대로 재현**하는 것이다.

| `COMPLETED` | `IN_PROGRESS` | 처리 | `isRewarded` | Status |
| --- | --- | --- | --- | --- |
| 없음 | 없음 | 새로 생성 | `false` | `201` |
| 없음 | 있음 | 이어서 반환 | `false` | `200` |
| 있음 | 있음 | 이어서 반환 | `true` | `200` |
| 있음 | 없음 | 재도전 생성 | `true` | `201` |

특히 헷갈리기 쉬운 두 가지를 **응답만이 아니라 DB 상태까지** 확인한다.

- 이어서 하는 경우에 **진행도가 늘어나지 않는지** (같은 미션에 `IN_PROGRESS` 는 최대 하나)
- 재도전으로 새로 만들 때 **기존 `COMPLETED` 기록이 그대로 남는지** (덮어쓰거나 지우면 안 된다)

`isRewarded` 는 "지금 진행도가 완료됐는지"가 아니라 "과거에 이 미션을 완료한 적이 있는지"라서,
사용자/미션이 다른 완료 기록에 오염되지 않는지도 따로 본다.

## 주요 검증 항목

### 1. 응답 형식

- 처음 시작하면 201로 응답하고, 응답 전체가 명세와 정확히 일치한다.
  (`cultureMissionProgressId`, `quizCount`, `currentQuizNumber`, `isRewarded`,
  `quizDetails`, `rewardDetail` / camelCase 확인)
- `quizDetails` 는 `quizIndex` 오름차순으로 반환한다.
  (목업은 3 → 1 → 2 순서로 저장해 두어, 정렬을 빠뜨리면 바로 드러난다)
- 주관식 문제는 `options` 가 `null`, 이미지가 없는 문제는 `imgUrl` 이 `null` 이다.

### 2. 진행 이력에 따른 분기

- **이력 없음** → 201, 새 진행도 1건 생성. DB에 `IN_PROGRESS` / `current_quiz_index=1` /
  `correct_number=0` / `completed_at=null` 로 저장된다.
- **진행 중 있음** → 200, 진행도 개수 그대로, 기존 진행도의 `current_quiz_index` 를 반환한다.
- **완료 + 진행 중** → 200, `isRewarded=true`, 진행도 개수 그대로.
- **완료만 있음** → 201, `currentQuizNumber=1`, `isRewarded=true`,
  기존 완료 기록(`current_quiz_index` / `correct_number`)은 변경되지 않는다.
- 시작 API를 **연속 두 번 호출**하면 첫 번째는 201, 두 번째는 200이고
  같은 진행도 id를 반환하며 진행도는 하나만 남는다.

### 3. 사용자 / 미션 구분

- 다른 사용자의 `IN_PROGRESS` 진행도는 이어받지 않고 새로 만든다.
- 다른 문화 미션의 `COMPLETED` 기록은 `isRewarded` 를 `true` 로 만들지 않는다.

### 4. 오류

- 문화 미션이 없으면 **404 `CULTURE_MISSION_NOT_FOUND`**.
  이때 **진행도를 만들지 않는다**는 것도 함께 확인한다. (조회 실패인데 데이터가 생기면 안 된다)
- `cultureMissionId` 가 정수가 아니거나 1보다 작으면 **400 `INVALID_REQUEST`**.

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
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고,
캐릭터/공통 미션/문화 미션/사용자 목업 데이터는 각 테스트의 `culture_mission_data` 픽스처에서 만든다.
진행 이력은 테스트마다 조합이 달라서 `_add_progress()` 헬퍼로 각 테스트에서 직접 만든다.
