## 방명록 저장
- http 메서드: POST
- 엔드포인트: `/api/v1/guestbooks`
- 도메인: guestbook

### API 설명

사용자가 일반 방명록 또는 길바닥 방명록을 저장할 때 호출한다.

요청 Body의 `guestbookType`으로 저장할 방명록 종류를 구분한다. `guestbookType`이 `GENERAL`이면 특정 장소에 귀속되는 일반 방명록으로 저장하고, `ROAD`이면 특정 LOCATION에 귀속되지 않고 사용자가 지정한 지도 좌표에 표시되는 길바닥 방명록으로 저장한다.

일반 방명록은 `locationId`와 `visitedAt`을 필수로 받는다. 길바닥 방명록은 `locationAlias`, `latitude`, `longitude`, `visitedAt`을 필수로 받는다.

방명록 콘텐츠는 모두 선택 값이다. 이미지, 글, 오디오, 날씨, 색상 정보를 받을 수도 있고 받지 않을 수도 있다. 일반 방명록은 미션 수행으로 생성된 방명록일 수 있으므로 `missionId`를 선택적으로 받을 수 있다. `missionId`가 없으면 일반 장소 방문 방명록으로 저장한다.

서버는 전달받은 값을 DB에 저장하고 응답 Body 없이 `204 No Content`를 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
|---|---:|:---:|---|
| `guestbookType` | string | O | 방명록 유형. `GENERAL \| ROAD` |
| `locationId` | number | 조건부 | 일반 방명록이면 필수. 길바닥 방명록이면 사용하지 않음 |
| `locationAlias` | string | 조건부 | 길바닥 방명록이면 필수. 지도에 표시할 위치 별칭 |
| `latitude` | number | 조건부 | 길바닥 방명록이면 필수. 방명록이 표시될 위도 |
| `longitude` | number | 조건부 | 길바닥 방명록이면 필수. 방명록이 표시될 경도 |
| `visitedAt` | string | O | 방문 날짜. `yyyy-MM-dd` 형식 |
| `contentImageUrls` | string[] \| null | X | 방명록 이미지 URL 목록. 없으면 `null` 또는 빈 배열 |
| `contentWriting` | string \| null | X | 방명록 글 내용. 없으면 `null` |
| `contentAudioUrls` | string[] \| null | X | 방명록 오디오 URL 목록. 없으면 `null` 또는 빈 배열 |
| `contentWeather` | string \| null | X | 방명록 날씨 정보. 없으면 `null` |
| `contentColorCode` | string \| null | X | 방명록 색상 코드. 없으면 `null` |
| `missionId` | number \| null | X | 일반 방명록에 연결할 미션 id. 연결된 미션이 없으면 `null` |

일반 방명록 요청 예시

```json
{
  "guestbookType": "GENERAL",
  "locationId": 39,
  "visitedAt": "2026-08-21",
  "contentImageUrls": [
    "https://example.com/guestbooks/39/image-1.jpg"
  ],
  "contentWriting": "현애원 산책하기 좋았어요.",
  "contentAudioUrls": null,
  "contentWeather": "맑음",
  "contentColorCode": "#84C7AE",
  "missionId": 501
}
```

길바닥 방명록 요청 예시

```json
{
  "guestbookType": "ROAD",
  "locationAlias": "성산 바다 앞",
  "latitude": 33.4582,
  "longitude": 126.9331,
  "visitedAt": "2026-08-21",
  "contentImageUrls": [],
  "contentWriting": null,
  "contentAudioUrls": null,
  "contentWeather": "흐림",
  "contentColorCode": "#7AA7D9",
  "missionId": null
}
```

- `guestbookType=GENERAL`이면 `locationId`는 필수이다.
- `guestbookType=ROAD`이면 `locationAlias`, `latitude`, `longitude`는 필수이다.
- `guestbookType=ROAD`에서는 `missionId`를 사용하지 않고 `null`로 보낸다.
- 콘텐츠 필드는 사용자가 입력하거나 첨부한 값만 전달하면 된다.

---

### 정상 응답 데이터
Status Code : 204

응답 Body 없음

---

### 오류 응답 데이터
Status Code : 400

`guestbookType`이 유효하지 않은 경우

```json
{
  "code": "GUESTBOOK_TYPE_INVALID"
}
```

Status Code : 400

일반 방명록 요청에서 `locationId`가 누락된 경우

```json
{
  "code": "GUESTBOOK_LOCATION_REQUIRED"
}
```

Status Code : 400

길바닥 방명록 요청에서 `locationAlias`, `latitude`, `longitude` 중 하나 이상이 누락된 경우

```json
{
  "code": "ROAD_GUESTBOOK_LOCATION_REQUIRED"
}
```

Status Code : 404

`locationId`에 해당하는 장소가 존재하지 않는 경우

```json
{
  "code": "LOCATION_NOT_FOUND"
}
```

Status Code : 404

`missionId`가 전달되었지만 해당 미션이 존재하지 않는 경우

```json
{
  "code": "MISSION_NOT_FOUND"
}
```



## 방명록 조회
- http 메서드: GET
- 엔드포인트: `/api/v1/guestbooks`
- 도메인: guestbook

### API 설명

로그인한 사용자가 작성한 전체 방명록 목록을 조회할 때 호출한다.

일반 방명록과 길바닥 방명록을 구분해서 반환한다. 일반 방명록은 특정 LOCATION에 귀속된 방명록이며, 길바닥 방명록은 특정 LOCATION에 귀속되지 않고 사용자가 지정한 지도 좌표에 표시되는 방명록이다.

페이지네이션을 적용하여 최신 저장순으로 반환한다. `page`는 0부터 시작하고, `size`는 한 페이지에 조회할 방명록 개수이다.

응답의 `generalGuestbooks`에는 일반 방명록 목록을 반환하고, `roadGuestbooks`에는 길바닥 방명록 목록을 반환한다. 각 방명록은 DB에 저장된 전체 정보를 반환한다.

---

### 요청 Query

| 필드 | 타입 | 필수 | 설명 |
|---|---:|:---:|---|
| `page` | number | X | 조회할 페이지 번호. 0부터 시작. 기본값 `0` |
| `size` | number | X | 한 페이지에 조회할 방명록 개수. 기본값 `30` |

요청 예시

```text
GET /api/v1/guestbooks?page=0&size=30
```

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 200

방명록 목록을 정상적으로 조회한 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `generalGuestbooks` | object[] | 일반 방명록 목록 |
| `generalGuestbooks[].id` | number | 일반 방명록 id |
| `generalGuestbooks[].location` | object | 방명록이 작성된 장소 정보 |
| `generalGuestbooks[].location.id` | number | LOCATION id |
| `generalGuestbooks[].location.locationTitle` | string | 장소 이름 |
| `generalGuestbooks[].location.locationAddress` | string | 장소 주소 |
| `generalGuestbooks[].location.locationCategory` | string | 장소 카테고리 |
| `generalGuestbooks[].location.latitude` | number | 장소 위도 |
| `generalGuestbooks[].location.longitude` | number | 장소 경도 |
| `generalGuestbooks[].visitedAt` | string | 방문 날짜. `yyyy-MM-dd` 형식 |
| `generalGuestbooks[].contentImageUrls` | string[] \| null | 방명록 이미지 URL 목록. 없으면 `null` |
| `generalGuestbooks[].contentWriting` | string \| null | 방명록 글 내용. 없으면 `null` |
| `generalGuestbooks[].contentAudioUrls` | string[] \| null | 방명록 오디오 URL 목록. 없으면 `null` |
| `generalGuestbooks[].contentWeather` | string \| null | 방명록 날씨 정보. 없으면 `null` |
| `generalGuestbooks[].contentColorCode` | string \| null | 방명록 색상 코드. 없으면 `null` |
| `generalGuestbooks[].savedAt` | string | 방명록 저장 시각 |
| `generalGuestbooks[].mission` | object \| null | 방명록에 연결된 미션 정보. 연결된 미션이 없으면 `null` |
| `generalGuestbooks[].mission.id` | number | 미션 id |
| `generalGuestbooks[].mission.missionType` | string | 미션 유형. `CULTURE \| COOPERATIVE \| TREASURE` |
| `generalGuestbooks[].mission.missionTitle` | string | 미션 이름 |
| `roadGuestbooks` | object[] | 길바닥 방명록 목록 |
| `roadGuestbooks[].id` | number | 길바닥 방명록 id |
| `roadGuestbooks[].locationAlias` | string | 지도에 표시할 위치 별칭 |
| `roadGuestbooks[].latitude` | number | 길바닥 방명록 위도 |
| `roadGuestbooks[].longitude` | number | 길바닥 방명록 경도 |
| `roadGuestbooks[].visitedAt` | string | 방문 날짜. `yyyy-MM-dd` 형식 |
| `roadGuestbooks[].contentImageUrls` | string[] \| null | 방명록 이미지 URL 목록. 없으면 `null` |
| `roadGuestbooks[].contentWriting` | string \| null | 방명록 글 내용. 없으면 `null` |
| `roadGuestbooks[].contentAudioUrls` | string[] \| null | 방명록 오디오 URL 목록. 없으면 `null` |
| `roadGuestbooks[].contentWeather` | string \| null | 방명록 날씨 정보. 없으면 `null` |
| `roadGuestbooks[].contentColorCode` | string \| null | 방명록 색상 코드. 없으면 `null` |
| `roadGuestbooks[].savedAt` | string | 방명록 저장 시각 |
| `pageInfo` | object | 페이지 정보 |
| `pageInfo.page` | number | 현재 페이지 번호 |
| `pageInfo.size` | number | 요청한 페이지 크기 |
| `pageInfo.hasNext` | boolean | 다음 페이지 존재 여부 |

```json
{
  "generalGuestbooks": [
    {
      "id": 101,
      "location": {
        "id": 39,
        "locationTitle": "현애원",
        "locationAddress": "제주특별자치도 서귀포시 성산읍",
        "locationCategory": "관광지",
        "latitude": 33.4582,
        "longitude": 126.9331
      },
      "visitedAt": "2026-08-21",
      "contentImageUrls": [
        "https://example.com/guestbooks/101/image-1.jpg"
      ],
      "contentWriting": "현애원 산책하기 좋았어요.",
      "contentAudioUrls": null,
      "contentWeather": "맑음",
      "contentColorCode": "#84C7AE",
      "savedAt": "2026-08-21T14:20:00",
      "mission": {
        "id": 501,
        "missionType": "TREASURE",
        "missionTitle": "현애원의 숨은 보물 찾기"
      }
    }
  ],
  "roadGuestbooks": [
    {
      "id": 201,
      "locationAlias": "성산 바다 앞",
      "latitude": 33.4582,
      "longitude": 126.9331,
      "visitedAt": "2026-08-21",
      "contentImageUrls": [],
      "contentWriting": null,
      "contentAudioUrls": null,
      "contentWeather": "흐림",
      "contentColorCode": "#7AA7D9",
      "savedAt": "2026-08-21T15:10:00"
    }
  ],
  "pageInfo": {
    "page": 0,
    "size": 30,
    "hasNext": false
  }
}
```

- 일반 방명록과 길바닥 방명록을 합친 전체 방명록 기준으로 페이지네이션한다.
- 한 페이지 안에서 일반 방명록과 길바닥 방명록을 각각 배열로 분리해서 반환한다.
- 일반 방명록에 연결된 미션이 없으면 `mission`은 `null`로 반환한다.
- 방명록 콘텐츠가 없으면 해당 콘텐츠 필드는 `null` 또는 빈 배열로 반환한다.

---

### 오류 응답 데이터

없음
