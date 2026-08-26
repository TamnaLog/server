## 미션 홈 조회
- http 메서드: get
- domain: mission
- endpoint: /api/v1/missions/{missionType}/{missionId}

### API 설명

사용자가 미션을 클릭하여 미션 홈 화면에 진입할 때 호출한다.

Path로 전달받은 `missionType`과 `missionId`를 사용하여 미션을 조회한다. `missionType`에 해당하는 유형별 세부 미션 테이블에서 `missionId`를 조회하고, 연결된 공통 미션의 유형과 제목, 설명, 단계 정보 및 세부 미션의 보상 정보를 반환한다.

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
| `rewardDetail` | object | 미션 완료 보상 정보 |
| `rewardDetail.arCharacter` | object | null | 보상으로 획득할 AR 캐릭터. 캐릭터 보상이 없으면 `null` |
| `rewardDetail.arCharacter.id` | number | AR 캐릭터 id |
| `rewardDetail.arCharacter.name` | string | AR 캐릭터 이름 |
| `rewardDetail.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `rewardDetail.point` | number | 보상 포인트. 포인트 보상이 없으면 `0` |
| `rewardDetail.coupon` | object | null | 쿠폰 보상 정보. 쿠폰 보상이 없으면 `null` |
| `rewardDetail.coupon.couponLocation` | string | 쿠폰 사용처 |
| `rewardDetail.coupon.couponPrice` | number | 쿠폰 금액 |
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
  "rewardDetail": {
    "arCharacter": {
      "id": 7,
      "name": "돌담이",
      "imageUrl": "<https://example.com/characters/stone-spirit.png>"
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

---

### 오류 응답 데이터

Status Code : 404

`missionType`에 해당하는 유형별 세부 미션에 `missionId`가 존재하지 않거나, `missionType`과 `missionId`가 서로 일치하지 않는 경우

```json
{
  "code": "MISSION_NOT_FOUND"
}
```