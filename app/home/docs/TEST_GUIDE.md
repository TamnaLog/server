# 홈 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `GET /api/v1/users/me/home` (홈 조회) | `app/home/tests/test_get_home.py` |

## 테스트 의도

홈 조회는 하나의 API가 서로 성격이 다른 네 가지를 한 번에 모아 준다.

1. 추천 미션 목록
2. 진행 중인 미션 목록 (문화 / 보물 찾기 / 협동)
3. 서비스에 쌓인 방명록 개수
4. 사용자에게 배정된 AR 캐릭터 이미지

그래서 테스트는 **네 덩어리를 각각 따로** 검증한다. 한 덩어리가 비어 있어도 나머지는 정상적으로 나와야 하고,
특히 사용자 데이터가 아예 없어도 500이 아니라 200으로 응답해야 한다. (명세에 오류 응답이 정의돼 있지 않다)

추천 미션 선정(`mission_recommender.py`)과 방명록 집계(`guestbook_counter.py`)는 기획이 확정되지 않아
각각 랜덤 / 전체 합산으로 구현돼 있다. 그래서 추천 결과는 **어떤 미션이 뽑혔는지**가 아니라
**DB에 존재하는 미션 중 하나가 중복 없이 뽑혔는지**로 검증한다.
추천 기준이 실제 로직으로 바뀌어도 이 테스트는 그대로 쓸 수 있다.

또 하나 중요한 축이 **미션 id를 어디서 가져오는지**다.
`MISSION` 은 유형/이름/단계만 갖는 분류 테이블이고, 실제 미션 한 건은 미션 유형별 테이블의 행이다.
그래서 응답의 `missionId` 는 `MISSION.id` 가 아니라 **유형별 테이블의 id** 여야 한다.
목업 데이터는 두 id를 겹치지 않게(분류 1~3, 유형별 11/21/31) 잡아서 잘못된 id가 나가면 바로 드러나게 했다.

거리·예상 소요 시간은 기대값을 테스트에 직접 적지 않고 `app/common/distance.py` 의 계산 함수로 검증한다.
좌표를 `lat`(위도) ↔ `lng`(경도) 순으로 잘못 넘기는 실수를 잡기 위해서다.
(DB는 `mx` = 경도, `my` = 위도로 저장하는데 응답은 `lat` / `lng` 라서 뒤집히기 쉽다)

## 주요 검증 항목

### 1. 응답 형식

- 200으로 응답한다.
- 최상위 필드는 `missionRecommend`, `progressMission`, `guestbookCount`, `characterImgUrl` 네 개다.
- 추천 미션 항목은 `missionId`, `missionType`, `missionTitle`, `locationTitle`, `location`,
  `distanceMeter`, `durationMinutes` 로 이루어진다.
- 진행 중 미션 항목은 추천 미션과 달리 `location` 대신 `totalStep`, `currentStep` 을 가진다. (camelCase 명세 확인)

### 2. 추천 미션

- `missionId` 는 유형별 테이블(CULTURE / COOPERATIVE / TREASURE_MISSION)의 id다.
- `missionType` / `missionTitle` 은 그 행이 속한 `MISSION` 의 값을 따른다.
- 추천된 미션은 모두 DB에 존재하는 미션이고, 같은 미션이 중복되지 않는다.
- 장소가 있는 미션은 `location.lat` / `location.lng` 가 DB의 `my` / `mx` 와 각각 일치하고,
  `distanceMeter` / `durationMinutes` 가 계산 결과와 일치한다.

### 3. 장소가 없는 미션

- 장소는 협동 / 보물 찾기 미션만 가지고, **문화 미션은 장소를 갖지 않는다.**
- 문화 미션은 `locationTitle`, `location`, `distanceMeter`, `durationMinutes` 가 모두 `null` 이다.

### 4. 진행 중인 미션

단계 정보(`totalStep` / `currentStep`)를 미션 유형마다 다른 곳에서 가져오기 때문에(BUSINESS_RULES 5번),
**유형별로 출처를 헷갈리지 않는지**가 이 항목의 핵심이다.
그래서 목업 데이터는 문화 미션의 `quiz_total_count`(5)와 `step_detail` 길이(3)를 **일부러 다르게** 잡아,
문화 미션이 공통 단계 정보를 잘못 쓰면 바로 드러나게 했다.

- **문화 미션**: 퀴즈 진행도를 쓴다. `CULTURE_MISSION.quiz_total_count` → `totalStep`,
  진행도의 `current_quiz_index` → `currentStep`. 장소 관련 필드는 모두 `null`.
- **보물 찾기 미션**: 공통 단계 정보를 쓴다. `MISSION.step_detail` 항목 개수 → `totalStep`,
  진행도의 `current_step` → `currentStep`. (단계는 1 | 2 | 3 이고 3이 완료 단계)
- **협동 미션**: 진행도 테이블에 `user_id` 가 없으므로 **참여자(`COOPERATIVE_MISSION_PARTICIPANT`)를 통해**
  현재 사용자의 방을 찾아야 한다. 단계 정보는 보물 찾기와 같이 공통 단계 정보를 쓴다.
- 세 유형의 진행 중 미션이 있으면 세 건이 모두 한 목록에 나온다.
- 완료된(`COMPLETED`) 미션과 **다른 사용자**의 진행 중 미션은 목록에 포함되지 않는다.
  (상태 필터와 사용자 필터가 둘 다 걸려 있는지 확인)

### 5. 방명록 개수

- 현재 사용자 것만이 아니라 **다른 사용자가 쓴 방명록도 포함**한다. (서비스에 쌓인 전체 수)
- 일반 방명록과 길 위의 방명록을 합산한다.
- `deleted_at` 이 있는 방명록은 제외한다.

### 6. 캐릭터 이미지

- 배정된 AR 캐릭터가 있으면 그 캐릭터의 이미지 URL이 나간다.
- 배정된 캐릭터가 없으면 `characterImgUrl` 은 `null` 이다.

### 7. 사용자 데이터가 없는 경우

- 로그인 전이라 사용자 id는 항상 1로 고정되는데, 해당 사용자 행이 없어도 200으로 응답한다.
  이때 `characterImgUrl` 은 `null`, `progressMission` 은 빈 배열이다.

### 8. 잘못된 요청

- `latitude` / `longitude` 가 없거나, 숫자가 아니거나, 범위를 벗어나면
  **400 `INVALID_REQUEST`** 로 응답한다.
  (FastAPI 기본 422가 아니라 공통 에러 형식 `{ "code": ... }` 으로 나가는지 확인)

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 홈 도메인만
pytest app/home

# 특정 테스트만
pytest app/home/tests/test_get_home.py -k 협동
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고, 장소/미션/사용자 목업 데이터는
각 테스트의 `home_data` 픽스처에서 만든다. 미션은 유형별로 1건씩만 둬서(추천 개수와 같음)
랜덤 추천이어도 세 건이 항상 모두 추천되게 했다.
진행도와 방명록은 검증할 내용이 테스트마다 달라서 `home_data` 에 넣지 않고 각 테스트에서 직접 추가한다.
