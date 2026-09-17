## 협동 미션 상태 조회
- http 메서드: get
- domian: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress

### API 설명

방장과 팀원이 협동 미션 방의 최신 상태를 조회할 때 호출한다.

프론트는 초대 단계인 `currentStep: 1`부터 협동 미션이 완료될 때까지 이 API를 polling하여 현재 단계, 참여자 상태, 역할 카드, 역할 배정 및 인증 상태를 갱신한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별하고, 해당 진행도의 참가자 row를 조회하여 `currentParticipant`를 구성한다. 프론트에서 현재 사용자의 `participantId`, 역할 또는 참여 상태를 전달받지 않는다.

`currentStep`은 `1 | 2 | 3 | 4`를 사용한다. `1`은 초대 단계, `2`는 역할 카드 배정 단계, `3`은 미션 수행 단계, `4`는 미션 완료 단계이다. 미션이 완료되는 순간 `missionProgressStatus`를 `COMPLETED`로 변경하고 `currentStep`도 `4`로 변경한다.

`participants`에는 방장과 `PENDING | ACCEPTED` 팀원을 반환한다. 방장은 `participantRole: HOST`, 팀원은 `participantRole: MEMBER`로 반환한다.

`roleCards`와 `roleProgresses`는 역할 배정 및 수행 화면에서 사용하는 `currentStep: 2 | 3`일 때만 반환한다. `currentStep: 1 | 4`이면 두 필드 모두 `null`로 반환한다. 2단계에서는 공통 역할 카드 6종 전체와 현재까지 저장된 역할 배정을 반환하며, 방장이 역할 카드 하나를 배정할 때마다 다음 polling 응답의 `roleProgresses`에 즉시 반영한다. 모든 역할 카드를 배정할 필요는 없으며 일부 역할 카드는 미배정으로 남길 수 있다. 하나의 역할 카드는 최대 한 명에게만 배정할 수 있고, 한 참가자는 서로 다른 여러 역할 카드를 배정받을 수 있다. 2단계에서 아직 저장된 역할 배정이 없으면 `roleProgresses`는 빈 배열을 반환한다.

`currentStep: 1 | 2 | 3`에서는 `completedLocation`, `reward`, `nextLocation`을 `null`로 반환한다. 저장된 역할 진행도가 모두 인증 완료되어 `currentStep: 4`, `missionProgressStatus: COMPLETED`가 되면 참가자, 역할 카드, 역할 진행도 및 역할 집계 필드는 `null`로 반환하고, 완료한 협동 미션의 장소와 보상 및 다음 추천 장소를 반환한다. `reward`의 AR 캐릭터, 포인트, 쿠폰은 각각 지급 결과에 따라 `null`일 수 있다.

Query의 사용자 좌표는 4단계에서 추천된 다음 장소까지의 직선거리를 계산하는 데 사용하며, 거리는 `nextLocation.distanceMeter`에 미터 단위로 반환한다. 1~3단계에서는 좌표를 사용하지 않지만 폴링 요청마다 동일하게 전달한다.

거절된 참여 요청은 참가자 row가 삭제되므로 정상 상태 응답을 반환하지 않는다. `PENDING` 상태로 polling하던 프론트가 `COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND`를 받으면 참여 요청이 거절된 것으로 처리한다.

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
| `cooperativeMissionProgressId` | number | O | 조회할 협동 미션 진행도 id. `COOPERATIVE_MISSION_PROGRESS.id` |

요청 예시

```
GET /api/v1/cooperative-missions/10/progress?latitude=33.4996&longitude=126.5312
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

현재 사용자가 참여 중인 협동 미션 상태가 정상적으로 조회된 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionProgressId` | number | 협동 미션 진행도 id |
| `missionId` | number | 협동 미션 id. `COOPERATIVE_MISSION.id` |
| `missionTitle` | string | 협동 미션 제목 |
| `missionProgressStatus` | string | 협동 미션 진행 상태. `IN_PROGRESS \| COMPLETED` |
| `currentStep` | number | 현재 단계. `1: 초대, 2: 역할 카드 배정, 3: 미션 수행, 4: 미션 완료` |
| `completedLocation` | object \| null | 완료한 협동 미션의 장소. 1~3단계에서는 `null`, 4단계에서만 객체로 반환 |
| `completedLocation.locationId` | number | 완료한 협동 미션이 진행된 `LOCATION.id` |
| `completedLocation.locationTitle` | string | 완료한 협동 미션이 진행된 장소명 |
| `currentParticipant` | object \| null | Bearer 토큰으로 식별한 현재 사용자의 참가자 정보. 4단계이면 `null` |
| `currentParticipant.participantId` | number | 현재 사용자의 참가자 id |
| `currentParticipant.participantRole` | string | 현재 사용자의 역할. `HOST \| MEMBER` |
| `currentParticipant.participantStatus` | string | 현재 사용자의 참여 상태. `PENDING \| ACCEPTED` |
| `participants` | object[] | 해당 진행도의 방장과 참여 요청 목록 |
| `participants[].participantId` | number | 참가자 id |
| `participants[].name` | string | 참가자 닉네임 |
| `participants[].participantRole` | string | 참가자 역할. `HOST \| MEMBER` |
| `participants[].participantStatus` | string | 참여 상태. `PENDING \| ACCEPTED` |
| `roleCards` | object[] | 협동 미션에서 사용하는 공통 역할 카드 전체 목록 |
| `roleCards[].roleCardId` | number | 역할 카드 id |
| `roleCards[].roleName` | string | 역할 이름 |
| `roleCards[].roleDescription` | string | 역할 설명 |
| `roleCards[].locationToFind` | string[] | 역할 수행을 위해 찾아야 하는 장소 또는 대상 |
| `roleProgresses` | object[] | 역할 카드가 배정될 때마다 생성되는 역할 진행도 목록. 저장된 배정이 없으면 빈 배열이며 같은 역할 카드 id가 여러 번 포함될 수 있음 |
| `roleProgresses[].roleProgressId` | number | 역할 진행도 id |
| `roleProgresses[].participantId` | number | 역할을 맡은 참가자 id |
| `roleProgresses[].participantName` | string | 역할을 맡은 참가자 닉네임 |
| `roleProgresses[].roleCardId` | number | 배정된 역할 카드 id |
| `roleProgresses[].roleName` | string | 배정된 역할 이름 |
| `roleProgresses[].progressStatus` | string | 역할 인증 진행 상태. `IN_PROGRESS \| COMPLETED` |
| `roleProgresses[].itemImgUrl` | string \| null | 역할 인증 이미지 URL. 저장된 이미지가 없으면 `null` |
| `completedRoleCount` | number \| null | 저장된 역할 진행도 중 인증을 완료한 수. 2~3단계에서만 반환 |
| `totalRoleCount` | number \| null | 실제로 생성된 역할 진행도 수. 2~3단계에서만 반환하며 배정하지 않은 역할 카드는 포함하지 않음 |
| `reward` | object \| null | 현재 사용자에게 지급된 완료 보상. 4단계에서만 객체로 반환 |
| `reward.arCharacter` | object \| null | 지급된 AR 캐릭터. 지급되지 않았으면 `null` |
| `reward.arCharacter.id` | number | AR 캐릭터 id |
| `reward.arCharacter.name` | string | AR 캐릭터 이름 |
| `reward.arCharacter.imageUrl` | string | AR 캐릭터 이미지 URL |
| `reward.point` | number \| null | 지급된 포인트. 지급되지 않았으면 `null` |
| `reward.coupon` | object \| null | 지급된 쿠폰. 지급되지 않았으면 `null` |
| `reward.coupon.couponLocation` | string | 쿠폰 사용처 |
| `reward.coupon.couponPrice` | number | 쿠폰 금액 |
| `nextLocation` | object \| null | 다음 추천 장소. 4단계에서만 객체로 반환 |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string \| null | 다음 장소 이미지 URL. 조회하지 못하면 `null` |
| `nextLocation.distanceMeter` | number | Query의 사용자 위치에서 다음 장소까지의 직선거리(m) |
| `nextLocation.mission` | object \| null | 다음 장소의 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `CULTURE \| COOPERATIVE \| TREASURE` |

1단계: 초대 진행 중인 경우

```json
{
  "missionProgressId": 10,
  "missionId": 12,
  "missionTitle": "함께 키우는 귤나무",
  "missionProgressStatus": "IN_PROGRESS",
  "currentStep": 1,
  "completedLocation": null,
  "currentParticipant": {
    "participantId": 1,
    "participantRole": "HOST",
    "participantStatus": "ACCEPTED"
  },
  "participants": [
    {
      "participantId": 1,
      "name": "나민",
      "participantRole": "HOST",
      "participantStatus": "ACCEPTED"
    },
    {
      "participantId": 2,
      "name": "이서연",
      "participantRole": "MEMBER",
      "participantStatus": "PENDING"
    },
    {
      "participantId": 3,
      "name": "김민우",
      "participantRole": "MEMBER",
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": null,
  "roleProgresses": null,
  "completedRoleCount": null,
  "totalRoleCount": null,
  "reward": null,
  "nextLocation": null
}
```

1단계에서 참여 요청을 보낸 팀원이 직접 조회하면 `currentParticipant.participantStatus`는 `PENDING`으로 반환한다. 방장이 수락하면 다음 polling 응답부터 `ACCEPTED`로 반환한다.

2단계: 역할 카드 배정 중인 경우

```json
{
  "missionProgressId": 10,
  "missionId": 12,
  "missionTitle": "함께 키우는 귤나무",
  "missionProgressStatus": "IN_PROGRESS",
  "currentStep": 2,
  "completedLocation": null,
  "currentParticipant": {
    "participantId": 1,
    "participantRole": "HOST",
    "participantStatus": "ACCEPTED"
  },
  "participants": [
    {
      "participantId": 1,
      "name": "나민",
      "participantRole": "HOST",
      "participantStatus": "ACCEPTED"
    },
    {
      "participantId": 2,
      "name": "이서연",
      "participantRole": "MEMBER",
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": [
    {
      "roleCardId": 1,
      "roleName": "땅지기",
      "roleDescription": "귤나무가 뿌리를 내릴 건강한 땅을 찾고 비료를 주는 역할입니다.",
      "locationToFind": ["화산토","흙길","밭","퇴비 주변"]
    },
    {
      "roleCardId": 2,
      "roleName": "물지기",
      "roleDescription": "귤나무에 생명을 불어넣는 물을 찾는 역할입니다.",
      "locationToFind": ["용천수","물길","연못","젖은 돌 주변"]
    },
    {
      "roleCardId": 3,
      "roleName": "빛지기",
      "roleDescription": "귤이 달콤하게 익을 수 있도록 햇빛이 잘 드는 장소를 찾는 역할입니다.",
      "locationToFind": ["양지바른 길","햇살 드는 공터","남향 돌담","빛이 비치는 나무 아래"]
    },
    {
      "roleCardId": 4,
      "roleName": "바람지기",
      "roleDescription": "어린 귤나무를 강한 바람으로부터 지켜줄 장소를 찾는 역할입니다.",
      "locationToFind": ["돌담","낮은 언덕 뒤","건물 사이 골목","방풍림"]
    },
    {
      "roleCardId": 5,
      "roleName": "이웃지기",
      "roleDescription": "귤나무와 함께 살아갈 수 있는 자연의 흔적을 찾는 역할입니다.",
      "locationToFind": ["꽃밭","풀숲","주변 나무","곤충의 흔적"]
    },
    {
      "roleCardId": 6,
      "roleName": "수확지기",
      "roleDescription": "제주 사람들의 손길과 감귤 수확의 흔적이 담긴 장소를 찾는 역할입니다.",
      "locationToFind": ["감귤 농장","귤 창고","수확 도구","오래된 과수원"]
    }
  ],
  "roleProgresses": [
    {
      "roleProgressId": 1,
      "participantId": 1,
      "participantName": "나민",
      "roleCardId": 1,
      "roleName": "땅지기",
      "progressStatus": "IN_PROGRESS",
      "itemImgUrl": null
    },
    {
      "roleProgressId": 2,
      "participantId": 2,
      "participantName": "이서연",
      "roleCardId": 2,
      "roleName": "물지기",
      "progressStatus": "IN_PROGRESS",
      "itemImgUrl": null
    }
  ],
  "completedRoleCount": 0,
  "totalRoleCount": 2,
  "reward": null,
  "nextLocation": null
}
```

하나의 역할 카드는 최대 한 명에게만 배정할 수 있고, 한 참가자는 서로 다른 여러 역할 카드를 맡을 수 있다. 배정하지 않은 역할 카드는 역할 진행도에 포함하지 않는다. 역할 배정 저장 API가 호출될 때마다 다음 polling 응답의 `roleProgresses`와 `totalRoleCount`에 반영한다.

3단계: 미션 수행 중인 경우

```json
{
  "missionProgressId": 10,
  "missionId": 12,
  "missionTitle": "함께 키우는 귤나무",
  "missionProgressStatus": "IN_PROGRESS",
  "currentStep": 3,
  "completedLocation": null,
  "currentParticipant": {
    "participantId": 2,
    "participantRole": "MEMBER",
    "participantStatus": "ACCEPTED"
  },
  "participants": [
    {
      "participantId": 1,
      "name": "나민",
      "participantRole": "HOST",
      "participantStatus": "ACCEPTED"
    },
    {
      "participantId": 2,
      "name": "이서연",
      "participantRole": "MEMBER",
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": [
    {
      "roleCardId": 1,
      "roleName": "땅지기",
      "roleDescription": "귤나무가 뿌리를 내릴 건강한 땅을 찾고 비료를 주는 역할입니다.",
      "locationToFind": ["화산토","흙길","밭","퇴비 주변"]
    },
    {
      "roleCardId": 2,
      "roleName": "물지기",
      "roleDescription": "귤나무에 생명을 불어넣는 물을 찾는 역할입니다.",
      "locationToFind": ["용천수","물길","연못","젖은 돌 주변"]
    },
    {
      "roleCardId": 3,
      "roleName": "빛지기",
      "roleDescription": "귤이 달콤하게 익을 수 있도록 햇빛이 잘 드는 장소를 찾는 역할입니다.",
      "locationToFind": ["양지바른 길","햇살 드는 공터","남향 돌담","빛이 비치는 나무 아래"]
    },
    {
      "roleCardId": 4,
      "roleName": "바람지기",
      "roleDescription": "어린 귤나무를 강한 바람으로부터 지켜줄 장소를 찾는 역할입니다.",
      "locationToFind": ["돌담","낮은 언덕 뒤","건물 사이 골목","방풍림"]
    },
    {
      "roleCardId": 5,
      "roleName": "이웃지기",
      "roleDescription": "귤나무와 함께 살아갈 수 있는 자연의 흔적을 찾는 역할입니다.",
      "locationToFind": ["꽃밭","풀숲","주변 나무","곤충의 흔적"]
    },
    {
      "roleCardId": 6,
      "roleName": "수확지기",
      "roleDescription": "제주 사람들의 손길과 감귤 수확의 흔적이 담긴 장소를 찾는 역할입니다.",
      "locationToFind": ["감귤 농장","귤 창고","수확 도구","오래된 과수원"]
    }
  ],
  "roleProgresses": [
    {
      "roleProgressId": 1,
      "participantId": 1,
      "participantName": "나민",
      "roleCardId": 1,
      "roleName": "땅지기",
      "progressStatus": "COMPLETED",
      "itemImgUrl": null
    },
    {
      "roleProgressId": 2,
      "participantId": 2,
      "participantName": "이서연",
      "roleCardId": 2,
      "roleName": "물지기",
      "progressStatus": "IN_PROGRESS",
      "itemImgUrl": null
    },
    {
      "roleProgressId": 3,
      "participantId": 1,
      "participantName": "나민",
      "roleCardId": 3,
      "roleName": "빛지기",
      "progressStatus": "IN_PROGRESS",
      "itemImgUrl": null
    }
  ],
  "completedRoleCount": 1,
  "totalRoleCount": 3,
  "reward": null,
  "nextLocation": null
}
```

4단계: 미션이 완료된 경우

```json
{
  "missionProgressId": 10,
  "missionId": 12,
  "missionTitle": "함께 키우는 귤나무",
  "missionProgressStatus": "COMPLETED",
  "currentStep": 4,
  "completedLocation": {
    "locationId": 68,
    "locationTitle": "제주레저힐링축제"
  },
  "currentParticipant": null,
  "participants": null,
  "roleCards": null,
  "roleProgresses": null,
  "completedRoleCount": null,
  "totalRoleCount": null,
  "reward": {
    "arCharacter": null,
    "point": 100,
    "coupon": null
  },
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
    "distanceMeter": 4200,
    "mission": {
      "id": 342,
      "missionType": "TREASURE"
    }
  }
}
```

4단계의 `reward.arCharacter`, `reward.point`, `reward.coupon`은 각각 `null`일 수 있다.

`completedLocation`은 방금 완료한 협동 미션의 장소이며 `nextLocation`과 다른 값이다. 프론트는 `completedLocation.locationId`를 장소 방명록 작성 요청의 `locationId`로 사용하고, `completedLocation.locationTitle`을 방명록 작성 화면에 표시한다.

다음 장소에 연결된 미션이 없으면 `nextLocation.mission`은 `null`로 반환한다.

---

### 오류 응답 데이터

Status Code : 404

`cooperativeMissionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

Bearer 토큰으로 식별한 현재 사용자가 해당 협동 미션 진행도의 참가자가 아닌 경우. 참여 요청 거절로 참가자 row가 삭제된 경우를 포함한다.

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```


## 협동 미션 진행도 저장
- http 메서드: patch
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionProgressId}/progress

### API 설명

방장이 협동 미션의 다음 단계로 이동할 때 호출한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별하고, Path의 `cooperativeMissionProgressId`에 해당하는 협동 미션 진행도에서 현재 사용자가 `HOST`이자 `ACCEPTED` 참가자인지 확인한다.

요청 Body의 `currentStep`에는 변경할 다음 단계를 전달한다. 단계는 `1 → 2 → 3 → 4` 순서로 한 단계씩만 변경할 수 있으며 동일 단계 요청, 역행 및 단계 건너뛰기는 허용하지 않는다.

이 API는 역할 배정 정보를 받거나 협동 미션 전체 상태를 반환하지 않는다. 역할 카드 배정은 별도의 역할 배정 저장 API에서 역할 카드 하나를 배정할 때마다 처리하고, 변경된 협동 미션 상태는 협동 미션 상태 조회 API의 polling 응답으로 확인한다.

`1 → 2`에서는 해당 진행도에 `PENDING` 상태인 참가자가 남아 있는지 확인한다. `PENDING` 참가자가 한 명이라도 존재하면 단계 변경을 허용하지 않으며, 방장이 모든 참여 요청을 수락하거나 거절한 뒤 다시 요청해야 한다.

`2 → 3`에서는 `ACCEPTED` 상태인 모든 참가자가 역할 카드를 최소 1개 이상 배정받았는지 검증한다. `PENDING` 참가자는 검증 대상에서 제외한다. 역할 카드 6종을 모두 배정할 필요는 없으며 일부 역할 카드는 미배정으로 남아도 된다. 한 참가자가 서로 다른 여러 역할 카드를 배정받는 것도 허용한다.

`3 → 4`에서는 인증하지 않은 역할 진행도가 남아 있어도 방장이 협동 미션을 종료할 수 있다. 이때 `current_step`을 `4`, `mission_status`를 `COMPLETED`로 변경하고 `completed_at`에 완료 시각을 저장한다. 보상과 다음 장소는 이 API에서 반환하지 않고 이후 협동 미션 상태 조회 API의 4단계 polling 응답에서 처리한다.

정상적으로 단계를 변경하면 응답 Body 없이 `204 No Content`를 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cooperativeMissionProgressId` | number | O | 단계를 변경할 협동 미션 진행도 id. `COOPERATIVE_MISSION_PROGRESS.id` |

요청 예시

```
PATCH /api/v1/cooperative-missions/10/progress
```

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `currentStep` | number | O | 변경할 다음 단계. `2 | 3 | 4` |

1단계에서 2단계로 이동하는 경우

```json
{
  "currentStep": 2
}
```

2단계에서 3단계로 이동하는 경우

```json
{
  "currentStep": 3
}
```

3단계에서 미션을 완료하는 경우

```json
{
  "currentStep": 4
}
```

---

### 정상 응답 데이터

Status Code : 204

협동 미션 단계를 정상적으로 변경한 경우

응답 Body 없음

---

### 오류 응답 데이터

Status Code : 403

현재 사용자가 해당 협동 미션 진행도의 방장이 아닌 경우

```json
{
  "code": "COOPERATIVE_MISSION_HOST_ONLY"
}
```

Status Code : 404

`cooperativeMissionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 409

이미 `currentStep: 4`, `missionProgressStatus: COMPLETED`인 협동 미션의 단계 변경을 요청한 경우

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```

Status Code : 409

동일 단계, 이전 단계, 두 단계 이상 이후 단계 또는 현재 단계에서 허용되지 않는 단계로 변경을 요청한 경우

```json
{
  "code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"
}
```

Status Code : 409

`1 → 2` 변경 시 아직 수락하거나 거절하지 않은 `PENDING` 참가자가 존재하는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PENDING_PARTICIPANT_EXISTS"
}
```

Status Code : 409

`2 → 3` 변경 시 역할 카드를 하나도 배정받지 않은 `ACCEPTED` 참가자가 존재하는 경우

```json
{
  "code": "COOPERATIVE_PARTICIPANT_ROLE_REQUIRED"
}
```


## 협동 미션 역할 배정 저장
- http 메서드: put
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionProgressId}/role-assignments/{roleCardId}

### API 설명

방장이 협동 미션 2단계에서 역할 카드 하나의 담당자를 배정하거나 변경할 때 호출한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별하고, Path의 `cooperativeMissionProgressId`에 해당하는 협동 미션 진행도에서 현재 사용자가 `HOST`이자 `ACCEPTED` 참가자인지 확인한다.

Path의 `roleCardId`를 배정 단위로 사용하고 Request Body의 `participantId`를 해당 역할 카드를 맡을 참가자로 사용한다.

해당 협동 미션 진행도에 `roleCardId`와 연결된 역할 진행도가 없으면 새로운 `COOPERATIVE_ROLE_PROGRESS`를 생성한다.

이미 같은 `roleCardId`의 역할 진행도가 존재하면 새로운 row를 생성하지 않고 기존 역할 진행도의 `participant_id`를 요청받은 참가자로 변경한다. 기존 `roleProgressId`와 `roleCardId`는 유지한다.

같은 역할 카드에는 한 명의 참가자만 배정할 수 있다. 한 참가자는 서로 다른 여러 역할 카드를 배정받을 수 있다.

같은 역할 카드와 같은 참가자로 요청을 반복하면 추가 변경 없이 정상 처리한다.

역할 배정 결과는 이 API에서 반환하지 않는다. 프론트는 협동 미션 상태 조회 API의 다음 polling 응답에서 갱신된 `roleProgresses`를 확인한다.

정상적으로 역할을 생성하거나 담당자를 변경하면 응답 Body 없이 `204 No Content`를 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cooperativeMissionProgressId` | number | O | 역할을 배정할 협동 미션 진행도 id. `COOPERATIVE_MISSION_PROGRESS.id` |
| `roleCardId` | number | O | 담당자를 배정하거나 변경할 역할 카드 id. `COOPERATIVE_ROLE_CARD.id` |

요청 예시

```
PUT /api/v1/cooperative-missions/10/role-assignments/1
```

---

### 요청 Body

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `participantId` | number | O | 해당 역할 카드를 배정할 `ACCEPTED` 참가자 id. `COOPERATIVE_MISSION_PARTICIPANT.id` |

역할 카드 1을 참가자 21에게 처음 배정하는 경우

```json
{
  "participantId": 21
}
```

같은 역할 카드 1의 담당자를 참가자 24로 변경하는 경우

```json
{
  "participantId": 24
}
```

두 요청 모두 같은 엔드포인트를 사용한다. 첫 요청에서 역할 진행도가 없으면 생성하고, 이후 요청에서는 기존 역할 진행도의 참가자만 변경한다.

---

### 정상 응답 데이터

Status Code : 204

역할 진행도를 새로 생성했거나 기존 역할 카드의 담당자를 정상적으로 변경했거나 동일한 배정을 다시 요청한 경우

응답 Body 없음

---

### 오류 응답 데이터

Status Code : 403

현재 사용자가 해당 협동 미션 진행도의 방장이 아닌 경우

```json
{
  "code": "COOPERATIVE_MISSION_HOST_ONLY"
}
```

Status Code : 404

`cooperativeMissionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

`participantId`에 해당하는 참가자가 존재하지 않거나, 해당 협동 미션 진행도에 속하지 않거나, `ACCEPTED` 상태가 아닌 경우

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```

Status Code : 404

`roleCardId`에 해당하는 역할 카드가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_ROLE_CARD_NOT_FOUND"
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

현재 협동 미션 단계가 역할 카드 배정 단계인 `2`가 아닌 경우

```json
{
  "code": "COOPERATIVE_MISSION_STEP_NOT_ALLOWED"
}
```


## 협동 미션 역할 진행도 저장
- http 메서드: post
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionProgressId}/role-progresses/{roleProgressId}/verification

### API 설명

참가자가 자신에게 배정된 역할 카드에 맞는 사진을 첨부하고 인증하기 버튼을 눌렀을 때 호출한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별한다. Path의 `cooperativeMissionProgressId`와 `roleProgressId`를 사용하여 해당 협동 미션에 속한 역할 진행도와 배정된 역할 카드를 조회한다.

현재 사용자는 해당 역할 진행도의 담당자이면서 `ACCEPTED` 상태인 참가자여야 한다. 프론트에서 `participantId`나 `roleCardId`를 전달받지 않는다.

프론트는 `multipart/form-data`의 `itemImage`로 인증할 사진 파일을 전송한다. 사진은 JPEG, PNG, WebP 형식만 허용하며 최대 크기는 10MB이다. HEIC/HEIF 형식은 직접 받지 않고 프론트에서 JPEG로 변환한 후 전송한다. 백엔드는 역할 카드의 역할 설명과 찾아야 할 장소 또는 대상을 기준으로 사진을 인증한다.

사진 인증에 실패하면 Blob Storage에 사진을 업로드하지 않고 역할 진행도도 변경하지 않은 채 `isVerified: false`만 반환한다.

사진 인증에 성공하면 원본 파일명을 사용하지 않고 실제 이미지 형식에 맞는 확장자로 정규화한다. `AZURE_STORAGE_CONTAINER`로 지정된 Azure Blob 컨테이너의 `cooperative_mission_role/{cooperativeMissionProgressId}/{roleProgressId}/{uuid}.{extension}` 경로에 사진을 업로드한다.

업로드가 완료되면 Blob URL을 `COOPERATIVE_ROLE_PROGRESS.item_img_url`에 저장하고, 해당 역할 진행도의 `progress_status`를 `COMPLETED`로 변경하며 `completed_at`에 인증 완료 시각을 저장한다. 모든 저장이 완료되면 `isVerified: true`를 반환한다.

사진 파일 자체를 MySQL BLOB 컬럼이나 App Service 또는 Docker 컨테이너의 로컬 파일 시스템에 저장하지 않는다. Azure Blob에는 이미지 파일을 저장하고 DB에는 업로드된 이미지 URL만 저장한다.

이 API는 마지막 역할 인증이 성공하더라도 협동 미션의 `current_step`이나 `mission_status`를 변경하지 않는다. 모든 역할 인증이 끝난 경우에도 방장이 협동 미션 진행도 저장 API를 호출하여 `3 → 4`로 변경해야 한다.

프론트는 이 API의 응답으로 사진 인증 성공 여부만 확인하고, 갱신된 역할별 상태와 `itemImgUrl`은 협동 미션 상태 조회 API의 다음 polling 응답으로 확인한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cooperativeMissionProgressId` | number | O | 역할 진행도가 속한 협동 미션 진행도 id. `COOPERATIVE_MISSION_PROGRESS.id` |
| `roleProgressId` | number | O | 사진을 인증할 역할 진행도 id. `COOPERATIVE_ROLE_PROGRESS.id` |

요청 예시

```
POST /api/v1/cooperative-missions/10/role-progresses/3/verification
```

---

### 요청 Body

Content-Type: `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `itemImage` | file | O | 역할 카드 조건에 맞는지 인증할 이미지 파일. JPEG, PNG, WebP만 허용하며 최대 10MB |

```
itemImage: material.jpg
```

---

### 정상 응답 데이터

Status Code : 200

사진 인증 결과가 정상적으로 반환된 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `isVerified` | boolean | 사진 인증 성공 여부 |

인증에 성공한 경우

```json
{
  "isVerified": true
}
```

인증에 실패한 경우

```json
{
  "isVerified": false
}
```

인증 실패는 API 오류가 아니므로 `200 OK`로 반환하고 역할 진행도는 변경하지 않는다.

---

### 오류 응답 데이터

Status Code : 400

`itemImage`가 누락되었거나 이미지 형식이 JPEG, PNG, WebP가 아니거나 파일 크기가 10MB를 초과한 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

Status Code : 403

현재 사용자가 해당 역할 진행도의 담당자가 아니거나 `ACCEPTED` 참가자가 아닌 경우

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_ACCESS_DENIED"
}
```

Status Code : 404

`cooperativeMissionProgressId`에 해당하는 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

`roleProgressId`에 해당하는 역할 진행도가 존재하지 않거나 해당 협동 미션 진행도에 속하지 않는 경우

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_NOT_FOUND"
}
```

Status Code : 409

현재 협동 미션 단계가 미션 수행 단계인 `3`이 아닌 경우

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

해당 역할 진행도가 이미 `COMPLETED` 상태인 경우

```json
{
  "code": "COOPERATIVE_ROLE_PROGRESS_ALREADY_COMPLETED"
}
```



## 협동미션 나가기
- http 메서드: delete
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/me

### API 설명

현재 사용자가 참여 중인 협동 미션에서 나갈 때 호출한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별하므로 참가자 id나 사용자 id를 요청으로 전달받지 않는다. Path의 `cooperativeMissionProgressId`에 해당하는 협동 미션 진행도와 현재 사용자의 삭제되지 않은 참가자 데이터를 조회한다.

일반 팀원이 나가면 해당 `COOPERATIVE_MISSION_PARTICIPANT`의 `deleted_at`을 현재 시각으로 저장하고, 그 참가자에게 연결된 모든 `COOPERATIVE_ROLE_PROGRESS`도 같은 방식으로 소프트 딜리트한다.

방장이 나가고 다른 `ACCEPTED` 팀원이 남아 있으면 방장과 방장의 역할 진행도를 소프트 딜리트한 후, 남은 `ACCEPTED` 팀원 중 `joined_at`이 가장 빠른 참가자의 `participantRole`을 `HOST`로 변경한다. `joined_at`이 같으면 참가자 id가 작은 참가자를 우선한다. `PENDING` 참가자는 방장 승계 대상이 아니다.

현재 사용자가 방에 남은 마지막 `ACCEPTED` 참가자라면 참가자와 역할 진행도를 소프트 딜리트하고, 협동 미션 진행도 자체도 `deleted_at`을 저장하여 소프트 딜리트한다. 이때 미션을 `COMPLETED`로 변경하거나 `completed_at`을 저장하지 않는다. 진행도가 삭제되면 그 진행도에 남아 있는 다른 참가자 및 역할 진행도도 함께 소프트 딜리트한다.

나가기에서는 AR 캐릭터, 포인트, 쿠폰을 지급하지 않는다. 응답의 세 보상 필드는 모두 `null`로 반환한다.

다음 추천 장소는 공통 다음 장소 추천 로직으로 조회한다. 사용자 좌표를 받지 않으므로 나간 협동 미션의 장소를 기준으로, 그 장소를 제외하고 가장 가까운 장소를 추천한다. 추천 가능한 장소가 없으면 `nextLocation`을 `null`로 반환하며, 추천 장소에 연결된 미션이 없으면 `nextLocation.mission`을 `null`로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cooperativeMissionProgressId` | number | O | 나갈 협동 미션 진행도 id. `COOPERATIVE_MISSION_PROGRESS.id` |

요청 예시

```
DELETE /api/v1/cooperative-missions/10/participants/me
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

현재 사용자가 협동 미션에서 정상적으로 나간 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionProgressId` | number | 나간 협동 미션 진행도 id |
| `reward` | object | 나가기 결과의 보상 정보. 실제 보상은 지급하지 않음 |
| `reward.arCharacter` | null | AR 캐릭터를 지급하지 않으므로 항상 `null` |
| `reward.point` | null | 포인트를 지급하지 않으므로 항상 `null` |
| `reward.coupon` | null | 쿠폰을 지급하지 않으므로 항상 `null` |
| `nextLocation` | object | null | 공통 추천 로직으로 선정한 다음 장소. 추천 가능한 장소가 없으면 `null` |
| `nextLocation.id` | number | 다음 장소 id |
| `nextLocation.locationTitle` | string | 다음 장소명 |
| `nextLocation.locationImageUrl` | string | null | 다음 장소 이미지 URL. 조회하지 못하면 `null` |
| `nextLocation.mission` | object | null | 다음 장소의 미션. 연결된 미션이 없으면 `null` |
| `nextLocation.mission.id` | number | 다음 미션 id |
| `nextLocation.mission.missionType` | string | 다음 미션 유형. `COOPERATIVE | TREASURE` |

```json
{
  "missionProgressId": 10,
  "reward": {
    "arCharacter": null,
    "point": null,
    "coupon": null
  },
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
    "mission": {
      "id": 3,
      "missionType": "TREASURE"
    }
  }
}
```

다음 장소에 연결된 미션이 없는 경우

```json
{
  "missionProgressId": 10,
  "reward": {
    "arCharacter": null,
    "point": null,
    "coupon": null
  },
  "nextLocation": {
    "id": 39,
    "locationTitle": "한담 해안 산책로",
    "locationImageUrl": "https://example.com/locations/handam.jpg",
    "mission": null
  }
}
```

---

### 오류 응답 데이터

Status Code : 404

`cooperativeMissionProgressId`에 해당하는 삭제되지 않은 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

Bearer 토큰으로 식별한 현재 사용자의 삭제되지 않은 참가자 데이터가 해당 협동 미션 진행도에 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```

Status Code : 409

이미 완료된 협동 미션에서 나가기를 요청한 경우

```json
{
  "code": "COOPERATIVE_MISSION_ALREADY_COMPLETED"
}
```
