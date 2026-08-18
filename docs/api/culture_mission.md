## 문화 미션 진행도 생성
- http 메서드: POST
- 엔드포인트: `/api/v1/culture-missions/{missionId}/progress`
- 도메인: culture-mission

### API 설명

사용자가 문화 미션을 시작하거나 진행 중이던 문화 미션을 이어서 할 때 호출한다.

Path로 전달받은 `missionId`를 사용하여 문화 미션을 조회한다. 로그인한 사용자의 진행도가 없으면 상태를 `INPROGRESS`, 현재 퀴즈 번호를 `1`, 정답 개수를 `0`으로 초기화하여 진행도를 생성한다.

이미 진행 중인 기록이 있으면 진행도를 새로 만들지 않고 기존 기록을 반환한다. `currentQuizNumber`에는 사용자가 다음에 풀 퀴즈 번호를 반환한다. 예를 들어 1번 퀴즈까지 풀었다면 `2`를 반환한다.

프론트에서 문화 미션 화면을 구성할 수 있도록 전체 문제 정보와 보상, 다음 장소 정보를 함께 반환한다. 문제의 정답은 주관식과 객관식 모두 문자열로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionId` | number | 진행도를 생성하거나 조회할 문화 미션 id |

요청 예시

```text
POST /api/v1/culture-missions/12/progress
```

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 201

문화 미션 진행도를 새로 생성한 경우

Status Code : 200

이미 진행 중인 문화 미션을 이어서 하는 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `quizCount` | number | 문화 미션의 전체 문제 수 |
| `currentQuizNumber` | number | 사용자가 다음에 풀 퀴즈 번호. 신규 진행도는 `1` |
| `quizDetails` | object[] | `quizIndex` 오름차순으로 정렬된 전체 문제 목록 |
| `quizDetails[].quizIndex` | number | 문제 번호 |
| `quizDetails[].imgUrl` | string \| null | 문제 이미지 URL. 이미지가 없으면 `null` |
| `quizDetails[].question` | string | 문제 내용 |
| `quizDetails[].options` | string[] \| null | 객관식 선택지. 주관식 문제이면 `null` |
| `quizDetails[].answer` | string | 문제 정답. 객관식도 선택지 번호가 아닌 정답 문자열 |
| `quizDetails[].hint` | string | 문제 힌트 |
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
  "quizCount": 3,
  "currentQuizNumber": 2,
  "quizDetails": [
    {
      "quizIndex": 1,
      "imgUrl": "https://example.com/images/quizzes/jeju-dialect-1.jpg",
      "question": "제주어로 할아버지는 무엇일까요?",
      "options": ["하르방", "하라범", "하르봉", "하르범"],
      "answer": "하르방",
      "hint": "제주의 돌하르방을 떠올려 보세요."
    },
    {
      "quizIndex": 2,
      "imgUrl": "https://example.com/images/quizzes/jeju-drama.jpg",
      "question": "제주를 배경으로 여러 인물의 삶을 옴니버스 형식으로 담아낸 노희경 작가의 드라마는 무엇일까요?",
      "options": ["우리들의 블루스", "우도의 봄", "갯마을 차차차", "도깨비"],
      "answer": "우리들의 블루스",
      "hint": "제목에 제주 바다를 연상시키는 색상이 들어가요."
    },
    {
      "quizIndex": 3,
      "imgUrl": null,
      "question": "'하영'은 제주 방언으로 어떤 뜻일까요?",
      "options": null,
      "answer": "많이",
      "hint": "수량이 넉넉하다는 의미로 사용해요."
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
  },
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
    "mission": {
      "id": 342,
      "missionType": "TREASURE"
    }
  }
}
```

다음 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.

---

### 오류 응답 데이터
Status Code : 404

`missionId`에 해당하는 문화 미션이 존재하지 않는 경우

```json
{
  "code": "CULTURE_MISSION_NOT_FOUND"
}
```

Status Code : 409

사용자가 이미 완료한 문화 미션인 경우

```json
{
  "code": "CULTURE_MISSION_ALREADY_COMPLETED"
}
```
