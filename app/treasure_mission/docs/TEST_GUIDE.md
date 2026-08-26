# 보물찾기 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `POST /api/v1/treasure-missions/{treasureMissionId}/progress` (보물찾기 시작/이어하기) | `app/treasure_mission/tests/test_start_treasure_mission.py` |
| `PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress` (보물찾기 진행도 저장) | `app/treasure_mission/tests/test_save_treasure_mission_progress.py` |
| `PATCH /api/v1/treasure-missions/{treasureMissionProgressId}/progress/stop` (보물찾기 중단) | `app/treasure_mission/tests/test_stop_treasure_mission.py` |
| `POST /api/v1/treasure-missions/pictures-with-character` (AR 캐릭터와 사진 저장) | `app/treasure_mission/tests/test_save_picture_with_character.py` |

## 시작/이어하기 테스트 의도

이 API는 **같은 요청이 상황에 따라 다르게 동작한다.** 진행 이력이 없으면 보물 좌표를 새로 만들어
`201` 로 돌려주고, `IN_PROGRESS` 진행도가 있으면 아무것도 만들지 않고 `200` 으로 기존 진행도를 돌려준다.

그래서 검증의 중심은 두 가지다.

- **좌표를 언제 만드는가.** 좌표는 진행도를 만들 때 딱 한 번 정해진다.
  이어하기 요청에 다른 사용자 위치를 보내도 저장된 좌표가 바뀌면 안 된다.
- **진행도가 몇 개 생기는가.** 같은 사용자/미션에 `IN_PROGRESS` 진행도는 하나뿐이어야 하므로,
  응답만이 아니라 **DB의 진행도 개수와 기존 완료 기록**까지 확인한다.

보물 좌표는 랜덤이라 값 자체를 비교하지 않는다. 대신 BUSINESS_RULES 5번의 두 조건
(장소 중심 등장 반경 안 / 사용자 쪽 반원 안)을 **응답 좌표로 직접 계산해서** 검증한다.
반경은 테스트에서도 숫자를 쓰지 않고 `app/treasure_mission/constants.py` 의 상수를 그대로 참조한다.

### 주요 검증 항목

#### 1. 응답 형식

- 처음 시작하면 201로 응답하고 명세의 필드를 모두 반환한다.
  (`treasureMissionProgressId`, `missionProgressStatus`, `location`, `treasureCount`,
  `treasureItems` / camelCase 확인)
- `location` 은 미션에 연결된 장소의 이름과 좌표다. (`my`=위도 / `mx`=경도를 뒤집지 않았는지 확인)
- `treasureItems` 는 `treasureIndex` 오름차순이고, 신규 진행도는 전부 `isFound=false` 다.
- 보물 표시/인식 반경은 프론트가 관리하므로 응답에 넣지 않는다.

#### 2. 신규 진행도 저장

- `item_detail` 에 좌표가 저장되고 `index` 는 1부터 중복 없이 매겨진다.
- `current_found_item_idx` 는 빈 배열, `mission_status` 는 `IN_PROGRESS`, `completed_at` 은 `null`.
- 저장된 좌표와 응답 좌표가 같다.

#### 3. 보물 좌표 생성 규칙

- 모든 보물은 장소 중심에서 `TREASURE_APPEAR_RADIUS_METER` 안에 있다.
  (`app/common/distance.py` 의 거리 계산으로 확인)
- 모든 보물은 사용자가 있는 쪽 반원에 있다. (장소→사용자 벡터와 장소→보물 벡터의 내적 ≥ 0)
- 사용자 위치가 장소와 같아 방향을 정할 수 없어도 반경 안에 정상 생성된다.
- 생성 개수는 `TREASURE_MISSION.item_total_count` 를 따른다.

#### 4. 이어하기

- `IN_PROGRESS` 진행도가 있으면 200이고 진행도 개수는 그대로다.
- **요청 좌표를 다르게 보내도** 저장된 보물 좌표를 그대로 반환한다. (좌표 재생성 금지)
- `current_found_item_idx` 에 든 index만 `isFound=true` 다.
- 완료 기록만 있으면 재도전으로 201, 새 진행도가 생기고 **기존 완료 기록은 그대로** 남는다.
- 시작 API를 연속 두 번 호출하면 201 → 200이고 같은 진행도 id를 반환한다.

#### 5. 사용자 / 미션 구분

- 다른 사용자의 `IN_PROGRESS` 진행도는 이어받지 않고 새로 만든다.
- 다른 보물찾기 미션의 진행도도 이어받지 않는다.

#### 6. 404 `TREASURE_MISSION_NOT_FOUND`

- 미션이 없으면 404이고, 이때 **진행도를 만들지 않는다.**

#### 7. 400 `INVALID_REQUEST`

- 위치(`latitude` / `longitude`) 누락·범위 초과·숫자 아님
- `treasureMissionId` 가 0 이하이거나 정수가 아님
- 이 경우에도 진행도가 생기지 않는지 확인한다.

## 진행도 저장 테스트 의도

이 API는 **보물 하나를 찾을 때마다 보상 하나를 즉시 지급한다.** 완료 시점에 몰아주지 않기 때문에
"몇 번째 보물이냐"가 아니라 **"지금 남아 있는 보상 중 우선순위가 가장 높은 것"** 이 무엇인지가 핵심이다.
그래서 보물 1·2·3을 순서대로 찾는 흐름을 한 테스트에서 이어 호출해 AR 캐릭터 → 포인트 → 쿠폰이
한 번씩 나가는지 확인한다.

두 번째 축은 **중복 방지**다. 같은 보물을 두 번 저장하거나(409), 재도전에서 같은 보상을 다시 주면 안 된다.
지급 이력은 현재 진행도가 아니라 같은 사용자·미션의 **모든 진행도**를 기준으로 판단하므로,
과거 완료 진행도에 지급 플래그를 세워 두고 이번 요청에서 건너뛰는지 확인한다.

마지막 축은 **완료 처리**다. 마지막 보물을 찾으면 그 요청 하나에서 보상 지급 + 완료 처리 +
다음 장소 추천이 모두 일어난다. 셋 중 하나라도 실패하면 보물 발견까지 롤백돼야 한다.

다음 장소 추천은 문화 미션과 같은 공용 로직(`app/common/next_location.py`)이라 랜덤이다.
그래서 어떤 장소/미션이 뽑혔는지가 아니라 **DB에 있는 값 중 하나인지**로 검증한다.

### 주요 검증 항목

#### 1. 진행 중 처리

- 응답 전체가 명세와 일치한다. (`missionProgressStatus`, `treasureCount`,
  `foundTreasureIndexes`, `nextLocation`, `reward` / camelCase 확인)
- 찾은 보물이 `current_found_item_idx` 에 저장되고 `current_step` 이 `2` 가 된다.
- 진행 중이면 `nextLocation` 은 `null` 이다.
- `foundTreasureIndexes` 는 오름차순으로 반환한다. (나중에 찾은 번호가 앞 번호보다 작아도 정렬)

#### 2. 보상 지급

- 보물을 찾을 때마다 AR 캐릭터 → 포인트 → 쿠폰 순으로 **하나씩** 지급한다.
- 지급한 항목만 진행도의 지급 여부 컬럼이 `true` 가 된다. (나머지는 `false` 유지)
- `reward_detail` 에 없는 보상은 건너뛰고 그다음 보상을 지급한다.
- 과거 진행도에서 이미 지급된 항목은 재도전에서 건너뛴다.
- 보상이 모두 소진됐으면 `reward` 항목 3개가 모두 `null` 이지만, **보물 발견과 진행도 갱신은 정상 처리**된다.
- 이미 보유한 캐릭터면 `ACQUIRED_AR_CHARACTER` 를 또 만들지 않지만 이번 지급은 성립한 것으로 본다.
- `ACQUIRED_AR_CHARACTER.acquired_mission_id` 는 보물찾기 미션 id가 아니라 공통 `MISSION.id` 다.
- 보상 지급 중 오류가 나면 **보물 발견도 저장되지 않는다.** (한 트랜잭션인지 확인)

#### 3. 완료 처리

- 마지막 보물을 찾으면 `COMPLETED` / `current_step=3` / `completed_at` 이 저장된다.
- 완료 응답의 `nextLocation` 은 반드시 객체이고 `distanceMeter` 는
  `app/common/distance.py` 계산 결과와 일치한다. (`my`=위도 / `mx`=경도 순서 확인)
- 완료 요청에서도 남아 있는 보상 하나를 지급한다.
- 이미지 조회에 실패하면 `locationImageUrl` 만 `null` 이고 완료는 정상 처리된다.
- 추천할 장소가 하나도 없으면 완료 응답을 만들지 않고 **500**, 보물 발견도 롤백된다.

#### 4. 404 / 409

- 진행도가 없거나 **다른 사용자의 진행도**이거나 **이미 완료된 진행도**면
  `404 TREASURE_MISSION_PROGRESS_NOT_FOUND` (셋을 구분해서 노출하지 않는다)
- 진행도의 `item_detail` 에 없는 보물 번호면 `404 TREASURE_ITEM_NOT_FOUND`
- 이미 찾은 보물이면 `409 TREASURE_ITEM_ALREADY_FOUND` 이고 보상도 다시 지급되지 않는다.

#### 5. 400 `INVALID_REQUEST`

- `treasureIndex` 누락·0 이하·정수 아님
- 위치(`latitude` / `longitude`) 누락·범위 초과
- 진행도 id가 0 이하이거나 정수가 아님
- 이 경우 진행도가 바뀌지 않는지도 확인한다.

## 중단 테스트 의도

중단은 **실패가 아니라 완료**다. 다만 문화 미션 중단과 달리 **보상을 지급하지 않는다.**
보물찾기 보상은 보물을 찾을 때마다 이미 나갔기 때문이다.
그래서 검증의 중심은 "무엇을 바꾸고 무엇을 그대로 두는가"다.

- 바뀌는 것: `mission_status`(→ `COMPLETED`), `current_step`(→ `3`), `completed_at`
- 그대로 두는 것: `current_found_item_idx`, `item_detail`, 보상 지급 여부 컬럼 3개

응답에도 `reward` 가 없다. 진행도 저장 응답과 헷갈리기 쉬워서 **응답 키에 `reward` 가 없는지**까지 본다.

다음 장소 추천은 진행도 저장의 완료 처리와 같은 공용 로직이라 랜덤이다.
어떤 장소/미션이 뽑혔는지가 아니라 DB에 있는 값 중 하나인지로 검증한다.

### 주요 검증 항목

#### 1. 중단 처리

- 응답 전체가 명세와 일치한다. (`missionProgressStatus`, `treasureCount`,
  `foundTreasureIndexes`, `nextLocation` / camelCase 확인) 응답에 `reward` 는 없다.
- `COMPLETED` / `current_step=3` / `completed_at` 이 저장된다.
- **찾은 보물 목록과 보물 좌표는 그대로**다. (중단이 진행 결과를 바꾸면 안 된다)
- 보물을 하나도 찾지 않은 상태에서도 중단할 수 있다.
- `foundTreasureIndexes` 는 오름차순으로 반환한다.

#### 2. 보상

- 중단으로는 포인트·캐릭터가 추가로 지급되지 않고, 지급 여부 컬럼도 바뀌지 않는다.

#### 3. 다음 장소 추천

- 연결된 미션이 있으면 **공통 `MISSION.id` 가 아니라 세부 미션 id** 와 유형을 반환한다.
- 이미지 조회에 실패하면 `locationImageUrl` 만 `null` 이고 중단은 정상 완료된다.
- 추천할 장소가 하나도 없으면 중단 응답을 만들지 않고 **500**, 완료 처리도 롤백된다.

#### 4. 404 `TREASURE_MISSION_PROGRESS_NOT_FOUND`

- 진행도가 없거나 **다른 사용자의 진행도**이거나 **이미 완료된 진행도**인 경우
  (셋을 구분해서 노출하지 않는다)

#### 5. 400 `INVALID_REQUEST`

- 위치(`latitude` / `longitude`) 누락·범위 초과·숫자 아님
- 진행도 id가 0 이하이거나 정수가 아님
- 이 경우 진행도 상태가 그대로인지도 확인한다.

## AR 캐릭터와 사진 저장 테스트 의도

이 API의 핵심은 **파일을 믿지 않는 것**이다.
파일명 확장자와 multipart 의 Content-Type 은 클라이언트가 마음대로 보낼 수 있으므로,
실제 파일 내용의 시그니처로 형식을 판별하고 저장 확장자도 그 결과로 정한다.
그래서 **"내용은 JPEG인데 파일명·Content-Type 은 PNG"** 같은 요청을 일부러 넣어 검증한다.

두 번째는 **저장소와 DB가 어긋나지 않는 것**이다.
Blob 업로드가 실패하면 DB 행이 생기면 안 되고, 반대로 DB 저장이 실패하면
이미 올라간 Blob 을 지워서 아무도 참조하지 않는 파일이 남지 않아야 한다.

Blob 업로드는 실제 Azure 로 나가면 안 되므로 `uploads` / `deletes` 픽스처로 가로채
**호출 인자까지 기록**한다. 업로드 경로와 확장자를 직접 확인하기 위해서다.

### 주요 검증 항목

#### 1. 정상 저장

- **204** 로 응답하고 응답 본문이 비어 있다.
- `PICTURE_WITH_CHARACTER` 에 로그인 사용자 id / 업로드 URL / 촬영 시각이 저장된다.
  (`takenAt` 은 KST 기준 offset 없는 값 그대로 `saved_at` 에 들어간다)
- 업로드 경로 prefix 가 `ar_character_picture/{userId}` 다.
- 파일 내용은 변환·압축 없이 그대로 올린다.
- 원본 파일명은 blob 이름에 쓰지 않는다.

#### 2. 이미지 형식 판별

- JPEG / PNG / WebP 를 모두 저장하고 각각 `.jpg` / `.png` / `.webp` 로 올린다.
- 파일명·Content-Type 이 실제 형식과 달라도 **실제 형식**을 따른다.
- `.jpeg` 로 보내도 저장 확장자는 `.jpg` 로 통일한다.
- GIF 등 허용하지 않는 형식은 **400** 이고 업로드도 DB 저장도 하지 않는다.

#### 3. 파일 크기

- 빈 파일은 400.
- 10MB 를 초과하면 400이고 업로드하지 않는다.
- 정확히 10MB 는 정상 저장한다. (경계값)

#### 4. 실패 시 되돌리기

- Blob 업로드가 실패하면 DB 행을 만들지 않는다.
- DB 저장이 실패하면 **업로드한 Blob 을 지운다.** (삭제 호출 인자까지 확인)

#### 5. 400 `INVALID_REQUEST`

- `picture` 또는 `takenAt` 누락
- `takenAt` 이 offset 포함(`+09:00`, `Z`)이거나 날짜만 있거나 형식이 아닌 경우

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 보물찾기 도메인만
pytest app/treasure_mission

# 특정 테스트만
pytest app/treasure_mission/tests/test_start_treasure_mission.py -k 반원
pytest app/treasure_mission/tests/test_save_treasure_mission_progress.py -k 보상
pytest app/treasure_mission/tests/test_stop_treasure_mission.py -k 중단
pytest app/treasure_mission/tests/test_save_picture_with_character.py -k 형식
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있고,
공통 미션/장소/보물찾기 미션/사용자 목업은 `treasure_mission_data` 픽스처에서 만든다.
진행 이력은 테스트마다 조합이 달라서 `_add_progress()` 헬퍼로 각 테스트에서 직접 만든다.
진행도 저장/중단 테스트는 `progress_data` 픽스처로 미션/장소/보상 캐릭터를 만들고, TourAPI 호출은 픽스처로 막는다.
사진 저장 테스트는 `uploads` / `deletes` 픽스처로 Blob 호출을 가로채므로 Azure 연결이 없어도 실행된다.
