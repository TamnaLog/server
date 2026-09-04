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

프론트에서 보물찾기 화면을 구성할 수 있도록 진행도 id, 진행 상태, 미션 장소의 id·이름·주소·좌표, 전체 보물 개수, 보물별 좌표와 발견 여부를 반환한다. 보물 표시 및 인식 반경은 프론트에서 관리하며 이 API의 요청과 응답에 포함하지 않는다.

---

### 요청 Query

| 필드        | 타입   | 필수 | 설명                                                      |
| ----------- | ------ | ---- | --------------------------------------------------------- |
| `latitude`  | number | Y    | 보물 좌표 생성 기준이 되는 사용자의 현재 위도. `-90~90`   |
| `longitude` | number | Y    | 보물 좌표 생성 기준이 되는 사용자의 현재 경도. `-180~180` |

---

### 요청 Path

| 필드                | 타입   | 설명                                        |
| ------------------- | ------ | ------------------------------------------- |
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

| 필드                            | 타입     | 설명                                                                   |
| ------------------------------- | -------- | ---------------------------------------------------------------------- |
| `treasureMissionProgressId`     | number   | 보물찾기 미션 진행도 id                                                |
| `missionProgressStatus`         | string   | 보물찾기 미션 진행 상태. `IN_PROGRESS`                                 |
| `location`                      | object   | 보물찾기 미션 장소 정보                                                |
| `location.locationId`           | number   | 미션 장소의 LOCATION id                                                |
| `location.locationTitle`        | string   | 미션 장소명                                                            |
| `location.locationAddress`      | string   | 미션 장소 주소                                                         |
| `location.lat`                  | number   | 미션 장소의 위도                                                       |
| `location.lng`                  | number   | 미션 장소의 경도                                                       |
| `treasureCount`                 | number   | 보물찾기 미션의 전체 보물 개수                                         |
| `treasureItems`                 | object[] | `treasureIndex` 오름차순으로 정렬된 전체 보물 목록                     |
| `treasureItems[].treasureIndex` | number   | 보물 번호                                                              |
| `treasureItems[].location`      | object   | 진행도 생성 시 사용자 위치를 기준으로 생성되어 저장된 보물 좌표        |
| `treasureItems[].location.lat`  | number   | 보물의 위도. 진행도 `item_detail[].my`                                 |
| `treasureItems[].location.lng`  | number   | 보물의 경도. 진행도 `item_detail[].mx`                                 |
| `treasureItems[].isFound`       | boolean  | 해당 `treasureIndex`가 `current_found_item_idx`에 포함되어 있는지 여부 |

신규 시작 응답 예시 `201 Created`

```json
{
  "treasureMissionProgressId": 3,
  "missionProgressStatus": "IN_PROGRESS",
  "location": {
    "locationId": 15,
    "locationTitle": "새별 오름",
    "locationAddress": "제주특별자치도 제주시 애월읍 봉성리 산59-8",
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
    "locationId": 15,
    "locationTitle": "새별 오름",
    "locationAddress": "제주특별자치도 제주시 애월읍 봉성리 산59-8",
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

| 필드        | 타입   | 필수 | 설명                                            |
| ----------- | ------ | ---- | ----------------------------------------------- |
| `latitude`  | number | O    | 사용자 현재 위치의 위도. `-90` 이상 `90` 이하   |
| `longitude` | number | O    | 사용자 현재 위치의 경도. `-180` 이상 `180` 이하 |

---

### 요청 Path

| 필드                        | 타입   | 설명                                                           |
| --------------------------- | ------ | -------------------------------------------------------------- |
| `treasureMissionProgressId` | number | 저장할 보물찾기 미션 진행도 id. `TREASURE_MISSION_PROGRESS.id` |

요청 예시

```
PATCH /api/v1/treasure-missions/31/progress?latitude=33.5572&longitude=126.7591
```

---

### 요청 Body

| 필드            | 타입   | 필수 | 설명                                                    |
| --------------- | ------ | ---- | ------------------------------------------------------- |
| `treasureIndex` | number | O    | 사용자가 찾은 보물 번호. 진행도의 `item_detail[].index` |

```json
{
  "treasureIndex": 2
}
```

---

### 정상 응답 데이터

Status Code : 200

보물찾기 미션 진행도를 정상적으로 저장한 경우

| 필드                               | 타입     | 설명                                                                  |
| ---------------------------------- | -------- | --------------------------------------------------------------------- | -------------------------------------------------------------------- | --------- |
| `missionProgressStatus`            | string   | 보물찾기 미션 진행 상태. `IN_PROGRESS                                 | COMPLETED`                                                           |
| `treasureCount`                    | number   | 보물찾기 미션의 전체 보물 개수                                        |
| `foundTreasureIndexes`             | number[] | 사용자가 찾은 보물 번호 목록. 오름차순으로 반환                       |
| `nextLocation`                     | object   | null                                                                  | 다음 추천 장소 정보. 진행 중이면 `null`, 완료되면 반드시 객체로 반환 |
| `nextLocation.id`                  | number   | 다음 장소 id                                                          |
| `nextLocation.locationTitle`       | string   | 다음 장소명                                                           |
| `nextLocation.locationImageUrl`    | string   | null                                                                  | 다음 장소 이미지 URL. TourAPI에서 조회하지 못하면 `null`             |
| `nextLocation.distanceMeter`       | number   | 사용자 위치에서 다음 장소까지의 직선거리(m)                           |
| `nextLocation.mission`             | object   | null                                                                  | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null`               |
| `nextLocation.mission.id`          | number   | 다음 미션 id                                                          |
| `nextLocation.mission.missionType` | string   | 다음 미션 유형. `CULTURE                                              | COOPERATIVE                                                          | TREASURE` |
| `reward`                           | object   | 이번 요청으로 실제 지급된 보상 정보. 지급된 보상이 없어도 객체로 반환 |
| `reward.arCharacter`               | object   | null                                                                  | 이번 요청으로 지급된 AR 캐릭터. 지급되지 않았으면 `null`             |
| `reward.arCharacter.id`            | number   | AR 캐릭터 id                                                          |
| `reward.arCharacter.name`          | string   | AR 캐릭터 이름                                                        |
| `reward.arCharacter.imageUrl`      | string   | AR 캐릭터 이미지 URL                                                  |
| `reward.point`                     | number   | null                                                                  | 이번 요청으로 지급된 포인트. 지급되지 않았으면 `null`                |
| `reward.coupon`                    | object   | null                                                                  | 이번 요청으로 지급된 쿠폰. 지급되지 않았으면 `null`                  |
| `reward.coupon.couponLocation`     | string   | 쿠폰 사용처                                                           |
| `reward.coupon.couponPrice`        | number   | 쿠폰 금액                                                             |

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

| 필드        | 타입   | 필수 | 설명                                            |
| ----------- | ------ | ---- | ----------------------------------------------- |
| `latitude`  | number | O    | 사용자 현재 위치의 위도. `-90` 이상 `90` 이하   |
| `longitude` | number | O    | 사용자 현재 위치의 경도. `-180` 이상 `180` 이하 |

---

### 요청 Path

| 필드                        | 타입   | 필수 | 설명                                                           |
| --------------------------- | ------ | ---- | -------------------------------------------------------------- |
| `treasureMissionProgressId` | number | O    | 중단할 보물찾기 미션 진행도 id. `TREASURE_MISSION_PROGRESS.id` |

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

| 필드                               | 타입     | 설명                                                          |
| ---------------------------------- | -------- | ------------------------------------------------------------- | -------------------------------------------------------- | --------- |
| `missionProgressStatus`            | string   | 보물찾기 미션 진행 상태. 항상 `COMPLETED`                     |
| `treasureCount`                    | number   | 보물찾기 미션의 전체 보물 개수                                |
| `foundTreasureIndexes`             | number[] | 중단 시점까지 사용자가 찾은 보물 번호 목록. 오름차순으로 반환 |
| `nextLocation`                     | object   | 다음 추천 장소 정보. 중단 완료 응답에서는 항상 객체로 반환    |
| `nextLocation.id`                  | number   | 다음 장소 id                                                  |
| `nextLocation.locationTitle`       | string   | 다음 장소명                                                   |
| `nextLocation.locationImageUrl`    | string   | null                                                          | 다음 장소 이미지 URL. TourAPI에서 조회하지 못하면 `null` |
| `nextLocation.distanceMeter`       | number   | 사용자 위치에서 다음 장소까지의 직선거리(m)                   |
| `nextLocation.mission`             | object   | null                                                          | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null`   |
| `nextLocation.mission.id`          | number   | 다음 미션 id                                                  |
| `nextLocation.mission.missionType` | string   | 다음 미션 유형. `CULTURE                                      | COOPERATIVE                                              | TREASURE` |

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

## ar 캐릭터와 사진 저장

- http 메서드: post
- domain: treasure-mission
- endpoint: /api/v1/treasure-missions/pictures-with-character

### API 설명

사용자가 AR 캐릭터와 함께 촬영한 사진을 저장할 때 호출한다.

프론트는 사진 파일과 사진 촬영 시각을 `multipart/form-data`로 전송한다. 서버는 사진 파일을 이미지 저장소에 업로드한 뒤 로그인한 사용자 id, 업로드된 사진 URL, 촬영 시각을 `PICTURE_WITH_CHARACTER`에 저장한다.

사진은 JPEG, PNG, WebP 형식만 허용하며 최대 크기는 10MB이다. 원본 파일명은 저장에 사용하지 않고 실제 이미지 형식에 맞는 확장자로 정규화한다. HEIC/HEIF 형식은 직접 저장하지 않으며 프론트에서 JPEG로 변환한 후 전송한다.

사진 파일은 App Service 또는 Docker 컨테이너의 로컬 파일 시스템에 저장하지 않는다. `AZURE_STORAGE_CONTAINER`로 지정된 Azure Blob 컨테이너의 `ar_character_picture/{userId}/{uuid}.{extension}` 경로에 저장한다.

- 로그인한 사용자 id → `PICTURE_WITH_CHARACTER.user_id`
- 업로드된 사진 URL → `PICTURE_WITH_CHARACTER.picture_url`
- 요청의 `takenAt` → `PICTURE_WITH_CHARACTER.saved_at`

저장이 완료되면 별도의 응답 데이터를 반환하지 않고 `204 No Content`를 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

Content-Type : `multipart/form-data`

| 필드      | 타입              | 필수 | 설명                                                                      |
| --------- | ----------------- | ---- | ------------------------------------------------------------------------- |
| `picture` | file              | O    | AR 캐릭터와 함께 촬영한 이미지 파일. JPEG, PNG, WebP만 허용하며 최대 10MB |
| `takenAt` | string(date-time) | O    | 사진 촬영 시각. KST 기준 offset 없는 ISO 8601 형식                        |

요청 예시

```bash
curl -X POST \
  "https://jankkan-jeju.azurewebsites.net/api/v1/treasure-missions/pictures-with-character" \
  -F "picture=@picture-with-character.jpg" \
  -F "takenAt=2026-08-26T14:32:10"
```

---

### 정상 응답 데이터

Status Code : 204

응답 Body 없음

---

### 오류 응답 데이터

없음

## 완료한 보물찾기 추천 화면

- http 메서드: get
- domain: treasure_mission
- endpoint: /api/v1/missions/{missionType}/{missionId}/completion

### API 설명

‼️ 기존의 구현해놓은 상태에서 특이하게 추가된 케이스라 해당 api 호출 트리거가 좀 요상한점 죄송합니다. 일단 미션홈 조회를 호출했을때 해당 미션이 보물찾기이면서 remainingReward가 보상 세 종류 모두 null일때 (즉 보물찾기인데 3개의 보물을 모두 찾았을때) 이 api를 호출해서 treasureHunt-detail-complete 화면을 만들어주시면 됩니다!

사용자가 모든 보물을 찾은 보물찾기 미션의 완료 화면에 진입할 때 호출한다.

Path의 `missionType`과 `missionId`로 현재 사용자가 완료한 보물찾기 미션을 조회하고, 가장 최근 완료 시각과 해당 미션에 설정된 AR 캐릭터 보상 이미지를 반환한다.

현재 사용자의 가장 최근 `COMPLETED` 진행도에서 설정된 모든 보물 index가 `current_found_item_idx`에 각각 한 번 이상 존재해야 한다. 중복된 index는 찾지 않은 다른 보물을 대신할 수 없다.

Query의 현재 사용자 좌표를 기준으로 가까운 보물찾기를 최대 3개 추천한다. 현재 조회 중인 보물찾기와 `item_total_count <= 0`으로 찾을 보물이 없는 보물찾기는 제외하며, 이전에 완료한 다른 보물찾기는 추천 대상에 포함할 수 있다.

추천 목록에는 화면 이동에 필요한 미션·장소 id, 미션명, 장소 대표 이미지, 거리, 예상 소요 시간 및 미션에 설정된 전체 보상과 종류별 수령 여부를 포함한다. 난이도는 반환하지 않는다.

현재 사용자가 문화·보물찾기·협동 미션에서 지금까지 받은 모든 쿠폰도 함께 반환한다. 쿠폰 사용처 이름과 `LOCATION.location_title`을 완전 일치로 조회하여 장소 id, 주소와 TourAPI 대표 이미지를 조합한다.

조회 전용 API이며 미션 진행도, 보상, 사용자 포인트와 쿠폰 수령 상태를 변경하지 않는다.

---

### 요청 Query

| 필드        | 타입   | 필수 | 설명                                 |
| ----------- | ------ | ---- | ------------------------------------ |
| `latitude`  | number | O    | 현재 사용자 위도. -90 이상 90 이하   |
| `longitude` | number | O    | 현재 사용자 경도. -180 이상 180 이하 |

요청 예시

```
?latitude=33.450701&longitude=126.570667
```

---

### 요청 Path

| 필드          | 타입    | 필수 | 설명                                         |
| ------------- | ------- | ---- | -------------------------------------------- |
| `missionType` | string  | O    | 조회할 미션 유형. 이 API는 `TREASURE`만 허용 |
| `missionId`   | integer | O    | `TREASURE_MISSION.id`                        |

요청 예시

```
GET /api/v1/missions/TREASURE/7/completion?latitude=33.450701&longitude=126.570667
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

| 필드                                                           | 타입              | 설명                                                                                         |
| -------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `completedMission`                                             | object            | 완료한 보물찾기 정보                                                                         |
| `completedMission.missionId`                                   | integer           | 완료한 보물찾기의 `TREASURE_MISSION.id`                                                      |
| `completedMission.missionType`                                 | string            | 항상 `TREASURE`                                                                              |
| `completedMission.completedAt`                                 | string(date-time) | 현재 사용자가 해당 미션을 가장 최근에 완료한 시각. KST 기준 offset 없는 ISO 8601 형식        |
| `completedMission.arCharacterImageUrl`                         | string            | null                                                                                         | 해당 미션의 AR 캐릭터 보상 이미지 URL. 캐릭터 보상이 없거나 연결된 캐릭터가 없으면 null                 |
| `nearbyTreasureMissions`                                       | object\[\]        | 현재 미션과 찾을 보물이 없는 미션을 제외한 가까운 보물찾기 목록. 최대 3개이며 없으면 빈 배열 |
| `nearbyTreasureMissions[].missionId`                           | integer           | 추천 보물찾기의 `TREASURE_MISSION.id`                                                        |
| `nearbyTreasureMissions[].missionType`                         | string            | 항상 `TREASURE`                                                                              |
| `nearbyTreasureMissions[].locationId`                          | integer           | 추천 보물찾기가 진행되는 `LOCATION.id`                                                       |
| `nearbyTreasureMissions[].missionTitle`                        | string            | 추천 보물찾기 제목                                                                           |
| `nearbyTreasureMissions[].representativeImageUrl`              | string            | null                                                                                         | 미션 장소의 TourAPI 대표 이미지 URL. `firstimage`, 없으면 `firstimage2`; 둘 다 없거나 조회 실패 시 null |
| `nearbyTreasureMissions[].distanceMeter`                       | integer           | 현재 사용자 좌표에서 추천 미션 장소까지의 직선거리(m)                                        |
| `nearbyTreasureMissions[].durationMinutes`                     | integer           | `distanceMeter`를 기존 공통 모듈로 변환한 예상 소요 시간(분)                                 |
| `nearbyTreasureMissions[].rewardDetail`                        | object            | 추천 미션에 설정된 전체 보상과 현재 사용자의 종류별 수령 여부                                |
| `nearbyTreasureMissions[].rewardDetail.arCharacter`            | object            | null                                                                                         | AR 캐릭터 보상. 해당 보상이 없으면 null                                                                 |
| `nearbyTreasureMissions[].rewardDetail.arCharacter.id`         | integer           | AR 캐릭터 id                                                                                 |
| `nearbyTreasureMissions[].rewardDetail.arCharacter.name`       | string            | AR 캐릭터 이름                                                                               |
| `nearbyTreasureMissions[].rewardDetail.arCharacter.imageUrl`   | string            | AR 캐릭터 이미지 URL                                                                         |
| `nearbyTreasureMissions[].rewardDetail.arCharacter.isReceived` | boolean           | 현재 사용자의 해당 AR 캐릭터 보상 수령 여부                                                  |
| `nearbyTreasureMissions[].rewardDetail.point`                  | object            | null                                                                                         | 포인트 보상. 해당 보상이 없으면 null                                                                    |
| `nearbyTreasureMissions[].rewardDetail.point.amount`           | integer           | 포인트 보상량                                                                                |
| `nearbyTreasureMissions[].rewardDetail.point.isReceived`       | boolean           | 현재 사용자의 해당 포인트 보상 수령 여부                                                     |
| `nearbyTreasureMissions[].rewardDetail.coupon`                 | object            | null                                                                                         | 쿠폰 보상. 해당 보상이 없으면 null                                                                      |
| `nearbyTreasureMissions[].rewardDetail.coupon.couponLocation`  | string            | 쿠폰 사용처                                                                                  |
| `nearbyTreasureMissions[].rewardDetail.coupon.couponPrice`     | integer           | 쿠폰 금액                                                                                    |
| `nearbyTreasureMissions[].rewardDetail.coupon.isReceived`      | boolean           | 현재 사용자의 해당 쿠폰 보상 수령 여부                                                       |
| `receivedCoupons`                                              | object\[\]        | 현재 사용자가 지금까지 받은 모든 미션 유형의 쿠폰 보상 목록. 없으면 빈 배열                  |
| `receivedCoupons[].couponLocation`                             | string            | 쿠폰 사용처                                                                                  |
| `receivedCoupons[].couponPrice`                                | integer           | 쿠폰 금액                                                                                    |
| `receivedCoupons[].locationId`                                 | integer           | null                                                                                         | 쿠폰 사용처 이름과 같은 `LOCATION.location_title`의 장소 id. 일치 장소가 없으면 null                    |
| `receivedCoupons[].locationAddress`                            | string            | null                                                                                         | 쿠폰 사용처와 일치한 장소의 `LOCATION.location_address`. 일치 장소가 없으면 null                        |
| `receivedCoupons[].locationImageUrl`                           | string            | null                                                                                         | 쿠폰 사용처 장소의 TourAPI 대표 이미지 URL. 장소가 없거나 이미지를 조회하지 못하면 null                 |

```json
{
  "completedMission": {
    "missionId": 7,
    "missionType": "TREASURE",
    "completedAt": "2026-08-25T14:30:00",
    "arCharacterImageUrl": "https://example.com/images/ar-characters/stone-spirit.png"
  },
  "nearbyTreasureMissions": [
    {
      "missionId": 12,
      "missionType": "TREASURE",
      "locationId": 31,
      "missionTitle": "새별오름의 숨겨진 보물",
      "representativeImageUrl": "https://example.com/images/locations/31/firstimage.jpg",
      "distanceMeter": 1200,
      "durationMinutes": 16,
      "rewardDetail": {
        "arCharacter": {
          "id": 4,
          "name": "오름 정령",
          "imageUrl": "https://example.com/images/ar-characters/4.png",
          "isReceived": false
        },
        "point": {
          "amount": 300,
          "isReceived": false
        },
        "coupon": null
      }
    }
  ],
  "receivedCoupons": [
    {
      "couponLocation": "타라 소품",
      "couponPrice": 1000,
      "locationId": 44,
      "locationAddress": "제주특별자치도 제주시 예시로 44",
      "locationImageUrl": "https://example.com/images/locations/44/firstimage.jpg"
    }
  ]
}
```

`nearbyTreasureMissions`는 `distanceMeter ASC`, 거리가 같으면 `missionId ASC` 순으로 반환한다.

추천 미션의 보상별 `isReceived`는 현재 사용자의 동일 보물찾기 전체 진행도 이력에서 각 보상 지급 여부를 OR하여 판단한다.

받은 쿠폰은 `(missionType, 유형별 세부 missionId)`당 한 번만 포함한다. 서로 다른 미션에서 같은 사용처와 같은 금액의 쿠폰을 받은 경우에는 별개 항목으로 유지한다.

같은 이름의 LOCATION이 여러 개면 `LOCATION.id ASC` 첫 행을 사용한다. 일치하는 장소가 없으면 `locationId`, `locationAddress`, `locationImageUrl`을 모두 null로 반환한다.

`nearbyTreasureMissions` 또는 `receivedCoupons`가 없으면 해당 필드는 생략하지 않고 빈 배열로 반환한다.

```json
{
  "completedMission": {
    "missionId": 7,
    "missionType": "TREASURE",
    "completedAt": "2026-08-25T14:30:00",
    "arCharacterImageUrl": null
  },
  "nearbyTreasureMissions": [],
  "receivedCoupons": []
}
```

---

### 오류 응답 데이터

Status Code : 404

`missionType`이 `TREASURE`가 아니거나, `missionId`에 해당하는 보물찾기 미션 또는 현재 사용자의 완료 진행도를 찾을 수 없는 경우

```json
{
  "code": "TREASURE_MISSION_NOT_FOUND"
}
```

Status Code : 409

가장 최근 완료 진행도에서 설정된 모든 보물 index를 한 번 이상 찾지 않은 경우

```json
{
  "code": "TREASURE_ITEMS_REMAINING"
}
```
