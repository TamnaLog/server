# 보물찾기 시작/이어하기 비즈니스 룰

## 1. 반경 상수

보물찾기 도메인에서 공통으로 사용하는 반경은 별도 상수 모듈에 정의한다.

```python
TREASURE_APPEAR_RADIUS_METER = 100
TREASURE_DETECTION_RADIUS_METER = 20
```

- `TREASURE_APPEAR_RADIUS_METER`: 미션 장소를 중심으로 보물 좌표를 생성할 수 있는 최대 반경
- `TREASURE_DETECTION_RADIUS_METER`: 사용자가 보물을 발견한 것으로 인식할 수 있는 반경

현재 임시값은 각각 `100m`, `20m`이다. 서비스 로직에 숫자를 직접 작성하지 않고 보물찾기 도메인의 공통 상수를 참조한다.

두 반경은 API 응답으로 반환하지 않는다. 보물찾기 시작/이어하기 API에서는 보물 좌표만 생성하거나 조회한다.

## 2. 요청 기준

- Path의 `treasureMissionId`로 보물찾기 미션을 조회한다.
- Query의 `latitude`, `longitude`로 사용자의 현재 위치를 받는다.
- 위도는 `-90~90`, 경도는 `-180~180` 범위여야 한다.
- 현재 사용자는 공통 사용자 식별 로직으로 조회한다.

사용자 위치는 새로운 진행도를 만들 때 보물 좌표를 생성하는 기준으로 사용한다. 진행 중인 미션을 이어갈 때는 기존에 저장된 보물 좌표를 사용하므로 요청 좌표로 보물 위치를 다시 계산하지 않는다.

## 3. 진행도 조회 기준

현재 사용자와 `treasureMissionId`가 일치하고 `mission_status`가 `IN_PROGRESS`인 진행도를 조회한다.

- `IN_PROGRESS` 진행도가 없으면 새로운 진행도를 생성한다.
- `IN_PROGRESS` 진행도가 있으면 새로운 진행도를 만들지 않고 기존 진행도를 반환한다.
- `COMPLETED` 진행도만 존재하면 재도전으로 판단하여 새로운 진행도를 생성한다.

동일한 사용자와 동일한 보물찾기 미션에 대해 `IN_PROGRESS` 진행도가 동시에 두 개 생성되지 않도록 진행도 조회와 생성을 하나의 트랜잭션 안에서 처리한다.

## 4. 최초 시작 처리

`IN_PROGRESS` 진행도가 없으면 다음 순서로 처리한다.

1. 보물찾기 미션과 해당 미션에 연결된 장소를 조회한다.
2. 사용자 좌표와 장소 좌표를 기준으로 보물 좌표를 생성한다.
3. 생성한 보물 좌표를 진행도의 `item_detail`에 저장한다.
4. `current_found_item_idx`를 빈 배열로 저장한다.
5. `mission_status`를 `IN_PROGRESS`로 저장한다.
6. 생성한 진행도 id와 미션 정보를 `201 Created`로 반환한다.

진행도에 저장하는 `item_detail` 형식은 다음과 같다.

```json
[
  {
    "index": 1,
    "mx": 126.3579,
    "my": 33.3665
  },
  {
    "index": 2,
    "mx": 126.3574,
    "my": 33.3661
  },
  {
    "index": 3,
    "mx": 126.3581,
    "my": 33.3668
  }
]
```

- `index`는 `1`부터 시작하며 중복되지 않는다.
- 생성할 항목 수는 `TREASURE_MISSION.item_total_count`를 따른다.
- `mx`는 경도, `my`는 위도이다.
- 새로 생성된 진행도의 모든 보물은 `isFound: false`로 반환한다.

## 5. 보물 좌표 생성

보물은 장소 중심의 등장 반경 안에서 사용자와 가까운 방향의 반원에 무작위로 배치한다.

1. 장소 좌표를 원의 중심으로 사용한다.
2. 장소 좌표와 사용자 좌표를 연결한 방향 벡터를 구한다.
3. 장소 좌표를 지나면서 해당 방향 벡터에 수직인 직선으로 원을 두 개의 반원으로 나눈다.
4. 두 반원 중 사용자가 존재하는 방향의 반원을 보물 생성 영역으로 선택한다.
5. 선택한 반원 내부에서 `item_total_count`만큼 좌표를 무작위로 생성한다.

장소를 `L`, 사용자를 `U`, 생성 후보 좌표를 `P`라고 할 때 후보 좌표는 다음 조건을 모두 만족해야 한다.

```text
distance(L, P) <= TREASURE_APPEAR_RADIUS_METER
dot(P - L, U - L) >= 0
```

첫 번째 조건은 장소 중심 `100m` 원 안에 있는지를 의미하고, 두 번째 조건은 사용자 방향의 반원에 있는지를 의미한다.

위도와 경도를 그대로 평면 좌표처럼 계산하지 않는다. 좌표 생성 시 미터 단위의 지역 평면 좌표로 변환하여 반원 내부의 점을 생성한 뒤 다시 위도와 경도로 변환한다.

사용자 좌표와 장소 좌표가 사실상 같아 방향 벡터를 정할 수 없는 경우에는 장소 중심의 전체 원 안에서 보물 좌표를 무작위로 생성한다.

생성된 좌표는 진행도 생성 시 한 번만 확정하여 `item_detail`에 저장한다. 이후 이어하기 요청에서는 좌표를 다시 생성하지 않는다.

## 6. 이어하기 처리

`IN_PROGRESS` 진행도가 존재하면 다음과 같이 처리한다.

- 진행도를 새로 생성하지 않는다.
- 진행도의 `item_detail`에 저장된 보물 좌표를 그대로 반환한다.
- `current_found_item_idx`에 포함된 보물 index는 `isFound: true`로 반환한다.
- 포함되지 않은 보물 index는 `isFound: false`로 반환한다.
- 기존 진행도 id와 미션 정보를 `200 OK`로 반환한다.

## 7. 장소 정보 및 응답 조합

신규 시작과 이어하기는 동일한 `_to_response()`와 `_to_mission_location()` 경로로 장소 정보를 조합하여 두 분기에서 필드가 달라지지 않게 한다.

1. `TREASURE_MISSION.location_id`로 연결된 `LOCATION`에서 id, 장소명, 주소와 좌표를 가져온다.
2. `LOCATION.content_id`를 `app.services.kto.get_location_overview()`에 전달하여 TourAPI `detailCommon2.overview`를 조회한다. 이 공통 함수가 HTML 엔티티 변환, 태그 제거와 연속 공백 정리를 담당하므로 보물찾기 서비스에 동일한 정리 코드를 복제하지 않는다.
3. 보물찾기 서비스의 별도 private 함수에서 정리된 설명의 첫 번째 문장만 추출한다. `.`, `!`, `?` 중 가장 먼저 등장한 종결 부호까지 포함하며, 종결 부호가 하나도 없으면 정리된 전체 문자열을 사용한다.
4. 공통 TourAPI 함수가 `None`을 반환하거나 정리 결과가 비어 있으면 장소 한 줄 설명을 `null`로 둔다. 인증키 미설정, 외부 통신 실패 또는 `overview` 부재를 이유로 진행도 생성 트랜잭션이나 이어하기 응답을 실패시키지 않는다.
5. 조회한 설명은 응답에만 사용하고 `LOCATION`이나 진행도 테이블에는 저장하지 않는다.

TourAPI 조회는 진행도 생성 여부와 무관하게 응답 한 건을 조합할 때 한 번만 수행한다. 이어하기에서도 현재 장소 설명을 반환하지만 보물 좌표와 진행도 데이터는 기존 저장값을 그대로 사용한다.

보물 목록은 진행도의 `item_detail`과 `current_found_item_idx`를 조합하고 `treasureIndex` 오름차순으로 정렬한다.

## 8. 오류 응답

### 400 `INVALID_REQUEST`

Path 또는 Query의 형식이나 값이 유효하지 않은 경우 공통 요청 오류로 처리한다.

- `treasureMissionId`가 정수가 아니거나 `1`보다 작은 경우
- `latitude` 또는 `longitude`가 누락되거나 숫자가 아닌 경우
- 위도 또는 경도가 허용 범위를 벗어난 경우

### 404 `TREASURE_MISSION_NOT_FOUND`

`treasureMissionId`에 해당하는 보물찾기 미션이 존재하지 않는 경우 반환한다.

# 보물찾기 진행도 저장 비즈니스 룰

## 1. 요청 기준

사용자가 보물 하나를 찾았을 때 호출한다.

- Path의 `treasureMissionProgressId`로 저장할 보물찾기 진행도를 식별한다.
- Body의 `treasureIndex`로 사용자가 찾은 보물을 식별한다.
- Query의 `latitude`, `longitude`로 사용자의 현재 위치를 받는다.
- 현재 사용자의 `IN_PROGRESS` 상태인 진행도만 갱신할 수 있다.

보물 발견 여부는 프론트에서 판단한다. 백엔드는 사용자 좌표와 보물 좌표 사이의 거리를 계산하여 발견 여부를 다시 검증하지 않고, 유효한 `treasureIndex`가 전달되면 해당 보물을 찾은 것으로 처리한다.

사용자 좌표는 이번 요청으로 미션이 완료될 때 다음 장소를 고르는 기준 좌표이자, 추천된 다음 장소까지의 `distanceMeter`를 계산하는 데 사용한다. 미션이 계속 진행 중이면 다음 장소를 추천하지 않는다.

## 2. 진행도와 보물 검증

다음 조건을 모두 만족하는 진행도를 조회한다.

- `TREASURE_MISSION_PROGRESS.id`가 `treasureMissionProgressId`와 일치한다.
- `user_id`가 현재 사용자 id와 일치한다.
- `mission_status`가 `IN_PROGRESS`이다.

진행도를 조회한 후 `treasureIndex`가 진행도의 `item_detail[].index`에 존재하는지 확인한다.

- 존재하지 않으면 `404 TREASURE_ITEM_NOT_FOUND`를 반환한다.
- 이미 `current_found_item_idx`에 포함되어 있으면 `409 TREASURE_ITEM_ALREADY_FOUND`를 반환한다.
- 유효하고 아직 찾지 않은 보물이면 `current_found_item_idx`에 추가한다.

`current_found_item_idx`는 응답에서 오름차순으로 정렬하여 반환한다.

## 3. 보물 개수와 진행 단계

현재 보물찾기 미션의 보물 개수는 `3개`로 고정한다. `TREASURE_MISSION.item_total_count`와 진행도의 `item_detail`도 3개의 보물을 가져야 한다.

유효한 보물 발견 요청을 반영한 뒤 진행 단계는 다음과 같이 갱신한다.

- 아직 찾지 않은 보물이 남아 있으면 `current_step`을 `2`로 저장하고 `mission_status`는 `IN_PROGRESS`로 유지한다.
- 세 번째 보물까지 모두 찾으면 `current_step`을 `3`으로 저장하고 `mission_status`를 `COMPLETED`로 변경한다.
- 완료 시 `completed_at`을 현재 시각으로 저장한다.

## 4. 보상 지급 기본 규칙

유효한 보물 하나를 새로 찾을 때마다 지급 가능한 보상 항목을 최대 하나 지급한다. 미션 완료 시점까지 보상을 모아서 지급하지 않고 각 보물 발견 요청에서 즉시 지급한다.

지급 우선순위는 다음과 같다.

1. AR 캐릭터
2. 포인트
3. 쿠폰

이미 지급되었거나 `TREASURE_MISSION.reward_detail`에 존재하지 않는 보상은 건너뛰고, 남아 있는 보상 중 우선순위가 가장 높은 항목 하나를 지급한다.

예를 들어 AR 캐릭터 보상이 존재하지 않으면 첫 번째 보물을 찾았을 때 포인트를 지급한다. AR 캐릭터가 이전 요청에서 이미 지급되었다면 다음 보물 발견 요청에서는 포인트를 지급한다.

보상 지급 로직은 진행도 저장 로직에 직접 작성하지 않고 보물찾기 도메인의 별도 모듈 `app/treasure_mission/reward_granter.py`로 분리한다. 응답의 공통 보상 형식은 `app/common/rewards.py`를 사용한다.

## 5. 보상 중복 지급 방지

보상은 같은 사용자와 같은 보물찾기 미션 기준으로 AR 캐릭터, 포인트, 쿠폰을 각각 한 번만 지급할 수 있다.

보물찾기 미션은 재도전할 수 있으므로 현재 진행도만 확인하지 않는다. 같은 사용자와 같은 `treasure_mission_id`를 가진 모든 보물찾기 진행도 이력에서 다음 컬럼을 조회한다.

- `ar_character_reward_granted`
- `point_reward_granted`
- `coupon_reward_granted`

각 컬럼 중 하나라도 `true`인 이력이 있으면 해당 보상 항목은 이전 시도에서 이미 지급된 것으로 판단하고 다시 지급하지 않는다.

이번 요청에서 실제 지급한 보상에 해당하는 현재 진행도의 지급 여부 컬럼만 `true`로 변경한다. 지급하지 않은 보상의 컬럼은 기존 값을 유지한다.

이전 시도에서 세 종류의 보상을 모두 받은 사용자가 같은 미션에 재도전하면, 보물을 새로 찾더라도 추가 보상을 지급하지 않는다. 보물 발견과 진행도 갱신은 정상 처리한다.

## 6. 보상 데이터 반영

실제 보상은 다음 위치에 반영한다.

| 보상 | 저장 방식 |
| --- | --- |
| AR 캐릭터 | `ACQUIRED_AR_CHARACTER`에 획득 기록 추가 |
| 포인트 | `USER.point`에 지급 포인트 누적 |
| 쿠폰 | 별도 보관 테이블이 없으므로 진행도 지급 여부를 기록하고 응답에 쿠폰 정보 반환 |

`ACQUIRED_AR_CHARACTER.acquired_mission_id`에는 `TREASURE_MISSION.id`가 아니라 해당 보물찾기 미션과 연결된 공통 `MISSION.id`를 저장한다.

사용자가 보상 AR 캐릭터를 이미 보유하여 동일한 `(user_id, ar_character_id)` 획득 기록이 존재하면 `ACQUIRED_AR_CHARACTER`에 중복 row를 추가하지 않는다.

이미 보유한 캐릭터인 경우에도 이번 보물 발견 요청의 AR 캐릭터 보상은 지급 처리된 것으로 본다. 현재 진행도의 `ar_character_reward_granted`를 `true`로 변경하고, 응답의 `reward.arCharacter`에는 해당 캐릭터 정보를 반환한다. 이후 같은 보물찾기 미션에서 AR 캐릭터 보상을 다시 지급하지 않는다.

## 7. 진행 중 처리

보물 발견을 반영한 뒤 `current_found_item_idx`의 개수가 `item_total_count`보다 작으면 미션을 계속 진행한다.

- `mission_status`: `IN_PROGRESS` 유지
- `nextLocation`: `null`
- `reward`: 이번 요청에서 실제 지급한 보상만 포함한 객체

첫 번째 보물에서는 지급 가능한 AR 캐릭터, 두 번째 보물에서는 지급 가능한 포인트가 우선 지급된다. 다만 과거 진행도의 지급 이력이나 `reward_detail` 구성에 따라 다른 보상이 지급되거나 모든 보상 항목이 `null`일 수 있다.

## 8. 완료 처리

이번 요청으로 `current_found_item_idx`의 개수가 `item_total_count`와 같아지면 미션을 즉시 완료 처리한다.

- 마지막 보물 index를 `current_found_item_idx`에 저장한다.
- 마지막 보물에 해당하는 지급 가능한 보상 하나를 즉시 지급한다.
- `current_step`을 `3`으로 변경한다.
- `mission_status`를 `COMPLETED`로 변경한다.
- `completed_at`을 현재 시각으로 저장한다.
- 문화 미션 완료 처리와 동일한 방식으로 다음 장소를 추천한다.
- 거리 정보를 포함한 `nextLocation` 객체를 반드시 반환한다.

마지막 보물을 찾았더라도 해당 미션에서 지급 가능한 보상이 남아 있지 않으면 보상을 추가로 지급하지 않는다. 이 경우에도 미션 완료와 다음 장소 추천은 정상 처리한다.

## 9. 다음 장소 추천

다음 장소 추천은 문화 미션 진행도 저장의 완료 처리와 동일한 추천 로직을 사용한다. 보물찾기 전용 추천 로직을 별도로 만들지 않는다.

- 기준 좌표(Query의 `latitude`, `longitude`)에서 직선거리가 가장 가까운 `LOCATION` 하나를 추천한다.
- 방금 보물찾기를 진행한 장소(`TREASURE_MISSION.location_id`)는 추천 대상에서 제외한다.
- 거리가 같으면 `LOCATION.id`가 작은 장소를 추천한다.
- 추천 장소에 연결된 세부 미션이 여러 개면 그중 하나를 무작위로 선택한다.
- 진행 중이면 `nextLocation`은 `null`이다.
- 완료되면 `nextLocation`은 반드시 객체이다.
- Query의 `latitude`, `longitude`에서 추천 장소까지의 직선거리를 계산한다.
- 거리는 `app/common/distance.py`의 `calculate_distance_meter()`를 사용하여 정수 미터 단위로 반환한다.
- 추천 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`이다.
- TourAPI 이미지 조회 실패는 미션 완료 실패로 처리하지 않고 `locationImageUrl`만 `null`로 반환한다.

`LOCATION.my`는 위도, `LOCATION.mx`는 경도이므로 거리 함수에는 다음 순서로 전달한다.

```python
distance.calculate_distance_meter(
    latitude,
    longitude,
    next_location.my,
    next_location.mx,
)
```

## 10. 보상 응답 구성

진행 상태와 관계없이 유효한 보물 발견 요청에는 `reward` 객체를 반환한다. 이번 요청에서 실제 지급한 항목만 값을 채우고 나머지는 `null`로 반환한다.

- `reward.arCharacter`: 이번 요청에서 AR 캐릭터를 지급했으면 캐릭터 정보, 아니면 `null`
- `reward.point`: 이번 요청에서 포인트를 지급했으면 지급 포인트, 아니면 `null`
- `reward.coupon`: 이번 요청에서 쿠폰을 지급했으면 쿠폰 정보, 아니면 `null`

지급 가능한 보상이 없으면 다음과 같이 반환한다.

```json
{
  "reward": {
    "arCharacter": null,
    "point": null,
    "coupon": null
  }
}
```

## 11. 트랜잭션과 동시 요청

다음 처리는 하나의 트랜잭션으로 묶는다.

- 진행도 row 잠금 및 발견 여부 재확인
- `current_found_item_idx` 갱신
- 지급 가능한 보상 조회
- 사용자 보상 데이터 반영
- 현재 진행도의 보상 지급 여부 갱신
- 마지막 보물인 경우 완료 상태와 완료 시각 저장

동일한 진행도에 대한 요청이 동시에 들어오더라도 같은 보물이 두 번 저장되거나 같은 보상이 중복 지급되지 않도록 진행도와 보상 지급 이력을 잠근 상태에서 처리한다.

처리 중 하나라도 실패하면 보물 발견, 보상 지급 및 완료 처리를 모두 롤백한다.

## 12. 완료된 진행도 재요청

이미 `COMPLETED` 상태인 진행도에는 추가 저장을 허용하지 않는다. 현재 사용자의 `IN_PROGRESS` 진행도를 찾지 못한 것으로 처리하여 `404 TREASURE_MISSION_PROGRESS_NOT_FOUND`를 반환한다.

## 13. 응답 데이터 구성

- `missionProgressStatus`: 갱신 후 `mission_status`
- `treasureCount`: `TREASURE_MISSION.item_total_count`. 현재 고정값 `3`
- `foundTreasureIndexes`: 갱신 후 `current_found_item_idx`를 오름차순으로 정렬한 목록
- `nextLocation`: 진행 중이면 `null`, 완료하면 거리 정보를 포함한 다음 장소 추천 결과 객체
- `reward`: 이번 요청에서 실제 지급된 보상 정보. 지급된 보상이 없으면 내부 필드가 모두 `null`인 객체

## 14. 오류 응답

### 400 `INVALID_REQUEST`

요청 Path, Query 또는 Body의 형식이나 값이 유효하지 않은 경우 공통 요청 오류로 처리한다.

- `treasureMissionProgressId`가 정수가 아니거나 `1`보다 작은 경우
- `treasureIndex`가 정수가 아니거나 `1`보다 작은 경우
- `latitude` 또는 `longitude`가 누락되거나 숫자가 아닌 경우
- 위도 또는 경도가 허용 범위를 벗어난 경우

### 404 `TREASURE_MISSION_PROGRESS_NOT_FOUND`

요청한 진행도를 현재 사용자의 진행 중인 보물찾기 진행도로 사용할 수 없는 경우 반환한다.

- `treasureMissionProgressId`에 해당하는 진행도가 없는 경우
- 해당 진행도가 다른 사용자의 진행도인 경우
- 해당 진행도가 이미 `COMPLETED` 상태인 경우

### 404 `TREASURE_ITEM_NOT_FOUND`

요청한 `treasureIndex`가 진행도의 `item_detail[].index`에 존재하지 않는 경우 반환한다.

### 409 `TREASURE_ITEM_ALREADY_FOUND`

요청한 `treasureIndex`가 이미 진행도의 `current_found_item_idx`에 포함되어 있는 경우 반환한다.

# 보물찾기 중단 비즈니스 룰

## 1. 요청 기준

사용자가 진행 중인 보물찾기 미션을 끝까지 수행하지 않고 중단할 때 호출한다.

- Path의 `treasureMissionProgressId`로 중단할 보물찾기 진행도를 식별한다.
- Query의 `latitude`, `longitude`로 사용자의 현재 위치를 받는다.
- 별도의 Request Body는 받지 않는다.
- 현재 사용자의 `IN_PROGRESS` 상태인 진행도만 중단할 수 있다.

사용자 좌표는 다음 장소를 고르는 기준 좌표이자, 추천된 다음 장소까지의 직선거리를 계산하는 데 사용한다.

## 2. 진행도 조회

다음 조건을 모두 만족하는 진행도를 조회한다.

- `TREASURE_MISSION_PROGRESS.id`가 `treasureMissionProgressId`와 일치한다.
- `user_id`가 현재 사용자 id와 일치한다.
- `mission_status`가 `IN_PROGRESS`이다.

조건을 만족하는 진행도가 없으면 `404 TREASURE_MISSION_PROGRESS_NOT_FOUND`를 반환한다.

## 3. 즉시 완료 처리

유효한 진행도를 조회하면 찾지 않은 보물이 남아 있어도 즉시 완료 처리한다.

- `mission_status`를 `COMPLETED`로 변경한다.
- `current_step`을 `3`으로 변경한다.
- `completed_at`을 중단 처리 시각으로 저장한다.
- `item_detail`은 변경하지 않는다.
- `current_found_item_idx`는 중단 시점의 값을 그대로 유지한다.
- 보상 지급 여부 컬럼은 변경하지 않는다.

중단 요청에서는 보물을 새로 발견한 것으로 처리하지 않으며, 보상을 추가로 지급하지 않는다. 보상 관련 데이터도 응답에 포함하지 않는다.

## 4. 다음 장소 추천

다음 장소 추천은 보물찾기 진행도 저장 API의 완료 처리에서 사용하는 기존 로직을 그대로 사용한다. 중단 전용 추천 로직을 별도로 만들지 않는다.

- 기준 좌표(Query의 `latitude`, `longitude`)에서 직선거리가 가장 가까운 `LOCATION` 하나를 추천한다.
- 중단한 보물찾기의 장소(`TREASURE_MISSION.location_id`)는 추천 대상에서 제외한다.
- 거리가 같으면 `LOCATION.id`가 작은 장소를 추천한다.
- 추천 장소에 연결된 세부 미션이 여러 개면 그중 하나를 무작위로 선택한다.
- 중단은 완료 처리이므로 `nextLocation`은 항상 객체로 반환한다.
- Query의 `latitude`, `longitude`에서 추천 장소까지의 직선거리를 계산한다.
- 거리는 `app/common/distance.py`의 `calculate_distance_meter()`를 사용하여 정수 미터 단위로 반환한다.
- 추천 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.
- TourAPI 이미지 조회 실패는 중단 실패로 처리하지 않고 `nextLocation.locationImageUrl`만 `null`로 반환한다.

`LOCATION.my`는 위도, `LOCATION.mx`는 경도이므로 거리 함수에는 다음 순서로 전달한다.

```python
distance.calculate_distance_meter(
    latitude,
    longitude,
    next_location.my,
    next_location.mx,
)
```

## 5. 처리 순서와 트랜잭션

1. Path와 Query 값을 검증한다.
2. 현재 사용자의 `IN_PROGRESS` 진행도를 잠금 조회한다.
3. 진행도를 즉시 `COMPLETED`로 변경한다.
4. 기존 다음 장소 추천 로직을 호출하고 거리 정보를 계산한다.
5. 완료 상태와 완료 시각을 저장한 뒤 응답을 반환한다.

동일한 진행도에 중단 요청과 보물 발견 요청이 동시에 들어오더라도 완료된 진행도가 다시 갱신되지 않도록 진행도 row를 잠근 상태에서 처리한다.

## 6. 응답 데이터 구성

- `missionProgressStatus`: 항상 `COMPLETED`
- `treasureCount`: `TREASURE_MISSION.item_total_count`. 현재 고정값 `3`
- `foundTreasureIndexes`: 중단 시점의 `current_found_item_idx`를 오름차순으로 정렬한 목록
- `nextLocation`: 거리 정보를 포함한 다음 장소 추천 결과 객체

응답에는 `reward`와 `rewardDetail`을 포함하지 않는다.

## 7. 오류 응답

### 400 `INVALID_REQUEST`

요청 Path 또는 Query의 형식이나 값이 유효하지 않은 경우 공통 요청 오류로 처리한다.

- `treasureMissionProgressId`가 정수가 아니거나 `1`보다 작은 경우
- `latitude` 또는 `longitude`가 누락되거나 숫자가 아닌 경우
- 위도 또는 경도가 허용 범위를 벗어난 경우

### 404 `TREASURE_MISSION_PROGRESS_NOT_FOUND`

요청한 진행도를 현재 사용자의 진행 중인 보물찾기 진행도로 사용할 수 없는 경우 반환한다.

- `treasureMissionProgressId`에 해당하는 진행도가 존재하지 않는 경우
- 해당 진행도가 다른 사용자의 진행도인 경우
- 해당 진행도가 이미 `COMPLETED` 상태인 경우

이미 완료된 진행도도 별도의 완료 오류로 구분하지 않고 `404 TREASURE_MISSION_PROGRESS_NOT_FOUND`로 처리한다.

# AR 캐릭터와 사진 저장 비즈니스 룰

## 1. 요청 기준

프론트는 `multipart/form-data`로 다음 두 필드를 전송한다.

- `picture`: AR 캐릭터와 함께 촬영한 사진 파일
- `takenAt`: 사진 촬영 시각

백엔드는 사진의 AR 캐릭터 합성 여부나 촬영 내용을 별도로 검증하지 않는다. 전달받은 사진 파일을 저장하고 촬영 시각과 로그인한 사용자 정보를 DB에 기록한다.

## 2. 허용 이미지 형식

다음 이미지 형식만 허용한다.

| 실제 이미지 형식 | 허용 Content-Type | 저장 확장자 |
| --- | --- | --- |
| JPEG | `image/jpeg` | `.jpg` |
| PNG | `image/png` | `.png` |
| WebP | `image/webp` | `.webp` |

`.jpeg` 확장자로 전달된 JPEG 파일도 저장할 때는 `.jpg`로 통일한다.

GIF, BMP, TIFF, SVG, HEIC, HEIF 등은 허용하지 않는다. 특히 모바일에서 HEIC/HEIF로 촬영된 사진은 프론트에서 JPEG로 변환한 후 전송한다.

파일명 확장자나 multipart의 Content-Type만 신뢰하지 않고 실제 파일 내용의 이미지 형식을 확인한다. 실제 형식과 파일명 또는 Content-Type이 다르면 실제 형식을 기준으로 검증하고 저장 확장자를 결정한다.

서버는 허용된 이미지의 크기 조절, 압축, 화질 변경 또는 포맷 변환을 하지 않고 전달받은 파일 내용을 그대로 저장한다.

## 3. 파일 크기

사진 파일의 최대 크기는 10MB이다.

- 파일이 비어 있으면 `400 INVALID_REQUEST`
- 파일이 10MB를 초과하면 `400 INVALID_REQUEST`

파일 전체를 메모리에 무제한으로 읽은 다음 크기를 확인하지 않는다. 업로드 데이터를 읽는 과정에서 10MB를 초과하면 즉시 중단하도록 구현한다.

## 4. Blob 저장 위치

사진은 App Service 또는 Docker 컨테이너의 로컬 파일 시스템에 저장하지 않는다. 컨테이너 로컬 디스크는 재시작이나 재배포 시 유지되지 않을 수 있으므로 Azure Blob Storage에 저장한다.

Azure Blob 컨테이너는 환경 변수 `AZURE_STORAGE_CONTAINER`에 설정된 값을 사용한다.

Blob 이름은 다음 형식으로 생성한다.

```text
ar_character_picture/{userId}/{uuid}.{extension}
```

예시:

```text
ar_character_picture/1/550e8400e29b41d4a716446655440000.jpg
```

저장 경로의 최상위 디렉터리 역할을 하는 prefix는 항상 `ar_character_picture/`로 고정한다. 사용자별 파일을 구분하기 위해 그 아래에 로그인한 사용자 id를 사용한다.

원본 파일명은 Blob 이름에 포함하지 않는다. 서버가 생성한 UUID를 사용하여 파일명 충돌과 원본 파일명을 통한 경로 조작을 방지한다.

구현에서는 공통 Blob 업로드 모듈 `app/services/blob_storage.py`의 `upload_file()`을 사용하고 다음 prefix를 전달한다.

```python
prefix = f"ar_character_picture/{current_user_id}"
```

## 5. DB 저장

Blob 업로드가 완료되면 `PICTURE_WITH_CHARACTER`에 다음 값을 저장한다.

| 컬럼 | 저장값 |
| --- | --- |
| `user_id` | 현재 로그인한 사용자 id |
| `picture_url` | 업로드된 Blob의 접근 URL |
| `saved_at` | 요청의 `takenAt` |

`takenAt`은 KST 기준 offset 없는 ISO 8601 형식으로 전달받아 `saved_at`에 저장한다.

## 6. 처리 순서

1. 로그인한 사용자 정보를 확인한다.
2. `picture`와 `takenAt`의 존재 여부와 형식을 검증한다.
3. 사진 크기가 10MB 이하인지 확인한다.
4. 실제 이미지 형식이 JPEG, PNG, WebP 중 하나인지 확인한다.
5. 실제 이미지 형식에 맞는 확장자와 UUID로 Blob 이름을 생성한다.
6. Azure Blob Storage의 `ar_character_picture/{userId}/` 아래에 사진을 업로드한다.
7. 업로드된 Blob URL과 촬영 시각을 `PICTURE_WITH_CHARACTER`에 저장한다.
8. 정상적으로 저장되면 응답 Body 없이 `204 No Content`를 반환한다.

Blob 업로드에 실패하면 DB 데이터를 생성하지 않는다. Blob 업로드는 성공했지만 DB 저장이 실패하면 업로드된 Blob을 삭제하여 DB에서 참조하지 않는 파일이 남지 않도록 한다.

## 7. 오류 응답

### 400 `INVALID_REQUEST`

사진 저장 요청의 모든 검증 실패는 공통 요청 오류인 `400 INVALID_REQUEST`로 처리한다.

- `picture` 또는 `takenAt`이 누락된 경우
- 사진 파일이 비어 있는 경우
- 사진 파일 크기가 10MB를 초과한 경우
- 실제 이미지 형식을 판별할 수 없거나 파일이 손상된 경우
- 실제 이미지 형식이 JPEG, PNG, WebP 중 하나가 아닌 경우
- `takenAt`이 KST 기준 offset 없는 ISO 8601 형식이 아닌 경우

# 완료한 보물찾기 추천 화면 비즈니스 룰

## 1. 완료 미션 조회와 검증 순서

1. `missionType`이 `TREASURE`인지 확인한다.
2. `TREASURE_MISSION.id = missionId`인 보물찾기를 `MISSION`, `LOCATION`과 함께 조회한다.
3. `TREASURE_MISSION_PROGRESS.user_id = current_user_id`, `treasure_mission_id = missionId`, `mission_status = COMPLETED`인 진행도 중 `completed_at DESC`, 동률이면 `id DESC` 첫 행을 선택한다.
4. 선택한 진행도의 `item_detail[].index` 전체가 `current_found_item_idx`에 각각 한 번 이상 포함되어 있는지 검사한다.

1~3단계에서 대상을 찾지 못하면 모두 `TREASURE_MISSION_NOT_FOUND`로 처리한다. 4단계에서 누락된 index가 하나라도 있으면 완료 상태로 저장되어 있더라도 `TREASURE_ITEMS_REMAINING`으로 처리한다. `current_found_item_idx`의 중복값은 서로 다른 보물을 찾은 것으로 세지 않는다.

완료 시각은 선택한 진행도의 `completed_at`을 사용한다. 완료 미션의 AR 캐릭터 이미지는 `TREASURE_MISSION.reward_detail.ar_character_id`로 `AR_CHARACTER`를 조회하여 구성하며, 보상이 설정되지 않았거나 연결된 캐릭터가 없으면 `null`로 둔다.

## 2. 근처 보물찾기 선정

추천 후보는 전체 `TREASURE_MISSION` 중 다음 조건을 모두 만족하는 행이다.

- 현재 화면의 `missionId`와 다른 미션
- `item_total_count > 0`인 미션
- 연결된 `MISSION`과 `LOCATION`을 조회할 수 있는 미션

현재 사용자가 이전에 완료한 다른 보물찾기도 후보에서 제외하지 않는다. 사용자 좌표와 `LOCATION.my`, `LOCATION.mx` 사이의 거리는 `app/common/distance.py`의 `calculate_distance_meter()`로 계산하고, `distanceMeter ASC`, 동률이면 `TREASURE_MISSION.id ASC`로 정렬하여 앞의 3개만 선택한다. 예상 소요 시간도 같은 공통 모듈의 `calculate_duration_minutes()`로 계산한다.

장소 대표 이미지는 `LOCATION.content_id`로 `app/services/kto.py`의 `get_location_image_url()`을 호출한다. TourAPI의 `firstimage`, `firstimage2` 순서로 사용하며, 이미지가 없거나 외부 조회가 실패해도 추천 조회 전체를 실패시키지 않고 해당 이미지만 `null`로 둔다.

## 3. 추천 미션 보상 구성

각 추천 미션은 `TREASURE_MISSION.reward_detail`에 설정된 AR 캐릭터, 포인트, 쿠폰 보상을 모두 유지한다. 이미 받은 보상도 제거하거나 `null`로 바꾸지 않고 `isReceived = true`로 구분하며, 해당 종류의 보상이 애초에 설정되지 않은 경우에만 그 보상 객체를 `null`로 둔다.

수령 여부는 가장 최근 진행도 한 건이 아니라 현재 사용자의 해당 `treasure_mission_id` 전체 `TREASURE_MISSION_PROGRESS` 이력을 보상 종류별로 OR하여 판단한다. 이 집계는 `app/mission/reward_history.py`의 `get_granted_rewards_map()`을 한 번 호출하여 처리하고, 추천 미션마다 개별 조회하지 않는다. 보상 응답 변환은 `app/common/rewards.py`의 `to_full_reward_detail()`을 사용한다.

## 4. 받은 쿠폰 집계

별도 쿠폰 테이블을 만들거나 조회하지 않는다. 현재 사용자가 수령한 쿠폰은 유형별 세부 미션의 `reward_detail`과 진행도의 `coupon_reward_granted`를 다음 기준으로 조합한다.

| 미션 유형 | 진행도와 사용자 연결 조건 |
| --- | --- |
| `CULTURE` | `CULTURE_MISSION_PROGRESS.user_id = current_user_id` |
| `TREASURE` | `TREASURE_MISSION_PROGRESS.user_id = current_user_id` |
| `COOPERATIVE` | 삭제되지 않은 `COOPERATIVE_MISSION_PROGRESS`에 연결된, `participant_status = ACCEPTED`이면서 삭제되지 않은 `COOPERATIVE_MISSION_PARTICIPANT.user_id = current_user_id` |

진행도의 `coupon_reward_granted = true`이고 해당 세부 미션의 `reward_detail`에 `coupon_location`과 `coupon_price`가 모두 설정된 경우만 포함한다. 같은 세부 미션을 여러 번 수행했더라도 `(missionType, 유형별 세부 missionId)`당 한 번만 포함한다. 서로 다른 미션에서 같은 사용처와 같은 금액의 쿠폰을 받았다면 서로 다른 수령 건이므로 합치지 않는다.

## 5. 쿠폰 장소 결합

각 쿠폰의 `coupon_location`과 `LOCATION.location_title`을 완전 일치로 비교한다. 부분 일치나 유사어 검색은 하지 않는다. 같은 이름의 장소가 여러 행이면 `LOCATION.id ASC` 첫 행을 사용한다.

일치한 장소에서는 다음 값을 가져온다.

- 장소 id: `LOCATION.id`
- 주소: `LOCATION.location_address`
- 대표 이미지 조회 키: `LOCATION.content_id`

대표 이미지는 근처 보물찾기와 동일하게 `get_location_image_url()`로 조회한다. 일치하는 장소가 없으면 장소 id, 주소, 대표 이미지를 모두 `null`로 둔다. 장소는 찾았지만 TourAPI 이미지가 없거나 조회에 실패한 경우에는 장소 id와 주소는 유지하고 대표 이미지만 `null`로 둔다.

## 6. 상태 변경과 구현 책임

이 기능은 조회 전용이다. 미션 진행도, 보상 지급 여부, 사용자 포인트, 획득 캐릭터를 생성하거나 변경하지 않는다. 추천 목록 또는 받은 쿠폰 목록이 없으면 각각 빈 배열로 유지한다.

완료 미션 검증, 근처 추천, 쿠폰 집계는 보물찾기 완료 화면 서비스에서 조합하되 거리·소요 시간, 보상 이력 집계, 보상 변환, TourAPI 이미지 조회는 기존 공통 모듈을 재사용한다. 목록 데이터와 보상 지급 이력은 일괄 조회하여 미션 또는 쿠폰 수에 비례하는 N+1 쿼리가 발생하지 않도록 한다.

## 7. 필수 테스트

- 최근 완료 진행도를 `completed_at DESC`, `id DESC`로 선택하는지 검증한다.
- `current_found_item_idx`에 중복만 있고 설정된 index가 누락된 경우 완료로 인정하지 않는지 검증한다.
- 현재 미션과 `item_total_count <= 0`인 미션은 제외하고, 다른 완료 미션은 포함하여 거리순 최대 3개를 반환하는지 검증한다.
- 추천 미션의 전체 진행도 이력을 OR하여 보상별 수령 여부를 계산하고, 미설정 보상만 `null`이 되는지 검증한다.
- 문화·보물찾기·협동 미션의 수령 쿠폰을 집계하고, 같은 세부 미션의 반복 진행만 제거하는지 검증한다.
- 협동 미션은 삭제되지 않은 `ACCEPTED` 참가 기록만 현재 사용자의 수령 이력으로 인정하는지 검증한다.
- 쿠폰 사용처와 같은 이름의 장소가 여러 개면 가장 작은 id의 장소 주소까지 반환하는지 검증한다.
- 장소 미일치와 TourAPI 조회 실패를 구분하여 장소 id·주소·이미지의 `null` 범위를 적용하는지 검증한다.
- 조회 전후 관련 테이블의 데이터가 변경되지 않는지 검증한다.
