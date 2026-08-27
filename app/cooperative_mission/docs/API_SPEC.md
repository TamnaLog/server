## 협동미션 시작하기/이어하기
- http 메서드: post
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionId}/progress

### API 설명

방장이 협동 미션을 처음 시작하거나 자신이 방장으로 참여 중인 협동 미션을 이어서 할 때 호출한다.

Path로 전달받은 `cooperativeMissionId`를 사용하여 협동 미션을 조회한다.

로그인한 사용자가 `HOST`로 참여하고 있는 해당 협동 미션의 `IN_PROGRESS` 진행도가 없으면 `currentStep`을 `1`, `missionProgressStatus`를 `IN_PROGRESS`로 초기화하여 새로운 진행도를 생성한다. 진행도를 생성할 때 로그인한 사용자를 `HOST`이자 `ACCEPTED` 상태의 참여자로 함께 생성하고 팀 토큰을 반환한다.

진행 중인 기록이 있으면 새로운 진행도를 생성하지 않고 기존 진행도의 팀 토큰, 참여자 목록, 공통 역할 카드 목록과 역할 진행도 목록을 반환한다.

백엔드는 완성된 초대 URL을 조합하지 않고 `teamToken`만 반환한다. 프론트가 현재 클라이언트 주소와 `teamToken`으로 초대 URL을 만든다.

완료된 진행도만 존재하면 완료된 진행도를 이어서 사용하지 않고 새로운 진행도를 생성한다. 다른 협동 미션 방에 `MEMBER`로 참여 중인 기록은 이 API의 이어하기 대상으로 보지 않는다.

시작하기와 이어하기 모두 동일한 응답 구조를 사용한다. 프론트는 `currentStep`을 기준으로 화면을 구성한다. 아직 존재하지 않는 목록 데이터는 빈 배열로 반환하며 보상 정보는 반환하지 않는다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `cooperativeMissionId` | number | 진행도를 생성하거나 조회할 협동 미션 id |

요청 예시

```
POST /api/v1/cooperative-missions/1/progress
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
| --- | --- | --- |
| `missionProgressId` | number | 협동 미션 진행도 id |
| `missionProgressStatus` | string | 협동 미션 진행 상태. `IN_PROGRESS | COMPLETED` |
| `currentStep` | number | 현재 협동 미션 단계. `1 | 2 | 3 | 4`이며 신규 진행도는 `1` |
| `teamToken` | string | 팀 단위 초대 토큰. 프론트는 이 값으로 초대 URL을 조합한다 |
| `participants` | object[] | 협동 미션 참여자 및 참여 요청 목록. 신규 진행도에는 방장이 포함됨 |
| `participants[].participantId` | number | 협동 미션 참여자 id |
| `participants[].name` | string | 참여 사용자의 닉네임 |
| `participants[].participantRole` | string | 참여자 역할. `HOST | MEMBER` |
| `participants[].participantStatus` | string | 참여 상태. `PENDING | ACCEPTED` |
| `roleCards` | object[] | 모든 협동 미션에서 공통으로 사용하는 역할 카드 6종 |
| `roleCards[].roleCardId` | number | 역할 카드 id |
| `roleCards[].roleName` | string | 역할 이름 |
| `roleCards[].roleDescription` | string | 역할 설명 및 수행 안내 |
| `roleCards[].locationToFind` | string[] | 역할 수행을 위해 찾아야 하는 장소 또는 대상의 예시 목록 |
| `roleProgresses` | object[] | 역할 배정 및 진행도 목록. 아직 역할을 배정하지 않았다면 빈 배열 |
| `roleProgresses[].roleProgressId` | number | 역할 진행도 id |
| `roleProgresses[].participantId` | number | 역할을 배정받은 참여자 id |
| `roleProgresses[].participantName` | string | 역할을 배정받은 참여자의 닉네임 |
| `roleProgresses[].roleCardId` | number | 배정된 역할 카드 id |
| `roleProgresses[].roleName` | string | 배정된 역할 이름 |
| `roleProgresses[].progressStatus` | string | 역할 진행 상태. `IN_PROGRESS | COMPLETED` |
| `roleProgresses[].itemImgUrl` | string | null | 역할 인증 이미지 URL. 아직 인증 전이면 `null` |

#### 시작하기 응답 예시

Status Code : 201

```json
{
  "missionProgressId": 10,
  "missionProgressStatus": "IN_PROGRESS",
  "currentStep": 1,
  "teamToken": "mock-team-token-10",
  "participants": [
    {
      "participantId": 21,
      "name": "몽글몽글파도",
      "participantRole": "HOST",
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": [
    {
      "roleCardId": 1,
      "roleName": "땅지기",
      "roleDescription": "귤나무가 뿌리를 내릴 건강한 땅을 찾고 비료를 주는 역할입니다. 제주의 화산토는 귤나무가 자라기에 최적의 환경을 제공합니다. 흙의 기운이 느껴지는 장소를 찾아 땅의 상태를 기록하세요. 좋은 땅이 있어야 귤나무가 뿌리를 깊이 내릴 수 있습니다.",
      "locationToFind": ["화산토", "흙길", "밭", "퇴비 주변"]
    },
    {
      "roleCardId": 2,
      "roleName": "물지기",
      "roleDescription": "귤나무에 생명을 불어넣는 물을 찾는 역할입니다. 제주는 화산암 지형 특성상 빗물이 지하로 스며들어 용천수로 솟아오릅니다. 물의 기운이 느껴지는 장소를 찾아 기록하세요. 귤나무는 적절한 수분 없이는 자랄 수 없습니다.",
      "locationToFind": ["용천수", "물길", "연못", "젖은 돌 주변"]
    },
    {
      "roleCardId": 3,
      "roleName": "빛지기",
      "roleDescription": "귤이 달콤하게 익으려면 충분한 햇빛이 필요합니다. 제주의 햇살이 잘 드는 양지바른 장소를 찾아 기록하세요. 빛이 충분해야 귤나무가 광합성을 하고 열매를 맺을 수 있습니다.",
      "locationToFind": ["양지바른 길", "햇살 드는 공터", "남향 돌담", "빛이 비치는 나무 아래"]
    },
    {
      "roleCardId": 4,
      "roleName": "바람지기",
      "roleDescription": "제주는 바람의 섬입니다. 하지만 강한 바람은 어린 귤나무에게 해가 될 수 있습니다. 바람을 막아줄 수 있는 돌담, 낮은 언덕, 건물 사이 골목 등 아늑한 장소를 찾아 기록하세요. 제주 돌담이 귤밭을 감싸는 데는 이유가 있습니다.",
      "locationToFind": ["돌담", "낮은 언덕 뒤", "건물 사이 골목", "방풍림"]
    },
    {
      "roleCardId": 5,
      "roleName": "이웃지기",
      "roleDescription": "귤나무 혼자서는 자랄 수 없습니다. 주변 생태계와 어우러져야 건강하게 자랍니다. 귤나무 주변에 함께 살아갈 수 있는 자연이 있는 장소를 찾아 기록하세요. 제주의 꽃, 풀, 나무와 곤충의 흔적이 귤나무의 이웃이 됩니다.",
      "locationToFind": ["꽃밭", "풀숲", "주변 나무", "곤충의 흔적"]
    },
    {
      "roleCardId": 6,
      "roleName": "수확지기",
      "roleDescription": "귤나무의 열매를 거두는 마지막 역할입니다. 제주 사람들의 손길이 느껴지는 장소, 오래된 감귤 농장 흔적, 수확의 기억이 담긴 공간을 찾아 기록하세요. 귤나무는 사람의 손길이 닿아야 비로소 완성됩니다.",
      "locationToFind": ["감귤 농장", "귤 창고", "수확 도구", "오래된 과수원"]
    }
  ],
  "roleProgresses": []
}
```

#### 이어하기 응답 예시

Status Code : 200

```json
{
  "missionProgressId": 10,
  "missionProgressStatus": "IN_PROGRESS",
  "currentStep": 3,
  "teamToken": "mock-team-token-10",
  "participants": [
    {
      "participantId": 21,
      "name": "몽글몽글파도",
      "participantRole": "HOST",
      "participantStatus": "ACCEPTED"
    },
    {
      "participantId": 22,
      "name": "한라봉주스",
      "participantRole": "MEMBER",
      "participantStatus": "ACCEPTED"
    },
    {
      "participantId": 23,
      "name": "오름러버",
      "participantRole": "MEMBER",
      "participantStatus": "ACCEPTED"
    }
  ],
  "roleCards": [
    {
      "roleCardId": 1,
      "roleName": "땅지기",
      "roleDescription": "귤나무가 뿌리를 내릴 건강한 땅을 찾고 비료를 주는 역할입니다. 제주의 화산토는 귤나무가 자라기에 최적의 환경을 제공합니다. 흙의 기운이 느껴지는 장소를 찾아 땅의 상태를 기록하세요. 좋은 땅이 있어야 귤나무가 뿌리를 깊이 내릴 수 있습니다.",
      "locationToFind": ["화산토", "흙길", "밭", "퇴비 주변"]
    },
    {
      "roleCardId": 2,
      "roleName": "물지기",
      "roleDescription": "귤나무에 생명을 불어넣는 물을 찾는 역할입니다. 제주는 화산암 지형 특성상 빗물이 지하로 스며들어 용천수로 솟아오릅니다. 물의 기운이 느껴지는 장소를 찾아 기록하세요. 귤나무는 적절한 수분 없이는 자랄 수 없습니다.",
      "locationToFind": ["용천수", "물길", "연못", "젖은 돌 주변"]
    },
    {
      "roleCardId": 3,
      "roleName": "빛지기",
      "roleDescription": "귤이 달콤하게 익으려면 충분한 햇빛이 필요합니다. 제주의 햇살이 잘 드는 양지바른 장소를 찾아 기록하세요. 빛이 충분해야 귤나무가 광합성을 하고 열매를 맺을 수 있습니다.",
      "locationToFind": ["양지바른 길", "햇살 드는 공터", "남향 돌담", "빛이 비치는 나무 아래"]
    },
    {
      "roleCardId": 4,
      "roleName": "바람지기",
      "roleDescription": "제주는 바람의 섬입니다. 하지만 강한 바람은 어린 귤나무에게 해가 될 수 있습니다. 바람을 막아줄 수 있는 돌담, 낮은 언덕, 건물 사이 골목 등 아늑한 장소를 찾아 기록하세요. 제주 돌담이 귤밭을 감싸는 데는 이유가 있습니다.",
      "locationToFind": ["돌담", "낮은 언덕 뒤", "건물 사이 골목", "방풍림"]
    },
    {
      "roleCardId": 5,
      "roleName": "이웃지기",
      "roleDescription": "귤나무 혼자서는 자랄 수 없습니다. 주변 생태계와 어우러져야 건강하게 자랍니다. 귤나무 주변에 함께 살아갈 수 있는 자연이 있는 장소를 찾아 기록하세요. 제주의 꽃, 풀, 나무와 곤충의 흔적이 귤나무의 이웃이 됩니다.",
      "locationToFind": ["꽃밭", "풀숲", "주변 나무", "곤충의 흔적"]
    },
    {
      "roleCardId": 6,
      "roleName": "수확지기",
      "roleDescription": "귤나무의 열매를 거두는 마지막 역할입니다. 제주 사람들의 손길이 느껴지는 장소, 오래된 감귤 농장 흔적, 수확의 기억이 담긴 공간을 찾아 기록하세요. 귤나무는 사람의 손길이 닿아야 비로소 완성됩니다.",
      "locationToFind": ["감귤 농장", "귤 창고", "수확 도구", "오래된 과수원"]
    }
  ],
  "roleProgresses": [
    {
      "roleProgressId": 31,
      "participantId": 21,
      "participantName": "몽글몽글파도",
      "roleCardId": 1,
      "roleName": "땅지기",
      "progressStatus": "COMPLETED",
      "itemImgUrl": "https://jamkkanjejustorage.blob.core.windows.net/ar-character-picture/cooperative-role/31.jpg"
    },
    {
      "roleProgressId": 32,
      "participantId": 22,
      "participantName": "한라봉주스",
      "roleCardId": 2,
      "roleName": "물지기",
      "progressStatus": "IN_PROGRESS",
      "itemImgUrl": null
    },
    {
      "roleProgressId": 33,
      "participantId": 23,
      "participantName": "오름러버",
      "roleCardId": 3,
      "roleName": "빛지기",
      "progressStatus": "IN_PROGRESS",
      "itemImgUrl": null
    }
  ]
}
```

---

### 오류 응답 데이터

Status Code : 404

`cooperativeMissionId`에 해당하는 협동 미션이 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_NOT_FOUND"
}
```



## url로 참여 요청
- http 메서드: post
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/join-requests

### API 설명

초대 URL을 연 팀원이 협동 미션 방에 참여를 요청할 때 호출한다.

프론트는 초대 URL에서 팀 토큰을 추출하여 요청 Body의 `teamToken`으로 전달한다.

백엔드는 팀 토큰으로 진행 중인 `COOPERATIVE_MISSION_PROGRESS`를 조회하고, 현재 로그인한 사용자를 `MEMBER`이자 `PENDING` 상태의 참여자로 저장한다.

새로운 참여 요청을 생성하면 `201 Created`를 반환한다. 동일한 사용자의 `PENDING` 또는 `ACCEPTED` 참여자 데이터가 이미 존재하면 중복 생성하지 않고 기존 참여자 정보를 `200 OK`로 반환한다.

프론트는 응답의 `missionProgressId`를 사용하여 자신의 참여 상태 조회 API를 폴링한다. `PENDING`이면 수락 대기 화면을 유지하고, `ACCEPTED`이면 협동 미션 방으로 이동한다.

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
| `teamToken` | string | 필수 | 프론트가 초대 URL에서 추출한 팀 단위 초대 토큰 |

```json
{
  "teamToken": "mock-team-token-10"
}
```

---

### 정상 응답 데이터

Status Code : 201

새로운 참여 요청을 생성한 경우

Status Code : 200

현재 사용자의 참여 요청 또는 수락된 참여자 데이터가 이미 존재하는 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionProgressId` | number | 참여를 요청한 협동 미션 진행도 id. 이후 참여 상태 폴링에 사용 |
| `participantId` | number | 현재 사용자의 협동 미션 참여자 id |
| `participantStatus` | string | 현재 참여 상태. `PENDING | ACCEPTED` |

#### 참여 요청 생성 응답 예시

Status Code : 201

```json
{
  "missionProgressId": 10,
  "participantId": 23,
  "participantStatus": "PENDING"
}
```

#### 기존 참여 정보 반환 예시

Status Code : 200

```json
{
  "missionProgressId": 10,
  "participantId": 23,
  "participantStatus": "PENDING"
}
```

이미 수락된 사용자가 같은 초대 URL로 다시 요청하면 `participantStatus`는 `ACCEPTED`로 반환한다.

---

### 오류 응답 데이터

Status Code : 404

전달받은 `teamToken`에 해당하는 진행 중인 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "INVALID_INVITE_TOKEN"
}
```

Status Code : 409

협동 미션 방의 수락된 참여자가 최대 인원에 도달한 경우

```json
{
  "code": "COOPERATIVE_MISSION_FULL"
}
```

Status Code : 409

협동 미션이 참여 요청을 받을 수 있는 단계를 지난 경우

```json
{
  "code": "COOPERATIVE_MISSION_JOIN_CLOSED"
}
```


## 참여 요청 수락
- http 메서드: patch
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/{participantId}/accept

### API 설명

방장이 협동 미션 참여 요청을 수락할 때 호출한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별하고, Path의 `cooperativeMissionProgressId`에 해당하는 진행 중인 협동 미션에서 현재 사용자가 `HOST`이자 `ACCEPTED` 참여자인지 확인한다.

Path의 `participantId`에 해당하는 같은 협동 미션의 `PENDING` 팀원을 조회한 뒤 다음과 같이 변경한다.

- `participant_status`: `PENDING → ACCEPTED`
- `joined_at`: 수락 처리 시각

수락이 완료되면 응답 Body 없이 `204 No Content`를 반환한다. 이미 `ACCEPTED` 상태인 동일 참여자에 대한 재요청도 추가 변경 없이 `204 No Content`를 반환한다.

수락된 팀원은 자신이 폴링 중인 협동 미션 상태 조회 API에서 `participantStatus: ACCEPTED`를 확인한 뒤 협동 미션 방으로 이동한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cooperativeMissionProgressId` | number | O | 참여 요청이 속한 협동 미션 진행도 id. `COOPERATIVE_MISSION_PROGRESS.id` |
| `participantId` | number | O | 수락할 참여 요청 id. `COOPERATIVE_MISSION_PARTICIPANT.id` |

요청 예시

```
PATCH /api/v1/cooperative-missions/10/participants/23/accept
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 204

참여 요청을 정상적으로 수락했거나 이미 수락된 동일 참여자에 대한 요청인 경우

응답 Body 없음

---

### 오류 응답 데이터

Status Code : 403

현재 사용자가 해당 협동 미션의 방장이 아닌 경우

```json
{
  "code": "COOPERATIVE_MISSION_HOST_ONLY"
}
```

Status Code : 404

`cooperativeMissionProgressId`에 해당하는 진행 중인 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

`participantId`에 해당하는 참여자가 존재하지 않거나 해당 협동 미션 진행도에 속하지 않는 경우, 참가자가 방장일 경우

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```

Status Code : 409

협동 미션이 참여 요청을 수락할 수 있는 초대 단계를 지난 경우

```json
{
  "code": "COOPERATIVE_MISSION_JOIN_CLOSED"
}
```


## 참여 요청 거절
- http 메서드: delete
- domain: cooperative-mission
- endpoint: /api/v1/cooperative-missions/{cooperativeMissionProgressId}/participants/{participantId}

### API 설명

방장이 협동 미션 참여 요청을 거절할 때 호출한다.

백엔드는 Authorization Bearer 토큰으로 현재 사용자를 식별하고, Path의 `cooperativeMissionProgressId`에 해당하는 진행 중인 협동 미션에서 현재 사용자가 `HOST`이자 `ACCEPTED` 참여자인지 확인한다.

Path의 `participantId`에 해당하는 같은 협동 미션의 `PENDING` 팀원을 조회한 뒤 `COOPERATIVE_MISSION_PARTICIPANT` row를 소프트 삭제한다. (row를 지우지 않고 `deleted_at`을 남기며, 이후 모든 조회에서 제외된다)

거절 상태는 별도로 저장하지 않는다. row가 조회에서 빠지므로 참여 가능 인원이 확보되며, 거절된 사용자는 동일한 초대 URL을 통해 다시 참여 요청할 수 있다.

거절된 팀원은 자신이 폴링 중인 협동 미션 상태 조회 API의 `participants`에서 자신의 `participantId`가 제외된 것을 확인한 뒤 참여 요청이 거절된 것으로 처리한다.

거절이 완료되면 응답 Body 없이 `204 No Content`를 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cooperativeMissionProgressId` | number | O | 참여 요청이 속한 협동 미션 진행도 id. `COOPERATIVE_MISSION_PROGRESS.id` |
| `participantId` | number | O | 거절할 참여 요청 id. `COOPERATIVE_MISSION_PARTICIPANT.id` |

요청 예시

```
DELETE /api/v1/cooperative-missions/10/participants/23
```

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 204

참여 요청을 정상적으로 거절하고 해당 참가자 row를 삭제한 경우

응답 Body 없음

---

### 오류 응답 데이터

Status Code : 403

현재 사용자가 해당 협동 미션의 방장이 아닌 경우

```json
{
  "code": "COOPERATIVE_MISSION_HOST_ONLY"
}
```

Status Code : 404

`cooperativeMissionProgressId`에 해당하는 진행 중인 협동 미션 진행도가 존재하지 않는 경우

```json
{
  "code": "COOPERATIVE_MISSION_PROGRESS_NOT_FOUND"
}
```

Status Code : 404

`participantId`에 해당하는 참여자가 존재하지 않거나 해당 협동 미션 진행도에 속하지 않거나 이미 삭제된 경우, 참가자가 방장일 경우

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_NOT_FOUND"
}
```

Status Code : 409

협동 미션이 참여 요청을 거절할 수 있는 초대 단계를 지난 경우

```json
{
  "code": "COOPERATIVE_MISSION_JOIN_CLOSED"
}
```

Status Code : 409

`participantId`에 해당하는 참여자가 이미 `ACCEPTED` 상태인 경우

```json
{
  "code": "COOPERATIVE_MISSION_PARTICIPANT_ALREADY_ACCEPTED"
}
```