## 지도 홈 조회

- http 메서드: get
- domain: map
- endpoint: /api/v1/map/contents

### API 설명

지도 화면에 표시되는 영역 안의 콘텐츠를 반환한다.

프론트는 현재 사용자 화면에 보이는 지도의 네 꼭짓점 GPS 좌표와 현재 사용자의 GPS 좌표를 Query로 전달한다. 백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별한다.

백엔드는 전달받은 네 꼭짓점 좌표로 지도 화면의 조회 영역을 계산하고, 그 영역 안에 포함되는 장소, 길바닥 방명록을 반환한다.

장소는 조회 영역 안의 내부 LOCATION 데이터를 `locations`로 반환한다. 미션이나 방명록이 없는 장소도 걸러내지 않고 함께 반환하며, 이 경우 `treasureMission`과 `cooperativeMission`은 `null`, `guestbooksCount`는 `0`이 된다. 하나의 LOCATION에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다.

특정 LOCATION에 속하지 않고 사용자가 작성한 위치에 표시되는 길바닥 방명록은 `roadGuestbooks`로 반환한다.

`isClustered=true`인 경우에는 클러스터링에 필요한 LOCATION 또는 길바닥 방명록 ID와 좌표를 반환하고, LOCATION에는 연결된 세부 미션의 `missionId`와 보물찾기인지 협동 미션인지 구분하는 `missionType`을 함께 반환한다.

`isClustered=false`인 경우에는 지도에서 항목 클릭 또는 모달 조회가 가능하도록 필요한 상세 정보를 반환한다.

---

### 요청 Query

| 자료형  | 변수명                 | 필수 여부 | 설명                                                                                  |
| ------- | ---------------------- | --------- | ------------------------------------------------------------------------------------- |
| number  | `leftTopLatitude`      | 필수      | 지도 화면 좌상단 위도                                                                 |
| number  | `leftTopLongitude`     | 필수      | 지도 화면 좌상단 경도                                                                 |
| number  | `rightTopLatitude`     | 필수      | 지도 화면 우상단 위도                                                                 |
| number  | `rightTopLongitude`    | 필수      | 지도 화면 우상단 경도                                                                 |
| number  | `leftBottomLatitude`   | 필수      | 지도 화면 좌하단 위도                                                                 |
| number  | `leftBottomLongitude`  | 필수      | 지도 화면 좌하단 경도                                                                 |
| number  | `rightBottomLatitude`  | 필수      | 지도 화면 우하단 위도                                                                 |
| number  | `rightBottomLongitude` | 필수      | 지도 화면 우하단 경도                                                                 |
| number  | `userLatitude`         | 필수      | 현재 사용자 위치의 위도. 장소까지의 거리와 예상 이동 시간 계산에 사용                 |
| number  | `userLongitude`        | 필수      | 현재 사용자 위치의 경도. 장소까지의 거리와 예상 이동 시간 계산에 사용                 |
| boolean | `isClustered`          | 필수      | 클러스터링 여부. `true`이면 ID·좌표·장소 미션 ID·유형만, `false`이면 상세 정보를 반환 |

**요청 예시**

```
GET /api/v1/map/contents?leftTopLatitude=33.4700&leftTopLongitude=126.9100&rightTopLatitude=33.4700&rightTopLongitude=126.9500&leftBottomLatitude=33.4300&leftBottomLongitude=126.9100&rightBottomLatitude=33.4300&rightBottomLongitude=126.9500&userLatitude=33.4524&userLongitude=126.9248&isClustered=false
```

- 주의할 점: 모든 위도와 경도의 소수 부분을 최대한 보존해서 보내야 한다.
- 네 꼭짓점 좌표는 현재 사용자 화면에 실제로 보이는 지도 영역을 기준으로 전달한다.

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : `200 OK`

**isClustered = false**

| 자료형  | 변수명                                        | 설명                                                                |
| ------- | --------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------- |
| array   | `locations`                                   | 조회 영역 안의 LOCATION 목록. 미션과 방명록이 없는 장소도 포함      |
| integer | `locations[].id`                              | LOCATION ID                                                         |
| string  | `locations[].locationTitle`                   | 장소 이름                                                           |
| number  | `locations[].latitude`                        | 장소 위도                                                           |
| number  | `locations[].longitude`                       | 장소 경도                                                           |
| integer | `locations[].distanceMeter`                   | 현재 사용자 위치에서 장소까지의 직선거리(m)                         |
| integer | `locations[].durationMinutes`                 | 현재 사용자 위치에서 장소까지의 예상 이동 시간(분)                  |
| object  | null                                          | `locations[].treasureMission`                                       | 해당 장소의 보물찾기 미션 정보. 없으면 null                   |
| integer | `locations[].treasureMission.id`              | 보물찾기 미션 ID. `TREASURE_MISSION.id`                             |
| string  | `locations[].treasureMission.missionTitle`    | 보물찾기 미션 제목                                                  |
| boolean | `locations[].treasureMission.isCompleted`     | 현재 사용자의 보물찾기 미션 완료 여부                               |
| boolean | null                                          | `locations[].treasureMission.hasWrittenGuestbook`                   | 완료한 미션을 참조하는 방명록 작성 여부. 미션 미완료이면 null |
| object  | null                                          | `locations[].cooperativeMission`                                    | 해당 장소의 협동 미션 정보. 없으면 null                       |
| integer | `locations[].cooperativeMission.id`           | 협동 미션 ID. `COOPERATIVE_MISSION.id`                              |
| string  | `locations[].cooperativeMission.missionTitle` | 협동 미션 제목                                                      |
| boolean | `locations[].cooperativeMission.isCompleted`  | 현재 사용자의 협동 미션 완료 여부                                   |
| boolean | null                                          | `locations[].cooperativeMission.hasWrittenGuestbook`                | 완료한 미션을 참조하는 방명록 작성 여부. 미션 미완료이면 null |
| integer | `locations[].guestbooksCount`                 | 해당 장소에 존재하는 방명록 개수. 없으면 0                          |
| string  | null                                          | `locations[].representativeImageUrl`                                | TourAPI 장소 대표 이미지 URL. 이미지가 없으면 null            |
| array   | `roadGuestbooks`                              | 특정 LOCATION에 속하지 않고 작성 위치에 표시되는 길바닥 방명록 목록 |
| integer | `roadGuestbooks[].id`                         | 길바닥 방명록 ID                                                    |
| number  | `roadGuestbooks[].latitude`                   | 길바닥 방명록 위도                                                  |
| number  | `roadGuestbooks[].longitude`                  | 길바닥 방명록 경도                                                  |
| string  | `roadGuestbooks[].locationAlias`              | 길바닥 방명록에 표시할 위치 별칭                                    |
| string  | null                                          | `roadGuestbooks[].representativeGuestbookImageUrl`                  | 길바닥 방명록 이미지 배열의 첫 번째 URL. 이미지가 없으면 null |

```json
{
  "locations": [
    {
      "id": 101,
      "locationTitle": "현애원",
      "latitude": 33.4582,
      "longitude": 126.9331,
      "distanceMeter": 1250,
      "durationMinutes": 15,
      "treasureMission": {
        "id": 301,
        "missionTitle": "오구포구 보물찾기",
        "isCompleted": true,
        "hasWrittenGuestbook": false
      },
      "cooperativeMission": null,
      "guestbooksCount": 2,
      "representativeImageUrl": "<https://example.com/guestbooks/45/1.jpg>"
    }
  ],
  "roadGuestbooks": [
    {
      "id": 131,
      "latitude": 33.4582,
      "longitude": 126.9331,
      "locationAlias": "성산 바다 앞",
      "representativeGuestbookImageUrl": "<https://example.com/guestbooks/45/1.jpg>"
    }
  ]
}
```

- 하나의 LOCATION에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다.
- 보물찾기 미션이 존재하면 `treasureMission`만 객체로 반환하고 `cooperativeMission`은 null로 반환한다.
- 협동 미션이 존재하면 `cooperativeMission`만 객체로 반환하고 `treasureMission`은 null로 반환한다.
- 미션이 없으면 두 필드를 모두 null로 반환한다.
- `isCompleted`는 Bearer 토큰으로 식별한 현재 사용자의 완료 이력을 기준으로 판단한다.
- `hasWrittenGuestbook`은 미션을 완료한 경우에만 현재 사용자가 해당 장소와 미션을 참조하여 작성한 삭제되지 않은 방명록이 있는지 확인한다. 미션을 완료하지 않았다면 `null`을 반환한다.
- `distanceMeter`와 `durationMinutes`는 공통 거리 모듈을 사용해 사용자 위치와 장소 좌표로 계산한다.
- 장소에 방명록이 없으면 `guestbooksCount`를 `0`으로, `representativeImageUrl`을 `null`로 반환한다.
- 한 장소에 방명록과 미션이 함께 존재하는 경우도 포함해서 반환한다.
- 미션도 방명록도 없는 장소도 제외하지 않는다. 두 미션은 `null`, `guestbooksCount`는 `0`으로 반환한다.

**isClustered = true**

| 자료형  | 변수명                       | 설명                                                                      |
| ------- | ---------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------- |
| array   | `locations`                  | 조회 영역 안의 LOCATION 클러스터링 목록. 미션과 방명록이 없는 장소도 포함 |
| integer | `locations[].id`             | LOCATION ID. 미션 ID가 아님                                               |
| number  | `locations[].latitude`       | 장소 위도                                                                 |
| number  | `locations[].longitude`      | 장소 경도                                                                 |
| integer | null                         | `locations[].missionId`                                                   | 장소에 연결된 세부 미션 ID. `TREASURE_MISSION.id` 또는 `COOPERATIVE_MISSION.id`. 미션이 없으면 null |
| string  | null                         | `locations[].missionType`                                                 | 장소에 연결된 미션 유형. `TREASURE                                                                  | COOPERATIVE`. 미션이 없으면 null |
| array   | `roadGuestbooks`             | 조회 영역 안의 길바닥 방명록 클러스터링 목록                              |
| integer | `roadGuestbooks[].id`        | 길바닥 방명록 ID                                                          |
| number  | `roadGuestbooks[].latitude`  | 길바닥 방명록 위도                                                        |
| number  | `roadGuestbooks[].longitude` | 길바닥 방명록 경도                                                        |

```json
{
  "locations": [
    {
      "id": 101,
      "latitude": 33.4582,
      "longitude": 126.9331,
      "missionId": 301,
      "missionType": "TREASURE"
    },
    {
      "id": 102,
      "latitude": 33.4561,
      "longitude": 126.9295,
      "missionId": 401,
      "missionType": "COOPERATIVE"
    },
    {
      "id": 103,
      "latitude": 33.4518,
      "longitude": 126.9252,
      "missionId": null,
      "missionType": null
    }
  ],
  "roadGuestbooks": [
    {
      "id": 131,
      "latitude": 33.4582,
      "longitude": 126.9331
    }
  ]
}
```

- 일정 줌 아웃 상태 이상에서는 클러스터링에 필요한 ID, 좌표와 장소의 미션 ID·유형만 반환한다.
- `locations[].id`는 LOCATION ID이다.
- `locations[].missionId`는 `missionType`에 대응하는 세부 미션 ID이다. `TREASURE`이면 `TREASURE_MISSION.id`, `COOPERATIVE`이면 `COOPERATIVE_MISSION.id`를 반환한다.
- 하나의 LOCATION에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다.
- 장소에 보물찾기 미션이 있으면 `missionId`와 `missionType = TREASURE`, 협동 미션이 있으면 `missionId`와 `missionType = COOPERATIVE`를 반환한다. 미션이 없으면 두 필드를 모두 `null`로 반환한다.
- `roadGuestbooks[].id`는 길바닥 방명록 ID이다.
- `isClustered=true`에서는 장소 이름, 거리·예상 시간, 미션 상세 정보, 방명록 수, 이미지 및 길바닥 방명록 상세 정보를 반환하지 않는다.

---

### 오류 응답 데이터

없음

## 지도 모달 조회

- http 메서드: get
- domain: map
- endpoint: /api/v1/map/modals

### API 설명

지도에서 장소 또는 길바닥 방명록 아이콘을 선택하면 호출한다.

이 API는 `Authorization: Bearer {accessToken}` 헤더가 필수이며, 백엔드는 액세스 토큰으로 현재 사용자를 식별하고 실제 사용자 존재 여부를 검증한다. 현재 사용자 정보는 장소 모달의 방문 여부를 판정하는 데 사용한다.

조회 대상은 `LOCATION | ROAD_GUESTBOOK`만 지원하며, 선택한 대상의 ID와 사용자의 현재 GPS 좌표를 Query로 전송한다.

`LOCATION`을 조회하면 장소 기본 정보, TourAPI 장소 대표 이미지, 현재 사용자의 방문 여부와 해당 장소를 참조하는 최신 방명록을 작성자 AR 캐릭터 이미지와 함께 최대 3개 반환하고, `ROAD_GUESTBOOK`을 조회하면 해당 길바닥 방명록의 상세 콘텐츠를 반환한다.

작성일은 모두 방명록의 `visited_at`을 기준으로 한다.

---

### 요청 Query

| 자료형  | 변수명          | 필수 여부 | 설명                                                               |
| ------- | --------------- | --------- | ------------------------------------------------------------------ |
| string  | `targetType`    | 필수      | 조회 대상 유형. `LOCATION \| ROAD_GUESTBOOK`                      |
| integer | `targetId`      | 필수      | `LOCATION`이면 LOCATION ID, `ROAD_GUESTBOOK`이면 ROAD_GUESTBOOK ID |
| number  | `userLatitude`  | 필수      | 사용자의 현재 GPS 위도                                             |
| number  | `userLongitude` | 필수      | 사용자의 현재 GPS 경도                                             |

**요청 예시**

```
GET /api/v1/map/modals?targetType=LOCATION&targetId=39&userLatitude=33.4524&userLongitude=126.9248
```

- 위도와 경도의 소수 부분을 최대한 보존해서 전송한다.

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : `200 OK`

**targetType = LOCATION**

| 자료형  | 변수명                                        | 설명                                                                                 |
| ------- | --------------------------------------------- | ------------------------------------------------------------------------------------ |
| integer | `id`                                          | LOCATION ID                                                                          |
| string  | `locationTitle`                               | 장소 이름                                                                            |
| string  | `locationCategory`                            | 장소 분류                                                                            |
| string \| null | `representativeImageUrl`                   | `LOCATION.content_id`로 TourAPI에서 조회한 `firstimage` URL. 이미지가 없거나 조회에 실패하면 null |
| number  | `distanceMeter`                               | 사용자의 현재 위치와 장소 사이의 직선거리(m)                                         |
| integer | `durationMinutes`                             | 사용자의 현재 위치에서 장소까지의 예상 이동 시간(분)                                 |
| boolean | `isVisited`                                   | 현재 사용자의 해당 장소 방문 여부. 방문 기록이 한 건 이상 있으면 true, 없으면 false  |
| object \| null | `mission`                                   | 해당 장소에 연결된 미션 정보. 미션이 없으면 null                                     |
| integer | `mission.missionId`                           | `missionType`에 해당하는 유형별 세부 미션 ID                                         |
| string  | `mission.missionType`                         | 장소에 연결된 미션 유형. `TREASURE \| COOPERATIVE`                                  |
| string  | `mission.missionTitle`                        | 미션 이름                                                                            |
| boolean | `mission.isCompleted`                         | 현재 사용자의 해당 미션 완료 여부                                                    |
| object  | `mission.rewardDetail`                        | 해당 미션의 전체 보상 정보. 수령 여부와 관계없이 AR 캐릭터, 포인트, 쿠폰을 모두 포함 |
| object  | `mission.rewardDetail.arCharacter`            | AR 캐릭터 보상 정보                                                                  |
| integer | `mission.rewardDetail.arCharacter.id`         | AR 캐릭터 ID                                                                         |
| string  | `mission.rewardDetail.arCharacter.name`       | AR 캐릭터 이름                                                                       |
| string  | `mission.rewardDetail.arCharacter.imageUrl`   | AR 캐릭터 이미지 URL                                                                 |
| boolean | `mission.rewardDetail.arCharacter.isReceived` | 현재 사용자의 해당 AR 캐릭터 보상 수령 여부                                          |
| object  | `mission.rewardDetail.point`                  | 포인트 보상 정보                                                                     |
| integer | `mission.rewardDetail.point.amount`           | 포인트 보상량                                                                        |
| boolean | `mission.rewardDetail.point.isReceived`       | 현재 사용자의 해당 포인트 보상 수령 여부                                             |
| object  | `mission.rewardDetail.coupon`                 | 쿠폰 보상 정보                                                                       |
| string  | `mission.rewardDetail.coupon.couponLocation`  | 쿠폰 사용처                                                                          |
| integer | `mission.rewardDetail.coupon.couponPrice`     | 쿠폰 금액                                                                            |
| boolean | `mission.rewardDetail.coupon.isReceived`      | 현재 사용자의 해당 쿠폰 보상 수령 여부                                               |
| integer | `guestbooksCount`                             | 해당 장소를 참조하는 방명록 전체 개수. 없으면 0                                      |
| array   | `guestbooks`                                  | 해당 장소를 참조하는 방명록 중 `visited_at` 최신순 최대 3개. 없으면 빈 배열          |
| integer | `guestbooks[].id`                             | 방명록 ID                                                                            |
| string \| null | `guestbooks[].representativeImageUrl`        | 방명록 이미지 배열의 첫 번째 이미지 URL. 이미지가 없으면 null                        |
| integer | `guestbooks[].userId`                         | 방명록 작성자 사용자 ID                                                              |
| string  | `guestbooks[].userNickname`                   | 방명록 작성자 닉네임                                                                 |
| string \| null | `guestbooks[].characterImgUrl`               | 방명록 작성자의 AR 캐릭터 이미지 URL. 배정된 캐릭터가 없으면 null                    |
| string \| null | `guestbooks[].missionTitle`                  | 방명록이 참조하는 미션 이름. 참조하는 미션이 없으면 null                             |
| string  | `guestbooks[].visitedAt`                      | 방명록 방문·작성일. `visited_at` 기준, `YYYY-MM-DD` 형식                             |
| string \| null | `guestbooks[].contentWriting`                | 방명록 글 내용. 없으면 null                                                          |

```json
{
  "id": 39,
  "locationTitle": "현애원",
  "locationCategory": "관광지",
  "representativeImageUrl": "https://example.com/images/locations/hyeonaewon.jpg",
  "distanceMeter": 1200,
  "durationMinutes": 15,
  "isVisited": true,
  "mission": {
    "missionId": 12,
    "missionType": "TREASURE",
    "missionTitle": "현애원의 숨은 보물 찾기",
    "isCompleted": true,
    "rewardDetail": {
      "arCharacter": {
        "id": 3,
        "name": "점박이 물범",
        "imageUrl": "https://example.com/images/ar-characters/3.png",
        "isReceived": true
      },
      "point": {
        "amount": 100,
        "isReceived": true
      },
      "coupon": {
        "couponLocation": "현애원 카페",
        "couponPrice": 3000,
        "isReceived": false
      }
    }
  },
  "guestbooksCount": 10,
  "guestbooks": [
    {
      "id": 300,
      "representativeImageUrl": "https://example.com/images/guestbooks/guestbook-300.jpg",
      "userId": 1,
      "userNickname": "여행자종화",
      "characterImgUrl": "https://example.com/images/ar-characters/1.png",
      "missionTitle": "현애원의 숨은 보물 찾기",
      "visitedAt": "2026-08-25",
      "contentWriting": "현애원 산책하기 좋았어요."
    },
    {
      "id": 302,
      "representativeImageUrl": null,
      "userId": 2,
      "userNickname": "제주도종화",
      "characterImgUrl": null,
      "missionTitle": null,
      "visitedAt": "2026-08-23",
      "contentWriting": null
    }
  ]
}
```

- `mission.missionId`는 공통 MISSION ID가 아니라 `missionType`에 해당하는 유형별 세부 미션 ID다.
- `rewardDetail`은 보상 수령 여부와 관계없이 미션에 설정된 AR 캐릭터, 포인트, 쿠폰 정보를 모두 반환한다.
- 각 보상의 `isReceived`는 현재 사용자가 해당 미션의 과거 및 현재 진행도에서 그 보상을 한 번이라도 지급받았는지를 나타낸다.
- `isCompleted`와 보상 수령 여부는 서로 독립적으로 계산한다.
- `isVisited`는 현재 사용자와 조회 장소가 일치하는 `VISITED_LOCATION`의 존재 여부를 나타낸다. 방명록 작성 여부나 미션 완료 여부와는 관계없다.
- `representativeImageUrl`은 `LOCATION.content_id`로 TourAPI `detailCommon2`를 조회하여 얻은 `firstimage`를 사용한다. `firstimage`가 없거나 TourAPI 조회에 실패하면 null을 반환하며, 이미지 조회 실패만으로 모달 조회 전체를 실패시키지 않는다.
- `guestbooksCount`는 반환 목록의 길이가 아니라 해당 장소를 참조하는 전체 방명록 개수다.
- `guestbooks`는 `visited_at DESC`로 정렬하고, 날짜가 같으면 방명록 ID가 큰 순서로 최대 3개를 반환한다.
- `guestbooks[].userId`는 방명록 작성자의 `GUESTBOOK.user_id`이며, 프론트가 작성자별 화면으로 이동할 때 사용한다.
- `guestbooks[].characterImgUrl`은 방명록 작성자의 `USER.ar_character_id`로 연결된 `AR_CHARACTER.character_img_url`이며, 작성자에게 배정된 AR 캐릭터가 없으면 null이다.
- 대표 이미지는 방명록의 이미지 URL 배열 첫 번째 값을 사용하며, 배열이 없거나 비어 있으면 null이다.

**targetType = ROAD_GUESTBOOK**

| 자료형   | 변수명            | 설명                                                               |
| -------- | ----------------- | ------------------------------------------------------------------ |
| integer  | `id`              | ROAD_GUESTBOOK ID                                                  |
| string   | `userNickname`    | 길바닥 방명록 작성자 닉네임                                        |
| string   | `locationAlias`   | 작성자가 지정한 장소 별칭                                          |
| number   | `distanceMeter`   | 사용자의 현재 위치와 길바닥 방명록 좌표 사이의 직선거리(m)         |
| integer  | `durationMinutes` | 사용자의 현재 위치에서 길바닥 방명록 좌표까지의 예상 이동 시간(분) |
| string   | `visitedAt`       | 방문·작성일. `visited_at` 기준, `YYYY-MM-DD` 형식                  |
| string[] \| null | `contentImageUrls`                                      | 사진 URL 목록. 사진이 없으면 null                                  |
| string \| null   | `contentWriting`                                        | 글 내용. 없으면 null                                               |
| string[] \| null | `contentAudioUrls`                                      | 오디오 URL 목록. 오디오가 없으면 null                              |
| string \| null   | `contentWeather`                                        | 날씨 콘텐츠. 없으면 null                                           |
| string \| null   | `contentColorCode`                                      | 색상 코드 콘텐츠. 없으면 null                                      |

```json
{
  "id": 100,
  "userNickname": "여행자종화",
  "locationAlias": "성산 바다 앞",
  "distanceMeter": 850,
  "durationMinutes": 15,
  "visitedAt": "2026-08-25",
  "contentImageUrls": [
    "https://example.com/images/guestbooks/road-guestbook-100-1.jpg",
    "https://example.com/images/guestbooks/road-guestbook-100-2.jpg"
  ],
  "contentWriting": "성산일출봉으로 가는 길에 잠시 쉬어가기 좋았어요.",
  "contentAudioUrls": null,
  "contentWeather": "SUNNY",
  "contentColorCode": null
}
```

- 길바닥 방명록의 각 콘텐츠는 저장된 값을 그대로 반환하며, 해당 콘텐츠가 없으면 null을 반환한다.

---

### 오류 응답 데이터

Status Code : `404 Not Found`

`targetType`에 해당하는 조회 대상이 존재하지 않거나 소프트 삭제된 경우

```json
{
  "code": "MAP_MODAL_TARGET_NOT_FOUND"
}
```

## 지도 장소 상세 조회

- http 메서드: get
- domain: map
- endpoint: /api/v1/map/locations/{locationId}

### API 설명

사용자가 장소 모달에서 상세보기를 눌러 장소 상세 화면에 진입할 때 호출한다.

Path로 전달받은 `locationId`로 LOCATION을 조회하고, 현재 사용자 좌표를 사용해 장소까지의 거리와 예상 이동 시간을 다시 계산한다.

장소명, 장소 분류, 거리, 예상 이동 시간, 주소, 현재 사용자의 방문 여부, TourAPI 상세 설명과 상세 이미지, 근처 추천 미션, 해당 장소의 전체 방명록과 작성자 AR 캐릭터 이미지, 해당 장소에 직접 연결된 미션 정보를 반환한다.

장소 및 미션 이미지는 부가 정보이므로 TourAPI 인증키 미설정, 통신 실패 또는 이미지 없음으로 조회하지 못해도 전체 API를 실패시키지 않고 해당 이미지 필드만 null로 반환한다.

---

### 요청 Query

| 자료형 | 변수명          | 필수 여부 | 설명                                |
| ------ | --------------- | --------- | ----------------------------------- |
| number | `userLatitude`  | 필수      | 현재 사용자 위치의 위도. `-90~90`   |
| number | `userLongitude` | 필수      | 현재 사용자 위치의 경도. `-180~180` |

**요청 예시**

```
GET /api/v1/map/locations/39?userLatitude=33.4524&userLongitude=126.9248
```

- 상세 API는 이전 모달 요청의 좌표를 서버에 보관하지 않으므로 거리와 예상 이동 시간을 계산하기 위해 사용자 좌표를 다시 받는다.
- 위도와 경도의 소수 부분을 최대한 보존해서 전송한다.

---

### 요청 Path

| 자료형  | 변수명       | 설명                    |
| ------- | ------------ | ----------------------- |
| integer | `locationId` | 상세 조회할 LOCATION ID |

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : `200 OK`

| 자료형   | 변수명                                                 | 설명                                                                                |
| -------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| string   | `locationTitle`                                        | 장소 이름. `LOCATION.location_title`                                                |
| string   | `locationCategory`                                     | 장소 분류. `LOCATION.location_category`                                             |
| integer  | `distanceMeter`                                        | 현재 사용자 위치와 장소 사이의 직선거리(m)                                          |
| integer  | `durationMinutes`                                      | 현재 사용자 위치에서 장소까지의 예상 이동 시간(분)                                  |
| string   | `locationAddress`                                      | 장소 주소. `LOCATION.location_address`                                              |
| boolean  | `isVisited`                                            | 현재 사용자의 해당 장소 방문 여부. 방문 기록이 한 건 이상 있으면 true, 없으면 false |
| string   | null                                                   | `locationDescription`                                                               | TourAPI `detailCommon2.overview`에서 HTML 태그·엔티티와 불필요한 공백을 정리한 일반 문자열. 값이 없거나 조회하지 못하면 null |
| string[] | null                                                   | `locationImageUrls`                                                                 | TourAPI `detailImage2.originimgurl` 상세 이미지 URL 목록. 최대 5장이고 이미지가 없거나 조회하지 못하면 null                  |
| array    | `nearbyMissions`                                       | 근처에서 할 수 있는 임시 추천 미션 목록. 최대 3개이며 없으면 빈 배열                |
| integer  | `nearbyMissions[].missionId`                           | `missionType`에 해당하는 유형별 세부 미션 ID                                        |
| string   | `nearbyMissions[].missionType`                         | 미션 유형. `TREASURE                                                                | COOPERATIVE`                                                                                                                 |
| string   | `nearbyMissions[].missionTitle`                        | 미션 제목                                                                           |
| string   | null                                                   | `nearbyMissions[].description`                                                      | 미션 설명. 없으면 null                                                                                                       |
| boolean  | `nearbyMissions[].isCompleted`                         | 현재 사용자의 해당 미션 완료 여부                                                   |
| object   | `nearbyMissions[].rewardDetail`                        | 해당 미션의 전체 보상 정보와 보상별 수령 여부                                       |
| object   | `nearbyMissions[].rewardDetail.arCharacter`            | AR 캐릭터 보상 정보                                                                 |
| integer  | `nearbyMissions[].rewardDetail.arCharacter.id`         | AR 캐릭터 ID                                                                        |
| string   | `nearbyMissions[].rewardDetail.arCharacter.name`       | AR 캐릭터 이름                                                                      |
| string   | `nearbyMissions[].rewardDetail.arCharacter.imageUrl`   | AR 캐릭터 이미지 URL                                                                |
| boolean  | `nearbyMissions[].rewardDetail.arCharacter.isReceived` | 현재 사용자의 AR 캐릭터 보상 수령 여부                                              |
| object   | `nearbyMissions[].rewardDetail.point`                  | 포인트 보상 정보                                                                    |
| integer  | `nearbyMissions[].rewardDetail.point.amount`           | 포인트 보상량                                                                       |
| boolean  | `nearbyMissions[].rewardDetail.point.isReceived`       | 현재 사용자의 포인트 보상 수령 여부                                                 |
| object   | `nearbyMissions[].rewardDetail.coupon`                 | 쿠폰 보상 정보                                                                      |
| string   | `nearbyMissions[].rewardDetail.coupon.couponLocation`  | 쿠폰 사용처                                                                         |
| integer  | `nearbyMissions[].rewardDetail.coupon.couponPrice`     | 쿠폰 금액                                                                           |
| boolean  | `nearbyMissions[].rewardDetail.coupon.isReceived`      | 현재 사용자의 쿠폰 보상 수령 여부                                                   |
| string   | `nearbyMissions[].locationTitle`                       | 해당 미션이 진행되는 장소 이름. `LOCATION.location_title`                           |
| string   | null                                                   | `nearbyMissions[].representativeImageUrl`                                           | 해당 미션 장소의 TourAPI `firstimage`. 이미지가 없거나 조회하지 못하면 null                                                  |
| array    | `guestbooks`                                           | 해당 장소를 참조하는 삭제되지 않은 전체 방명록 목록. 없으면 빈 배열                 |
| integer  | `guestbooks[].id`                                      | 방명록 ID                                                                           |
| string   | null                                                   | `guestbooks[].missionTitle`                                                         | 방명록이 참조하는 미션 제목. 참조하는 미션이 없으면 null                                                                     |
| string   | null                                                   | `guestbooks[].representativeImageUrl`                                               | 방명록 이미지 배열의 첫 번째 이미지 URL. 이미지가 없으면 null                                                                |
| integer  | `guestbooks[].userId`                                  | 방명록 작성자 사용자 ID                                                             |
| string   | `guestbooks[].userNickname`                            | 방명록 작성자 닉네임                                                                |
| string   | null                                                   | `guestbooks[].characterImgUrl`                                                      | 방명록 작성자에게 배정된 AR 캐릭터 이미지 URL. 배정된 캐릭터가 없으면 null                                                   |
| string   | `guestbooks[].visitedAt`                               | 방문·작성일. `GUESTBOOK.visited_at` 기준, `YYYY-MM-DD` 형식                         |
| string   | null                                                   | `guestbooks[].contentWriting`                                                       | 방명록 글 내용. 없으면 null                                                                                                  |
| object   | null                                                   | `locationMission`                                                                   | 해당 장소에 직접 연결된 단일 미션 정보. 없으면 null                                                                          |
| integer  | `locationMission.missionId`                            | `missionType`에 해당하는 유형별 세부 미션 ID                                        |
| string   | `locationMission.missionType`                          | 미션 유형. `TREASURE                                                                | COOPERATIVE`                                                                                                                 |
| string   | `locationMission.missionTitle`                         | 미션 제목                                                                           |
| string   | null                                                   | `locationMission.description`                                                       | 미션 설명. 없으면 null                                                                                                       |
| boolean  | `locationMission.isCompleted`                          | 현재 사용자의 해당 미션 완료 여부                                                   |
| object   | `locationMission.rewardDetail`                         | 해당 미션의 전체 보상 정보와 보상별 수령 여부                                       |
| object   | `locationMission.rewardDetail.arCharacter`             | AR 캐릭터 보상 정보                                                                 |
| integer  | `locationMission.rewardDetail.arCharacter.id`          | AR 캐릭터 ID                                                                        |
| string   | `locationMission.rewardDetail.arCharacter.name`        | AR 캐릭터 이름                                                                      |
| string   | `locationMission.rewardDetail.arCharacter.imageUrl`    | AR 캐릭터 이미지 URL                                                                |
| boolean  | `locationMission.rewardDetail.arCharacter.isReceived`  | 현재 사용자의 AR 캐릭터 보상 수령 여부                                              |
| object   | `locationMission.rewardDetail.point`                   | 포인트 보상 정보                                                                    |
| integer  | `locationMission.rewardDetail.point.amount`            | 포인트 보상량                                                                       |
| boolean  | `locationMission.rewardDetail.point.isReceived`        | 현재 사용자의 포인트 보상 수령 여부                                                 |
| object   | `locationMission.rewardDetail.coupon`                  | 쿠폰 보상 정보                                                                      |
| string   | `locationMission.rewardDetail.coupon.couponLocation`   | 쿠폰 사용처                                                                         |
| integer  | `locationMission.rewardDetail.coupon.couponPrice`      | 쿠폰 금액                                                                           |
| boolean  | `locationMission.rewardDetail.coupon.isReceived`       | 현재 사용자의 쿠폰 보상 수령 여부                                                   |

```json
{
  "locationTitle": "성산일출봉",
  "locationCategory": "관광지",
  "distanceMeter": 1200,
  "durationMinutes": 15,
  "locationAddress": "제주특별자치도 서귀포시 성산읍 일출로 284-12",
  "isVisited": true,
  "locationDescription": "제주 동쪽 바다 위로 솟아오른 응회구로, 정상에서 분화구와 해안 풍경을 함께 볼 수 있습니다.",
  "locationImageUrls": [
    "https://example.com/images/locations/39/detail-1.jpg",
    "https://example.com/images/locations/39/detail-2.jpg",
    "https://example.com/images/locations/39/detail-3.jpg"
  ],
  "nearbyMissions": [
    {
      "missionId": 2,
      "missionType": "COOPERATIVE",
      "missionTitle": "함께 키우는 귤나무",
      "description": "역할을 나누어 제주 귤나무를 함께 완성하는 미션입니다.",
      "isCompleted": false,
      "rewardDetail": {
        "arCharacter": {
          "id": 4,
          "name": "귤밭 지킴이",
          "imageUrl": "https://example.com/images/ar-characters/4.png",
          "isReceived": false
        },
        "point": {
          "amount": 150,
          "isReceived": false
        },
        "coupon": {
          "couponLocation": "성산 기념품점",
          "couponPrice": 5000,
          "isReceived": false
        }
      },
      "locationTitle": "귤림성",
      "representativeImageUrl": "https://example.com/images/locations/12/firstimage.jpg"
    }
  ],
  "guestbooks": [
    {
      "id": 300,
      "missionTitle": "성산일출봉 보물찾기",
      "representativeImageUrl": "https://example.com/images/guestbooks/guestbook-300.jpg",
      "userId": 1,
      "userNickname": "활발한 귤돌이",
      "characterImgUrl": "https://example.com/images/ar-characters/1.png",
      "visitedAt": "2026-01-15",
      "contentWriting": "정상에서 보는 풍경이 정말 좋았어요."
    },
    {
      "id": 302,
      "missionTitle": null,
      "representativeImageUrl": null,
      "userId": 2,
      "userNickname": "씩씩한 고래",
      "characterImgUrl": null,
      "visitedAt": "2026-01-12",
      "contentWriting": null
    }
  ],
  "locationMission": {
    "missionId": 1,
    "missionType": "TREASURE",
    "missionTitle": "성산일출봉 보물찾기",
    "description": "성산일출봉 곳곳에 숨겨진 보물을 찾아보세요.",
    "isCompleted": true,
    "rewardDetail": {
      "arCharacter": {
        "id": 3,
        "name": "점박이 물범",
        "imageUrl": "https://example.com/images/ar-characters/3.png",
        "isReceived": true
      },
      "point": {
        "amount": 100,
        "isReceived": true
      },
      "coupon": {
        "couponLocation": "성산 카페",
        "couponPrice": 3000,
        "isReceived": false
      }
    }
  }
}
```

- `locationImageUrls`는 `LOCATION.content_id`로 TourAPI `detailImage2`를 조회하고 비어 있지 않은 `originimgurl`을 최대 5개 반환한다. 이미지가 1~4장이면 조회된 수만큼만 반환하고, 이미지가 없거나 조회에 실패하면 빈 배열이 아니라 null을 반환한다.
- 상세 이미지는 TourAPI 응답의 `serialnum ASC` 순서로 정렬하고, 같은 URL은 한 번만 포함한다.
- `nearbyMissions`는 별도 추천 함수에서 조회하며, 정식 추천 로직이 적용되기 전까지 보물찾기와 협동 미션 중 최대 3개를 중복 없이 임의로 선택한다.
- 현재 장소에 연결된 미션도 추천 후보에 포함할 수 있다.
- 현재 사용자가 이미 완료한 미션은 추천 후보에서 제외한다.
- 요청할 때마다 추천 결과가 달라져도 된다.
- 추천 가능한 미션이 없으면 `nearbyMissions`는 빈 배열을 반환한다.
- `nearbyMissions[].locationTitle`은 추천 미션이 진행되는 장소 이름이며, 상세 조회 중인 장소의 이름이 아니다. 추천 대상은 장소를 가진 보물찾기·협동 미션뿐이므로 항상 값이 있다.
- `locationMission`은 상세 조회 중인 장소의 미션이므로 최상위 `locationTitle`과 중복되는 장소 이름을 따로 반환하지 않는다.
- `nearbyMissions[].representativeImageUrl`은 미션이 연결된 `LOCATION.content_id`로 TourAPI `detailCommon2`를 직접 조회하여 `firstimage`를 사용한다. `firstimage`가 없으면 `firstimage2`를 사용하고, 둘 다 없거나 조회에 실패하면 null이다. 장소명 기반 `searchKeyword2`는 사용하지 않는다.
- `locationMission`과 `nearbyMissions[]`의 `missionId`는 공통 MISSION ID가 아니라 `missionType`에 해당하는 유형별 세부 미션 ID다.
- 두 미션 응답의 `rewardDetail`은 수령 여부와 관계없이 AR 캐릭터, 포인트, 쿠폰 전체 정보를 반환하며, 각 `isReceived`는 현재 사용자가 해당 미션의 모든 진행도 중 그 보상을 한 번이라도 지급받았는지를 나타낸다.
- 두 미션 응답의 `isCompleted`는 현재 사용자가 해당 미션을 한 번이라도 완료했는지를 나타내며 보상 수령 여부와 독립적으로 계산한다.
- `isVisited`는 현재 사용자와 조회 장소가 일치하는 `VISITED_LOCATION`의 존재 여부를 나타낸다. 방명록 작성 여부나 미션 완료 여부와는 관계없다.
- `guestbooks`는 해당 장소를 참조하는 삭제되지 않은 방명록을 `visited_at DESC`, 같은 날짜에는 방명록 ID 내림차순으로 모두 반환한다.
- `guestbooks[].characterImgUrl`은 방명록 작성자의 `USER.ar_character_id`로 연결된 `AR_CHARACTER.character_img_url`이며, 작성자에게 배정된 AR 캐릭터가 없으면 null이다.
- 방명록에 연결된 미션이 없으면 `missionTitle`은 null이다.
- 방명록 이미지 배열이 없거나 비어 있으면 `representativeImageUrl`은 null이다.
- 방명록에 글이 없으면 `contentWriting`은 null이다.
- 하나의 장소에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다.
- 해당 장소에 직접 연결된 미션이 없으면 `locationMission = null`을 반환한다.

---

### 오류 응답 데이터

Status Code : `404 Not Found`

`locationId`에 해당하는 장소가 존재하지 않는 경우

```json
{
  "code": "LOCATION_NOT_FOUND"
}
```

## 지도 검색 결과 조회

- http 메서드: get
- domain: map
- endpoint: /api/v1/map/search

### API 설명

사용자가 지도 검색 화면에서 검색어를 입력할 때 호출한다.

한글 입력 중 조합 중인 글자에는 호출하지 않고, `성`, `성산`, `성산일`처럼 한글 음절이 완성될 때마다 프론트가 API를 호출한다.

백엔드는 검색어가 `LOCATION.location_title`에 포함된 모든 장소를 조회하고, 장소에 미션이 없는지 또는 보물찾기·협동 미션이 연결되어 있는지에 따라 두 배열로 분류하여 반환한다.

이 API는 `Authorization: Bearer {accessToken}` 헤더가 필수이며, 백엔드는 액세스 토큰으로 현재 사용자의 존재 여부를 검증한다.

검색 결과에 표시할 이미지는 `LOCATION.content_id`를 사용해 TourAPI에서 조회한 `firstimage`를 사용하고, 사용자와 장소 사이의 거리는 공통 거리 모듈로 계산한다.

---

### 요청 Query

| 자료형 | 변수명          | 필수 여부 | 설명                                                                              |
| ------ | --------------- | --------- | --------------------------------------------------------------------------------- |
| string | `keyword`       | 필수      | 장소 이름에 포함되는지 검색할 키워드. 앞뒤 공백을 제거한 후 한 글자 이상이어야 함 |
| number | `userLatitude`  | 필수      | 사용자의 현재 GPS 위도. 장소까지의 거리 계산에 사용                               |
| number | `userLongitude` | 필수      | 사용자의 현재 GPS 경도. 장소까지의 거리 계산에 사용                               |

**요청 예시**

```
GET /api/v1/map/search?keyword=성&userLatitude=33.4524&userLongitude=126.9248
```

- 한글 조합 완료 여부는 프론트에서 판단하며 조합 중인 글자에는 API를 호출하지 않는다.
- 위도와 경도의 소수 부분을 최대한 보존해서 전송한다.

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : `200 OK`

| 자료형  | 변수명                                    | 설명                                                                          |
| ------- | ----------------------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------- |
| array   | `recommendedLocations`                    | 장소 이름에 검색어가 포함되고 연결된 미션이 없는 장소 전체 목록               |
| integer | `recommendedLocations[].locationId`       | LOCATION ID                                                                   |
| string  | `recommendedLocations[].locationTitle`    | 장소 이름                                                                     |
| string  | `recommendedLocations[].locationCategory` | 장소 카테고리. `LOCATION.location_category`                                   |
| string  | null                                      | `recommendedLocations[].representativeImageUrl`                               | TourAPI `firstimage` URL. 이미지가 없거나 조회하지 못하면 null |
| integer | `recommendedLocations[].distanceMeter`    | 현재 사용자 위치에서 장소까지의 직선거리(m)                                   |
| array   | `missionLocations`                        | 장소 이름에 검색어가 포함되고 보물찾기 또는 협동 미션이 연결된 장소 전체 목록 |
| integer | `missionLocations[].locationId`           | LOCATION ID                                                                   |
| integer | `missionLocations[].missionId`            | `missionType`에 해당하는 유형별 세부 미션 ID                                  |
| string  | `missionLocations[].missionType`          | 미션 유형. `TREASURE                                                          | COOPERATIVE`                                                   |
| string  | `missionLocations[].locationTitle`        | 미션이 연결된 장소 이름                                                       |
| string  | `missionLocations[].missionTitle`         | 세부 미션이 참조하는 공통 미션 제목                                           |
| string  | null                                      | `missionLocations[].representativeImageUrl`                                   | TourAPI `firstimage` URL. 이미지가 없거나 조회하지 못하면 null |
| integer | `missionLocations[].distanceMeter`        | 현재 사용자 위치에서 미션 장소까지의 직선거리(m)                              |

```json
{
  "recommendedLocations": [
    {
      "locationId": 39,
      "locationTitle": "성산일출봉",
      "locationCategory": "자연",
      "representativeImageUrl": "https://example.com/images/locations/seongsan-ilchulbong.jpg",
      "distanceMeter": 1200
    },
    {
      "locationId": 41,
      "locationTitle": "성산포항",
      "locationCategory": "항구",
      "representativeImageUrl": null,
      "distanceMeter": 3500
    }
  ],
  "missionLocations": [
    {
      "locationId": 52,
      "missionId": 3,
      "missionType": "TREASURE",
      "locationTitle": "성산 해안 산책로",
      "missionTitle": "보물찾기",
      "representativeImageUrl": "https://example.com/images/locations/seongsan-coast.jpg",
      "distanceMeter": 5100
    },
    {
      "locationId": 61,
      "missionId": 2,
      "missionType": "COOPERATIVE",
      "locationTitle": "성읍민속마을",
      "missionTitle": "함께 키우는 귤나무",
      "representativeImageUrl": "https://example.com/images/locations/seongeup-village.jpg",
      "distanceMeter": 8200
    }
  ]
}
```

- 검색은 미션 제목이 아니라 `LOCATION.location_title`을 기준으로 수행한다.
- 검색어가 장소 이름의 시작·중간·끝 어디에 포함되어 있어도 결과에 포함한다.
- 검색된 장소에 미션이 없으면 `recommendedLocations`에만 포함한다.
- 검색된 장소에 미션이 있으면 `missionLocations`에만 포함한다.
- 하나의 장소에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다.
- 두 배열은 페이지네이션과 개수 제한 없이 조건을 만족하는 전체 장소를 반환한다.
- 각 배열은 `distanceMeter ASC`, 거리가 같으면 `locationId ASC` 순으로 반환한다.
- 결과가 없으면 해당 배열을 생략하지 않고 빈 배열로 반환한다.
- 대표 이미지는 TourAPI `firstimage`를 사용하며, 이미지가 없거나 TourAPI 이미지 조회에 실패하면 null로 반환하고 전체 검색은 정상 처리한다.
- 거리 계산은 `app/common/distance.py`의 공통 로직을 사용한다.
- 추천 장소와 미션 장소의 조회 및 응답 변환 로직은 각각 별도 함수로 분리한다.
- `missionLocations[].missionId`는 공통 `MISSION.id`가 아니라 `missionType`에 해당하는 유형별 세부 미션 ID다.

---

### 오류 응답 데이터
