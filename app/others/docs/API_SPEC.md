## 걸음 수 저장

- http 메서드: put
- domain: others
- endpoint: /api/v1/users/me/step-counts

### API 설명

프론트가 사용자의 하루 누적 걸음 수를 저장할 때 호출한다. 프론트는 자정마다 기록 대상 날짜와 해당 날짜의 최종 누적 걸음 수를 전송한다.

서버는 액세스 토큰으로 식별한 현재 사용자와 요청의 `recordedDate`를 기준으로 `STEP_COUNT`를 저장한다. 클라이언트에서 사용자 id는 받지 않는다.

`STEP_COUNT.user_id`에는 현재 사용자 id, `steps_count`에는 요청의 `stepsCount`, `saved_at`에는 `recordedDate`의 KST 자정에 해당하는 offset 없는 `YYYY-MM-DDT00:00:00` 값을 저장한다.

한 사용자와 기록 날짜 조합에는 한 행만 유지한다. 같은 `recordedDate`로 처음 요청하면 새 행을 생성하고, 기존 행이 있으면 새 행을 추가하지 않고 `steps_count`를 요청값으로 갱신한다. 재요청 값은 기존 값보다 작아도 요청값으로 교체한다.

사용자별 날짜당 한 행을 DB 수준에서도 보장하기 위해 `(user_id, saved_at)` 유니크 제약을 사용한다. 동시 요청으로 유니크 충돌이 발생하면 기존 행을 다시 조회해 요청값으로 갱신한다.

`recordedDate`는 KST 기준 현재 날짜 또는 과거 날짜만 허용한다. 미래 날짜는 저장하지 않는다.

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

| 필드           | 타입         | 필수 | 설명                                                                             |
| -------------- | ------------ | ---- | -------------------------------------------------------------------------------- |
| `recordedDate` | string(date) | O    | 걸음 수 기록 대상 날짜. KST 기준 `YYYY-MM-DD` 형식이며 미래 날짜는 허용하지 않음 |
| `stepsCount`   | number       | O    | 해당 날짜의 최종 누적 걸음 수. 0 이상의 정수                                     |

요청 예시

```json
{
  "recordedDate": "2026-09-02",
  "stepsCount": 8241
}
```

---

### 정상 응답 데이터

Status Code : 204

응답 Body 없음

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
