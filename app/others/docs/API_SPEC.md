## 걸음 수 저장

- http 메서드: put
- domain: others
- endpoint: /api/v1/users/me/step-counts

### API 설명

프론트가 특정 시점의 사용자 누적 걸음 수를 저장할 때 호출한다. 프론트는 걸음 수를 측정한 시각, 해당 시점의 누적 걸음 수, 목표 걸음 수 달성 여부를 전송한다.

서버는 액세스 토큰으로 현재 사용자를 식별한다. `STEP_COUNT.user_id`에는 현재 사용자 ID, `saved_at`에는 요청의 `recordedAt`, `steps_count`에는 요청의 `stepsCount`를 저장한다. 클라이언트에서 사용자 ID는 받지 않는다.

`isGoalAchieved = true`이면 AR 캐릭터 ID `1`, `2`, `3` 중 하나를 무작위로 선택한다. 현재 사용자가 선택된 캐릭터를 보유하지 않았다면 `ACQUIRED_AR_CHARACTER`에 획득 기록을 생성하고 `acquired_mission_id`는 `NULL`로 저장한다. 이미 보유했다면 중복 저장하지 않는다.

이미 보유한 캐릭터가 선택된 경우에도 다시 추첨하지 않는다. 선택된 캐릭터의 이름과 이미지 URL을 동일하게 응답한다.

`isGoalAchieved = false`이면 캐릭터를 추첨하거나 획득 기록을 생성하지 않으며, 응답의 캐릭터 이름과 이미지 URL은 `null`이다.

저장이 완료되면 선택된 캐릭터 정보와 현재 사용자의 목표 걸음 수를 `200 OK`로 반환한다. 목표 걸음 수는 현재 ERD 기준 `USER.target_step`에서 가져온다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

Content-Type : `application/json`

| 필드             | 타입              | 필수 | 설명                                                                                 |
| ---------------- | ----------------- | ---- | ------------------------------------------------------------------------------------ |
| `recordedAt`     | string(date-time) | O    | 걸음 수를 측정한 시각. KST 기준 offset 없는 `YYYY-MM-DDTHH:mm:ss` 형식               |
| `stepsCount`     | integer           | O    | 해당 시점의 누적 걸음 수. 0 이상의 정수                                              |
| `isGoalAchieved` | boolean           | O    | 프론트가 판단한 목표 걸음 수 달성 여부. true이면 AR 캐릭터 1~3 중 하나를 무작위 선택 |

요청 예시

```json
{
  "recordedAt": "2026-09-10T18:30:00",
  "stepsCount": 10234,
  "isGoalAchieved": true
}
```

---

### 정상 응답 데이터

Status Code : `200 OK`

| 필드               | 타입           | 설명                                                                                          |
| ------------------ | -------------- | --------------------------------------------------------------------------------------------- |
| `characterName`    | string \| null | `isGoalAchieved = true`일 때 무작위로 선택된 AR 캐릭터 이름. false이면 null                   |
| `characterImageUrl` | string \| null | 선택된 AR 캐릭터 이미지 URL. 목표 미달이면 null                                               |
| `targetStep`       | integer        | 현재 사용자의 목표 걸음 수. 현재 ERD 기준 `USER.target_step`                                 |

목표 걸음 수 달성 응답 예시

```json
{
  "characterName": "누비",
  "characterImageUrl": "https://cdn.jamkkan-jeju.dev/ar/nubi.png",
  "targetStep": 10000
}
```

목표 걸음 수 미달 응답 예시

```json
{
  "characterName": null,
  "characterImageUrl": null,
  "targetStep": 10000
}
```

---

### 오류 응답 데이터

없음

## GPS 및 방문 장소 저장

- http 메서드: post
- domain: others
- endpoint: /api/v1/users/me/gps

### API 설명

프론트가 사용자의 GPS 좌표를 일정 간격으로 저장할 때 호출한다. 프론트는 좌표를 측정한 시각과 위도·경도를 전송한다.

서버는 액세스 토큰으로 식별한 현재 사용자를 기준으로 `GPS`를 저장한다. 클라이언트에서 사용자 id는 받지 않는다.

`GPS.user_id`에는 현재 사용자 id, `mx`에는 요청의 `longitude`, `my`에는 요청의 `latitude`, `saved_at`에는 요청의 `recordedAt`을 저장한다.

같은 요청에서 현재 좌표를 기준으로 방문 장소를 판정하고, 방문한 장소가 있으면 `VISITED_LOCATION`에 기록한다.

저장이 완료되면 별도의 응답 데이터를 반환하지 않고 `204 No Content`를 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

Content-Type : `application/json`

| 필드         | 타입              | 필수 | 설명                                                                |
| ------------ | ----------------- | ---- | ------------------------------------------------------------------- |
| `recordedAt` | string(date-time) | O    | 좌표를 측정한 시각. KST 기준 offset 없는 `YYYY-MM-DDTHH:mm:ss` 형식 |
| `latitude`   | number            | O    | 사용자 위도. -90 이상 90 이하                                       |
| `longitude`  | number            | O    | 사용자 경도. -180 이상 180 이하                                     |

요청 예시

```json
{
  "recordedAt": "2026-09-03T14:30:00",
  "latitude": 37.5665,
  "longitude": 126.978
}
```

---

### 정상 응답 데이터

Status Code : 204

응답 Body 없음

---

### 오류 응답 데이터

없음
