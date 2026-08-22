## 마이페이지 조회
- http 메서드: GET
- 엔드포인트: `/api/v1/users/me/mypage`
- 도메인: mypage

### API 설명

사용자가 마이페이지 화면에 진입할 때 호출한다.

마이페이지 첫 화면을 구성하기 위해 사용자 프로필 정보, 오늘 걸음 수, 목표 걸음 수, 방문한 장소 수, 완료한 미션 수, 보유 포인트, 진행 중인 미션, AR 캐릭터 도감 정보를 함께 반환한다.

AR 캐릭터 도감은 전체 캐릭터를 반환한다. 사용자가 획득한 캐릭터는 캐릭터 상세 화면을 구성할 수 있도록 획득일, 획득 장소, 캐릭터 이야기, 해시태그 등 전체 정보를 반환한다. 사용자가 아직 획득하지 못한 캐릭터는 잠금 상태로 반환하고, 획득 조건만 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 200

마이페이지 정보를 정상적으로 조회한 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `profile` | object | 사용자 프로필 정보 |
| `profile.nickname` | string \| null | 사용자 닉네임. 설정하지 않았으면 `null` |
| `profile.travelStyleTags` | string[] | 사용자 여행 스타일 태그 목록 |
| `profile.selectedArCharacter` | object \| null | 마이페이지에 노출할 대표 AR 캐릭터. 선택한 캐릭터가 없으면 `null` |
| `profile.selectedArCharacter.id` | number | AR 캐릭터 id |
| `profile.selectedArCharacter.name` | string | AR 캐릭터 이름 |
| `profile.selectedArCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `dailyStep` | object | 오늘 걸음 수 정보 |
| `dailyStep.stepCount` | number | 오늘 걸음 수 |
| `dailyStep.targetStepCount` | number | 목표 걸음 수 |
| `summary` | object | 마이페이지 요약 수치 |
| `summary.visitedLocationCount` | number | 방문한 장소 수 |
| `summary.completedMissionCount` | number | 완료한 미션 수 |
| `summary.point` | number | 보유 포인트 |
| `progressMissions` | object[] | 진행 중인 미션 목록 |
| `progressMissions[].missionId` | number | 진행 중인 미션 id |
| `progressMissions[].missionType` | string | 미션 유형. `CULTURE \| TREASURE \| COOPERATIVE` |
| `progressMissions[].missionTitle` | string | 진행 중인 미션 이름 |
| `progressMissions[].currentCount` | number | 현재 진행 수 |
| `progressMissions[].totalCount` | number | 전체 진행 수 |
| `progressMissions[].progressRatio` | number | 진행률. 0부터 1 사이 숫자 |
| `progressMissions[].thumbnailImageUrl` | string \| null | 진행 중인 미션 썸네일 이미지 URL. 없으면 `null` |
| `arCharacters` | object[] | AR 캐릭터 도감 목록 |
| `arCharacters[].id` | number | AR 캐릭터 id |
| `arCharacters[].name` | string | AR 캐릭터 이름 |
| `arCharacters[].imageUrl` | string \| null | AR 캐릭터 이미지 URL. 미획득 캐릭터도 실루엣 처리가 가능하면 이미지 URL을 반환하고, 없으면 `null` |
| `arCharacters[].isAcquired` | boolean | 캐릭터 획득 여부 |
| `arCharacters[].acquiredAt` | string \| null | 캐릭터 획득 날짜. 미획득이면 `null` |
| `arCharacters[].acquiredLocation` | string \| null | 캐릭터 획득 장소. 미획득이면 `null` |
| `arCharacters[].storyTitle` | string \| null | 캐릭터 이야기 제목. 미획득이면 `null` |
| `arCharacters[].storyContent` | string \| null | 캐릭터 이야기 내용. 미획득이면 `null` |
| `arCharacters[].hashtags` | string[] \| null | 캐릭터 해시태그 목록. 미획득이면 `null` |
| `arCharacters[].acquireCondition` | string | 캐릭터 획득 조건 |
| `arCharacters[].acquiredMission` | object \| null | 캐릭터를 획득한 미션 정보. 미획득이면 `null` |
| `arCharacters[].acquiredMission.id` | number | 획득 미션 id |
| `arCharacters[].acquiredMission.missionType` | string | 획득 미션 유형. `CULTURE \| TREASURE \| COOPERATIVE` |
| `arCharacters[].acquiredMission.missionTitle` | string | 획득 미션 이름 |

```json
{
  "profile": {
    "nickname": "몽글몽글파도",
    "travelStyleTags": ["기록 탐험가", "인생샷", "렌트카"],
    "selectedArCharacter": {
      "id": 2,
      "name": "로컬 탐험가",
      "imageUrl": "https://example.com/characters/local-explorer.png"
    }
  },
  "dailyStep": {
    "stepCount": 6820,
    "targetStepCount": 10000
  },
  "summary": {
    "visitedLocationCount": 12,
    "completedMissionCount": 8,
    "point": 1240
  },
  "progressMissions": [
    {
      "missionId": 501,
      "missionType": "TREASURE",
      "missionTitle": "보물 찾기",
      "currentCount": 3,
      "totalCount": 5,
      "progressRatio": 0.6,
      "thumbnailImageUrl": "https://example.com/missions/treasure-box.png"
    }
  ],
  "arCharacters": [
    {
      "id": 1,
      "name": "바람 정령",
      "imageUrl": "https://example.com/characters/wind-spirit.png",
      "isAcquired": true,
      "acquiredAt": "2026-08-20",
      "acquiredLocation": "새별오름",
      "storyTitle": "제주 바람의 장난꾸러기",
      "storyContent": "제주 오름 사이를 뛰어다니며 여행자의 발걸음을 가볍게 만들어줘요.",
      "hashtags": ["#오름", "#제주바람", "#산책친구"],
      "acquireCondition": "새별오름 미션을 완료하면 만날 수 있어요.",
      "acquiredMission": {
        "id": 201,
        "missionType": "CULTURE",
        "missionTitle": "오름 바람 퀴즈"
      }
    },
    {
      "id": 3,
      "name": "점박이 물범",
      "imageUrl": "https://example.com/characters/spotted-seal.png",
      "isAcquired": true,
      "acquiredAt": "2026-08-21",
      "acquiredLocation": "섭지코지",
      "storyTitle": "제주 바다의 느긋한 안내자",
      "storyContent": "제주 해안가에 살던 물범. 여행자의 발걸음을 따라다니며 좋은 사진 포인트를 알려줘요.",
      "hashtags": ["#자연물입가", "#제주바다", "#사진친구"],
      "acquireCondition": "섭지코지 방명록 미션을 완료하고 걸음수 보상을 3회 달성하면 만날 수 있어요.",
      "acquiredMission": {
        "id": 301,
        "missionType": "TREASURE",
        "missionTitle": "섭지코지 방명록 미션"
      }
    },
    {
      "id": 4,
      "name": "미획득 캐릭터",
      "imageUrl": null,
      "isAcquired": false,
      "acquiredAt": null,
      "acquiredLocation": null,
      "storyTitle": null,
      "storyContent": null,
      "hashtags": null,
      "acquireCondition": "협동 미션을 완료하면 만날 수 있어요.",
      "acquiredMission": null
    }
  ]
}
```

- `progressMissions`는 진행 중인 미션이 없으면 빈 배열로 반환한다.
- `arCharacters`는 획득 여부와 관계없이 전체 캐릭터를 반환한다.
- 미획득 캐릭터는 `acquireCondition`만 의미 있는 값으로 반환하고, 상세 정보는 `null`로 반환한다.
- 미획득 캐릭터의 `name`과 `imageUrl` 노출 여부는 프론트의 잠금 UI 표현 방식에 따라 조정할 수 있다.

---

### 오류 응답 데이터

없음



## 사용자 정보 변경
- http 메서드: PATCH
- 엔드포인트: `/api/v1/users/me/profile`
- 도메인: mypage

### API 설명

사용자가 프로필 수정 화면에서 닉네임, 여행 기대 항목, 이동수단, 자투리 시간 여행 방식, 목표 걸음 수를 변경한 뒤 저장할 때 호출한다.

프론트는 사용자가 수정한 프로필 정보를 요청 Body로 전달한다. 서버는 로그인한 사용자의 닉네임, 여행 기대 항목, 이동수단, 자투리 시간 여행 방식, 목표 걸음 수를 저장하고 응답 Body 없이 `204 No Content`를 반환한다.

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
| `nickname` | string | O | 변경할 사용자 닉네임 |
| `categories` | string[] | O | 변경할 여행 기대 항목. `PHOTO \| LOCAL \| NATURE \| CULTURE \| CAFE \| WALKING` |
| `transportation` | string[] | O | 변경할 이동수단 목록. `WALK \| BUS \| CAR \| BICYCLE` |
| `travelStyle` | string[] | O | 변경할 자투리 시간 여행 방식 목록. `RIGHT_HERE \| NEAR_AROUND \| NEAR_DESTINATION` |
| `targetStepCount` | number | O | 변경할 목표 걸음 수 |

```json
{
  "nickname": "몽글몽글파도",
  "categories": ["PHOTO", "LOCAL"],
  "transportation": ["WALK", "BUS"],
  "travelStyle": ["RIGHT_HERE", "NEAR_AROUND"],
  "targetStepCount": 10000
}
```

- `categories`, `transportation`, `travelStyle`은 온보딩 API와 동일한 영문 코드를 사용한다.
- 각 배열은 프론트에서 선택된 값만 전달한다.
- 목표 걸음 수를 직접 입력한 경우에도 `targetStepCount`에 숫자로 전달한다.

---

### 정상 응답 데이터
Status Code : 204

사용자 정보를 정상적으로 변경한 경우

응답 Body 없음

---

### 오류 응답 데이터
Status Code : 400

닉네임이 비어 있거나 허용 길이를 초과한 경우

```json
{
  "code": "USER_NICKNAME_INVALID"
}
```

Status Code : 400

여행 기대 항목 값이 유효하지 않은 경우

```json
{
  "code": "USER_CATEGORY_INVALID"
}
```

Status Code : 400

이동수단 값이 유효하지 않은 경우

```json
{
  "code": "USER_TRANSPORTATION_INVALID"
}
```

Status Code : 400

자투리 시간 여행 방식 값이 유효하지 않은 경우

```json
{
  "code": "USER_TRAVEL_STYLE_INVALID"
}
```

Status Code : 400

목표 걸음 수가 유효하지 않은 경우

```json
{
  "code": "USER_TARGET_STEP_COUNT_INVALID"
}
```
