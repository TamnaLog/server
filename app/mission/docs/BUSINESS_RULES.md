# 미션 홈 조회 비즈니스 룰

## 1. 미션 식별 기준

미션 홈 조회는 `missionType`과 `missionId`를 함께 사용한다.

`missionId`는 공통 `MISSION.id`가 아니라, `missionType`에 해당하는 유형별 세부 미션 테이블의 id이다.

| `missionType` | 조회할 테이블 | `missionId`가 가리키는 컬럼 |
| --- | --- | --- |
| `CULTURE` | `CULTURE_MISSION` | `CULTURE_MISSION.id` |
| `COOPERATIVE` | `COOPERATIVE_MISSION` | `COOPERATIVE_MISSION.id` |
| `TREASURE` | `TREASURE_MISSION` | `TREASURE_MISSION.id` |

세부 미션 테이블마다 id 값이 중복될 수 있으므로 `missionId`만으로는 조회 대상을 결정하지 않는다.

`MISSION.id`는 세부 미션이 공통 미션 정보를 참조하기 위한 내부 식별자로 사용하며, 이 API의 요청 경로와 응답의 `id`에는 노출하지 않는다.

## 2. 세부 미션 조회

요청받은 `missionType`에 따라 조회할 세부 미션 테이블을 먼저 결정한 후, 해당 테이블에서 `id = missionId`인 데이터를 조회한다.

다른 유형의 세부 미션 테이블까지 같은 id를 가진 데이터가 있는지 검색해서 대신 반환하지 않는다.

예를 들어 `CULTURE/5` 요청은 `CULTURE_MISSION.id = 5`만 조회한다. 같은 id의 협동 미션이나 보물찾기 미션이 존재하더라도 문화 미션으로 반환하지 않는다.

## 3. 공통 미션 정보 조회

세부 미션을 찾으면 세부 미션의 `mission_id`를 사용하여 연결된 `MISSION` 데이터를 조회한다.

응답에 필요한 다음 정보는 공통 `MISSION`에서 가져온다.

- `missionType`: `MISSION.mission_type`
- `missionTitle`: `MISSION.mission_title`
- `description`: `MISSION.description`
- `steps`: `MISSION.step_detail`

세부 미션의 `mission_id`로 연결된 `MISSION.mission_type`은 요청받은 `missionType`과 일치해야 한다.

`MISSION.step_detail`의 단계 목록은 `step` 오름차순으로 정렬하여 반환한다.

## 4. 진행도 조회 기준

남은 보상을 판단하기 위해 현재 사용자의 해당 미션 진행도 이력을 함께 조회한다.

진행도 조회 기준:

| `missionType` | 진행도 테이블 | 조회 기준 |
| --- | --- | --- |
| `CULTURE` | `CULTURE_MISSION_PROGRESS` | `culture_mission_id = missionId`, `user_id = currentUserId` |
| `TREASURE` | `TREASURE_MISSION_PROGRESS` | `treasure_mission_id = missionId`, `user_id = currentUserId` |
| `COOPERATIVE` | `COOPERATIVE_MISSION_PROGRESS` | `cooperative_mission_id = missionId`이고, 현재 사용자가 참여자로 연결된 진행도 |

같은 미션은 여러 번 진행할 수 있으므로 진행도 이력이 여러 개 존재할 수 있다.

남은 보상은 가장 최근 진행도 하나가 아니라, 해당 미션의 모든 진행도 이력을 기준으로 판단한다.

진행도 이력 중 특정 보상이 한 번이라도 지급된 적이 있으면 해당 보상은 이미 지급된 것으로 본다.

진행도 데이터가 하나도 없으면 아직 보상을 지급받은 적이 없는 것으로 본다.

## 5. 남은 보상 정보

`remainingReward`는 미션에 연결된 전체 보상 중 해당 미션에서 아직 한 번도 지급되지 않은 보상만 반환한다.

전체 보상 정보는 공통 `MISSION`이 아니라 조회된 유형별 세부 미션의 `reward_detail`에서 가져온다. 따라서 같은 유형의 미션이라도 세부 미션마다 서로 다른 보상을 가질 수 있다.

보상 지급 여부는 유형별 진행도 테이블의 아래 컬럼을 기준으로 판단한다.

| 보상 | 지급 여부 컬럼 |
| --- | --- |
| AR 캐릭터 | `ar_character_reward_granted` |
| 포인트 | `point_reward_granted` |
| 쿠폰 | `coupon_reward_granted` |

사용자가 해당 미션을 한 번도 진행한 적이 없어 진행도 데이터가 없으면, 세 보상은 모두 아직 지급되지 않은 것으로 본다.

진행도 이력이 있고 모든 진행도에서 특정 보상의 지급 여부가 `FALSE`이면 해당 보상 정보를 반환한다.

진행도 이력 중 하나라도 특정 보상의 지급 여부가 `TRUE`이면 해당 보상은 이미 지급된 것으로 보고 `null`로 반환한다.

예를 들어 같은 문화 미션을 여러 번 풀 수 있고, 첫 번째 시도에서 AR 캐릭터 보상을 받았고 두 번째 시도에서 포인트 보상을 받았다면, 세 번째로 미션 홈을 조회할 때 `remainingReward.arCharacter`와 `remainingReward.point`는 `null`로 반환한다. 쿠폰 보상이 아직 한 번도 지급되지 않았다면 `remainingReward.coupon`만 반환한다.

`reward_detail.ar_character_id`가 있고 모든 진행도 이력에서 `ar_character_reward_granted = FALSE`이면 `AR_CHARACTER`를 조회하여 캐릭터 id, 이름, 이미지 URL을 조합한다. 캐릭터 보상이 없거나 과거 진행도에서 한 번이라도 지급됐으면 `remainingReward.arCharacter`는 `null`로 반환한다.

포인트 보상이 있고 모든 진행도 이력에서 `point_reward_granted = FALSE`이면 `remainingReward.point`에 포인트 값을 반환한다. 포인트 보상이 없거나 과거 진행도에서 한 번이라도 지급됐으면 `remainingReward.point`는 `null`로 반환한다.

쿠폰 보상이 있고 모든 진행도 이력에서 `coupon_reward_granted = FALSE`이면 `remainingReward.coupon`에 쿠폰 정보를 반환한다. 쿠폰 보상이 없거나 과거 진행도에서 한 번이라도 지급됐으면 `remainingReward.coupon`은 `null`로 반환한다.

예를 들어 한 번도 진행한 적 없는 미션은 보상 3개가 모두 반환될 수 있다.

반대로 과거 진행도 이력에서 보상 3개를 모두 한 번 이상 지급받은 미션은 아래처럼 반환한다.

```json
{
  "remainingReward": {
    "arCharacter": null,
    "point": null,
    "coupon": null
  }
}
```

## 6. 응답 조합 기준

최종 응답은 다음 기준으로 조합한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `id` | 유형별 세부 미션의 `id` |
| `missionType` | 연결된 `MISSION.mission_type` |
| `missionTitle` | 연결된 `MISSION.mission_title` |
| `description` | 연결된 `MISSION.description` |
| `remainingReward` | 유형별 세부 미션의 `reward_detail`, 진행도 테이블의 보상 지급 여부, 연결된 `AR_CHARACTER` |
| `steps` | 연결된 `MISSION.step_detail` |

## 7. 오류 기준

### 400 `INVALID_REQUEST`

요청 형식이나 값 자체가 유효하지 않아 조회 대상을 결정할 수 없는 경우 반환한다.

- `missionType`이 `CULTURE`, `COOPERATIVE`, `TREASURE` 중 하나가 아닌 경우
- `missionId`가 정수가 아닌 경우
- `missionId`가 1보다 작은 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 404 `MISSION_NOT_FOUND`

요청 형식은 유효하지만 요청한 유형의 세부 미션이 존재하지 않는 경우 반환한다.

- `missionType`에 해당하는 세부 미션 테이블에 `missionId`가 없는 경우
- 다른 유형의 세부 미션에는 같은 `missionId`가 존재하지만, 요청한 유형에는 존재하지 않는 경우
- 세부 미션과 연결된 공통 `MISSION`의 유형이 요청한 `missionType`과 일치하지 않는 경우

```json
{
  "code": "MISSION_NOT_FOUND"
}
```

유효하지 않은 `missionType`은 존재 여부를 조회할 수 없는 잘못된 요청이므로 `404`가 아니라 `400`으로 처리한다.

예상하지 못한 DB 오류나 응답 조합 중 발생한 시스템 오류는 위 비즈니스 오류로 바꾸지 않고 공통 예외 처리기를 통해 `500 INTERNAL_SERVER_ERROR`로 처리한다.
