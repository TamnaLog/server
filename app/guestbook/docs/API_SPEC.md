## 방명록 작성 가능 여부 조회
- http 메서드: get
- domain: guestbook
- endpoint: /api/v1/guestbooks/write-availability

### API 설명

현재 사용자가 특정 장소의 방명록을 작성할 수 있는지 조회할 때 호출한다.

서버는 먼저 `locationId`에 해당하는 장소의 존재 여부를 확인한 뒤, 인증된 현재 사용자와 해당 장소에 대응하는 `VISITED_LOCATION` 방문 기록을 조회한다.

방문 기록이 하나 이상 존재하면 `canWrite=true`와 장소 정보 및 가장 최근 방문 시각을 반환한다. 동일한 장소를 여러 번 방문한 경우 `visited_at DESC`, 방문 시각이 같으면 방문 기록 id 내림차순으로 가장 최근 기록 한 건을 선택한다.

방문 기록이 없으면 `canWrite=false`와 `visitedLocation=null`을 반환한다.

이 API는 방문 여부만 판단하며, 해당 장소에 방명록을 이미 작성했는지는 확인하지 않는다.

---

### 요청 Query

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `locationId` | number | O | 방명록 작성 가능 여부를 확인할 장소 id |

요청 예시

```
GET /api/v1/guestbooks/write-availability?locationId=39
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

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `canWrite` | boolean | 현재 사용자의 해당 장소 방명록 작성 가능 여부 |
| `visitedLocation` | object | null | 가장 최근 방문 장소 정보. 방문 기록이 없으면 `null` |
| `visitedLocation.locationId` | number | 방문한 장소 id |
| `visitedLocation.locationName` | string | 방문한 장소명 |
| `visitedLocation.visitedAt` | string | 가장 최근 방문 시각. KST 기준 offset 없는 ISO 8601 형식 |

방문 기록이 있는 경우

```json
{
  "canWrite": true,
  "visitedLocation": {
    "locationId": 39,
    "locationName": "섭지코지",
    "visitedAt": "2026-08-29T14:20:00"
  }
}
```

방문 기록이 없는 경우

```json
{
  "canWrite": false,
  "visitedLocation": null
}
```

---

### 오류 응답 데이터

Status Code : 404

`locationId`에 해당하는 장소가 존재하지 않는 경우

```json
{
  "code": "LOCATION_NOT_FOUND"
}
```


## 방명록 작성
- http 메서드: post
- domain: guestbook
- endpoint: /api/v1/guestbooks

### API 설명

현재 사용자가 일반 방명록 또는 길바닥 방명록을 작성할 때 호출한다.

요청은 이미지와 오디오 파일을 함께 받을 수 있도록 `multipart/form-data`를 사용하며, `guestbookType`의 `GENERAL | ROAD` 값으로 저장 테이블과 조건부 필드를 구분한다.

`GENERAL`은 등록된 장소에 작성하는 일반 방명록이다. `locationId`에 해당하는 장소가 존재하고 현재 사용자의 `VISITED_LOCATION` 방문 이력이 한 건 이상 있어야 한다. 방문 이력의 날짜와 요청의 `visitedAt`이 같을 필요는 없다. 방문 이력이 한 번이라도 있으면 같은 장소에 횟수 제한 없이 방명록을 계속 작성할 수 있으며, 기존 방명록 존재 여부로 중복을 차단하지 않는다.

일반 방명록의 `missionId`는 선택 값이다. 전달된 미션이 존재하고 현재 사용자가 완료한 미션이면 `GUESTBOOK.mission_id`에 저장한다. 미션은 존재하지만 현재 사용자가 완료하지 않았다면 방명록 작성 자체는 허용하고 `mission_id=null`로 저장한다. 존재하지 않는 미션이면 오류를 반환한다.

`ROAD`는 특정 LOCATION에 귀속되지 않는 길바닥 방명록이다. `locationAlias`, `latitude`, `longitude`를 받아 지도에 표시할 위치를 저장하며 방문 이력을 검사하지 않는다. `locationId`와 `missionId`는 사용하지 않고 `null`로 저장한다.

이미지와 오디오 파일은 Azure Blob Storage에 저장하고, MySQL에는 업로드된 Blob URL 배열만 저장한다. 나머지 콘텐츠와 위치·방문 정보는 MySQL에 저장한다. 콘텐츠 5종은 모두 선택 값이며 전부 전달하지 않아도 방명록을 작성할 수 있다.

저장 성공 시 새로 저장한 방명록 정보를 중첩 객체 없이 1-depth 구조로 반환한다. 유형에서 사용하지 않는 필드도 생략하지 않고 `null`로 반환한다.

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
| --- | --- | --- | --- |
| `guestbookType` | string | O | 방명록 유형. `GENERAL | ROAD` |
| `locationId` | number | null | 조건부 | `GENERAL`이면 필수. 저장할 `LOCATION.id`. `ROAD`이면 미전송 |
| `locationAlias` | string | null | 조건부 | `ROAD`이면 필수. 최대 100자. `GENERAL`이면 미전송 |
| `latitude` | number | null | 조건부 | `ROAD`이면 필수. 길바닥 방명록 위도. -90 이상 90 이하. `GENERAL`이면 미전송 |
| `longitude` | number | null | 조건부 | `ROAD`이면 필수. 길바닥 방명록 경도. -180 이상 180 이하. `GENERAL`이면 미전송 |
| `visitedAt` | string | O | 방명록에 기록할 방문 날짜. `yyyy-MM-dd` 형식 |
| `imageFiles` | binary[] | null | X | 방명록 이미지 파일 목록. 여러 파일은 같은 필드명을 반복해서 전송. 없으면 미전송 |
| `contentWriting` | string | null | X | 방명록 글 내용. 최대 500자. 없으면 미전송 |
| `audioFiles` | binary[] | null | X | 방명록 오디오 파일 목록. 여러 파일은 같은 필드명을 반복해서 전송. 없으면 미전송 |
| `contentWeather` | string | null | X | 날씨 정보. 최대 20자. 없으면 미전송 |
| `contentColorCode` | string | null | X | 색상 코드. 최대 20자. 없으면 미전송 |
| `missionId` | number | null | X | `GENERAL`에서만 사용. 연결할 공통 `MISSION.id`. 없으면 미전송. `ROAD`이면 미전송 |

multipart에서 선택 필드를 보내지 않으면 해당 값은 `null`로 처리한다. `imageFiles`와 `audioFiles`는 Blob URL이 아니라 실제 파일을 전송한다. 파일 개수는 명세상 고정하지 않는다.

일반 방명록 요청 예시

```bash
curl -X POST "/api/v1/guestbooks" \
  -H "Authorization: Bearer {accessToken}" \
  -F "guestbookType=GENERAL" \
  -F "locationId=39" \
  -F "visitedAt=2026-08-29" \
  -F "imageFiles=@jeju-1.jpg" \
  -F "imageFiles=@jeju-2.webp" \
  -F "contentWriting=현애원 산책하기 좋았어요." \
  -F "audioFiles=@memo.m4a" \
  -F "contentWeather=맑음" \
  -F "contentColorCode=#84C7AE" \
  -F "missionId=501"
```

길바닥 방명록 요청 예시

```bash
curl -X POST "/api/v1/guestbooks" \
  -H "Authorization: Bearer {accessToken}" \
  -F "guestbookType=ROAD" \
  -F "locationAlias=성산 바다 앞" \
  -F "latitude=33.4582" \
  -F "longitude=126.9331" \
  -F "visitedAt=2026-08-29" \
  -F "contentWriting=바다가 잘 보이는 길이에요." \
  -F "contentWeather=흐림"
```

#### 파일 저장 규칙

이미지 파일은 JPEG, PNG, WebP를 허용하며 파일당 최대 크기는 10MB다. 원본 파일명과 multipart Content-Type만 믿지 않고 파일 내용으로 실제 형식을 판별한다. JPEG는 원본 확장자가 `.jpeg`여도 `.jpg`로 저장한다.

오디오 파일은 MP3, M4A, AAC, WAV, OGG, WebM을 허용하며 파일당 최대 크기는 30MB다. 파일 내용으로 판별한 실제 형식을 우선하고, 실제 형식에 맞는 `.mp3 | .m4a | .aac | .wav | .ogg | .webm` 확장자와 Content-Type으로 저장한다.

Blob 이름에는 원본 파일명을 사용하지 않고 UUID를 사용한다.

```
guestbook/general/{guestbookId}/images/{uuid}.{extension}
guestbook/general/{guestbookId}/audios/{uuid}.{extension}
guestbook/road/{guestbookId}/images/{uuid}.{extension}
guestbook/road/{guestbookId}/audios/{uuid}.{extension}
```

---

### 정상 응답 데이터

Status Code : 201

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `guestbookId` | number | 새로 저장한 일반 또는 길바닥 방명록 id |
| `guestbookType` | string | 저장된 방명록 유형. `GENERAL | ROAD` |
| `locationId` | number | null | 일반 방명록의 장소 id. `ROAD`이면 `null` |
| `locationAlias` | string | null | 길바닥 방명록의 장소 별칭. `GENERAL`이면 `null` |
| `latitude` | number | null | 길바닥 방명록 위도. `GENERAL`이면 `null` |
| `longitude` | number | null | 길바닥 방명록 경도. `GENERAL`이면 `null` |
| `visitedAt` | string | 저장된 방문 날짜. `yyyy-MM-dd` 형식 |
| `contentImageUrls` | string[] | null | Blob에 저장된 이미지 URL 목록. 이미지가 없으면 `null` |
| `contentWriting` | string | null | 저장된 글 내용. 없으면 `null` |
| `contentAudioUrls` | string[] | null | Blob에 저장된 오디오 URL 목록. 오디오가 없으면 `null` |
| `contentWeather` | string | null | 저장된 날씨 정보. 없으면 `null` |
| `contentColorCode` | string | null | 저장된 색상 코드. 없으면 `null` |
| `missionId` | number | null | 저장된 미션 id. 미션이 없거나 전달된 미션을 현재 사용자가 완료하지 않았거나 `ROAD`이면 `null` |
| `savedAt` | string | 방명록 저장 시각. KST 기준 offset 없는 ISO 8601 형식 |

일반 방명록 응답 예시

```json
{
  "guestbookId": 101,
  "guestbookType": "GENERAL",
  "locationId": 39,
  "locationAlias": null,
  "latitude": null,
  "longitude": null,
  "visitedAt": "2026-08-29",
  "contentImageUrls": [
    "https://example.blob.core.windows.net/media/guestbook/general/101/images/4b690ea8.jpg",
    "https://example.blob.core.windows.net/media/guestbook/general/101/images/7f9fd43c.webp"
  ],
  "contentWriting": "현애원 산책하기 좋았어요.",
  "contentAudioUrls": [
    "https://example.blob.core.windows.net/media/guestbook/general/101/audios/16bc1c76.m4a"
  ],
  "contentWeather": "맑음",
  "contentColorCode": "#84C7AE",
  "missionId": 501,
  "savedAt": "2026-08-29T15:30:00"
}
```

길바닥 방명록 응답 예시

```json
{
  "guestbookId": 202,
  "guestbookType": "ROAD",
  "locationId": null,
  "locationAlias": "성산 바다 앞",
  "latitude": 33.4582,
  "longitude": 126.9331,
  "visitedAt": "2026-08-29",
  "contentImageUrls": null,
  "contentWriting": "바다가 잘 보이는 길이에요.",
  "contentAudioUrls": null,
  "contentWeather": "흐림",
  "contentColorCode": null,
  "missionId": null,
  "savedAt": "2026-08-29T15:35:00"
}
```

---

### 오류 응답 데이터

Status Code : 404

`GENERAL` 요청의 `locationId`에 해당하는 장소가 존재하지 않는 경우

```json
{
  "code": "LOCATION_NOT_FOUND"
}
```

Status Code : 404

전달된 `missionId`에 해당하는 미션이 존재하지 않는 경우

```json
{
  "code": "MISSION_NOT_FOUND"
}
```

Status Code : 409

`GENERAL` 요청의 장소에 현재 사용자의 방문 이력이 한 건도 없는 경우

```json
{
  "code": "LOCATION_NOT_VISITED"
}
```


## 방명록 조회
- http 메서드: get
- domain: guestbook
- endpoint: /api/v1/guestbooks

### API 설명

현재 사용자가 작성한 전체 방명록을 조회할 때 호출한다.

일반 방명록과 길바닥 방명록을 각각 `generalGuestbooks`, `roadGuestbooks` 배열로 구분하여 반환한다. 일반 방명록은 장소 정보와 연결된 미션 정보를 포함하고, 길바닥 방명록은 장소 별칭과 지도 좌표를 포함한다.

페이지네이션을 적용하지 않으며 현재 사용자의 소프트 삭제되지 않은 방명록을 전부 반환한다. 두 배열은 각각 `savedAt` 내림차순으로 정렬하고, 저장 시각이 같으면 방명록 id 내림차순으로 정렬한다.

조회 결과가 없으면 오류를 반환하지 않고 두 배열을 모두 빈 배열로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `generalGuestbooks` | object[] | 현재 사용자가 작성한 일반 방명록 전체 목록 |
| `generalGuestbooks[].id` | number | 일반 방명록 id |
| `generalGuestbooks[].location` | object | 방명록이 작성된 장소 정보 |
| `generalGuestbooks[].location.id` | number | LOCATION id |
| `generalGuestbooks[].location.locationTitle` | string | 장소 이름 |
| `generalGuestbooks[].location.locationAddress` | string | 장소 주소 |
| `generalGuestbooks[].location.locationCategory` | string | 장소 카테고리 |
| `generalGuestbooks[].location.latitude` | number | 장소 위도 |
| `generalGuestbooks[].location.longitude` | number | 장소 경도 |
| `generalGuestbooks[].visitedAt` | string | 방문 날짜. `yyyy-MM-dd` 형식 |
| `generalGuestbooks[].contentImageUrls` | string[] | null | 방명록 이미지 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]` |
| `generalGuestbooks[].contentWriting` | string | null | 방명록 글 내용. 없으면 `null` |
| `generalGuestbooks[].contentAudioUrls` | string[] | null | 방명록 오디오 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]` |
| `generalGuestbooks[].contentWeather` | string | null | 방명록 날씨 정보. 없으면 `null` |
| `generalGuestbooks[].contentColorCode` | string | null | 방명록 색상 코드. 없으면 `null` |
| `generalGuestbooks[].savedAt` | string | 방명록 저장 시각. KST 기준 offset 없는 ISO 8601 형식 |
| `generalGuestbooks[].mission` | object | null | 방명록에 연결된 미션 정보. 연결된 미션이 없으면 `null` |
| `generalGuestbooks[].mission.id` | number | 공통 MISSION id |
| `generalGuestbooks[].mission.missionType` | string | 미션 유형. `CULTURE | COOPERATIVE | TREASURE` |
| `generalGuestbooks[].mission.missionTitle` | string | 미션 이름 |
| `roadGuestbooks` | object[] | 현재 사용자가 작성한 길바닥 방명록 전체 목록 |
| `roadGuestbooks[].id` | number | 길바닥 방명록 id |
| `roadGuestbooks[].locationAlias` | string | 지도에 표시할 위치 별칭 |
| `roadGuestbooks[].latitude` | number | 길바닥 방명록 위도 |
| `roadGuestbooks[].longitude` | number | 길바닥 방명록 경도 |
| `roadGuestbooks[].visitedAt` | string | 방문 날짜. `yyyy-MM-dd` 형식 |
| `roadGuestbooks[].contentImageUrls` | string[] | null | 방명록 이미지 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]` |
| `roadGuestbooks[].contentWriting` | string | null | 방명록 글 내용. 없으면 `null` |
| `roadGuestbooks[].contentAudioUrls` | string[] | null | 방명록 오디오 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]` |
| `roadGuestbooks[].contentWeather` | string | null | 방명록 날씨 정보. 없으면 `null` |
| `roadGuestbooks[].contentColorCode` | string | null | 방명록 색상 코드. 없으면 `null` |
| `roadGuestbooks[].savedAt` | string | 방명록 저장 시각. KST 기준 offset 없는 ISO 8601 형식 |

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
        "https://example.blob.core.windows.net/media/guestbook/general/101/images/4b690ea8.jpg"
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
      "contentImageUrls": null,
      "contentWriting": "바다가 잘 보이는 길이에요.",
      "contentAudioUrls": null,
      "contentWeather": "흐림",
      "contentColorCode": "#7AA7D9",
      "savedAt": "2026-08-21T15:10:00"
    }
  ]
}
```

조회 결과가 없는 경우

```json
{
  "generalGuestbooks": [],
  "roadGuestbooks": []
}
```

---

### 오류 응답 데이터

없음