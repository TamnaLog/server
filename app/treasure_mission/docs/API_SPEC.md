## 보물찾기 시작/이어하기
- http 메서드: post
- domain: treasure-mission
- endpoint: /api/v1/treasure-missions/{treasureMissionId}/progress

### API 설명

사용자가 보물찾기 미션을 시작하거나 진행 중이던 보물찾기 미션을 이어서 할 때 호출한다.

Path로 전달받은 `treasureMissionId`를 사용하여 보물찾기 미션을 조회한다.

현재 사용자의 `IN_PROGRESS` 진행도가 없으면 새로운 진행도를 생성한다. 이때 Query로 전달받은 사용자 위치를 기준으로 보물별 좌표를 생성하여 진행도의 `item_detail`에 저장하고, `current_found_item_idx`는 빈 배열로 초기화한다.

현재 사용자의 `IN_PROGRESS` 진행도가 이미 있으면 새로운 진행도를 만들거나 보물 좌표를 다시 생성하지 않고 기존 진행도를 반환한다. 요청으로 전달된 사용자 위치는 이어하기 처리에서는 사용하지 않는다.

완료된 진행도만 존재하고 `IN_PROGRESS` 진행도가 없으면 재도전으로 판단하여 새로운 진행도를 생성한다.

프론트에서 보물찾기 화면을 구성할 수 있도록 진행도 id, 진행 상태, 미션 장소 정보, 전체 보물 개수, 보물별 좌표와 발견 여부를 반환한다. 보물 표시 및 인식 반경은 프론트에서 관리하며 이 API의 요청과 응답에 포함하지 않는다.

---

### 요청 Query

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `latitude` | number | Y | 보물 좌표 생성 기준이 되는 사용자의 현재 위도. `-90~90` |
| `longitude` | number | Y | 보물 좌표 생성 기준이 되는 사용자의 현재 경도. `-180~180` |

---

### 요청 Path

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `treasureMissionId` | number | 진행도를 생성하거나 조회할 보물찾기 미션 id |

요청 예시

```
POST /api/v1/treasure-missions/12/progress?latitude=33.3663&longitude=126.3577
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 201

보물찾기 미션 진행도를 새로 생성한 경우

Status Code : 200

이미 진행 중인 보물찾기 미션을 이어서 하는 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `treasureMissionProgressId` | number | 보물찾기 미션 진행도 id |
| `missionProgressStatus` | string | 보물찾기 미션 진행 상태. `IN_PROGRESS` |
| `location` | object | 보물찾기 미션 장소 정보 |
| `location.locationTitle` | string | 미션 장소명 |
| `location.lat` | number | 미션 장소의 위도 |
| `location.lng` | number | 미션 장소의 경도 |
| `treasureCount` | number | 보물찾기 미션의 전체 보물 개수 |
| `treasureItems` | object[] | `treasureIndex` 오름차순으로 정렬된 전체 보물 목록 |
| `treasureItems[].treasureIndex` | number | 보물 번호 |
| `treasureItems[].location` | object | 진행도 생성 시 사용자 위치를 기준으로 생성되어 저장된 보물 좌표 |
| `treasureItems[].location.lat` | number | 보물의 위도. 진행도 `item_detail[].my` |
| `treasureItems[].location.lng` | number | 보물의 경도. 진행도 `item_detail[].mx` |
| `treasureItems[].isFound` | boolean | 해당 `treasureIndex`가 `current_found_item_idx`에 포함되어 있는지 여부 |

신규 시작 응답 예시 `201 Created`

```json
{
  "treasureMissionProgressId": 3,
  "missionProgressStatus": "IN_PROGRESS",
  "location": {
    "locationTitle": "새별 오름",
    "lat": 33.3663,
    "lng": 126.3577
  },
  "treasureCount": 3,
  "treasureItems": [
    {
      "treasureIndex": 1,
      "location": {
        "lat": 33.3665,
        "lng": 126.3579
      },
      "isFound": false
    },
    {
      "treasureIndex": 2,
      "location": {
        "lat": 33.3661,
        "lng": 126.3574
      },
      "isFound": false
    },
    {
      "treasureIndex": 3,
      "location": {
        "lat": 33.3668,
        "lng": 126.3581
      },
      "isFound": false
    }
  ]
}
```

이어하기 응답 예시 `200 OK`

```json
{
  "treasureMissionProgressId": 3,
  "missionProgressStatus": "IN_PROGRESS",
  "location": {
    "locationTitle": "새별 오름",
    "lat": 33.3663,
    "lng": 126.3577
  },
  "treasureCount": 3,
  "treasureItems": [
    {
      "treasureIndex": 1,
      "location": {
        "lat": 33.3665,
        "lng": 126.3579
      },
      "isFound": true
    },
    {
      "treasureIndex": 2,
      "location": {
        "lat": 33.3661,
        "lng": 126.3574
      },
      "isFound": false
    },
    {
      "treasureIndex": 3,
      "location": {
        "lat": 33.3668,
        "lng": 126.3581
      },
      "isFound": false
    }
  ]
}
```

---

### 오류 응답 데이터

Status Code : 404

`treasureMissionId`에 해당하는 보물찾기 미션이 존재하지 않는 경우

```json
{
  "code": "TREASURE_MISSION_NOT_FOUND"
}
```


## 보물찾기 진행도 저장
- http 메서드: patch
- domain: treasure-mission
- endpoint: /api/v1/treasure-missions/{treasureMissionProgressId}/progress

### API 설명

사용자가 보물찾기 미션에서 보물을 찾을 때마다 호출한다.

Path로 전달받은 `treasureMissionProgressId`를 사용하여 로그인한 사용자의 `IN_PROGRESS` 보물찾기 진행도를 조회한다. 요청 Body의 `treasureIndex`가 진행도의 `item_detail`에 존재하고 아직 발견하지 않은 보물이면 `current_found_item_idx`에 추가한다.

보물을 하나 찾을 때마다 지급 가능한 보상 한 종류를 즉시 지급한다. 지급 순서는 AR 캐릭터, 포인트, 쿠폰 순서이며, 같은 사용자와 같은 보물찾기 미션에서는 각 보상 종류를 한 번만 지급할 수 있다. 현재 진행도뿐 아니라 이전에 완료한 모든 진행도의 지급 이력을 확인하여 이미 지급된 보상은 다시 지급하지 않는다.

응답의 `reward`에는 이번 요청으로 실제 지급된 보상만 포함한다. 지급되지 않은 항목은 `null`로 반환하며, 이전 시도에서 모든 보상을 받은 경우에는 보물을 찾더라도 모든 보상 항목을 `null`로 반환한다.

아직 찾지 않은 보물이 남아 있으면 진행도 상태를 `IN_PROGRESS`로 유지하고 `nextLocation`을 `null`로 반환한다.

이번 요청으로 모든 보물을 찾으면 진행도 상태를 `COMPLETED`로 변경하고 완료 시각을 저장한다. 마지막 보물에 대한 보상도 동일한 기준으로 지급하며, 문화 미션 완료 처리와 동일한 방식으로 다음 장소를 추천한다. Query의 사용자 좌표는 추천된 다음 장소까지의 직선거리를 계산하는 데 사용하며, 거리는 `distanceMeter`에 미터 단위로 반환한다.

`nextLocation.locationImageUrl`은 `LOCATION.content_id`로 TourAPI를 조회하여 채운다. 인증키 미설정, 통신 실패 또는 이미지가 없는 경우에도 진행도 저장 전체를 실패시키지 않고 `locationImageUrl`만 `null`로 반환한다.

---

### 요청 Query

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `latitude` | number | O | 사용자 현재 위치의 위도. `-90` 이상 `90` 이하 |
| `longitude` | number | O | 사용자 현재 위치의 경도. `-180` 이상 `180` 이하 |

---

### 요청 Path

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `treasureMissionProgressId` | number | 저장할 보물찾기 미션 진행도 id. `TREASURE_MISSION_PROGRESS.id` |

요청 예시

```
PATCH /api/v1/treasure-missions/31/progress?latitude=33.5572&longitude=126.7591
```

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `treasureIndex` | number | O | 사용자가 찾은 보물 번호. 진행도의 `item_detail[].index` |

```json
{
  "treasureIndex": 2
}
```

---

### 정상 응답 데이터

Status Code : 200

보물찾기 미션 진행도를 정상적으로 저장한 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionProgressStatus` | string | 보물찾기 미션 진행 상태. `IN_PROGRESS | COMPLETED` |
| `treasureCount` | number | 보물찾기 미션의 전체 보물 개수 |
| `foundTreasureIndexes` | number[] | 사용자가 찾은 보물 번호 목록. 오름차순으로 반환 |
| `nextLocation` | object | null | 다음 추천 장소 정보. 진행 중이면 `null`, 완료되면 반드시 객체로 반환 |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string | null | 다음 장소 이미지 URL. TourAPI에서 조회하지 못하면 `null` |
| `nextLocation.distanceMeter` | number | 사용자 위치에서 다음 장소까지의 직선거리(m) |
| `nextLocation.mission` | object | null | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE | COOPERATIVE | TREASURE` |
| `reward` | object | 이번 요청으로 실제 지급된 보상 정보. 지급된 보상이 없어도 객체로 반환 |
| `reward.arCharacter` | object | null | 이번 요청으로 지급된 AR 캐릭터. 지급되지 않았으면 `null` |
| `reward.arCharacter.id` | number | AR 캐릭터 id |
| `reward.arCharacter.name` | string | AR 캐릭터 이름 |
| `reward.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `reward.point` | number | null | 이번 요청으로 지급된 포인트. 지급되지 않았으면 `null` |
| `reward.coupon` | object | null | 이번 요청으로 지급된 쿠폰. 지급되지 않았으면 `null` |
| `reward.coupon.couponLocation` | string | 쿠폰 사용처 |
| `reward.coupon.couponPrice` | number | 쿠폰 금액 |

첫 번째 보물을 찾아 미션이 아직 진행 중이며 AR 캐릭터가 지급된 예시

```json
{
  "missionProgressStatus": "IN_PROGRESS",
  "treasureCount": 3,
  "foundTreasureIndexes": [1],
  "nextLocation": null,
  "reward": {
    "arCharacter": {
      "id": 7,
      "name": "돌담이",
      "imageUrl": "https://example.com/characters/stone-spirit.png"
    },
    "point": null,
    "coupon": null
  }
}
```

두 번째 보물을 찾아 미션이 아직 진행 중이며 포인트가 지급된 예시

```json
{
  "missionProgressStatus": "IN_PROGRESS",
  "treasureCount": 3,
  "foundTreasureIndexes": [1, 2],
  "nextLocation": null,
  "reward": {
    "arCharacter": null,
    "point": 100,
    "coupon": null
  }
}
```

마지막 보물을 찾아 미션이 완료되고 쿠폰이 지급된 예시

```json
{
  "missionProgressStatus": "COMPLETED",
  "treasureCount": 3,
  "foundTreasureIndexes": [1, 2, 3],
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
    "distanceMeter": 4200,
    "mission": {
      "id": 342,
      "missionType": "CULTURE"
    }
  },
  "reward": {
    "arCharacter": null,
    "point": null,
    "coupon": {
      "couponLocation": "종화네 막국수",
      "couponPrice": 3000
    }
  }
}
```

이전 시도에서 모든 보상을 지급받아 이번 요청에서 지급할 보상이 없는 예시

```json
{
  "missionProgressStatus": "IN_PROGRESS",
  "treasureCount": 3,
  "foundTreasureIndexes": [1],
  "nextLocation": null,
  "reward": {
    "arCharacter": null,
    "point": null,
    "coupon": null
  }
}
```

다음 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.

---

### 오류 응답 데이터

Status Code : 404

`treasureMissionProgressId`에 해당하는 로그인한 사용자의 `IN_PROGRESS` 보물찾기 진행도가 존재하지 않는 경우

```json
{
  "code": "TREASURE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

요청한 `treasureIndex`가 진행도의 `item_detail`에 존재하지 않는 경우

```json
{
  "code": "TREASURE_ITEM_NOT_FOUND"
}
```

Status Code : 409

요청한 `treasureIndex`가 이미 `current_found_item_idx`에 포함되어 있는 경우

```json
{
  "code": "TREASURE_ITEM_ALREADY_FOUND"
}
```



## 보물찾기 중단
- http 메서드: patch
- domain: treasure-mission
- endpoint: /api/v1/treasure-missions/{treasureMissionProgressId}/progress/stop

### API 설명

사용자가 보물찾기 미션을 끝까지 진행하지 않고 중단할 때 호출한다.

Path로 전달받은 `treasureMissionProgressId`를 사용하여 로그인한 사용자의 `IN_PROGRESS` 보물찾기 진행도를 조회한다. 유효한 진행도가 있으면 남아 있는 보물 개수와 관계없이 진행도 상태를 즉시 `COMPLETED`로 변경하고 완료 시각을 저장한다.

보상은 보물을 발견할 때마다 보물찾기 진행도 저장 API에서 즉시 지급되므로 중단 요청에서는 보상을 추가로 지급하지 않으며, 응답에도 보상 정보를 포함하지 않는다.

중단한 보물찾기 미션도 완료한 미션으로 취급한다. 문화 미션 완료 처리와 동일한 방식으로 다음 장소를 추천하고, Query로 전달받은 사용자 위치에서 추천 장소까지의 직선거리를 `distanceMeter`에 미터 단위로 반환한다. 중단 완료 응답의 `nextLocation`은 항상 객체이다.

---

### 요청 Query

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `latitude` | number | O | 사용자 현재 위치의 위도. `-90` 이상 `90` 이하 |
| `longitude` | number | O | 사용자 현재 위치의 경도. `-180` 이상 `180` 이하 |

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `treasureMissionProgressId` | number | O | 중단할 보물찾기 미션 진행도 id. `TREASURE_MISSION_PROGRESS.id` |

요청 예시

```
PATCH /api/v1/treasure-missions/31/progress/stop?latitude=33.5572&longitude=126.7591
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

보물찾기 미션을 정상적으로 중단하고 완료 처리한 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionProgressStatus` | string | 보물찾기 미션 진행 상태. 항상 `COMPLETED` |
| `treasureCount` | number | 보물찾기 미션의 전체 보물 개수 |
| `foundTreasureIndexes` | number[] | 중단 시점까지 사용자가 찾은 보물 번호 목록. 오름차순으로 반환 |
| `nextLocation` | object | 다음 추천 장소 정보. 중단 완료 응답에서는 항상 객체로 반환 |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string | null | 다음 장소 이미지 URL. TourAPI에서 조회하지 못하면 `null` |
| `nextLocation.distanceMeter` | number | 사용자 위치에서 다음 장소까지의 직선거리(m) |
| `nextLocation.mission` | object | null | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE | COOPERATIVE | TREASURE` |

```json
{
  "missionProgressStatus": "COMPLETED",
  "treasureCount": 3,
  "foundTreasureIndexes": [1, 2],
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
    "distanceMeter": 4200,
    "mission": {
      "id": 342,
      "missionType": "CULTURE"
    }
  }
}
```

다음 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.

---

### 오류 응답 데이터

Status Code : 404

`treasureMissionProgressId`에 해당하는 로그인한 사용자의 `IN_PROGRESS` 보물찾기 진행도가 존재하지 않는 경우

- 진행도 id에 해당하는 데이터가 없는 경우
- 해당 진행도가 다른 사용자의 진행도인 경우
- 해당 진행도가 이미 `COMPLETED` 상태인 경우

```json
{
  "code": "TREASURE_MISSION_PROGRESS_NOT_FOUND"
}
```

