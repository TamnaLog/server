## 문화 미션 시작/이어하기
- http 메서드: post
- domain: culture-mission
- /api/v1/culture-missions/{cultureMissionId}/progress

### API 설명

사용자가 문화 미션을 처음 시작하거나 진행 중이던 문화 미션을 이어서 할 때 호출한다.

`cultureMissionId`에 해당하는 문화 미션과 로그인한 사용자의 진행도를 조회한다. `cultureMissionId`는 공통 `MISSION.id`가 아니라 `CULTURE_MISSION.id`를 의미한다. 진행 중인 기록이 없으면 현재 퀴즈 번호를 `1`, 정답 개수를 `0`으로 초기화한 진행도를 새로 생성한다. 이미 `IN_PROGRESS` 상태인 기록이 있으면 새로 생성하지 않고 해당 진행도를 반환한다.

완료한 진행도가 있더라도 같은 문화 미션을 다시 시작할 수 있다. 이 경우 기존 완료 기록은 유지하고 새로운 진행도를 생성하여 Status Code `201`로 반환한다.

`currentQuizNumber`에는 사용자가 다음에 풀 퀴즈 번호를 반환한다. 예를 들어 1번 퀴즈까지 풀었다면 `2`를 반환한다.

프론트에서 이후 진행도 저장 요청에 사용할 수 있도록 현재 진행 중인 `CULTURE_MISSION_PROGRESS.id`를 `cultureMissionProgressId`로 반환한다. 신규 진행도를 생성한 경우에는 새로 생성된 진행도 id를, 기존 미션을 이어서 하는 경우에는 조회된 진행도 id를 반환한다.

프론트에서 문화 미션 화면을 구성할 수 있도록 전체 문제 정보와 각 문제의 해설을 함께 반환한다. 문제의 정답은 주관식과 객관식 모두 문자열로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cultureMissionId` | number | O | 진행도를 생성하거나 조회할 `CULTURE_MISSION.id` |

요청 예시

```
POST /api/v1/culture-missions/12/progress
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 201

문화 미션 진행도를 새로 생성한 경우. 처음 시작하는 경우와 완료한 미션을 다시 시작하는 경우를 포함한다.

Status Code : 200

이미 진행 중인 문화 미션을 이어서 하는 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `cultureMissionProgressId` | number | 현재 진행 중인 문화 미션 진행도 id. `CULTURE_MISSION_PROGRESS.id` |
| `quizCount` | number | 문화 미션의 전체 문제 수 |
| `currentQuizNumber` | number | 사용자가 다음에 풀 퀴즈 번호. 신규 진행도는 `1` |
| `quizDetails` | object[] | `quizIndex` 오름차순으로 정렬된 전체 문제 목록 |
| `quizDetails[].quizIndex` | number | 문제 번호 |
| `quizDetails[].imgUrl` | string \| null | 문제 이미지 URL. 이미지가 없으면 `null` |
| `quizDetails[].question` | string | 문제 내용 |
| `quizDetails[].options` | string[] \| null | 객관식 선택지. 주관식 문제이면 `null` |
| `quizDetails[].answer` | string | 문제 정답. 객관식도 선택지 번호가 아닌 정답 문자열 |
| `quizDetails[].hint` | string | 문제 힌트 |
| `quizDetails[].explanation` | string | 문제 정답 해설 |


```json
{
  "cultureMissionProgressId": 1,
  "quizCount": 3,
  "currentQuizNumber": 1,
  "quizDetails": [
    {
      "quizIndex": 1,
      "imgUrl": "<https://example.com/images/quizzes/jeju-dialect-1.jpg>",
      "question": "제주어로 할아버지는 무엇일까요?",
      "options": ["하르방", "하라범", "하르봉", "하르범"],
      "answer": "하르방",
      "hint": "제주의 돌하르방을 떠올려 보세요.",
      "explanation": "제주어에서 할아버지를 뜻하는 대표적인 표현은 하르방입니다."
    },
    {
      "quizIndex": 2,
      "imgUrl": "<https://example.com/images/quizzes/jeju-drama.jpg>",
      "question": "제주를 배경으로 여러 인물의 삶을 옴니버스 형식으로 담아낸 노희경 작가의 드라마는 무엇일까요?",
      "options": ["우리들의 블루스", "우도의 봄", "갯마을 차차차", "도깨비"],
      "answer": "우리들의 블루스",
      "hint": "제목에 제주 바다를 연상시키는 색상이 들어가요.",
      "explanation": "우리들의 블루스는 제주를 배경으로 여러 인물의 삶을 옴니버스 형식으로 그린 드라마입니다."
    },
    {
      "quizIndex": 3,
      "imgUrl": null,
      "question": "'하영'은 제주 방언으로 어떤 뜻일까요?",
      "options": null,
      "answer": "많이",
      "hint": "수량이 넉넉하다는 의미로 사용해요.",
      "explanation": "하영은 제주 방언으로 많이라는 뜻입니다."
    }
  ]
}
```

---

### 오류 응답 데이터

Status Code : 404

`cultureMissionId`에 해당하는 문화 미션이 존재하지 않는 경우

```json
{
  "code": "CULTURE_MISSION_NOT_FOUND"
}
```



## 문화 미션 진행도 저장
- http 메서드: patch
- domian: culture-mission
- endpoint: /api/v1/culture-missions/{cultureMissionProgressId}/progress

### API 설명

사용자가 문화 미션 퀴즈를 풀고 다음 문제로 이동할 때 호출한다.

Path로 전달받은 `cultureMissionProgressId`를 사용하여 로그인한 사용자의 진행 중인 문화 미션 진행도를 조회하고, 해당 진행도와 연결된 문화 미션을 조회한다. 요청 Body로 전달받은 `quizIndex`가 진행도의 `current_quiz_index`와 일치하면 진행도를 갱신한다.

`isCorrect`가 `true`이면 정답 개수를 `1` 증가시키고, `false`이면 정답 개수를 그대로 유지한다.

제출한 `quizIndex`가 문화 미션의 마지막 퀴즈 번호가 아니면 `current_quiz_index`를 `1` 증가시킨다. 마지막 퀴즈 번호이면 `current_quiz_index`를 증가시키지 않고 진행도 상태를 `COMPLETED`로 변경한다.

응답의 `currentQuizNumber`에는 저장된 `current_quiz_index`를 반환한다. 따라서 마지막 퀴즈를 제출해 완료된 경우에도 `null`이 아니라 마지막 퀴즈 번호를 그대로 반환하고, 다음 장소 정보를 함께 반환한다.

Query로 전달받은 사용자의 위도와 경도는 미션 완료 후 추천된 다음 장소까지의 직선거리를 계산하는 데 사용한다. 거리는 미터 단위의 `distanceMeter`로 반환한다. 현재 다음 장소는 랜덤으로 추천하므로 사용자 좌표는 추천 장소 선정 기준으로 사용하지 않는다.

문화 미션이 아직 진행 중이면 `nextLocation`과 `reward`는 `null`로 반환한다.

마지막 퀴즈를 제출해 미션을 완료하면 정답 개수에 따라 보상을 지급한다. 보상은 AR 캐릭터, 포인트, 쿠폰 순서로 지급하며, 같은 사용자와 같은 문화 미션에서는 각 보상 항목을 한 번만 지급할 수 있다. 이미 과거 진행도에서 지급된 보상 항목은 다시 지급하지 않는다.

완료 응답의 `reward`에는 이번 요청으로 실제 지급된 보상만 포함한다. 미션을 완료했더라도 지급할 보상이 없거나 정답 개수보다 남은 보상 수가 적으면 각 보상 항목은 `null`일 수 있다.

`nextLocation.locationImageUrl`은 `LOCATION.content_id`로 TourAPI를 조회해서 채운다. 이미지 URL은 부가 정보이므로, 인증키 미설정·통신 실패·이미지 없음 등으로 조회하지 못하면 미션 완료 응답 전체를 실패시키지 않고 `null`로 반환한다.

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
| `cultureMissionProgressId` | number | 저장할 문화 미션 진행도 id. `CULTURE_MISSION_PROGRESS.id` |

요청 예시

```
PATCH /api/v1/culture-missions/31/progress?latitude=33.5572&longitude=126.7591
```

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `quizIndex` | number | O | 사용자가 제출한 퀴즈 번호 |
| `isCorrect` | boolean | O | 사용자가 해당 퀴즈를 맞혔는지 여부 |

```json
{
  "quizIndex": 2,
  "isCorrect": true
}
```

---

### 정상 응답 데이터

Status Code : 200

문화 미션 진행도를 정상적으로 저장한 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionProgressStatus` | string | 문화 미션 진행 상태. `IN_PROGRESS | COMPLETED` |
| `quizCount` | number | 문화 미션의 전체 문제 수 |
| `currentQuizNumber` | number | 현재 진행도에 저장된 퀴즈 번호 |
| `correctNumber` | number | 현재까지 맞힌 문제 수 |
| `nextLocation` | object \| null | 다음 추천 장소 정보. 진행 중이면 `null`, 완료되면 반드시 객체로 반환 |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string \| null | 다음 장소 이미지 URL. TourAPI 에서 조회하지 못하면 `null` |
| `nextLocation.distanceMeter` | number | 사용자 위치에서 다음 장소까지의 직선거리(m) |
| `nextLocation.mission` | object | null | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE \| COOPERATIVE \| TREASURE` |
| `reward` | object \| null | 이번 요청으로 실제 지급된 보상 정보. 진행 중이면 `null` |
| `reward.arCharacter` | object \| null | 이번 요청으로 지급된 AR 캐릭터. 지급되지 않았으면 `null` |
| `reward.arCharacter.id` | number | AR 캐릭터 id |
| `reward.arCharacter.name` | string | AR 캐릭터 이름 |
| `reward.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `reward.point` | number \| null | 이번 요청으로 지급된 포인트. 지급되지 않았으면 `null` |
| `reward.coupon` | object \| null | 이번 요청으로 지급된 쿠폰. 지급되지 않았으면 `null` |
| `reward.coupon.couponLocation` | string | 쿠폰 사용처 |
| `reward.coupon.couponPrice` | number | 쿠폰 금액 |

```json
{
  "missionProgressStatus": "IN_PROGRESS",
  "quizCount": 3,
  "currentQuizNumber": 3,
  "correctNumber": 2,
  "nextLocation": null,
  "reward": null
}
```

마지막 퀴즈를 제출하여 문화 미션을 완료하면 `missionProgressStatus`는 `COMPLETED`로 반환한다. 이때 `current_quiz_index`는 증가시키지 않으며 `currentQuizNumber`에는 마지막 퀴즈 번호를 그대로 반환한다.

아래 예시는 이번 완료 요청에서 정답 3개를 반영했고, 과거에 지급된 보상이 없어 AR 캐릭터, 포인트, 쿠폰이 모두 지급된 경우이다.

```json
{
  "missionProgressStatus": "COMPLETED",
  "quizCount": 3,
  "currentQuizNumber": 3,
  "correctNumber": 3,
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "<https://example.com/locations/handam.jpg>",
    "distanceMeter": 4200,
    "mission": {
      "id": 342,
      "missionType": "TREASURE"
    }
  },
  "reward": {
    "arCharacter": {
      "id": 7,
      "name": "돌담이",
      "imageUrl": "<https://example.com/characters/stone-spirit.png>"
    },
    "point": 100,
    "coupon": {
      "couponLocation": "종화네 막국수",
      "couponPrice": 3000
    }
  }
}
```

이번 완료 요청에서 포인트만 지급된 경우처럼 지급되지 않은 보상 항목은 `null`로 반환한다.

```json
{
  "missionProgressStatus": "COMPLETED",
  "quizCount": 3,
  "currentQuizNumber": 3,
  "correctNumber": 1,
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "<https://example.com/locations/handam.jpg>",
    "distanceMeter": 4200,
    "mission": null
  },
  "reward": {
    "arCharacter": null,
    "point": 100,
    "coupon": null
  }
}
```

다음 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.

---

### 오류 응답 데이터

Status Code : 404

`cultureMissionProgressId`에 해당하는 로그인한 사용자의 `IN_PROGRESS` 문화 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 409

요청한 `quizIndex`가 사용자가 현재 풀어야 하는 퀴즈 번호와 일치하지 않는 경우

```json
{
  "code": "CULTURE_MISSION_QUIZ_INDEX_MISMATCH"
}
```



## 문화 미션 중단
- http 메서드: patch
- domain: culture-mission
- endpoint: /api/v1/culture-missions/{cultureMissionProgressId}/progress/stop

### API 설명

사용자가 문화 미션을 끝까지 풀지 않고 중단할 때 호출한다.

Path로 전달받은 `cultureMissionProgressId`를 사용하여 로그인한 사용자의 진행 중인 문화 미션 진행도를 조회한다. 진행 중인 문화 미션 진행도가 있으면 진행도 상태를 즉시 `COMPLETED`로 변경한다.

중단한 문화 미션도 완료한 문화 미션처럼 취급한다. 따라서 중단 시점까지의 `correctNumber`를 기준으로 보상을 지급하고, 다음 추천 장소 정보를 함께 반환한다.

보상 지급 로직은 문화 미션 진행도 저장 API의 완료 처리와 동일하다. 같은 사용자와 같은 문화 미션의 전체 진행도 이력을 보고 이미 지급된 보상 항목은 제외하며, AR 캐릭터, 포인트, 쿠폰 순서로 정답 1개당 보상 항목 1개를 지급한다. 남은 보상보다 더 많이 지급하지 않는다.

`nextLocation`은 중단 완료 응답에서 항상 객체로 반환한다.

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
| `cultureMissionProgressId` | number | O | 중단할 문화 미션 진행도 id. `CULTURE_MISSION_PROGRESS.id` |

요청 예시

```
PATCH /api/v1/culture-missions/31/progress/stop?latitude=33.5572&longitude=126.7591
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

문화 미션을 정상적으로 중단하고 완료 처리한 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionProgressStatus` | string | 문화 미션 진행 상태. `COMPLETED` |
| `quizCount` | number | 문화 미션의 전체 문제 수 |
| `correctNumber` | number | 중단 시점까지 맞힌 문제 수 |
| `nextLocation` | object | 다음 추천 장소 정보. 중단 완료 응답에서는 항상 객체로 반환 |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string | null | 다음 장소 이미지 URL. TourAPI에서 조회하지 못하면 `null` |
| `nextLocation.distanceMeter` | number | 사용자 위치에서 다음 장소까지의 직선거리(m) |
| `nextLocation.mission` | object | null | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE | COOPERATIVE | TREASURE` |
| `reward` | object | 이번 중단 요청으로 실제 지급된 보상 정보. 중단은 완료 처리이므로 객체로 반환 |
| `reward.arCharacter` | object | null | 이번 요청으로 지급된 AR 캐릭터. 지급되지 않았으면 `null` |
| `reward.arCharacter.id` | number | AR 캐릭터 id |
| `reward.arCharacter.name` | string | AR 캐릭터 이름 |
| `reward.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `reward.point` | number | null | 이번 요청으로 지급된 포인트. 지급되지 않았으면 `null` |
| `reward.coupon` | object | null | 이번 요청으로 지급된 쿠폰. 지급되지 않았으면 `null` |
| `reward.coupon.couponLocation` | string | 쿠폰 사용처 |
| `reward.coupon.couponPrice` | number | 쿠폰 금액 |

```json
{
  "missionProgressStatus": "COMPLETED",
  "quizCount": 3,
  "correctNumber": 1,
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "<https://example.com/locations/handam.jpg>",
    "distanceMeter": 4200,
    "mission": {
      "id": 342,
      "missionType": "TREASURE"
    }
  },
  "reward": {
    "arCharacter": {
      "id": 7,
      "name": "돌담이",
      "imageUrl": "<https://example.com/characters/stone-spirit.png>"
    },
    "point": null,
    "coupon": null
  }
}
```

이번 중단 요청으로 지급되지 않은 보상 항목은 `null`로 반환한다. 예를 들어 이미 AR 캐릭터를 지급받은 상태에서 정답 1개로 중단하면 `reward.arCharacter`는 `null`, `reward.point`는 지급 포인트, `reward.coupon`은 `null`이 될 수 있다.

다음 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.

---

### 오류 응답 데이터

Status Code : 404

`cultureMissionProgressId`에 해당하는 로그인한 사용자의 `IN_PROGRESS` 문화 미션 진행도가 존재하지 않는 경우

- 진행도 id에 해당하는 데이터가 없는 경우
- 해당 진행도가 다른 사용자의 진행도인 경우
- 해당 진행도가 이미 `COMPLETED` 상태인 경우

```json
{
  "code": "CULTURE_MISSION_PROGRESS_NOT_FOUND"
}
```