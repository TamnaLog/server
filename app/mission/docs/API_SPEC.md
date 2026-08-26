## 미션 홈 조회
- http 메서드: get
- domain: mission
- endpoint: /api/v1/missions/{missionType}/{missionId}

### API 설명

사용자가 미션을 클릭하여 미션 홈 화면에 진입할 때 호출한다.

Path로 전달받은 `missionType`과 `missionId`를 사용하여 미션을 조회한다. `missionType`에 해당하는 유형별 세부 미션 테이블에서 `missionId`를 조회하고, 연결된 공통 미션의 유형과 제목, 설명, 단계 정보 및 아직 한 번도 지급되지 않은 보상 정보를 반환한다.

같은 미션을 여러 번 진행할 수 있으므로, 특정 보상이 해당 미션의 과거 진행도 중 한 번이라도 지급된 적이 있으면 해당 보상은 `remainingReward`에 포함하지 않고 `null`로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionType` | string | 조회할 미션 유형. `CULTURE | COOPERATIVE | TREASURE` |
| `missionId` | number | `missionType`에 해당하는 유형별 세부 미션 id |

요청 예시

```
GET /api/v1/missions/CULTURE/1
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | number | `missionType`에 해당하는 유형별 세부 미션 id |
| `missionType` | string | 미션 유형. `CULTURE | COOPERATIVE | TREASURE` |
| `missionTitle` | string | 미션 제목 |
| `description` | string | 미션 설명 |
| `remainingReward` | object | 아직 한 번도 지급되지 않은 미션 보상 정보 |
| `remainingReward.arCharacter` | object | null | 아직 한 번도 지급되지 않은 AR 캐릭터 보상. 과거 진행도에서 한 번이라도 지급됐거나 캐릭터 보상이 없으면 `null` |
| `remainingReward.arCharacter.id` | number | AR 캐릭터 id |
| `remainingReward.arCharacter.name` | string | AR 캐릭터 이름 |
| `remainingReward.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `remainingReward.point` | number | null | 아직 한 번도 지급되지 않은 포인트 보상. 과거 진행도에서 한 번이라도 지급됐거나 포인트 보상이 없으면 `null` |
| `remainingReward.coupon` | object | null | 아직 한 번도 지급되지 않은 쿠폰 보상 정보. 과거 진행도에서 한 번이라도 지급됐거나 쿠폰 보상이 없으면 `null` |
| `remainingReward.coupon.couponLocation` | string | 쿠폰 사용처 |
| `remainingReward.coupon.couponPrice` | number | 쿠폰 금액 |
| `steps` | object[] | 미션 단계 목록. `step` 오름차순으로 반환 |
| `steps[].step` | number | 단계 번호 |
| `steps[].stepTitle` | string | 단계 제목 |
| `steps[].description` | string | 단계 설명 |

```json
{
  "id": 12,
  "missionType": "CULTURE",
  "missionTitle": "오늘의 제주 퀴즈",
  "description": "제주의 퀴즈를 맞춰보세요.",
  "remainingReward": {
    "arCharacter": {
      "id": 7,
      "name": "돌담이",
      "imageUrl": "https://example.com/characters/stone-spirit.png"
    },
    "point": 100,
    "coupon": {
      "couponLocation": "종화네 막국수",
      "couponPrice": 1000
    }
  },
  "steps": [
    {
      "step": 1,
      "stepTitle": "퀴즈 시작하기",
      "description": "제주 방언에 대한 퀴즈를 풀어보세요."
    },
    {
      "step": 2,
      "stepTitle": "3문제 풀기",
      "description": "각 문제마다 4개의 보기 중 정답을 선택하세요."
    },
    {
      "step": 3,
      "stepTitle": "정답 확인",
      "description": "문제를 다 풀면 결과를 확인할 수 있어요."
    }
  ]
}
```

이미 진행한 미션의 과거 진행도에서 보상 3개가 모두 한 번 이상 지급된 경우

```json
{
  "id": 12,
  "missionType": "CULTURE",
  "missionTitle": "오늘의 제주 퀴즈",
  "description": "제주의 퀴즈를 맞춰보세요.",
  "remainingReward": {
    "arCharacter": null,
    "point": null,
    "coupon": null
  },
  "steps": [
    {
      "step": 1,
      "stepTitle": "퀴즈 시작하기",
      "description": "제주 방언에 대한 퀴즈를 풀어보세요."
    }
  ]
}
```

---

### 오류 응답 데이터

Status Code : 404

`missionType`에 해당하는 유형별 세부 미션에 `missionId`가 존재하지 않거나, `missionType`과 `missionId`가 서로 일치하지 않는 경우

```json
{
  "code": "MISSION_NOT_FOUND"
}
```
