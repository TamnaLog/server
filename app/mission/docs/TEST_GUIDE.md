# 미션 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `GET /api/v1/missions/{missionType}/{missionId}` (미션 홈 조회) | `app/mission/tests/test_get_mission_home.py` |

## 테스트 의도

이 API의 핵심은 **미션 하나를 어떻게 특정하느냐**다.

`missionId` 는 공통 `MISSION.id` 가 아니라 유형별 세부 미션 테이블의 id이고,
세 테이블은 각자 auto increment를 쓰기 때문에 **`CULTURE_MISSION.id = 5` 와 `COOPERATIVE_MISSION.id = 5` 가 동시에 존재할 수 있다.**
그래서 `missionType` 없이 id만으로 조회하거나, 요청한 유형에 없다고 다른 유형 테이블을 뒤지면 엉뚱한 미션이 나간다.

목업 데이터는 이 실수를 잡으려고 **문화 미션과 협동 미션에 일부러 같은 id(5)** 를 넣어 두었다.
또 응답의 `id` 가 세부 미션 id인지 확인하려고 공통 미션 id(1~3)와 세부 미션 id(5)를 겹치지 않게 잡았다.

두 번째 축은 **어떤 값을 어디서 가져오는지**다. 한 응답이 세 곳에서 조립된다.

- 유형/제목/설명/단계 → 연결된 공통 `MISSION`
- 보상 → **유형별 세부 미션의 `reward_detail`** (같은 유형이어도 세부 미션마다 다를 수 있다)
- 보상 캐릭터 → `AR_CHARACTER`

그래서 보상은 유형이 같고 공통 미션이 같아도 세부 미션마다 다른 값이 나오는지를 따로 검증한다.

## 주요 검증 항목

### 1. 정상 조회

- 200으로 응답한다.
- 응답 전체가 명세와 정확히 일치한다. (`id`, `missionType`, `missionTitle`, `description`,
  `rewardDetail`, `steps` / camelCase 확인)
- 응답의 `id` 는 공통 미션 id가 아니라 세부 미션 id다.

### 2. 미션 특정

- 같은 id(5)를 가진 문화 미션과 협동 미션이 둘 다 있을 때, **요청한 유형의 미션만** 반환한다.
- 단계 목록은 `step` 오름차순으로 반환한다.
  (목업은 3 → 1 → 2 순서로 저장해 두어, 정렬을 빠뜨리면 바로 드러난다)

### 3. 보상 정보

- 보상은 공통 미션이 아니라 세부 미션의 `reward_detail` 에서 온다.
  (문화 100p / 협동 200p 로 다르게 두고 확인)
- 캐릭터 보상이 없으면 `arCharacter` 는 `null`, 쿠폰 보상이 없으면 `coupon` 은 `null`.
- 포인트 보상이 없으면 `point` 는 `0`.

### 4. 404 `MISSION_NOT_FOUND`

- 요청한 유형의 세부 미션에 그 id가 없는 경우
- **다른 유형에만 그 id가 존재하는 경우** (그 유형으로 조회하면 200이 나오는 것까지 같이 확인해서,
  "데이터가 아예 없어서" 404가 난 게 아님을 분명히 한다)
- 세부 미션이 참조하는 공통 미션의 유형이 요청 유형과 다른 경우 (잘못 연결된 데이터)

### 5. 400 `INVALID_REQUEST`

- `missionType` 이 `CULTURE` / `COOPERATIVE` / `TREASURE` 가 아닌 경우 (소문자 포함)
- `missionId` 가 정수가 아니거나 1보다 작은 경우

유효하지 않은 `missionType` 은 존재 여부를 조회할 수조차 없으므로 **404가 아니라 400**이어야 한다.
이 구분이 비즈니스 룰의 명시적 요구라서 테스트로 고정해 둔다.

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 미션 도메인만
pytest app/mission

# 특정 테스트만
pytest app/mission/tests/test_get_mission_home.py -k 유형
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고,
장소/캐릭터/공통 미션/세부 미션 목업 데이터는 각 테스트의 `mission_data` 픽스처에서 만든다.
검증 대상이 테스트마다 다른 보물찾기 미션과 잘못 연결된 데이터는 각 테스트에서 직접 추가한다.
