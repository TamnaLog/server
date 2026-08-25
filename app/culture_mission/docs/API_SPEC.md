## 문화 미션 시작/이어하기
- http 메서드: post
- domain: culture_mission
- endpoint: /api/v1/culture-missions/{missionId}/progress

### API 설명

사용자가 문화 미션을 처음 시작하거나 진행 중이던 문화 미션을 이어서 할 때 호출한다.

`missionId`에 해당하는 문화 미션과 로그인한 사용자의 진행도를 조회한다. 진행 중인 기록이 없으면 현재 퀴즈 번호를 `1`, 정답 개수를 `0`으로 초기화한 진행도를 새로 생성한다. 이미 `IN_PROGRESS` 상태인 기록이 있으면 새로 생성하지 않고 해당 진행도를 반환한다.

완료한 진행도가 있더라도 같은 문화 미션을 다시 시작할 수 있다. 이 경우 기존 완료 기록은 유지하고 새로운 진행도를 생성하여 Status Code `201`로 반환한다.

`isRewarded`는 사용자가 해당 미션의 보상을 이미 받은 적이 있는지를 나타낸다. 동일한 사용자와 문화 미션에 `COMPLETED` 상태의 이전 진행도가 하나 이상 있으면 `true`, 없으면 `false`를 반환한다. 문화 미션의 최초 완료 처리와 보상 지급은 하나의 트랜잭션으로 처리하므로 완료된 진행도는 보상이 지급된 기록으로 간주한다. 재도전 완료 시에도 백엔드는 이전 완료 기록을 확인하여 보상을 중복 지급하지 않는다.

`currentQuizNumber`에는 사용자가 다음에 풀 퀴즈 번호를 반환한다. 예를 들어 1번 퀴즈까지 풀었다면 `2`를 반환한다.

프론트에서 문화 미션 화면을 구성할 수 있도록 전체 문제 정보와 각 문제의 해설, 보상 정보를 함께 반환한다. 문제의 정답은 주관식과 객관식 모두 문자열로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `missionId` | number | O | 진행도를 생성하거나 조회할 문화 미션 id |

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

문화 미션 진행도를 새로 생성한 경우. 처음 시작하는 경우와 완료한 미션을 다시 시작하는 경우를 포함한다.

Status Code : 200

이미 진행 중인 문화 미션을 이어서 하는 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `quizCount` | number | 문화 미션의 전체 문제 수 |
| `currentQuizNumber` | number | 사용자가 다음에 풀 퀴즈 번호. 신규 진행도는 `1` |
| `isRewarded` | boolean | 동일한 사용자와 문화 미션에 보상 지급을 완료한 이전 `COMPLETED` 진행도가 있는지 여부 |
| `quizDetails` | object[] | `quizIndex` 오름차순으로 정렬된 전체 문제 목록 |
| `quizDetails[].quizIndex` | number | 문제 번호 |
| `quizDetails[].imgUrl` | string \| null | 문제 이미지 URL. 이미지가 없으면 `null` |
| `quizDetails[].question` | string | 문제 내용 |
| `quizDetails[].options` | string[] \| null | 객관식 선택지. 주관식 문제이면 `null` |
| `quizDetails[].answer` | string | 문제 정답. 객관식도 선택지 번호가 아닌 정답 문자열 |
| `quizDetails[].hint` | string | 문제 힌트 |
| `quizDetails[].explanation` | string | 문제 정답 해설 |
| `rewardDetail` | object | 미션 완료 보상 정보 |
| `rewardDetail.arCharacter` | object \| null | 보상으로 획득할 AR 캐릭터. 캐릭터 보상이 없으면 `null` |
| `rewardDetail.arCharacter.id` | number | AR 캐릭터 id |
| `rewardDetail.arCharacter.name` | string | AR 캐릭터 이름 |
| `rewardDetail.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `rewardDetail.point` | number | 보상 포인트. 포인트 보상이 없으면 `0` |
| `rewardDetail.coupon` | object \| null | 쿠폰 보상 정보. 쿠폰 보상이 없으면 `null` |
| `rewardDetail.coupon.couponLocation` | string | 쿠폰 사용처 |
| `rewardDetail.coupon.couponPrice` | number | 쿠폰 금액 |

완료한 문화 미션을 다시 시작한 경우의 응답 예시

```json
{
  "quizCount": 3,
  "currentQuizNumber": 1,
  "isRewarded": true,
  "quizDetails": [
    {
      "quizIndex": 1,
      "imgUrl": "https://example.com/images/quizzes/jeju-dialect-1.jpg",
      "question": "제주어로 할아버지는 무엇일까요?",
      "options": ["하르방", "하라범", "하르봉", "하르범"],
      "answer": "하르방",
      "hint": "제주의 돌하르방을 떠올려 보세요.",
      "explanation": "제주어에서 할아버지를 뜻하는 대표적인 표현은 하르방입니다."
    },
    {
      "quizIndex": 2,
      "imgUrl": "https://example.com/images/quizzes/jeju-drama.jpg",
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

`missionId`에 해당하는 문화 미션이 존재하지 않는 경우

```json
{
  "code": "CULTURE_MISSION_NOT_FOUND"
}
```
