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

| 필드         | 타입   | 필수 | 설명                                   |
| ------------ | ------ | ---- | -------------------------------------- |
| `locationId` | number | O    | 방명록 작성 가능 여부를 확인할 장소 id |

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

| 필드                           | 타입    | 설명                                                    |
| ------------------------------ | ------- | ------------------------------------------------------- | --------------------------------------------------- |
| `canWrite`                     | boolean | 현재 사용자의 해당 장소 방명록 작성 가능 여부           |
| `visitedLocation`              | object  | null                                                    | 가장 최근 방문 장소 정보. 방문 기록이 없으면 `null` |
| `visitedLocation.locationId`   | number  | 방문한 장소 id                                          |
| `visitedLocation.locationName` | string  | 방문한 장소명                                           |
| `visitedLocation.visitedAt`    | string  | 가장 최근 방문 시각. KST 기준 offset 없는 ISO 8601 형식 |

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

이미지와 오디오 파일은 Azure Blob Storage에 저장하고, MySQL에는 업로드된 Blob URL 배열만 저장한다. 나머지 콘텐츠와 위치·방문 정보는 MySQL에 저장한다. 이미지, 글, 오디오, 날씨, 기온과 색상은 모두 선택 값이며 전부 전달하지 않아도 방명록을 작성할 수 있다. 오디오 제목은 프론트에서 받지 않고 첨부된 오디오가 있을 때 서버가 OpenAI 모델로 생성한다.

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

| 필드                        | 타입     | 필수 | 설명                                         |
| --------------------------- | -------- | ---- | -------------------------------------------- | -------------------------------------------------------------------------------- |
| `guestbookType`             | string   | O    | 방명록 유형. `GENERAL                        | ROAD`                                                                            |
| `locationId`                | number   | null | 조건부                                       | `GENERAL`이면 필수. 저장할 `LOCATION.id`. `ROAD`이면 미전송                      |
| `locationAlias`             | string   | null | 조건부                                       | `ROAD`이면 필수. 최대 100자. `GENERAL`이면 미전송                                |
| `latitude`                  | number   | null | 조건부                                       | `ROAD`이면 필수. 길바닥 방명록 위도. -90 이상 90 이하. `GENERAL`이면 미전송      |
| `longitude`                 | number   | null | 조건부                                       | `ROAD`이면 필수. 길바닥 방명록 경도. -180 이상 180 이하. `GENERAL`이면 미전송    |
| `visitedAt`                 | string   | O    | 방명록에 기록할 방문 날짜. `yyyy-MM-dd` 형식 |
| `imageFiles`                | binary[] | null | X                                            | 방명록 이미지 파일 목록. 여러 파일은 같은 필드명을 반복해서 전송. 없으면 미전송  |
| `contentWriting`            | string   | null | X                                            | 방명록 글 내용. 최대 500자. 없으면 미전송                                        |
| `audioFiles`                | binary[] | null | X                                            | 방명록 오디오 파일 목록. 여러 파일은 같은 필드명을 반복해서 전송. 없으면 미전송  |
| `contentWeather`            | string   | null | X                                            | 날씨 정보. 최대 20자. 없으면 미전송                                              |
| `contentTemperatureCelsius` | number   | null | X                                            | 섭씨 기온. `-999.9~999.9` 범위이며 소수 첫째 자리까지 허용. 없으면 미전송        |
| `contentColorCode`          | string   | null | X                                            | 색상 코드. 최대 20자. 없으면 미전송                                              |
| `missionId`                 | number   | null | X                                            | `GENERAL`에서만 사용. 연결할 공통 `MISSION.id`. 없으면 미전송. `ROAD`이면 미전송 |

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
  -F "contentTemperatureCelsius=24.5" \
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
  -F "audioFiles=@waves.m4a" \
  -F "contentWeather=흐림" \
  -F "contentTemperatureCelsius=21.3"
```

#### 파일 저장 규칙

이미지 파일은 JPEG, PNG, WebP를 허용하며 파일당 최대 크기는 10MB다. 원본 파일명과 multipart Content-Type만 믿지 않고 파일 내용으로 실제 형식을 판별한다. JPEG는 원본 확장자가 `.jpeg`여도 `.jpg`로 저장한다.

오디오 파일은 MP3, M4A, AAC, WAV, OGG, WebM을 허용하며 파일당 최대 크기는 30MB다. 파일 내용으로 판별한 실제 형식을 우선하고, 실제 형식에 맞는 `.mp3 | .m4a | .aac | .wav | .ogg | .webm` 확장자와 Content-Type으로 저장한다.

오디오 파일이 있으면 서버가 각 파일을 OpenAI 음성 전사 모델로 처리한 뒤 전체 전사 내용을 대표하는 한국어 제목 한 개를 GPT 모델로 생성한다. 여러 오디오의 제목도 파일별로 만들지 않고 방명록당 하나만 생성한다. 오디오가 없으면 `audioTitle`은 `null`이며 OpenAI API를 호출하지 않는다.

생성된 제목은 한 줄의 최대 50자 문자열로 저장한다. OpenAI 설정 누락, 호출 실패·시간 초과 또는 유효한 제목 생성 실패 시 작성 요청은 `500 INTERNAL_SERVER_ERROR`로 실패하고 DB 행과 업로드된 Blob을 남기지 않는다.

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

| 필드                        | 타입     | 설명                                                 |
| --------------------------- | -------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `guestbookId`               | number   | 새로 저장한 일반 또는 길바닥 방명록 id               |
| `guestbookType`             | string   | 저장된 방명록 유형. `GENERAL                         | ROAD`                                                                                         |
| `locationId`                | number   | null                                                 | 일반 방명록의 장소 id. `ROAD`이면 `null`                                                      |
| `locationAlias`             | string   | null                                                 | 길바닥 방명록의 장소 별칭. `GENERAL`이면 `null`                                               |
| `latitude`                  | number   | null                                                 | 길바닥 방명록 위도. `GENERAL`이면 `null`                                                      |
| `longitude`                 | number   | null                                                 | 길바닥 방명록 경도. `GENERAL`이면 `null`                                                      |
| `visitedAt`                 | string   | 저장된 방문 날짜. `yyyy-MM-dd` 형식                  |
| `contentImageUrls`          | string[] | null                                                 | Blob에 저장된 이미지 URL 목록. 이미지가 없으면 `null`                                         |
| `contentWriting`            | string   | null                                                 | 저장된 글 내용. 없으면 `null`                                                                 |
| `contentAudioUrls`          | string[] | null                                                 | Blob에 저장된 오디오 URL 목록. 오디오가 없으면 `null`                                         |
| `audioTitle`                | string   | null                                                 | 서버가 첨부 오디오를 OpenAI 모델로 분석해 생성한 제목. 오디오가 없으면 `null`                 |
| `contentWeather`            | string   | null                                                 | 저장된 날씨 정보. 없으면 `null`                                                               |
| `contentTemperatureCelsius` | number   | null                                                 | 저장된 섭씨 기온. 소수 첫째 자리까지 반환하며 없으면 `null`                                   |
| `contentColorCode`          | string   | null                                                 | 저장된 색상 코드. 없으면 `null`                                                               |
| `missionId`                 | number   | null                                                 | 저장된 미션 id. 미션이 없거나 전달된 미션을 현재 사용자가 완료하지 않았거나 `ROAD`이면 `null` |
| `savedAt`                   | string   | 방명록 저장 시각. KST 기준 offset 없는 ISO 8601 형식 |

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
  "audioTitle": "새소리",
  "contentWeather": "맑음",
  "contentTemperatureCelsius": 24.5,
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
  "contentAudioUrls": [
    "https://example.blob.core.windows.net/media/guestbook/road/202/audios/6e14f508.m4a"
  ],
  "audioTitle": "파도소리",
  "contentWeather": "흐림",
  "contentTemperatureCelsius": 21.3,
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

DB에 저장된 일반 방명록과 길바닥 방명록을 전체 또는 현재 사용자 작성분으로 조회할 때 호출한다.

일반 방명록과 길바닥 방명록을 각각 `generalGuestbooks`, `roadGuestbooks` 배열로 구분하여 반환한다. 일반 방명록은 장소·미션 정보를 포함하고, 길바닥 방명록은 장소 별칭과 지도 좌표를 포함한다. 두 유형 모두 작성자 정보, 오디오 제목, 기온과 현재 사용자의 좋아요 여부 및 전체 좋아요 수를 반환한다.

현재 사용자가 방문한 장소는 `visitedLocations` 배열로 별도 반환하며 각 장소의 ID와 장소명만 포함한다.

`scope=ALL`이면 작성자와 관계없이 소프트 삭제되지 않은 방명록을 모두 반환하고, `scope=MINE`이면 그중 현재 사용자가 작성한 방명록만 반환한다. `scope`를 생략하면 `ALL`로 처리한다. 페이지네이션은 적용하지 않는다. 두 배열은 각각 `savedAt` 내림차순으로 정렬하고, 저장 시각이 같으면 방명록 id 내림차순으로 정렬한다.

조회 결과가 없으면 오류를 반환하지 않고 두 배열을 모두 빈 배열로 반환한다.

---

### 요청 Query

| 필드    | 타입   | 필수 | 설명                                                                                     |
| ------- | ------ | ---- | ---------------------------------------------------------------------------------------- |
| `scope` | string | X    | 조회 범위. `ALL \| MINE`. 생략하면 `ALL`, `MINE`이면 현재 사용자가 작성한 방명록만 조회 |

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

| 필드                                            | 타입     | 설명                                                                      |
| ----------------------------------------------- | -------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------- | --------- |
| `visitedLocations`                              | object[] | 현재 사용자가 방문한 장소 목록. 없으면 빈 배열                            |
| `visitedLocations[].id`                         | number   | LOCATION id                                                               |
| `visitedLocations[].locationTitle`              | string   | 장소 이름                                                                 |
| `generalGuestbooks`                             | object[] | DB에 저장된 삭제되지 않은 일반 방명록 전체 목록                            |
| `generalGuestbooks[].id`                        | number   | 일반 방명록 id                                                            |
| `generalGuestbooks[].userId`                    | number   | 방명록 작성자 사용자 ID                                                   |
| `generalGuestbooks[].characterImgUrl`           | string   | null                                                                      | 작성자에게 배정된 AR 캐릭터 이미지 URL. 배정된 캐릭터가 없으면 `null` |
| `generalGuestbooks[].userNickname`              | string   | null                                                                      | 방명록 작성자 닉네임. 없으면 `null`                                   |
| `generalGuestbooks[].location`                  | object   | 방명록이 작성된 장소 정보                                                 |
| `generalGuestbooks[].location.id`               | number   | LOCATION id                                                               |
| `generalGuestbooks[].location.locationTitle`    | string   | 장소 이름                                                                 |
| `generalGuestbooks[].location.locationAddress`  | string   | 장소 주소                                                                 |
| `generalGuestbooks[].location.locationCategory` | string   | 장소 카테고리                                                             |
| `generalGuestbooks[].location.latitude`         | number   | 장소 위도                                                                 |
| `generalGuestbooks[].location.longitude`        | number   | 장소 경도                                                                 |
| `generalGuestbooks[].visitedAt`                 | string   | 방문 날짜. `yyyy-MM-dd` 형식                                              |
| `generalGuestbooks[].contentImageUrls`          | string[] | null                                                                      | 방명록 이미지 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]`   |
| `generalGuestbooks[].contentWriting`            | string   | null                                                                      | 방명록 글 내용. 없으면 `null`                                         |
| `generalGuestbooks[].contentAudioUrls`          | string[] | null                                                                      | 방명록 오디오 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]`   |
| `generalGuestbooks[].audioTitle`                | string   | null                                                                      | 녹음 콘텐츠 제목. 없으면 `null`                                       |
| `generalGuestbooks[].contentWeather`            | string   | null                                                                      | 방명록 날씨 정보. 없으면 `null`                                       |
| `generalGuestbooks[].contentTemperatureCelsius` | number   | null                                                                      | 방명록의 섭씨 기온. 소수 첫째 자리까지 반환하며 없으면 `null`         |
| `generalGuestbooks[].contentColorCode`          | string   | null                                                                      | 방명록 색상 코드. 없으면 `null`                                       |
| `generalGuestbooks[].isLiked`                   | boolean  | 현재 사용자가 해당 일반 방명록에 좋아요를 눌렀으면 `true`, 아니면 `false` |
| `generalGuestbooks[].likeCount`                 | number   | 해당 일반 방명록에 달린 삭제되지 않은 전체 좋아요 수. 없으면 `0`          |
| `generalGuestbooks[].savedAt`                   | string   | 방명록 저장 시각. KST 기준 offset 없는 ISO 8601 형식                      |
| `generalGuestbooks[].mission`                   | object   | null                                                                      | 방명록에 연결된 미션 정보. 연결된 미션이 없으면 `null`                |
| `generalGuestbooks[].mission.id`                | number   | 공통 MISSION id                                                           |
| `generalGuestbooks[].mission.missionType`       | string   | 미션 유형. `CULTURE                                                       | COOPERATIVE                                                           | TREASURE` |
| `generalGuestbooks[].mission.missionTitle`      | string   | 미션 이름                                                                 |
| `roadGuestbooks`                                | object[] | DB에 저장된 삭제되지 않은 길바닥 방명록 전체 목록                          |
| `roadGuestbooks[].id`                           | number   | 길바닥 방명록 id                                                          |
| `roadGuestbooks[].userId`                       | number   | 방명록 작성자 사용자 ID                                                   |
| `roadGuestbooks[].characterImgUrl`              | string   | null                                                                      | 작성자에게 배정된 AR 캐릭터 이미지 URL. 배정된 캐릭터가 없으면 `null` |
| `roadGuestbooks[].userNickname`                 | string   | null                                                                      | 방명록 작성자 닉네임. 없으면 `null`                                   |
| `roadGuestbooks[].locationAlias`                | string   | 지도에 표시할 위치 별칭                                                   |
| `roadGuestbooks[].latitude`                     | number   | 길바닥 방명록 위도                                                        |
| `roadGuestbooks[].longitude`                    | number   | 길바닥 방명록 경도                                                        |
| `roadGuestbooks[].visitedAt`                    | string   | 방문 날짜. `yyyy-MM-dd` 형식                                              |
| `roadGuestbooks[].contentImageUrls`             | string[] | null                                                                      | 방명록 이미지 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]`   |
| `roadGuestbooks[].contentWriting`               | string   | null                                                                      | 방명록 글 내용. 없으면 `null`                                         |
| `roadGuestbooks[].contentAudioUrls`             | string[] | null                                                                      | 방명록 오디오 URL 목록. DB 값이 `NULL`이면 `null`, 빈 배열이면 `[]`   |
| `roadGuestbooks[].audioTitle`                   | string   | null                                                                      | 녹음 콘텐츠 제목. 없으면 `null`                                       |
| `roadGuestbooks[].contentWeather`               | string   | null                                                                      | 방명록 날씨 정보. 없으면 `null`                                       |
| `roadGuestbooks[].contentTemperatureCelsius`    | number   | null                                                                      | 방명록의 섭씨 기온. 소수 첫째 자리까지 반환하며 없으면 `null`         |
| `roadGuestbooks[].contentColorCode`             | string   | null                                                                      | 방명록 색상 코드. 없으면 `null`                                       |
| `roadGuestbooks[].isLiked`                      | boolean  | 현재 사용자가 해당 길바닥 방명록에 좋아요를 눌렀으면 `true`, 아니면 `false` |
| `roadGuestbooks[].likeCount`                    | number   | 해당 길바닥 방명록에 달린 삭제되지 않은 전체 좋아요 수. 없으면 `0`       |
| `roadGuestbooks[].savedAt`                      | string   | 방명록 저장 시각. KST 기준 offset 없는 ISO 8601 형식                      |

```json
{
  "visitedLocations": [
    {
      "id": 39,
      "locationTitle": "현애원"
    },
    {
      "id": 42,
      "locationTitle": "성산일출봉"
    }
  ],
  "generalGuestbooks": [
    {
      "id": 101,
      "userId": 1,
      "characterImgUrl": "https://example.com/images/ar-characters/1.png",
      "userNickname": "여행자종화",
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
      "contentAudioUrls": [
        "https://example.blob.core.windows.net/media/guestbook/general/101/audios/16bc1c76.m4a"
      ],
      "audioTitle": "새소리",
      "contentWeather": "맑음",
      "contentTemperatureCelsius": 24.5,
      "contentColorCode": "#84C7AE",
      "isLiked": true,
      "likeCount": 12,
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
      "userId": 1,
      "characterImgUrl": "https://example.com/images/ar-characters/1.png",
      "userNickname": "여행자종화",
      "locationAlias": "성산 바다 앞",
      "latitude": 33.4582,
      "longitude": 126.9331,
      "visitedAt": "2026-08-21",
      "contentImageUrls": null,
      "contentWriting": "바다가 잘 보이는 길이에요.",
      "contentAudioUrls": null,
      "audioTitle": null,
      "contentWeather": "흐림",
      "contentTemperatureCelsius": 21.3,
      "contentColorCode": "#7AA7D9",
      "isLiked": false,
      "likeCount": 4,
      "savedAt": "2026-08-21T15:10:00"
    }
  ]
}
```

- `visitedLocations`는 현재 사용자의 `VISITED_LOCATION`을 기준으로 구성하며 같은 장소를 여러 번 방문했어도 한 번만 포함한다. 장소별 최근 방문 시각 내림차순, 방문 시각이 같으면 LOCATION ID 내림차순으로 정렬한다.
- 각 유형의 `isLiked`는 현재 사용자의 대응 좋아요 테이블(`GUESTBOOK_LIKE` 또는 `ROAD_GUESTBOOK_LIKE`)에 `deleted_at IS NULL`인 행이 존재하는지를 나타낸다. 좋아요가 없거나 취소되어 소프트 삭제된 경우 `false`다.
- 각 유형의 `likeCount`는 사용자 구분 없이 대응 좋아요 테이블에서 `deleted_at IS NULL`인 전체 행 수다. 현재 사용자의 좋아요도 포함하며 활성 좋아요가 없으면 `0`이다.
- 각 방명록의 `userId`, `characterImgUrl`, `userNickname`은 해당 방명록 작성자 정보다. 작성자에게 배정된 AR 캐릭터가 없으면 `characterImgUrl`은 `null`이다.
- `audioTitle`과 `contentTemperatureCelsius`는 DB 값이 없으면 `null`이며 응답에서 키를 생략하지 않는다.

현재 사용자의 방문 장소와 조회 가능한 방명록이 모두 없는 경우

```json
{
  "visitedLocations": [],
  "generalGuestbooks": [],
  "roadGuestbooks": []
}
```

---

### 오류 응답 데이터

없음

## 방명록 좋아요

### API 설명

현재 사용자가 일반 방명록 또는 길바닥 방명록의 좋아요 상태를 변경할 때 호출한다.

`guestbookType`의 `GENERAL | ROAD` 값으로 대상 방명록 테이블과 좋아요 테이블을 구분한다. `GENERAL`이면 `GUESTBOOK`과 `GUESTBOOK_LIKE`, `ROAD`이면 `ROAD_GUESTBOOK`과 `ROAD_GUESTBOOK_LIKE`를 사용한다. 두 방명록 테이블은 id가 서로 겹칠 수 있으므로 `guestbookId`만으로 유형을 추론하지 않는다.

`isLiked`는 현재 상태를 반전시키라는 의미가 아니라 요청 완료 후 적용되어야 하는 최종 좋아요 상태다. 같은 요청을 여러 번 보내도 결과가 같도록 멱등하게 처리한다.

`isLiked=true`이고 좋아요 행이 없으면 새 행을 생성한다. 소프트 삭제된 행이 있으면 새 행을 만들지 않고 해당 행의 `deleted_at`을 `null`로 변경한다. 이미 활성 상태이면 값을 변경하지 않고 성공 응답을 반환한다.

`isLiked=false`이고 활성 좋아요 행이 있으면 `deleted_at`에 현재 KST 시각을 저장한다. 좋아요 행이 없거나 이미 소프트 삭제된 상태이면 값을 변경하지 않고 성공 응답을 반환한다.

각 좋아요 테이블의 `(guestbook_id, user_id)` 유니크 제약을 사용하여 한 사용자가 같은 방명록에 중복 좋아요 행을 만들지 못하게 한다. 동시 요청에서도 유니크 제약을 기준으로 기존 행을 다시 조회하여 최종 상태가 요청의 `isLiked`와 같도록 처리한다.

현재 사용자가 작성한 방명록에는 좋아요 상태 변경을 요청할 수 없다. 본인 방명록이면 `isLiked` 값과 관계없이 409 오류를 반환한다.

대상 방명록이 존재하지 않거나 소프트 삭제된 경우, 또는 `guestbookType`과 실제 저장 테이블이 일치하지 않는 경우 404 오류를 반환한다.

정상 처리 후 적용된 좋아요 상태와 해당 방명록의 활성 좋아요 수를 반환한다. 좋아요 수는 선택된 좋아요 테이블에서 `guestbook_id`가 같고 `deleted_at IS NULL`인 행만 센다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드          | 타입   | 필수 | 설명                                            |
| ------------- | ------ | ---- | ----------------------------------------------- |
| `guestbookId` | number | O    | 좋아요 상태를 변경할 일반 또는 길바닥 방명록 id |

요청 예시

```jsx
PUT / api / v1 / guestbooks / 101 / like;
```

---

### 요청 Body

Content-Type : `application/json`

| 필드            | 타입    | 필수 | 설명                                                                         |
| --------------- | ------- | ---- | ---------------------------------------------------------------------------- | ----------------------------------------------- |
| `guestbookType` | string  | O    | 방명록 유형. `GENERAL                                                        | ROAD`. 대상 방명록 및 좋아요 테이블을 구분한다. |
| `isLiked`       | boolean | O    | 요청 완료 후 적용할 최종 좋아요 상태. `true`면 좋아요, `false`면 좋아요 취소 |

일반 방명록 좋아요 요청 예시

```json
{
  "guestbookType": "GENERAL",
  "isLiked": true
}
```

길바닥 방명록 좋아요 취소 요청 예시

```json
{
  "guestbookType": "ROAD",
  "isLiked": false
}
```

---

### 정상 응답 데이터

Status Code : 200

| 필드            | 타입    | 설명                                                   |
| --------------- | ------- | ------------------------------------------------------ | ----- |
| `guestbookId`   | number  | 좋아요 상태를 변경한 방명록 id                         |
| `guestbookType` | string  | 대상 방명록 유형. `GENERAL                             | ROAD` |
| `isLiked`       | boolean | 요청 처리 후 현재 사용자의 최종 좋아요 상태            |
| `likeCount`     | number  | 해당 방명록의 삭제되지 않은 전체 좋아요 수. 없으면 `0` |

좋아요 설정 응답 예시

```json
{
  "guestbookId": 101,
  "guestbookType": "GENERAL",
  "isLiked": true,
  "likeCount": 13
}
```

좋아요 취소 응답 예시

```json
{
  "guestbookId": 202,
  "guestbookType": "ROAD",
  "isLiked": false,
  "likeCount": 4
}
```

---

### 오류 응답 데이터

Status Code : 404

`guestbookType`에 해당하는 테이블에서 `guestbookId`의 방명록을 찾을 수 없거나 해당 방명록이 소프트 삭제된 경우

```json
{
  "code": "GUESTBOOK_NOT_FOUND"
}
```

Status Code : 409

현재 사용자가 작성한 방명록의 좋아요 상태 변경을 요청한 경우

```json
{
  "code": "OWN_GUESTBOOK_LIKE_NOT_ALLOWED"
}
```
