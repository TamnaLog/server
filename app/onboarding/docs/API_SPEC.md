## 사용자 온보딩 정보 저장
- http 메서드: patch
- domain: onborading
- endpoint: /api/v1/users/me


### API 설명

사용자가 시작 화면의 온보딩의 모든 스텝을 완료하거나 **나중에 할게요**를 선택했을 때 호출한다.

온보딩에서 선택한 여행 기대 항목, 주 이동 수단, 자투리 시간 여행 방식을 기준으로 `user` 테이블에 사용자 정보를 생성한다.

---

### 처리 정책

- 온보딩을 정상적으로 진행한 경우 `categories`, `transportation`, `travelStyle` 값을 저장한다.
- `categories`는 여행 기대 항목이며 `PHOTO`, `LOCAL`, `NATURE`, `CULTURE`, `CAFE`, `WALKING` 중 선택된 값을 전달한다.
- `transportation`은 주 이동 수단이며 `WALK`, `BUS`, `CAR`, `BICYCLE` 중 선택된 값을 전달한다.
- `travelStyle`은 자투리 시간 여행 방식이며 `RIGHT_HERE`, `NEAR_AROUND`, `NEAR_DESTINATION` 중 선택된 값을 전달한다.
- **나중에 할게요**를 선택한 경우 요청 Body는 빈 객체 `{}`로 전달한다.
- **나중에 할게요**를 선택하면 사용자 스타일은 `null`로 남겨두고 기본 캐릭터인 돌멍이를 반환한다.
- 로그인 구현 전에는 현재 사용자를 항상 id=1로 간주한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `categories` | string[] | X | 여행 기대 항목. 허용값: `PHOTO`, `LOCAL`, `NATURE`, `CULTURE`, `CAFE`, `WALKING` |
| `transportation` | string[] | X | 주 이동 수단. 허용값: `WALK`, `BUS`, `CAR`, `BICYCLE` |
| `travelStyle` | string[] | X | 자투리 시간 여행 방식. 허용값: `RIGHT_HERE`, `NEAR_AROUND`, `NEAR_DESTINATION` |

온보딩을 정상적으로 진행한 경우

```json
{
  "categories": ["PHOTO", "LOCAL", "NATURE", "CAFE"],
  "transportation": ["WALK", "BICYCLE"],
  "travelStyle": ["RIGHT_HERE", "NEAR_DESTINATION"]
}
```

**나중에 할게요**를 선택한 경우

```json
{}
```

---

### 정상 응답 데이터

Status Code : 201

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `user` | object | 생성된 사용자 정보 |
| `user.id` | number | 사용자 id |
| `user.arCharacter` | object | 사용자에게 배정된 AR 캐릭터 정보 |
| `user.arCharacter.id` | number | AR 캐릭터 id |
| `user.arCharacter.name` | string | AR 캐릭터 이름 |
| `user.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `user.userTravelStyle` | object or null | 사용자에게 배정된 여행 유형 정보. **나중에 할게요**를 선택하면 `null` |
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
      "hashtags": ["#인생사진", "#로컬 탐방", "#자연", "#혼자 여행"]
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
      "id": 11,
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