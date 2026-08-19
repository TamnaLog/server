## 보물찾기 미션 시작/이어하기
- http 메서드: POST
- 엔드포인트: `/api/v1/treasure-missions/{missionId}/progress`
- 도메인: treasure-mission

### API 설명

사용자가 보물찾기 미션을 시작하거나 진행 중이던 보물찾기 미션을 이어서 할 때 호출한다.

Path로 전달받은 `missionId`를 사용하여 보물찾기 미션을 조회한다. 로그인한 사용자의 진행도가 없으면 상태를 `INPROGRESS`로 초기화하여 진행도를 생성하고, 각 보물의 발견 여부를 `false`로 초기화한다.

이미 진행 중인 기록이 있으면 진행도를 새로 만들지 않고 기존 기록을 반환한다. 각 보물의 `isFound`에는 사용자가 해당 보물을 찾았는지 여부를 반환한다.

프론트에서 보물찾기 미션 화면을 구성할 수 있도록 미션 장소 정보, 보물이 나타나는 반경, 전체 보물 개수, 보물별 위치와 발견 여부, 보상 정보를 함께 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionId` | number | 진행도를 생성하거나 조회할 보물찾기 미션 id |

요청 예시

```text
POST /api/v1/treasure-missions/12/progress
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
|---|---:|---|
| `missionProgressStatus` | string | 보물찾기 미션 진행 상태. `INPROGRESS` |
| `location` | object | 보물찾기 미션 장소 정보 |
| `location.locationTitle` | string | 미션 장소명 |
| `location.lat` | number | 미션 장소의 위도 |
| `location.lng` | number | 미션 장소의 경도 |
| `treasureAppearRadius` | number | 보물이 나타나는 반경. 단위는 meter |
| `treasureCount` | number | 보물찾기 미션의 전체 보물 개수 |
| `treasureItems` | object[] | `treasureIndex` 오름차순으로 정렬된 전체 보물 목록 |
| `treasureItems[].treasureIndex` | number | 보물 번호 |
| `treasureItems[].location` | object | 보물 좌표 정보 |
| `treasureItems[].location.lat` | number | 보물의 위도 |
| `treasureItems[].location.lng` | number | 보물의 경도 |
| `treasureItems[].isFound` | boolean | 사용자가 해당 보물을 찾았는지 여부 |
| `rewardDetail` | object | 미션 완료 보상 정보 |
| `rewardDetail.arCharacter` | object \| null | 보상으로 획득할 AR 캐릭터. 캐릭터 보상이 없으면 `null` |
| `rewardDetail.arCharacter.id` | number | AR 캐릭터 id |
| `rewardDetail.arCharacter.name` | string | AR 캐릭터 이름 |
| `rewardDetail.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `rewardDetail.point` | number | 보상 포인트. 포인트 보상이 없으면 `0` |
| `rewardDetail.coupon` | object \| null | 쿠폰 보상 정보. 쿠폰 보상이 없으면 `null` |
| `rewardDetail.coupon.couponLocation` | string | 쿠폰 사용처 |
| `rewardDetail.coupon.couponPrice` | number | 쿠폰 금액 |

```json
{
  "missionProgressStatus": "INPROGRESS",
  "location": {
    "locationTitle": "새별 오름",
    "lat": 33.3663,
    "lng": 126.3577
  },
  "treasureAppearRadius": 30,
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
  ],
  "rewardDetail": {
    "arCharacter": {
      "id": 7,
      "name": "돌담이",
      "imageUrl": "https://example.com/characters/stone-spirit.png"
    },
    "point": 100,
    "coupon": {
      "couponLocation": "종화네 막국수",
      "couponPrice": 3000
    }
  }
}
```

---

### 오류 응답 데이터
Status Code : 404

`missionId`에 해당하는 보물찾기 미션이 존재하지 않는 경우

```json
{
  "code": "TREASURE_MISSION_NOT_FOUND"
}
```

Status Code : 409

사용자가 이미 완료한 보물찾기 미션인 경우

```json
{
  "code": "TREASURE_MISSION_ALREADY_COMPLETED"
}
```




## 보물찾기 미션 진행도 저장
- http 메서드: PATCH
- 엔드포인트: `/api/v1/treasure-missions/{missionId}/progress`
- 도메인: treasure-mission

### API 설명

사용자가 보물찾기 미션에서 보물을 찾을 때마다 호출한다.

Path로 전달받은 `missionId`를 사용하여 보물찾기 미션을 조회하고, 로그인한 사용자의 진행 중인 보물찾기 미션 진행도를 조회한다. 요청 Body로 전달받은 `treasureIndex`가 해당 미션에 포함된 보물 번호이면 사용자가 해당 보물을 찾은 것으로 저장한다.

모든 보물을 찾으면 진행도 상태를 `COMPLETED`로 변경한다. 완료된 경우 다음 장소 정보를 함께 반환한다.

보물찾기 미션이 아직 진행 중이면 `nextLocation`은 `null`로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionId` | number | 진행도를 저장할 보물찾기 미션 id |

요청 예시

```text
PATCH /api/v1/treasure-missions/12/progress
```

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
|---|---:|:---:|---|
| `treasureIndex` | number | O | 사용자가 찾은 보물 번호 |

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
|---|---:|---|
| `missionProgressStatus` | string | 보물찾기 미션 진행 상태. `INPROGRESS \| COMPLETED` |
| `treasureCount` | number | 보물찾기 미션의 전체 보물 개수 |
| `foundTreasureIndexes` | number[] | 사용자가 찾은 보물 번호 목록. 오름차순으로 반환 |
| `nextLocation` | object \| null | 다음 추천 장소 정보. 진행 중이면 `null` |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string | 다음 장소 이미지 URL |
| `nextLocation.mission` | object \| null | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE \| COOPERATIVE \| TREASURE` |

```json
{
  "missionProgressStatus": "INPROGRESS",
  "treasureCount": 3,
  "foundTreasureIndexes": [1, 2],
  "nextLocation": null
}
```

마지막 보물을 찾아 보물찾기 미션을 완료하면 `missionProgressStatus`는 `COMPLETED`로 반환한다.

```json
{
  "missionProgressStatus": "COMPLETED",
  "treasureCount": 3,
  "foundTreasureIndexes": [1, 2, 3],
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
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

`missionId`에 해당하는 보물찾기 미션이 존재하지 않는 경우

```json
{
  "code": "TREASURE_MISSION_NOT_FOUND"
}
```

Status Code : 404

로그인한 사용자의 진행 중인 보물찾기 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "TREASURE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

요청한 `treasureIndex`에 해당하는 보물이 존재하지 않는 경우

```json
{
  "code": "TREASURE_ITEM_NOT_FOUND"
}
```

Status Code : 409

사용자가 이미 완료한 보물찾기 미션인 경우

```json
{
  "code": "TREASURE_MISSION_ALREADY_COMPLETED"
}
```

Status Code : 409

사용자가 이미 찾은 보물인 경우

```json
{
  "code": "TREASURE_ITEM_ALREADY_FOUND"
}
```

## 보물찾기 미션 중단
- http 메서드: PATCH
- 엔드포인트: `/api/v1/treasure-missions/{missionId}/progress/stop`
- 도메인: treasure-mission

### API 설명

사용자가 보물찾기 미션을 끝까지 진행하지 않고 중단할 때 호출한다.

Path로 전달받은 `missionId`를 사용하여 보물찾기 미션을 조회하고, 로그인한 사용자의 진행 중인 보물찾기 미션 진행도를 조회한다. 진행 중인 보물찾기 미션이 있으면 진행도 상태를 즉시 `COMPLETED`로 변경한다.

중단한 보물찾기 미션도 완료한 보물찾기 미션처럼 취급한다.

프론트에서 중단 완료 화면을 구성할 수 있도록 진행 상태, 전체 보물 수, 찾은 보물 번호 목록, 보상 정보, 다음 장소 정보를 함께 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionId` | number | 중단할 보물찾기 미션 id |

요청 예시

```text
PATCH /api/v1/treasure-missions/12/progress/stop
```

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 200

보물찾기 미션을 정상적으로 중단하고 완료 처리한 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressStatus` | string | 보물찾기 미션 진행 상태. `COMPLETED` |
| `treasureCount` | number | 보물찾기 미션의 전체 보물 개수 |
| `foundTreasureIndexes` | number[] | 사용자가 찾은 보물 번호 목록. 오름차순으로 반환 |
| `rewardDetail` | object | 미션 완료 보상 정보 |
| `rewardDetail.arCharacter` | object \| null | 보상으로 획득할 AR 캐릭터. 캐릭터 보상이 없으면 `null` |
| `rewardDetail.arCharacter.id` | number | AR 캐릭터 id |
| `rewardDetail.arCharacter.name` | string | AR 캐릭터 이름 |
| `rewardDetail.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `rewardDetail.point` | number | 보상 포인트. 포인트 보상이 없으면 `0` |
| `rewardDetail.coupon` | object \| null | 쿠폰 보상 정보. 쿠폰 보상이 없으면 `null` |
| `rewardDetail.coupon.couponLocation` | string | 쿠폰 사용처 |
| `rewardDetail.coupon.couponPrice` | number | 쿠폰 금액 |
| `nextLocation` | object | 다음 추천 장소 정보 |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string | 다음 장소 이미지 URL |
| `nextLocation.mission` | object \| null | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE \| COOPERATIVE \| TREASURE` |

```json
{
  "missionProgressStatus": "COMPLETED",
  "treasureCount": 3,
  "foundTreasureIndexes": [1, 2],
  "rewardDetail": {
    "arCharacter": {
      "id": 7,
      "name": "돌담이",
      "imageUrl": "https://example.com/characters/stone-spirit.png"
    },
    "point": 100,
    "coupon": {
      "couponLocation": "종화네 막국수",
      "couponPrice": 3000
    }
  },
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
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

`missionId`에 해당하는 보물찾기 미션이 존재하지 않는 경우

```json
{
  "code": "TREASURE_MISSION_NOT_FOUND"
}
```

Status Code : 404

로그인한 사용자의 진행 중인 보물찾기 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "TREASURE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 409

사용자가 이미 완료한 보물찾기 미션인 경우

```json
{
  "code": "TREASURE_MISSION_ALREADY_COMPLETED"
}
```
