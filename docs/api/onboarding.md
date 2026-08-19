## 사용자 온보딩 정보 수정
- http 메서드: PATCH
- 엔드포인트: `/api/v1/users/me`
- 도메인: onboarding

### API 설명

사용자가 시작 화면의 온보딩을 완료하거나 **나중에 할게요**를 선택했을 때 호출한다.

로그인할 때 생성된 현재 사용자의 `user` 데이터에 온보딩에서 선택한 여행 기대 항목, 이동 수단, 자투리 시간 여행 방식을 반영한다.

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
| `categories` | string[] | X | 여행 기대 항목. 선택 개수 제한 없음. `PHOTO \| LOCAL \| NATURE \| CULTURE \| CAFE \| WALKING` |
| `transportation` | string[] | X | 이동 수단 목록. 선택 개수 제한 없음. `WALK \| BUS \| CAR \| BICYCLE` |
| `travelStyle` | string[] | X | 자투리 시간 여행 방식 목록. 선택 개수 제한 없음. `RIGHT_HERE \| NEAR_AROUND \| NEAR_DESTINATION` |

온보딩을 정상적으로 진행한 경우

```json
{
  "categories": ["PHOTO", "LOCAL", "NATURE", "CAFE"],
  "transportation": ["WALK", "BUS", "CAR", "BICYCLE"],
  "travelStyle": ["RIGHT_HERE", "NEAR_AROUND", "NEAR_DESTINATION"]
}
```

**나중에 할게요**를 선택한 경우

```json
{}
```

---

### 정상 응답 데이터
Status Code : 200

| 필드 | 타입 | 설명 |
|---|---:|---|
| `user` | object | 온보딩 정보가 반영된 사용자 정보 |
| `user.id` | number | 사용자 id |
| `user.arCharacter` | object | 사용자에게 배정된 AR 캐릭터 정보 |
| `user.arCharacter.id` | number | AR 캐릭터 id |
| `user.arCharacter.name` | string | AR 캐릭터 이름 |
| `user.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `user.userTravelStyle` | object \| null | 사용자에게 배정된 여행 유형 정보 |
| `user.userTravelStyle.id` | number | 사용자 여행 유형 id |
| `user.userTravelStyle.userType` | string | 사용자 여행 유형명 |
| `user.userTravelStyle.typeDescription` | string | 사용자 여행 유형 설명 |
| `user.userTravelStyle.hashtags` | string[] | 사용자 여행 유형을 나타내는 해시태그 목록 |

온보딩을 정상적으로 진행한 경우

```json
{
  "user": {
    "id": 1,
    "arCharacter": {
      "id": 1,
      "name": "자청비 모티브 탐험가",
      "imageUrl": "https://example.com/images/characters/jacheongbi.png"
    },
    "userTravelStyle": {
      "id": 1,
      "userType": "새로운 순간을 담는 기록 탐험가",
      "typeDescription": "새로운 장소를 발견하고 사진과 포토스팟으로 순간을 남기는 걸 좋아하는 타입이에요.",
      "hashtags": ["인생사진", "로컬 탐방", "자연", "혼자 여행"]
    }
  }
}
```

**나중에 할게요**를 선택한 경우

```json
{
  "user": {
    "id": 1,
    "arCharacter": {
      "id": 1,
      "name": "돌멍이",
      "imageUrl": "https://example.com/images/characters/dolmungii.png"
    },
    "userTravelStyle": null
  }
}
```

---

### 오류 응답 데이터

없음
