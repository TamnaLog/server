## 마이페이지 조회

- http 메서드: get
- domain: mypage
- endpoint: /api/v1/users/me/mypage

### API 설명

사용자가 마이페이지 화면에 진입할 때 호출한다.

마이페이지 첫 화면을 구성하기 위해 사용자 프로필, 목표 걸음 수, 방문한 장소 수, 완료한 미션 수, 보유 포인트, 진행 중인 미션과 AR 캐릭터 도감 정보를 함께 반환한다.

AR 캐릭터 도감은 사용자의 획득 여부와 관계없이 전체 캐릭터를 반환한다. 미획득 캐릭터도 이름, 실제 이미지, 캐릭터 이야기, 해시태그, 획득 조건과 연결된 미션 목록을 반환한다. `acquiredAt`은 미획득이면 null이고, `acquiredLocation`은 미획득이거나 획득 장소를 확인할 수 없으면 null이다.

이 API는 `Authorization: Bearer {accessToken}` 헤더가 필수이며, 액세스 토큰으로 현재 사용자를 식별한다.

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

Status Code : `200 OK`

마이페이지 정보를 정상적으로 조회한 경우

| 필드                                             | 타입     | 설명                                                                             |
| ------------------------------------------------ | -------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------ |
| `profile`                                        | object   | 사용자 프로필 정보                                                               |
| `profile.nickname`                               | string   | null                                                                             | 사용자 닉네임. 설정하지 않았으면 null                                       |
| `profile.travelStyle`                            | object   | null                                                                             | 사용자 여행 스타일. 진단된 여행 스타일이 없으면 null                        |
| `profile.travelStyle.userType`                   | string   | 사용자 여행 유형명. `USER_TRAVEL_STYLE.user_type`                                |
| `profile.travelStyle.hashtags`                   | string[] | 사용자 여행 스타일 해시태그 목록. `USER_TRAVEL_STYLE.hashtags`                   |
| `profile.selectedArCharacter`                    | object   | null                                                                             | 마이페이지에 노출할 대표 AR 캐릭터. 선택한 캐릭터가 없으면 null             |
| `profile.selectedArCharacter.id`                 | integer  | AR 캐릭터 ID                                                                     |
| `profile.selectedArCharacter.name`               | string   | AR 캐릭터 이름                                                                   |
| `profile.selectedArCharacter.imageUrl`           | string   | AR 캐릭터 이미지 URL                                                             |
| `dailyStep`                                      | object   | 목표 걸음 수 정보                                                                |
| `dailyStep.targetStepCount`                      | integer  | 목표 걸음 수                                                                     |
| `summary`                                        | object   | 마이페이지 요약 수치                                                             |
| `summary.visitedLocationCount`                   | integer  | 중복을 제외한 방문 장소 수                                                       |
| `summary.completedMissionCount`                  | integer  | 완료한 미션 수. 협동 미션은 삭제되지 않은 ACCEPTED 참가 기록만 포함              |
| `summary.point`                                  | integer  | 현재 사용자의 보유 포인트. `USER.point`                                          |
| `progressMissions`                               | object[] | 현재 사용자의 진행 중인 미션 목록. 없으면 빈 배열                                |
| `progressMissions[].missionId`                   | integer  | `missionType`에 해당하는 유형별 세부 미션 ID                                     |
| `progressMissions[].missionType`                 | string   | 미션 유형. `CULTURE                                                              | TREASURE                                                                    | COOPERATIVE` |
| `progressMissions[].missionTitle`                | string   | 진행 중인 미션 제목                                                              |
| `progressMissions[].currentCount`                | integer  | 현재 진행 수. 문화는 현재 퀴즈 번호, 보물찾기는 발견한 보물 수, 협동은 현재 단계 |
| `progressMissions[].totalCount`                  | integer  | 전체 진행 수. 문화는 전체 퀴즈 수, 보물찾기는 전체 보물 수, 협동은 전체 단계 수  |
| `arCharacters`                                   | object[] | 획득 여부와 관계없이 반환하는 전체 AR 캐릭터 도감 목록                           |
| `arCharacters[].id`                              | integer  | AR 캐릭터 ID                                                                     |
| `arCharacters[].name`                            | string   | AR 캐릭터 이름. 미획득 캐릭터도 반환                                             |
| `arCharacters[].imageUrl`                        | string   | AR 캐릭터 실제 이미지 URL. 미획득 캐릭터도 동일하게 반환                         |
| `arCharacters[].isAcquired`                      | boolean  | 현재 사용자의 캐릭터 획득 여부                                                   |
| `arCharacters[].acquiredAt`                      | string   | null                                                                             | 캐릭터 획득 날짜. 미획득이면 null, 획득했으면 YYYY-MM-DD 형식               |
| `arCharacters[].acquiredLocation`                | string   | null                                                                             | 캐릭터 획득 장소. 미획득이거나 연결된 미션에서 장소를 확인할 수 없으면 null |
| `arCharacters[].storyTitle`                      | string   | 캐릭터 이야기 제목. 미획득 캐릭터도 반환                                         |
| `arCharacters[].storyContent`                    | string   | 캐릭터 이야기 내용. 미획득 캐릭터도 반환                                         |
| `arCharacters[].hashtags`                        | string[] | 캐릭터 해시태그 목록. 미획득 캐릭터도 반환                                       |
| `arCharacters[].acquireCondition`                | string   | 캐릭터 획득 조건                                                                 |
| `arCharacters[].acquiredMissions`                | object[] | 캐릭터를 획득할 수 있는 미션 목록. 없으면 빈 배열, 최대 3개                      |
| `arCharacters[].acquiredMissions[].id`           | integer  | `missionType`에 해당하는 유형별 세부 미션 ID                                     |
| `arCharacters[].acquiredMissions[].missionType`  | string   | 미션 유형. `CULTURE                                                              | TREASURE                                                                    | COOPERATIVE` |
| `arCharacters[].acquiredMissions[].missionTitle` | string   | 미션 제목                                                                        |

```json
{
  "profile": {
    "nickname": "몽글몽글파도",
    "travelStyle": {
      "userType": "기록 탐험가",
      "hashtags": ["#인생샷", "#로컬탐방", "#자연"]
    },
    "selectedArCharacter": {
      "id": 2,
      "name": "로컬 탐험가",
      "imageUrl": "https://example.com/characters/local-explorer.png"
    }
  },
  "dailyStep": {
    "targetStepCount": 10000
  },
  "summary": {
    "visitedLocationCount": 12,
    "completedMissionCount": 8,
    "point": 1240
  },
  "progressMissions": [
    {
      "missionId": 1,
      "missionType": "TREASURE",
      "missionTitle": "보물 찾기",
      "currentCount": 1,
      "totalCount": 3
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
      "acquiredMissions": [
        {
          "id": 1,
          "missionType": "CULTURE",
          "missionTitle": "오름 바람 퀴즈"
        }
      ]
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
      "acquireCondition": "섭지코지 보물찾기를 완료하면 만날 수 있어요.",
      "acquiredMissions": [
        {
          "id": 3,
          "missionType": "TREASURE",
          "missionTitle": "섭지코지 보물찾기"
        }
      ]
    },
    {
      "id": 4,
      "name": "귤나무 정령",
      "imageUrl": "https://example.com/characters/tangerine-tree-spirit.png",
      "isAcquired": false,
      "acquiredAt": null,
      "acquiredLocation": null,
      "storyTitle": "제주 귤밭의 작은 수호자",
      "storyContent": "제주의 따뜻한 햇살과 바람을 먹고 자라며 여행자와 함께 귤나무를 돌봐요.",
      "hashtags": ["#제주감귤", "#귤나무", "#협동친구"],
      "acquireCondition": "함께 키우는 귤나무 협동 미션을 완료하면 만날 수 있어요.",
      "acquiredMissions": [
        {
          "id": 2,
          "missionType": "COOPERATIVE",
          "missionTitle": "함께 키우는 귤나무"
        }
      ]
    }
  ]
}
```

- `summary.visitedLocationCount`는 현재 사용자의 `VISITED_LOCATION.location_id`를 중복 제거해 집계한다.
- `summary.completedMissionCount`는 세 미션 유형의 완료 기록을 합산한다. 협동 미션은 현재 사용자의 `participant_status = ACCEPTED`이고 `deleted_at IS NULL`인 참가 기록만 포함한다.
- `progressMissions`는 진행 중인 미션이 없으면 빈 배열로 반환한다.
- `progressMissions[].currentCount`는 문화 미션의 현재 퀴즈 번호, 보물찾기 미션의 발견한 보물 수, 협동 미션의 현재 단계를 사용한다.
- `progressMissions[].totalCount`는 문화 미션의 전체 퀴즈 수, 보물찾기 미션의 전체 보물 수, 협동 미션의 전체 단계 수를 사용한다.
- `arCharacters`는 현재 사용자의 획득 여부와 관계없이 전체 캐릭터를 반환한다. `USER.ar_character_id`에 배정되었지만 `ACQUIRED_AR_CHARACTER`에 없는 캐릭터는 대표 캐릭터로 반환될 수 있으며 도감의 `isAcquired`는 false다.
- 미획득 캐릭터도 실제 `imageUrl`을 반환하며, 실루엣·잠금 효과는 프론트가 `isAcquired = false`를 기준으로 적용한다.
- 미획득 캐릭터도 `name`, `storyTitle`, `storyContent`, `hashtags`, `acquireCondition`, `acquiredMissions`를 획득 캐릭터와 동일하게 반환한다.
- `acquiredAt`은 미획득이면 null이다. `acquiredLocation`은 미획득이거나 연결된 미션에서 장소를 확인할 수 없으면 null이다.
- `arCharacters[].acquiredMissions`는 해당 캐릭터를 보상으로 설정한 미션을 공통 `MISSION.id ASC`로 정렬한 뒤 최대 3개 반환한다.
- `progressMissions[].missionId`와 `arCharacters[].acquiredMissions[].id`는 공통 `MISSION.id`가 아니라 `missionType`에 해당하는 유형별 세부 미션 ID다.

---

### 오류 응답 데이터

## 사용자 정보 변경

- http 메서드: put
- domain: mypage
- endpoint: /api/v1/users/me/profile

### API 설명

사용자가 프로필 수정 화면에서 닉네임, 여행 기대 항목, 이동수단, 자투리 시간 여행 방식과 목표 걸음 수를 변경한 뒤 저장할 때 호출한다.

프론트는 수정 화면의 전체 프로필 정보를 전달한다. 서버는 액세스 토큰으로 식별한 현재 사용자의 정보를 교체하고, 변경된 선택값을 기존 온보딩 매칭 모듈에 전달해 사용자 여행 유형과 AR 캐릭터를 다시 배정한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

Content-Type : `application/json`

| 필드              | 타입     | 필수 | 설명                                                                              |
| ----------------- | -------- | ---- | --------------------------------------------------------------------------------- |
| `nickname`        | string   | O    | 앞뒤 공백을 제거한 뒤 1~20자. 중복 닉네임 허용                                    |
| `categories`      | string[] | O    | 빈 배열 허용, 중복 불가. `PHOTO \| LOCAL \| NATURE \| CULTURE \| CAFE \| WALKING` |
| `transportation`  | string[] | O    | 빈 배열 허용, 중복 불가. `WALK \| BUS \| CAR \| BICYCLE`                          |
| `travelStyle`     | string[] | O    | 빈 배열 허용, 중복 불가. `RIGHT_HERE \| NEAR_AROUND \| NEAR_DESTINATION`          |
| `targetStepCount` | integer  | O    | 1 이상 100000 이하의 정수                                                         |

```json
{
  "nickname": "몽글몽글파도",
  "categories": ["PHOTO", "LOCAL"],
  "transportation": ["WALK", "BUS"],
  "travelStyle": ["RIGHT_HERE", "NEAR_AROUND"],
  "targetStepCount": 10000
}
```

- 모든 필드는 필수이며 현재 값을 포함한 전체 프로필 정보를 전달한다.
- 선택 배열에 중복값이 있으면 `400 Bad Request`를 반환한다.
- 닉네임 길이 또는 목표 걸음 수 형식·범위가 유효하지 않으면 `400 Bad Request`를 반환한다.

---

### 정상 응답 데이터

Status Code : 204

응답 Body 없음

---

### 오류 응답 데이터

## 사용자 정보 조회

- http 메서드: get
- domain: mypage
- endpoint: /api/v1/users/me

### API 설명

프로필 수정 화면에 필요한 현재 사용자 정보를 조회한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별하고, 사용자의 여행 유형, 대표 AR 캐릭터 이미지, 닉네임, 현재 설정된 여행 선택값과 목표 걸음 수를 반환한다.

사용자 정보를 조회만 하며 데이터는 변경하지 않는다.

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

Status Code : `200 OK`

| 자료형   | 변수명            | 설명                                                |
| -------- | ----------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------- | -------------------------- | ---- | -------------------------- |
| string   | null              | `userType`                                          | 현재 사용자에게 배정된 여행 유형. `USER.user_travel_style_id`로 연결된 `USER_TRAVEL_STYLE.user_type`. 배정되지 않았으면 null      |
| string   | null              | `arCharacterImageUrl`                               | 현재 사용자의 대표 AR 캐릭터 이미지 URL. `USER.ar_character_id`로 연결된 `AR_CHARACTER.character_img_url`. 배정되지 않았으면 null |
| string   | null              | `nickname`                                          | 현재 사용자 닉네임. 설정되지 않았으면 null                                                                                        |
| string[] | null              | `categories`                                        | 현재 설정된 여행 기대 항목. `USER.expectation`. `PHOTO                                                                            | LOCAL       | NATURE                              | CULTURE                    | CAFE | WALKING`. 설정 전이면 null |
| string[] | null              | `transportation`                                    | 현재 설정된 이동수단 목록. `USER.transportation`. `WALK                                                                           | BUS         | CAR                                 | BICYCLE`. 설정 전이면 null |
| string[] | null              | `travelStyle`                                       | 현재 설정된 자투리 시간 여행 방식 목록. `USER.travel_style`. `RIGHT_HERE                                                          | NEAR_AROUND | NEAR_DESTINATION`. 설정 전이면 null |
| integer  | `targetStepCount` | 현재 사용자의 하루 목표 걸음 수. `USER.target_step` |

```json
{
  "userType": "동네 깊숙이 걷는 로컬 탐험가",
  "arCharacterImageUrl": "https://example.com/characters/local-explorer.png",
  "nickname": "몽글몽글파도",
  "categories": ["PHOTO", "LOCAL"],
  "transportation": ["WALK", "BUS"],
  "travelStyle": ["RIGHT_HERE", "NEAR_AROUND"],
  "targetStepCount": 10000
}
```

- 응답의 `categories`는 DB 컬럼 `USER.expectation`을 API에서 사용하는 이름이다.
- `categories`, `transportation`, `travelStyle`은 사용자 온보딩 정보 저장 및 사용자 정보 변경 API와 동일한 영문 코드를 사용한다.
- 세 배열은 설정 전 상태의 `null`과 사용자가 아무 항목도 선택하지 않은 빈 배열 `[]`을 구분하여 저장된 값을 그대로 반환한다.
- `userType`과 `arCharacterImageUrl`은 각각 연결된 여행 유형과 대표 AR 캐릭터가 없으면 `null`을 반환한다.
- `targetStepCount`는 `NOT NULL` 컬럼이며 기본값은 `10000`이다.

---

### 오류 응답 데이터

없음

## 여행 마무리 엽서 요소 조회

- http 메서드: get
- domain: mypage
- endpoint: /api/v1/users/me/travel-ending-elements

### API 설명

사용자가 여행 마무리 엽서에 넣을 요소를 선택하기 위해 호출한다.

현재 사용자의 보유 포인트, 방문 장소와 완료 미션을 반환한다. 방문 장소와 완료 미션은 각각 배열과 배열 항목 수를 함께 반환하며 사진 정보는 포함하지 않는다.

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

| 필드                                                      | 타입           | 설명                                                             |
| --------------------------------------------------------- | -------------- | ---------------------------------------------------------------- |
| `point`                                                   | integer        | 현재 사용자의 보유 포인트                                        |
| `visitedLocationCount`                                    | integer        | 중복을 제외한 방문 장소 수. `visitedLocations` 배열 길이와 동일  |
| `visitedLocations`                                        | object[]       | 방문 장소 목록. 없으면 빈 배열                                   |
| `visitedLocations[].id`                                   | integer        | LOCATION id                                                      |
| `visitedLocations[].locationTitle`                        | string         | 장소명                                                           |
| `completedMissionCount`                                   | integer        | 중복을 제외한 완료 미션 수. `completedMissions` 배열 길이와 동일 |
| `completedMissions`                                       | object[]       | 완료 미션 목록. 없으면 빈 배열                                   |
| `completedMissions[].missionId`                           | integer        | `missionType`에 해당하는 유형별 세부 미션 id                     |
| `completedMissions[].missionType`                         | string         | `CULTURE \| TREASURE \| COOPERATIVE`                             |
| `completedMissions[].missionTitle`                        | string         | 미션 제목                                                        |
| `completedMissions[].completedLocation`                   | string \| null | 완료 장소명. 장소가 없는 문화 미션은 `null`                      |
| `completedMissions[].completedAt`                         | string         | 가장 최근 완료 시각. KST 기준 offset 없는 ISO 8601 형식          |
| `completedMissions[].rewardDetail`                        | object         | 미션에 설정된 전체 보상과 종류별 수령 여부                       |
| `completedMissions[].rewardDetail.arCharacter`            | object \| null | AR 캐릭터 보상. 없으면 `null`                                    |
| `completedMissions[].rewardDetail.arCharacter.id`         | integer        | AR 캐릭터 id                                                     |
| `completedMissions[].rewardDetail.arCharacter.name`       | string         | AR 캐릭터 이름                                                   |
| `completedMissions[].rewardDetail.arCharacter.imageUrl`   | string         | AR 캐릭터 이미지 URL                                             |
| `completedMissions[].rewardDetail.arCharacter.isReceived` | boolean        | AR 캐릭터 보상 수령 여부                                         |
| `completedMissions[].rewardDetail.point`                  | object \| null | 포인트 보상. 없으면 `null`                                       |
| `completedMissions[].rewardDetail.point.amount`           | integer        | 포인트 보상량                                                    |
| `completedMissions[].rewardDetail.point.isReceived`       | boolean        | 포인트 보상 수령 여부                                            |
| `completedMissions[].rewardDetail.coupon`                 | object \| null | 쿠폰 보상. 없으면 `null`                                         |
| `completedMissions[].rewardDetail.coupon.couponLocation`  | string         | 쿠폰 사용 장소                                                   |
| `completedMissions[].rewardDetail.coupon.couponPrice`     | integer        | 쿠폰 금액                                                        |
| `completedMissions[].rewardDetail.coupon.isReceived`      | boolean        | 쿠폰 보상 수령 여부                                              |

```json
{
  "point": 2000,
  "visitedLocationCount": 3,
  "visitedLocations": [
    { "id": 15, "locationTitle": "성산일출봉" },
    { "id": 22, "locationTitle": "애월 해변" },
    { "id": 31, "locationTitle": "한라산" }
  ],
  "completedMissionCount": 2,
  "completedMissions": [
    {
      "missionId": 4,
      "missionType": "CULTURE",
      "missionTitle": "성산일출봉 문화 퀴즈",
      "completedLocation": null,
      "completedAt": "2026-08-20T14:20:00",
      "rewardDetail": {
        "arCharacter": null,
        "point": { "amount": 100, "isReceived": true },
        "coupon": null
      }
    },
    {
      "missionId": 7,
      "missionType": "TREASURE",
      "missionTitle": "한라산 보물찾기",
      "completedLocation": "한라산",
      "completedAt": "2026-08-19T11:30:00",
      "rewardDetail": {
        "arCharacter": {
          "id": 3,
          "name": "바람 정령",
          "imageUrl": "https://example.com/characters/wind-spirit.png",
          "isReceived": true
        },
        "point": { "amount": 100, "isReceived": true },
        "coupon": {
          "couponLocation": "한라산 기념품숍",
          "couponPrice": 3000,
          "isReceived": false
        }
      }
    }
  ]
}
```

조회 결과가 없으면 count는 `0`, 목록은 빈 배열로 반환한다. 사진 목록과 사진 개수는 반환하지 않는다.

---

### 오류 응답 데이터

없음

## 여행 마무리 엽서 저장

- http 메서드: post
- domain: mypage
- endpoint: /api/v1/users/me/travel-ending-contents

### API 설명

사용자가 선택한 방문 장소, 완료 미션과 사진을 바탕으로 여행 마무리 엽서 이미지를 생성할 때 호출한다.

한 번의 요청에서 방문 장소, 완료 미션, 사진을 각각 1개 이상 3개 이하로 선택해야 하며 여행 한 줄은 선택적으로 전달한다.

백엔드는 액세스 토큰으로 현재 사용자를 식별하고, 전달된 방문 장소와 완료 미션이 현재 사용자의 여행 마무리 엽서 요소 조회 결과에 포함될 수 있는 데이터인지 검증한다.

검증이 완료되면 선택한 방문 장소의 이름과 대표 이미지, 완료 미션의 이름과 관련 장소 이름·대표 이미지, 사용자가 첨부한 사진 및 여행 한 줄을 모두 활용하여 세로형 게시판·스크랩북 형태의 이미지 한 장을 생성한다.

이미지 생성 전에 현재 사용자의 보유 포인트가 100 이상인지 확인한다. 정상적으로 생성된 이미지는 Azure Blob Storage에 저장하고 Blob URL을 `TRAVEL_ENDING_CONTENT.image_url`에 저장하며, 생성 1회마다 `USER.point`에서 100포인트를 차감한다.

이미지 생성부터 Blob 및 DB 저장까지 모두 완료한 뒤 생성된 엽서 id, 이미지 URL과 차감 후 잔여 포인트를 동기 응답으로 반환한다. 같은 내용으로 다시 요청하더라도 새로운 이미지를 생성하고 100포인트를 다시 차감한다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

Content-Type: `multipart/form-data`

| 필드                     | 타입                     | 필수 | 설명                                                                                                                 |
| ------------------------ | ------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------- | -------- | ------------ |
| `visitedLocationIds`     | string(JSON integer\[\]) | O    | 엽서에 포함할 방문 장소의 `LOCATION.id` 배열을 JSON 문자열로 전달. 1~3개이며 중복 불가                               |
| `missions`               | string(JSON object\[\])  | O    | 엽서에 포함할 완료 미션 배열을 JSON 문자열로 전달. 1~3개이며 동일한 `missionType`과 `missionId` 조합은 중복 불가     |
| `missions[].missionType` | string                   | O    | 미션 유형. `CULTURE                                                                                                  | TREASURE | COOPERATIVE` |
| `missions[].missionId`   | integer                  | O    | `missionType`에 해당하는 유형별 세부 미션 id                                                                         |
| `photos`                 | file\[\]                 | O    | 엽서에 포함할 사용자 사진. 동일한 `photos` 필드명을 반복하여 1~3개 전송. JPEG, PNG, WebP만 허용하며 파일당 최대 10MB |
| `travelNote`             | string                   | X    | 엽서에 포함할 여행 한 줄. 생략 가능하며 비즈니스상 글자 수 제한 없음                                                 |

요청 예시

```
visitedLocationIds: [15, 22, 31]
missions: [{"missionType":"CULTURE","missionId":4},{"missionType":"TREASURE","missionId":7}]
photos: seongsan.jpg
photos: aewol.png
travelNote: 잠깐 머문, 오래 남는 순간.
```

`visitedLocationIds`와 `missions`는 각 JSON 배열 전체를 하나의 multipart 문자열 필드로 전송한다. `photos`는 파일마다 동일한 필드명을 반복한다.

각 선택 목록이 1~3개 범위를 벗어나거나, 중복값·허용되지 않은 미션 유형·잘못된 JSON·허용되지 않은 이미지가 포함된 경우 `400 Bad Request`를 반환한다.

현재 사용자가 방문하지 않은 장소 또는 완료하지 않은 미션을 전달한 경우에도 `400 Bad Request`를 반환한다.

---

### 정상 응답 데이터

Status Code : 201

| 필드             | 타입    | 설명                                                            |
| ---------------- | ------- | --------------------------------------------------------------- |
| `id`             | integer | 생성된 여행 마무리 엽서 id. `TRAVEL_ENDING_CONTENT.id`          |
| `imageUrl`       | string  | 생성 후 Azure Blob Storage에 저장된 여행 마무리 엽서 이미지 URL |
| `remainingPoint` | integer | 엽서 생성 비용 100포인트 차감 후 현재 사용자의 잔여 포인트      |

```json
{
  "id": 12,
  "imageUrl": "https://jamkkanjejustorage.blob.core.windows.net/media/travel-ending/1/7a13d8f0f6bc4af1899166fd14d6188b.png",
  "remainingPoint": 1900
}
```

---

### 오류 응답 데이터

Status Code : 409

이미지 생성을 시작하기 전 현재 사용자의 보유 포인트가 100 미만인 경우

```json
{
  "code": "INSUFFICIENT_POINT"
}
```
