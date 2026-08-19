## 보물찾기 미션 시작/이어하기
- http 메서드: POST
- 엔드포인트: `/api/v1/treasure-missions/{missionId}/progress`
- 도메인: treasure-mission

### API 설명

사용자가 보물찾기 미션을 시작하거나 진행 중이던 보물찾기 미션을 이어서 할 때 호출한다.

Path로 전달받은 `missionId`를 사용하여 보물찾기 미션을 조회한다. 로그인한 사용자의 진행도가 없으면 상태를 `INPROGRESS`로 초기화하여 진행도를 생성하고, 각 보물의 발견 여부를 `false`로 초기화한다.

이미 진행 중인 기록이 있으면 진행도를 새로 만들지 않고 기존 기록을 반환한다. 각 보물의 `isFound`에는 사용자가 해당 보물을 찾았는지 여부를 반환한다.

프론트에서 보물찾기 미션 화면을 구성할 수 있도록 미션 장소 정보, 보물이 나타나는 공통 반경, 보물을 인식하는 공통 반경, 전체 보물 개수, 보물별 위치와 발견 여부, 보상 정보를 함께 반환한다. 두 반경 값은 모든 보물에 동일하게 적용한다.

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
| `treasureAppearRadius` | number | 보물이 나타나는 공통 반경(m) |
| `treasureDetectionRadius` | number | 보물을 인식할 수 있는 공통 반경(m). 모든 보물에 동일하게 적용 |
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
  "treasureDetectionRadius": 3,
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

---

### 추가 고려 사항
- 보물찾기 메인 장소에 대한 반경, 각 보물당 인증이 가능한 반경 같은 수치 값은 검증을 통해 정해질 예정이다.




## AR 캐릭터와 사진 저장
- http 메서드: POST
- 엔드포인트: `/api/v1/treasure-missions/pictures-with-character`
- 도메인: treasure-mission

### API 설명

사용자가 AR 캐릭터와 함께 사진을 촬영한 뒤 사진을 저장할 때 호출한다.

프론트에서 촬영한 사진 파일을 `multipart/form-data`로 전송한다. 서버는 사진을 이미지 저장소에 업로드하고, 로그인한 사용자 id와 업로드된 사진 URL 및 저장 시각을 `PICTURE_WITH_CHARACTER`에 저장한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body
Content-Type : `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
|---|---:|:---:|---|
| `picture` | file | O | AR 캐릭터와 함께 촬영한 사진 파일 |

요청 예시

```bash
curl -X POST \
  "https://jankkan-jeju.azurewebsites.net/api/v1/treasure-missions/pictures-with-character" \
  -F "picture=@picture-with-character.jpg"
```

---

### 정상 응답 데이터
Status Code : 204

응답 Body 없음

---

### 오류 응답 데이터

없음
