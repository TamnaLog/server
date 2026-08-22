## 협동 미션 시작하기/이어하기
- http 메서드: POST
- 엔드포인트: `/api/v1/cooperative-missions/{missionId}/progress`
- 도메인: cooperative-mission

### API 설명

방장이 협동 미션을 시작하거나 진행 중이던 협동 미션을 이어서 할 때 호출한다.

Path로 전달받은 `missionId`를 사용하여 협동 미션을 조회한다. 로그인한 사용자의 진행 중인 협동 미션 진행도가 없으면 `currentStep`을 `1`, 상태를 `INPROGRESS`로 초기화하여 진행도를 생성한다.

진행도를 새로 생성할 때 방장을 참여자로 함께 생성한다. 방장은 `participantType`을 `USER`, `isHost`를 `true`로 저장한다. 또한 팀원이 같은 협동 미션 방에 참여할 수 있도록 팀 단위 초대 URL을 생성하여 반환한다.

이미 진행 중인 기록이 있으면 진행도를 새로 만들지 않고 기존 협동 미션 방 상태를 반환한다. 기존 초대 URL, 참여자 목록, 역할 카드 목록, 역할 배정 및 진행 상태를 함께 반환한다.

프론트에서 현재 협동 미션 화면을 구성할 수 있도록 진행도 정보, 초대 URL, 참여자 목록, 역할 카드 목록, 역할 진행도 목록, 보상 정보를 함께 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionId` | number | 진행도를 생성하거나 조회할 협동 미션 id |

요청 예시

```text
POST /api/v1/cooperative-missions/12/progress
```

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 201

협동 미션 진행도를 새로 생성한 경우

Status Code : 200

이미 진행 중인 협동 미션을 이어서 하는 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 협동 미션 진행도 id |
| `missionProgressStatus` | string | 협동 미션 진행 상태. `INPROGRESS \| COMPLETED` |
| `currentStep` | number | 현재 협동 미션 단계. 신규 진행도는 `1` |
| `inviteUrl` | string | 팀원이 협동 미션 방에 참여할 수 있는 팀 단위 초대 URL |
| `participants` | object[] | 협동 미션 참여자 목록 |
| `participants[].participantId` | number | 참여자 id |
| `participants[].name` | string | 참여자 이름. 사용자는 닉네임, 게스트는 입력한 이름 |
| `participants[].participantType` | string | 참여자 유형. `USER \| GUEST` |
| `participants[].isHost` | boolean | 방장 여부 |
| `participants[].participantStatus` | string | 참여자 상태. `ACCEPTED \| LEFT` |
| `roleCards` | object[] | 협동 미션의 전체 역할 카드 목록 |
| `roleCards[].roleCardId` | number | 역할 카드 id |
| `roleCards[].roleName` | string | 역할 이름 |
| `roleCards[].roleDescription` | string | 역할 설명 |
| `roleCards[].locationToFind` | string | 역할 수행을 위해 찾아야 하는 장소 또는 대상 |
| `roleCards[].hint` | string | 역할 수행 힌트 |
| `roleCards[].pictureGuide` | string | 사진 인증 가이드 |
| `roleProgresses` | object[] | 저장된 역할 배정 및 진행도 목록. 아직 배정 전이면 빈 배열 |
| `roleProgresses[].roleProgressId` | number | 역할 진행도 id |
| `roleProgresses[].participantId` | number | 역할을 맡은 참여자 id |
| `roleProgresses[].participantName` | string | 역할을 맡은 참여자 이름 |
| `roleProgresses[].roleCardId` | number | 배정된 역할 카드 id |
| `roleProgresses[].roleName` | string | 배정된 역할 이름 |
| `roleProgresses[].progressStatus` | string | 역할 진행 상태. `INPROGRESS \| COMPLETED` |
| `roleProgresses[].itemImgUrl` | string \| null | 역할 인증 이미지 URL. 아직 인증 전이면 `null` |
| `rewardDetail` | object | 미션 완료 보상 정보 |
| `rewardDetail.arCharacter` | object \| null | 보상으로 획득할 AR 캐릭터. 캐릭터 보상이 없으면 `null` |
| `rewardDetail.arCharacter.id` | number | AR 캐릭터 id |
| `rewardDetail.arCharacter.name` | string | AR 캐릭터 이름 |
| `rewardDetail.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `rewardDetail.point` | number | 보상 포인트. 포인트 보상이 없으면 `0` |
| `rewardDetail.coupon` | object \| null | 쿠폰 보상 정보. 쿠폰 보상이 없으면 `null` |
| `rewardDetail.coupon.couponLocation` | string | 쿠폰 사용처 |
| `rewardDetail.coupon.couponPrice` | number | 쿠폰 금액 |

```json
{
  "missionProgressId": 10,
  "missionProgressStatus": "INPROGRESS",
  "currentStep": 1,
  "inviteUrl": "https://front.example.com/cooperative-missions/invite?token=team-token",
  "participants": [
    {
      "participantId": 1,
      "name": "나민",
      "participantType": "USER",
      "isHost": true,
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": [
    {
      "roleCardId": 1,
      "roleName": "비료 주기 담당",
      "roleDescription": "영양 만점 제주 감귤나무로 자랄 수 있도록 풍부한 비료 성분을 찾아주세요.",
      "locationToFind": "귤 농장",
      "hint": "귤나무 주변 흙을 살펴보세요.",
      "pictureGuide": "비료 또는 흙 주변이 보이도록 촬영해주세요."
    },
    {
      "roleCardId": 2,
      "roleName": "물주기 담당",
      "roleDescription": "귤나무가 마르지 않게 미션 장소 근처 식물이나 깨끗한 물 배경을 촬영해 촉촉함을 유지해주세요.",
      "locationToFind": "해변가",
      "hint": "물이 보이는 장소를 찾아보세요.",
      "pictureGuide": "물 또는 식물이 함께 보이도록 촬영해주세요."
    },
    {
      "roleCardId": 3,
      "roleName": "가지치기 담당",
      "roleDescription": "이쁜 감귤 모양과 햇살을 잘 받을 수 있도록 불필요한 가지 대신 둥근 하늘을 찾아 잘 담아주세요.",
      "locationToFind": "올레길",
      "hint": "나뭇가지와 하늘이 보이는 곳을 찾아보세요.",
      "pictureGuide": "나뭇가지와 하늘이 함께 보이도록 촬영해주세요."
    }
  ],
  "roleProgresses": [],
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

`missionId`에 해당하는 협동 미션이 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_NOT_FOUND"
}
```

Status Code : 409

사용자가 이미 완료한 협동 미션인 경우

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```



## 초대 url 정보 조회
- http 메서드: GET
- 엔드포인트: `/api/v1/cooperative-missions/invitations/{inviteToken}`
- 도메인: cooperative-mission

### API 설명

초대 URL을 받은 게스트가 협동 미션 참여 화면에 진입할 때 호출한다.

Path로 전달받은 `inviteToken`을 사용하여 협동 미션 진행도를 조회한다. 유효한 초대 URL이면 게스트가 어떤 협동 미션 방에 초대되었는지 확인할 수 있도록 미션 정보, 현재 단계, 참여자 목록을 반환한다.

이 API는 초대 정보를 조회만 하며, 게스트 참여자를 생성하지 않는다. 게스트가 이름이나 별명을 입력하고 참여를 확정하면 `초대 url로 게스트 참여` API를 호출한다.

프론트는 이 응답을 사용하여 초대 URL이 유효한지 확인하고, 게스트 이름 입력 화면 또는 현재 협동 미션 대기 화면을 구성한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `inviteToken` | string | 팀 단위 초대 URL 토큰 |

요청 예시

```text
GET /api/v1/cooperative-missions/invitations/team-token
```

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 200

초대 URL 정보가 정상적으로 조회된 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 협동 미션 진행도 id |
| `missionId` | number | 협동 미션 id |
| `missionTitle` | string | 협동 미션 제목 |
| `missionProgressStatus` | string | 협동 미션 진행 상태. `INPROGRESS \| COMPLETED` |
| `currentStep` | number | 현재 협동 미션 단계 |
| `participants` | object[] | 협동 미션 참여자 목록 |
| `participants[].participantId` | number | 참여자 id |
| `participants[].name` | string | 참여자 이름. 사용자는 닉네임, 게스트는 입력한 이름 |
| `participants[].participantType` | string | 참여자 유형. `USER \| GUEST` |
| `participants[].isHost` | boolean | 방장 여부 |
| `participants[].participantStatus` | string | 참여자 상태. `ACCEPTED \| LEFT` |

```json
{
  "missionProgressId": 10,
  "missionId": 12,
  "missionTitle": "함께 키우는 귤나무",
  "missionProgressStatus": "INPROGRESS",
  "currentStep": 1,
  "participants": [
    {
      "participantId": 1,
      "name": "나민",
      "participantType": "USER",
      "isHost": true,
      "participantStatus": "ACCEPTED"
    }
  ]
}
```

---

### 오류 응답 데이터
Status Code : 404

`inviteToken`에 해당하는 초대 URL이 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_INVITATION_NOT_FOUND"
}
```

Status Code : 409

이미 완료된 협동 미션 초대 URL인 경우

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```




## 초대 url로 게스트 참여
- http 메서드: POST
- 엔드포인트: `/api/v1/cooperative-missions/invitations/{inviteToken}/participants`
- 도메인: cooperative-mission

### API 설명

초대 URL을 받은 게스트가 이름이나 별명을 입력하고 협동 미션 방 참여를 확정할 때 호출한다.

Path로 전달받은 `inviteToken`을 사용하여 협동 미션 진행도를 조회한다. 유효한 초대 URL이면 요청 Body로 전달받은 `guestName`을 사용하여 게스트 참여자를 생성한다.

게스트 참여자는 `participantType`을 `GUEST`, `participantStatus`를 `ACCEPTED`, `isHost`를 `false`로 저장한다. 백엔드는 게스트를 다시 식별할 수 있도록 `guestToken`을 생성하여 함께 저장한다.

프론트는 URL에서 읽은 `inviteToken`과 응답으로 받은 `missionProgressId`, `participantId`, `guestToken`, `name`을 게스트의 로컬 저장소 또는 쿠키에 저장해둔다. 이후 게스트가 같은 초대 URL로 재접속하면 저장된 `inviteToken`, `participantId`, `guestToken`을 사용하여 기존 게스트로 복귀하고, 협동 미션 상태 조회, 역할 배정, 역할 인증 요청에서 본인 식별값으로 사용한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `inviteToken` | string | 팀 단위 초대 URL 토큰 |

요청 예시

```text
POST /api/v1/cooperative-missions/invitations/team-token/participants
```

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
|---|---:|:---:|---|
| `guestName` | string | O | 게스트가 입력한 이름 또는 별명 |

```json
{
  "guestName": "이서연"
}
```

---

### 정상 응답 데이터
Status Code : 201

게스트가 협동 미션 방에 정상적으로 참여한 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 협동 미션 진행도 id |
| `participantId` | number | 생성된 게스트 참여자 id |
| `name` | string | 게스트 이름 |
| `participantType` | string | 참여자 유형. `GUEST` |
| `guestToken` | string | 게스트 재접속 및 본인 식별에 사용할 게스트 토큰 |
| `isHost` | boolean | 방장 여부. 게스트는 `false` |
| `participantStatus` | string | 참여자 상태. `ACCEPTED` |

```json
{
  "missionProgressId": 10,
  "participantId": 2,
  "name": "이서연",
  "participantType": "GUEST",
  "guestToken": "guest-token-xyz",
  "isHost": false,
  "participantStatus": "ACCEPTED"
}
```

---

### 오류 응답 데이터
Status Code : 404

`inviteToken`에 해당하는 초대 URL이 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_INVITATION_NOT_FOUND"
}
```

Status Code : 409

이미 완료된 협동 미션 초대 URL인 경우

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```





## 협동 미션 진행도 저장
- http 메서드: PATCH
- 엔드포인트: `/api/v1/cooperative-missions/{missionProgressId}/progress`
- 도메인: cooperative-mission

### API 설명

방장이 협동 미션의 다음 단계로 이동할 때 호출한다.

Path로 전달받은 `missionProgressId`를 사용하여 협동 미션 진행도를 조회한다. 요청 Body로 전달받은 `currentStep`으로 협동 미션 진행도의 현재 단계를 변경한다.

`currentStep`이 `2`이면 팀 확정 단계로, 별도의 추가 데이터 없이 단계만 변경한다.

`currentStep`이 `3`이면 역할 배정 확정 단계로, 프론트에서 확정한 역할 배정 정보를 `roleAssignments`로 함께 전달한다. 백엔드는 협동 미션에 존재하는 모든 역할 카드가 정확히 한 번씩 배정되었는지 검증한 뒤 역할 진행도를 저장하고 단계를 변경한다.

역할 인증과 미션 완료 처리는 `협동 미션 역할 진행도 저장` API에서 처리한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 저장할 협동 미션 진행도 id |

요청 예시

```text
PATCH /api/v1/cooperative-missions/10/progress
```

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
|---|---:|:---:|---|
| `currentStep` | number | O | 변경할 협동 미션 단계. `2 \| 3` |
| `roleAssignments` | object[] | 조건부 | 역할 배정 목록. `currentStep`이 `3`이면 필수 |
| `roleAssignments[].participantId` | number | O | 역할을 맡을 참여자 id |
| `roleAssignments[].roleCardId` | number | O | 배정할 역할 카드 id |

1단계에서 2단계로 이동하는 경우

```json
{
  "currentStep": 2
}
```

2단계에서 3단계로 이동하며 역할 배정을 저장하는 경우

```json
{
  "currentStep": 3,
  "roleAssignments": [
    {
      "participantId": 1,
      "roleCardId": 1
    },
    {
      "participantId": 2,
      "roleCardId": 2
    },
    {
      "participantId": 1,
      "roleCardId": 3
    }
  ]
}
```

---

### 정상 응답 데이터
Status Code : 200

협동 미션 진행도를 정상적으로 저장한 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 협동 미션 진행도 id |
| `missionProgressStatus` | string | 협동 미션 진행 상태. `INPROGRESS \| COMPLETED` |
| `currentStep` | number | 저장된 협동 미션 단계 |
| `roleProgresses` | object[] | 저장된 역할 배정 및 진행도 목록 |
| `roleProgresses[].roleProgressId` | number | 역할 진행도 id |
| `roleProgresses[].participantId` | number | 역할을 맡은 참여자 id |
| `roleProgresses[].participantName` | string | 역할을 맡은 참여자 이름 |
| `roleProgresses[].roleCardId` | number | 배정된 역할 카드 id |
| `roleProgresses[].roleName` | string | 배정된 역할 이름 |
| `roleProgresses[].progressStatus` | string | 역할 진행 상태. `INPROGRESS \| COMPLETED` |
| `roleProgresses[].itemImgUrl` | string \| null | 역할 인증 이미지 URL. 아직 인증 전이면 `null` |

1단계에서 2단계로 이동한 경우

```json
{
  "missionProgressId": 10,
  "missionProgressStatus": "INPROGRESS",
  "currentStep": 2,
  "roleProgresses": []
}
```

2단계에서 3단계로 이동하며 역할 배정을 저장한 경우

```json
{
  "missionProgressId": 10,
  "missionProgressStatus": "INPROGRESS",
  "currentStep": 3,
  "roleProgresses": [
    {
      "roleProgressId": 1,
      "participantId": 1,
      "participantName": "나민",
      "roleCardId": 1,
      "roleName": "비료 주기 담당",
      "progressStatus": "INPROGRESS",
      "itemImgUrl": null
    },
    {
      "roleProgressId": 2,
      "participantId": 2,
      "participantName": "이서연",
      "roleCardId": 2,
      "roleName": "물주기 담당",
      "progressStatus": "INPROGRESS",
      "itemImgUrl": null
    },
    {
      "roleProgressId": 3,
      "participantId": 1,
      "participantName": "나민",
      "roleCardId": 3,
      "roleName": "가지치기 담당",
      "progressStatus": "INPROGRESS",
      "itemImgUrl": null
    }
  ]
}
```

---

### 오류 응답 데이터
Status Code : 404

`missionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

## 협동 미션 중단
- http 메서드: PATCH
- 엔드포인트: `/api/v1/cooperative-missions/{missionProgressId}/progress/stop`
- 도메인: cooperative-mission

### API 설명

방장이 협동 미션을 끝까지 진행하지 않고 중단할 때 호출한다.

Path로 전달받은 `missionProgressId`를 사용하여 협동 미션 진행도를 조회한다. 진행 중인 협동 미션이 있으면 진행도 상태를 즉시 `COMPLETED`로 변경한다.

중단한 협동 미션도 완료한 협동 미션처럼 취급한다.

프론트에서 중단 완료 화면을 구성할 수 있도록 진행 상태, 전체 역할 카드 수, 인증 완료된 역할 수, 미션의 전체 보상 정보, 다음 장소 정보를 함께 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 중단할 협동 미션 진행도 id |

요청 예시

```text
PATCH /api/v1/cooperative-missions/10/progress/stop
```

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 200

협동 미션을 정상적으로 중단하고 완료 처리한 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 협동 미션 진행도 id |
| `missionProgressStatus` | string | 협동 미션 진행 상태. `COMPLETED` |
| `totalRoleCount` | number | 전체 역할 카드 수 |
| `completedRoleCount` | number | 인증 완료된 역할 수 |
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
  "missionProgressId": 10,
  "missionProgressStatus": "COMPLETED",
  "totalRoleCount": 3,
  "completedRoleCount": 1,
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

`missionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 409

이미 완료된 협동 미션인 경우

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```

## 협동 미션 역할 진행도 저장
- http 메서드: PATCH
- 엔드포인트: `/api/v1/cooperative-missions/{missionProgressId}/role-progress/{roleProgressId}`
- 도메인: cooperative-mission

### API 설명

팀원이 역할 카드에 맞는 사진을 첨부하고 인증하기 버튼을 눌렀을 때 호출한다.

Path로 전달받은 `missionProgressId`와 `roleProgressId`를 사용하여 협동 미션 역할 진행도를 조회한다. `multipart/form-data`로 전달받은 `itemImage` 파일을 사용하여 해당 역할 카드의 인증 조건에 맞는 사진인지 검증한다.

사진 인증에 실패하면 역할 진행도를 변경하지 않고 인증 실패 결과만 반환한다.

사진 인증에 성공하면 해당 역할 진행도의 `progressStatus`를 `COMPLETED`로 변경한다. 사진 파일은 DB에 저장하지 않는다. 모든 역할 진행도가 `COMPLETED`이면 협동 미션 진행도 상태를 `COMPLETED`로 변경한다.

프론트는 이 API의 응답으로 인증 성공 여부만 확인하고, 이후 polling 중인 `협동 미션 상태 조회` API 응답을 통해 역할 진행도와 미션 완료 여부를 갱신한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 협동 미션 진행도 id |
| `roleProgressId` | number | 저장할 역할 진행도 id |

요청 예시

```text
PATCH /api/v1/cooperative-missions/10/role-progress/3
```

---

### 요청 Body

Content-Type: `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
|---|---:|:---:|---|
| `itemImage` | file | O | 인증에 사용할 사진 파일 |

```text
itemImage: material.jpg
```

---

### 정상 응답 데이터
Status Code : 200

사진 인증 결과가 정상적으로 반환된 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `isVerified` | boolean | 사진 인증 성공 여부 |
| `verificationMessage` | string | 사진 인증 결과 메시지 |

인증에 성공한 경우

```json
{
  "isVerified": true,
  "verificationMessage": "역할 인증에 성공했습니다."
}
```

인증에 실패한 경우

```json
{
  "isVerified": false,
  "verificationMessage": "역할 카드의 인증 조건에 맞는 사진이 아닙니다."
}
```

---

### 오류 응답 데이터
Status Code : 404

`missionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

`roleProgressId`에 해당하는 역할 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_NOT_FOUND"
}
```

Status Code : 409

현재 협동 미션 단계가 미션 수행 단계가 아닌 경우

```json
{
  "code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"
}
```

Status Code : 409

이미 완료된 협동 미션인 경우

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```

Status Code : 409

이미 완료된 역할 진행도인 경우

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED"
}
```

## 협동 미션 상태 조회
- http 메서드: GET
- 엔드포인트: `/api/v1/cooperative-missions/{missionProgressId}/progress`
- 도메인: cooperative-mission

### API 설명

방장과 게스트가 협동 미션 방의 최신 상태를 조회할 때 호출한다.

프론트는 협동 미션 진행 중 이 API를 polling하여 현재 단계, 참여자 목록, 역할 카드 목록, 역할 배정 및 인증 상태를 갱신한다.

`currentStep`은 `1`, `2`, `3`만 사용한다. `1`은 초대 단계, `2`는 역할 정하기 단계, `3`은 미션 수행 단계이다. 미션 완료 여부는 `currentStep`이 아니라 `missionProgressStatus`로 판단한다.

프론트는 게스트 참여 시 로컬 저장소 또는 쿠키에 저장한 `participantId`와 응답의 `participants`, `roleProgresses`를 비교하여 현재 게스트 본인과 본인이 맡은 역할을 판단한다.

협동 미션이 아직 완료되지 않았으면 `nextLocation`은 `null`로 반환한다. 모든 역할 인증이 완료되어 미션이 완료된 경우 `missionProgressStatus`는 `COMPLETED`이고 `nextLocation`을 함께 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 조회할 협동 미션 진행도 id |

요청 예시

```text
GET /api/v1/cooperative-missions/10/progress
```

---

### 요청 Body

없음

---

### 정상 응답 데이터
Status Code : 200

협동 미션 상태가 정상적으로 조회된 경우

| 필드 | 타입 | 설명 |
|---|---:|---|
| `missionProgressId` | number | 협동 미션 진행도 id |
| `missionId` | number | 협동 미션 id |
| `missionTitle` | string | 협동 미션 제목 |
| `missionProgressStatus` | string | 협동 미션 진행 상태. `INPROGRESS \| COMPLETED` |
| `currentStep` | number | 현재 협동 미션 단계. `1: 초대, 2: 역할 정하기, 3: 미션 수행` |
| `participants` | object[] | 협동 미션 참여자 목록 |
| `participants[].participantId` | number | 참여자 id |
| `participants[].name` | string | 참여자 이름. 사용자는 닉네임, 게스트는 입력한 이름 |
| `participants[].participantType` | string | 참여자 유형. `USER \| GUEST` |
| `participants[].isHost` | boolean | 방장 여부 |
| `participants[].participantStatus` | string | 참여자 상태. `ACCEPTED \| LEFT` |
| `roleCards` | object[] | 협동 미션의 전체 역할 카드 목록 |
| `roleCards[].roleCardId` | number | 역할 카드 id |
| `roleCards[].roleName` | string | 역할 이름 |
| `roleCards[].roleDescription` | string | 역할 설명 |
| `roleCards[].locationToFind` | string | 역할 수행을 위해 찾아야 하는 장소 또는 대상 |
| `roleCards[].hint` | string | 역할 수행 힌트 |
| `roleCards[].pictureGuide` | string | 사진 인증 가이드 |
| `roleProgresses` | object[] | 저장된 역할 배정 및 진행도 목록. 아직 배정 전이면 빈 배열 |
| `roleProgresses[].roleProgressId` | number | 역할 진행도 id |
| `roleProgresses[].participantId` | number | 역할을 맡은 참여자 id |
| `roleProgresses[].participantName` | string | 역할을 맡은 참여자 이름 |
| `roleProgresses[].roleCardId` | number | 배정된 역할 카드 id |
| `roleProgresses[].roleName` | string | 배정된 역할 이름 |
| `roleProgresses[].progressStatus` | string | 역할 진행 상태. `INPROGRESS \| COMPLETED` |
| `roleProgresses[].itemImgUrl` | string \| null | 역할 인증 이미지 URL. 아직 인증 전이면 `null` |
| `completedRoleCount` | number | 인증 완료된 역할 수 |
| `totalRoleCount` | number | 전체 역할 카드 수 |
| `nextLocation` | object \| null | 다음 추천 장소 정보. 완료 전이면 `null` |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string | 다음 장소 이미지 URL |
| `nextLocation.mission` | object \| null | 다음 장소에서 수행할 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE \| COOPERATIVE \| TREASURE` |

```json
{
  "missionProgressId": 10,
  "missionId": 12,
  "missionTitle": "함께 키우는 귤나무",
  "missionProgressStatus": "INPROGRESS",
  "currentStep": 3,
  "participants": [
    {
      "participantId": 1,
      "name": "나민",
      "participantType": "USER",
      "isHost": true,
      "participantStatus": "ACCEPTED"
    },
    {
      "participantId": 2,
      "name": "이서연",
      "participantType": "GUEST",
      "isHost": false,
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": [
    {
      "roleCardId": 1,
      "roleName": "비료 주기 담당",
      "roleDescription": "영양 만점 제주 감귤나무로 자랄 수 있도록 풍부한 비료 성분을 찾아주세요.",
      "locationToFind": "귤 농장",
      "hint": "귤나무 주변 흙을 살펴보세요.",
      "pictureGuide": "비료 또는 흙 주변이 보이도록 촬영해주세요."
    },
    {
      "roleCardId": 2,
      "roleName": "물주기 담당",
      "roleDescription": "귤나무가 마르지 않게 미션 장소 근처 식물이나 깨끗한 물 배경을 촬영해 촉촉함을 유지해주세요.",
      "locationToFind": "해변가",
      "hint": "물이 보이는 장소를 찾아보세요.",
      "pictureGuide": "물 또는 식물이 함께 보이도록 촬영해주세요."
    }
  ],
  "roleProgresses": [
    {
      "roleProgressId": 1,
      "participantId": 1,
      "participantName": "나민",
      "roleCardId": 1,
      "roleName": "비료 주기 담당",
      "progressStatus": "COMPLETED",
      "itemImgUrl": "https://example.com/images/fertilizer.jpg"
    },
    {
      "roleProgressId": 2,
      "participantId": 2,
      "participantName": "이서연",
      "roleCardId": 2,
      "roleName": "물주기 담당",
      "progressStatus": "INPROGRESS",
      "itemImgUrl": null
    }
  ],
  "completedRoleCount": 1,
  "totalRoleCount": 2,
  "nextLocation": null
}
```

미션이 완료되면 `missionProgressStatus`는 `COMPLETED`로 반환하고 `nextLocation`을 함께 반환한다.

```json
{
  "missionProgressId": 10,
  "missionId": 12,
  "missionTitle": "함께 키우는 귤나무",
  "missionProgressStatus": "COMPLETED",
  "currentStep": 3,
  "participants": [
    {
      "participantId": 1,
      "name": "나민",
      "participantType": "USER",
      "isHost": true,
      "participantStatus": "ACCEPTED"
    },
    {
      "participantId": 2,
      "name": "이서연",
      "participantType": "GUEST",
      "isHost": false,
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": [],
  "roleProgresses": [],
  "completedRoleCount": 2,
  "totalRoleCount": 2,
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

`missionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```
