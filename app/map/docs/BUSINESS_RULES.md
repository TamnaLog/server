# 지도 홈 조회 비즈니스 룰

## 1. 요청

- HTTP 메서드: `GET`
- 엔드포인트: `/api/v1/map/contents`
- Request Path와 Body는 받지 않는다.
- 프론트는 현재 지도 화면에 보이는 네 꼭짓점 좌표, 현재 사용자 좌표와 클러스터링 여부를 Query로 전달한다.
- 현재 사용자는 Authorization Bearer 토큰의 `get_current_user_id()`로 식별한다.

| Query 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `leftTopLatitude` | number | O | 지도 화면 좌상단 위도 |
| `leftTopLongitude` | number | O | 지도 화면 좌상단 경도 |
| `rightTopLatitude` | number | O | 지도 화면 우상단 위도 |
| `rightTopLongitude` | number | O | 지도 화면 우상단 경도 |
| `leftBottomLatitude` | number | O | 지도 화면 좌하단 위도 |
| `leftBottomLongitude` | number | O | 지도 화면 좌하단 경도 |
| `rightBottomLatitude` | number | O | 지도 화면 우하단 위도 |
| `rightBottomLongitude` | number | O | 지도 화면 우하단 경도 |
| `userLatitude` | number | O | 현재 사용자 위치의 위도 |
| `userLongitude` | number | O | 현재 사용자 위치의 경도 |
| `isClustered` | boolean | O | `true`이면 좌표만, `false`이면 상세 정보를 반환 |

위도와 경도는 프론트에서 임의로 반올림하지 않고 지도 SDK에서 얻은 정밀도를 최대한 유지하여 전달한다.

## 2. 조회 영역

전달받은 좌표를 다음 순서로 연결하여 현재 지도 화면의 조회 영역을 구성한다.

```text
좌상단 → 우상단 → 우하단 → 좌하단 → 좌상단
```

장소와 길바닥 방명록의 좌표가 이 영역 내부 또는 경계선 위에 있는 경우에만 응답 대상에 포함한다.

| 대상 | 위도 | 경도 |
| --- | --- | --- |
| `LOCATION` | `my` | `mx` |
| `ROAD_GUESTBOOK` | `my` | `mx` |

지도 회전으로 네 꼭짓점이 위도·경도 축에 평행하지 않을 수 있으므로 네 꼭짓점이 만드는 영역을 기준으로 포함 여부를 판단한다. DB 조회를 최적화하기 위해 좌표의 최솟값과 최댓값으로 후보를 먼저 좁힐 수 있지만, 최종 결과는 실제 조회 영역 내부에 있는 데이터만 포함해야 한다.

조회 결과가 없더라도 오류로 처리하지 않고 `locations`와 `roadGuestbooks`를 빈 배열로 반환한다.

## 3. 장소 조회

조회 영역 안에 좌표가 존재하는 `LOCATION`을 조회한다. 미션이나 방명록 존재 여부로 장소를 걸러내지 않고, 조회 영역 안의 장소는 모두 반환한다. `isClustered = false`이면 각 장소의 다음 기본 정보를 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `id` | `LOCATION.id` |
| `locationTitle` | `LOCATION.location_title` |
| `latitude` | `LOCATION.my` |
| `longitude` | `LOCATION.mx` |
| `distanceMeter` | 현재 사용자 위치에서 장소까지의 직선거리(m) |
| `durationMinutes` | 현재 사용자 위치에서 장소까지의 예상 이동 시간(분) |

각 장소에 연결된 미션, 방명록 개수와 대표 이미지는 뒤의 규칙에 따라 추가한다.

거리와 예상 이동 시간은 `app/common/distance.py`의 공통 함수를 사용한다.

```python
distance_meter = calculate_distance_meter(
    userLatitude,
    userLongitude,
    location.my,
    location.mx,
)
duration_minutes = calculate_duration_minutes(distance_meter)
```

- `distanceMeter`에는 `calculate_distance_meter()`의 결과를 반환한다.
- `durationMinutes`에는 위 거리로 `calculate_duration_minutes()`를 호출한 결과를 반환한다.
- 지도 도메인에 거리 공식이나 이동 시간 계산식을 중복 구현하지 않는다.
- 장소의 미션 정보와 관계없이 거리와 시간은 미션 객체에 중복하지 않고 장소 레벨에 한 번만 반환한다.

## 4. 장소 미션 정보

장소별로 `TREASURE_MISSION.location_id`와 `COOPERATIVE_MISSION.location_id`를 조회한다.

다음 데이터 관계를 비즈니스 규칙으로 전제한다.

- 하나의 장소에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다.
- 보물찾기 미션과 협동 미션이 같은 장소에 동시에 존재하지 않는다고 전제한다.
- 문화 미션은 장소를 참조하지 않으므로 지도 장소 미션 정보에 포함하지 않는다.

응답은 배열이 아니라 유형별 nullable 단일 미션 객체를 사용한다.

| 응답 필드 | 값 |
| --- | --- |
| `treasureMission` | 연결된 보물찾기 미션 정보. 없으면 `null` |
| `cooperativeMission` | 연결된 협동 미션 정보. 없으면 `null` |

각 미션 객체는 다음 값을 반환한다.

| 하위 필드 | 데이터 출처 |
| --- | --- |
| `id` | 유형별 세부 미션의 id. `TREASURE_MISSION.id` 또는 `COOPERATIVE_MISSION.id` |
| `missionTitle` | 세부 미션의 `mission_id`로 연결된 `MISSION.mission_title` |
| `isCompleted` | 현재 사용자의 해당 세부 미션 완료 여부 |
| `hasWrittenGuestbook` | 완료한 미션을 참조하여 현재 사용자가 방명록을 작성했는지 여부. 미완료이면 `null` |

보물찾기 미션이 존재하면 `treasureMission`만 객체로 반환하고 `cooperativeMission`은 `null`로 반환한다. 협동 미션이 존재하면 반대로 반환한다. 장소에 미션이 없으면 두 필드를 생략하지 않고 모두 `null`로 반환한다.

### 사용자별 미션 완료 여부

보물찾기 미션은 다음 조건을 만족하는 진행도가 하나 이상 존재하면 `isCompleted = true`로 판단한다.

```text
TREASURE_MISSION_PROGRESS.treasure_mission_id = TREASURE_MISSION.id
AND TREASURE_MISSION_PROGRESS.user_id = current_user_id
AND TREASURE_MISSION_PROGRESS.mission_status = COMPLETED
```

협동 미션은 현재 사용자의 삭제되지 않은 참가자 데이터와 삭제되지 않은 완료 진행도가 연결되어 있으면 `isCompleted = true`로 판단한다.

```text
COOPERATIVE_MISSION_PROGRESS.cooperative_mission_id = COOPERATIVE_MISSION.id
AND COOPERATIVE_MISSION_PROGRESS.mission_status = COMPLETED
AND COOPERATIVE_MISSION_PROGRESS.deleted_at IS NULL
AND COOPERATIVE_MISSION_PARTICIPANT.cooperative_mission_progress_id
    = COOPERATIVE_MISSION_PROGRESS.id
AND COOPERATIVE_MISSION_PARTICIPANT.user_id = current_user_id
AND COOPERATIVE_MISSION_PARTICIPANT.participant_status = ACCEPTED
AND COOPERATIVE_MISSION_PARTICIPANT.deleted_at IS NULL
```

진행 이력이 없거나 `IN_PROGRESS` 진행도만 존재하면 `isCompleted = false`다. 여러 번 진행한 이력이 있더라도 완료 이력이 하나 이상 존재하면 `true`다.

### 미션 방명록 작성 여부

`hasWrittenGuestbook`은 현재 사용자가 해당 미션을 완료한 경우에만 조회한다.

- `isCompleted = false`이면 방명록을 조회하지 않고 `hasWrittenGuestbook = null`을 반환한다.
- `isCompleted = true`이면 아래 조건을 만족하는 삭제되지 않은 방명록이 하나 이상 존재할 때 `true`, 없으면 `false`를 반환한다.

```text
GUESTBOOK.user_id = current_user_id
AND GUESTBOOK.location_id = LOCATION.id
AND GUESTBOOK.mission_id = 유형별 세부 미션이 참조하는 MISSION.id
AND GUESTBOOK.deleted_at IS NULL
```

`GUESTBOOK.mission_id`는 유형별 세부 미션 id가 아니라 공통 `MISSION.id`를 참조한다. 따라서 `location_id`와 `mission_id`를 함께 사용한다. 한 장소에는 유형별 세부 미션이 최대 하나만 존재한다는 규칙에 따라 이 조합으로 해당 장소의 보물찾기 또는 협동 미션 방명록을 판단할 수 있다.

## 5. 장소 방명록 개수

각 장소를 참조하는 삭제되지 않은 `GUESTBOOK` 개수를 계산한다.

```text
GUESTBOOK.location_id = LOCATION.id
AND GUESTBOOK.deleted_at IS NULL
```

- 조회된 개수를 `guestbooksCount`로 반환한다.
- 방명록이 없으면 필드를 생략하지 않고 `0`을 반환한다.
- 소프트 딜리트된 방명록은 개수에 포함하지 않는다.

## 6. 장소 대표 이미지

장소의 `representativeImageUrl`은 장소 방명록 이미지가 아니라 TourAPI의 장소 대표 이미지다.

1. `LOCATION.content_id`로 TourAPI 장소 이미지 정보를 조회한다.
2. TourAPI 응답의 `firstimage` URL을 `representativeImageUrl`로 반환한다.
3. `firstimage`가 비어 있거나 TourAPI에서 이미지를 조회하지 못하면 `null`을 반환한다.

TourAPI 이미지 조회는 기존 KTO 서비스 모듈을 사용하며 지도 서비스에 HTTP 호출 코드를 중복 구현하지 않는다.

## 7. 길바닥 방명록 조회

조회 영역 안에 좌표가 존재하면서 소프트 딜리트되지 않은 `ROAD_GUESTBOOK`을 조회한다.

```text
ROAD_GUESTBOOK.deleted_at IS NULL
```

`isClustered = false`이면 다음 정보를 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `id` | `ROAD_GUESTBOOK.id` |
| `latitude` | `ROAD_GUESTBOOK.my` |
| `longitude` | `ROAD_GUESTBOOK.mx` |
| `locationAlias` | `ROAD_GUESTBOOK.location_alias` |
| `representativeGuestbookImageUrl` | `ROAD_GUESTBOOK.content_img_url`의 첫 번째 이미지 |

`content_img_url`은 Blob Storage URL을 담은 문자열 배열이다.

- 배열이 없거나 비어 있으면 `representativeGuestbookImageUrl`을 `null`로 반환한다.
- 이미지가 한 장 이상 있으면 배열의 첫 번째 URL을 그대로 반환한다.
- 이 API에서는 이미지를 새로 업로드하거나 Blob URL을 변경하지 않는다.

## 8. `isClustered = false` 응답

클러스터링되지 않은 지도에서는 마커 표시와 후속 모달 조회에 필요한 상세 정보를 반환한다.

```json
{
  "locations": [
    {
      "id": 101,
      "locationTitle": "현애원",
      "latitude": 33.4582,
      "longitude": 126.9331,
      "distanceMeter": 1250,
      "durationMinutes": 15,
      "treasureMission": {
        "id": 301,
        "missionTitle": "오구포구 보물찾기",
        "isCompleted": true,
        "hasWrittenGuestbook": false
      },
      "cooperativeMission": null,
      "guestbooksCount": 2,
      "representativeImageUrl": "https://example.com/locations/101.jpg"
    }
  ],
  "roadGuestbooks": [
    {
      "id": 131,
      "latitude": 33.4582,
      "longitude": 126.9331,
      "locationAlias": "성산 바다 앞",
      "representativeGuestbookImageUrl": "https://example.com/guestbooks/131/1.jpg"
    }
  ]
}
```

프론트는 다음 기준으로 장소의 표시 카테고리를 구성할 수 있다.

- `treasureMission != null`: 보물찾기
- `cooperativeMission != null`: 협동 미션
- `guestbooksCount > 0`: 장소 방명록
- `roadGuestbooks`: 길바닥 방명록

한 장소가 여러 조건을 동시에 만족하면 프론트가 해당 장소를 여러 카테고리에 포함할 수 있다.

## 9. `isClustered = true` 응답

클러스터링 상태에서는 대량 데이터 전송을 줄이기 위해 장소와 길바닥 방명록의 식별자와 좌표만 반환한다. 장소에는 프론트가 보물찾기와 협동 미션을 구분할 수 있도록 연결된 세부 미션의 ID와 유형도 함께 반환한다.

```json
{
  "locations": [
    {
      "id": 101,
      "latitude": 33.4582,
      "longitude": 126.9331,
      "missionId": 301,
      "missionType": "TREASURE"
    },
    {
      "id": 102,
      "latitude": 33.4561,
      "longitude": 126.9295,
      "missionId": null,
      "missionType": null
    }
  ],
  "roadGuestbooks": [
    {
      "id": 131,
      "latitude": 33.4582,
      "longitude": 126.9331
    }
  ]
}
```

각 필드는 다음 기준으로 구성한다.

| 응답 필드 | 데이터 출처 및 규칙 |
| --- | --- |
| `locations[].id` | `LOCATION.id` |
| `locations[].latitude` | `LOCATION.my` |
| `locations[].longitude` | `LOCATION.mx` |
| `locations[].missionId` | 보물찾기이면 `TREASURE_MISSION.id`, 협동 미션이면 `COOPERATIVE_MISSION.id`, 연결된 미션이 없으면 `null` |
| `locations[].missionType` | 보물찾기이면 `TREASURE`, 협동 미션이면 `COOPERATIVE`, 연결된 미션이 없으면 `null` |
| `roadGuestbooks[].id` | `ROAD_GUESTBOOK.id` |
| `roadGuestbooks[].latitude` | `ROAD_GUESTBOOK.my` |
| `roadGuestbooks[].longitude` | `ROAD_GUESTBOOK.mx` |

하나의 `LOCATION`에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다. `missionId`와 `missionType`은 항상 한 쌍으로 반환하며, 미션이 없는 장소에서는 두 필드를 모두 `null`로 반환한다. `locations[].id`는 LOCATION ID이고 `locations[].missionId`는 유형별 세부 미션 ID이므로 서로 다른 값이다.

다음 정보는 조회하거나 응답에 포함하지 않는다.

- 장소명
- 사용자와 장소 사이의 거리 및 예상 이동 시간
- 공통 미션 정보와 제목, 완료 여부 및 미션 방명록 작성 여부
- 장소 방명록 개수
- TourAPI 대표 이미지
- 길바닥 방명록 위치 별칭
- 길바닥 방명록 대표 이미지

`isClustered = true`일 때는 각 LOCATION에 연결된 보물찾기 또는 협동 미션의 세부 ID와 유형만 일괄 조회한다. 공통 `MISSION` 정보, 사용자 진행도, 미션 방명록 작성 여부는 조회하지 않는다. 거리·시간 계산, 방명록 개수 집계와 TourAPI 이미지 조회도 생략한다. 백엔드는 데이터를 클러스터 단위로 합치거나 개수를 계산하지 않고 식별자와 원본 좌표 목록을 반환하며, 실제 클러스터 구성과 표시 개수 계산은 프론트가 담당한다.

## 10. 처리 순서

1. Query 필드의 누락 여부, 타입과 지도 꼭짓점 및 사용자 좌표 범위를 검증한다.
2. 네 꼭짓점 좌표로 지도 조회 영역을 구성한다.
3. 조회 영역 안의 `LOCATION`과 삭제되지 않은 `ROAD_GUESTBOOK`을 조회한다.
4. `isClustered = true`이면 장소별 보물찾기 또는 협동 미션의 세부 ID와 유형만 일괄 조회하고, 두 목록을 ID·좌표·미션 식별 정보 응답으로 변환하여 즉시 반환한다.
5. `isClustered = false`이면 각 장소까지의 `distanceMeter`와 `durationMinutes`를 공통 모듈로 계산한다.
6. 각 장소의 보물찾기 미션과 협동 미션을 조회하고 공통 `MISSION`에서 제목을 가져온다.
7. 현재 사용자의 유형별 미션 완료 여부를 일괄 조회한다.
8. 완료한 미션에 대해서만 현재 사용자의 미션 방명록 작성 여부를 일괄 조회한다.
9. 각 장소를 참조하는 삭제되지 않은 방명록 개수를 계산한다.
10. 각 장소의 TourAPI `firstimage`를 조회한다.
11. 각 길바닥 방명록의 첫 번째 이미지 URL을 선택한다.
12. 상세 응답을 조합하여 `200 OK`를 반환한다.

장소별 반복 조회로 N+1 문제가 발생하지 않도록 미션, 사용자 완료 이력, 미션 방명록 작성 여부와 방명록 개수는 가능한 한 일괄 조회한다. TourAPI 이미지 조회도 기존 서비스의 캐시 또는 일괄 처리 기능을 사용할 수 있으면 이를 우선한다.

## 11. 정상 응답

조회가 정상적으로 완료되면 콘텐츠 존재 여부와 관계없이 `200 OK`를 반환한다.

- 조회 결과가 있으면 `isClustered` 값에 맞는 데이터를 반환한다.
- 조회 결과가 없으면 다음과 같이 빈 배열을 반환한다.

```json
{
  "locations": [],
  "roadGuestbooks": []
}
```

## 12. 오류 처리

### 400 `INVALID_REQUEST`

다음 경우 공통 요청 오류를 반환한다.

- 필수 Query가 누락된 경우
- 위도 또는 경도가 숫자가 아닌 경우
- 위도가 `-90~90` 범위를 벗어난 경우
- 경도가 `-180~180` 범위를 벗어난 경우
- `userLatitude` 또는 `userLongitude`가 누락되거나 유효한 범위를 벗어난 경우
- `isClustered`가 boolean으로 해석할 수 없는 경우
- 네 꼭짓점이 유효한 조회 영역을 구성하지 못하는 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

### 500 `INTERNAL_SERVER_ERROR`

DB 조회 또는 응답 구성 중 예상하지 못한 오류가 발생하면 공통 서버 오류를 반환한다. TourAPI에서 특정 장소의 이미지를 조회하지 못하는 것은 `representativeImageUrl: null`로 처리하며 전체 지도 조회를 실패시키지 않는다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```

# 지도 모달 조회 비즈니스 룰

## 1. 요청

- HTTP 메서드: `GET`
- 엔드포인트: `/api/v1/map/modals`
- Request Path와 Body는 받지 않는다.
- `Authorization: Bearer {accessToken}` 헤더는 필수다.
- 현재 사용자는 공통 의존성 `get_current_user_id()`로 식별하며, 토큰에 해당하는 사용자가 실제로 존재하는지 검증한다.
- 응답 구성에 사용자 ID를 직접 사용하지 않더라도 인증된 사용자만 호출할 수 있다.
- 프론트는 조회 대상 유형과 ID, 현재 사용자의 GPS 좌표를 Query로 전달한다.
- 조회 대상은 장소와 길바닥 방명록만 지원하며 미션 자체는 조회 대상으로 받지 않는다.

| Query 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `targetType` | string | O | `LOCATION \| ROAD_GUESTBOOK` |
| `targetId` | integer | O | `LOCATION`이면 `LOCATION.id`, `ROAD_GUESTBOOK`이면 `ROAD_GUESTBOOK.id` |
| `userLatitude` | number | O | 현재 사용자 위치의 위도 |
| `userLongitude` | number | O | 현재 사용자 위치의 경도 |

위도와 경도는 프론트에서 임의로 반올림하지 않고 GPS 또는 지도 SDK에서 얻은 정밀도를 최대한 유지하여 전달한다.

## 2. 조회 대상 판별

`targetType`에 따라 다음 테이블에서 `targetId`와 일치하는 데이터를 조회한다.

| `targetType` | 조회 대상 |
| --- | --- |
| `LOCATION` | `LOCATION.id = targetId` |
| `ROAD_GUESTBOOK` | `ROAD_GUESTBOOK.id = targetId AND ROAD_GUESTBOOK.deleted_at IS NULL` |

- 조회 대상이 존재하지 않으면 `404 MAP_MODAL_TARGET_NOT_FOUND`를 반환한다.
- 소프트 딜리트 컬럼이 존재하는 조회 대상과 연관 데이터는 `deleted_at IS NULL`인 데이터만 사용한다.
- 장소는 존재하지만 해당 장소를 참조하는 방명록이 없는 경우에는 오류가 아니라 정상 조회로 처리한다.
- `targetType`과 다른 테이블에서 같은 ID가 존재하더라도 조회 결과로 사용하지 않는다.

## 3. 거리와 예상 이동 시간

현재 사용자 위치와 조회 대상 좌표를 사용하여 `distanceMeter`와 `durationMinutes`를 계산한다.

| `targetType` | 대상 위도 | 대상 경도 |
| --- | --- | --- |
| `LOCATION` | `LOCATION.my` | `LOCATION.mx` |
| `ROAD_GUESTBOOK` | `ROAD_GUESTBOOK.my` | `ROAD_GUESTBOOK.mx` |

거리와 예상 이동 시간은 `app/common/distance.py`의 공통 함수를 사용한다.

```python
distance_meter = calculate_distance_meter(
    userLatitude,
    userLongitude,
    target.my,
    target.mx,
)
duration_minutes = calculate_duration_minutes(distance_meter)
```

- `distanceMeter`는 `calculate_distance_meter()`가 반환한 미터 단위 정수값을 사용한다.
- `durationMinutes`는 `calculate_duration_minutes()`가 반환한 분 단위 정수값을 그대로 사용한다.
- 지도 모달 서비스에 거리 공식, 이동 속도 또는 반올림 규칙을 중복 구현하지 않는다.

## 4. 장소 모달 조회

`targetType = LOCATION`이면 다음 장소 기본 정보를 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `id` | `LOCATION.id` |
| `locationTitle` | `LOCATION.location_title` |
| `locationCategory` | `LOCATION.location_category` |
| `distanceMeter` | 공통 거리 모듈의 계산 결과 |
| `durationMinutes` | 공통 거리 모듈의 계산 결과 |

### 장소 방명록 개수

다음 조건을 만족하는 방명록 전체 개수를 `guestbooksCount`로 반환한다.

```text
GUESTBOOK.location_id = LOCATION.id
AND GUESTBOOK.deleted_at IS NULL
```

- 방명록이 없으면 `guestbooksCount = 0`을 반환한다.
- `guestbooksCount`는 응답에 포함되는 최신 방명록 목록의 길이가 아니라 조건을 만족하는 전체 방명록 개수다.

### 최신 방명록 3개

장소를 참조하는 삭제되지 않은 방명록을 다음 순서로 정렬하여 최대 3개를 `guestbooks`에 반환한다.

```text
GUESTBOOK.visited_at DESC,
GUESTBOOK.id DESC
```

- 최신 여부는 `created_at`이나 `saved_at`이 아니라 `visited_at`을 기준으로 판단한다.
- `visited_at`이 같은 경우에는 `id`가 큰 방명록을 더 최신 데이터로 판단한다.
- 방명록이 없으면 `guestbooks = []`를 반환한다.

각 방명록은 다음 값을 반환한다.

| 응답 필드 | 데이터 출처 및 규칙 |
| --- | --- |
| `id` | `GUESTBOOK.id` |
| `representativeImageUrl` | `GUESTBOOK.content_img_url` 배열의 첫 번째 URL |
| `userNickname` | `GUESTBOOK.user_id`로 연결된 `USER.nickname` |
| `missionTitle` | `GUESTBOOK.mission_id`로 연결된 `MISSION.mission_title` |
| `visitedAt` | `GUESTBOOK.visited_at`, `YYYY-MM-DD` 형식 |
| `contentWriting` | `GUESTBOOK.content_writing` |

- `content_img_url`이 `null`이거나 빈 배열이면 `representativeImageUrl = null`을 반환한다.
- 이미지가 한 장 이상이면 배열의 첫 번째 URL을 순서 변경 없이 반환한다.
- `mission_id`가 `null`이면 `missionTitle = null`을 반환한다.
- `content_writing`이 없으면 `contentWriting = null`을 반환한다.
- `GUESTBOOK.mission_id`는 유형별 세부 미션 ID가 아니라 공통 `MISSION.id`를 참조한다.

## 5. 길바닥 방명록 모달 조회

`targetType = ROAD_GUESTBOOK`이면 조회한 길바닥 방명록과 작성자 정보를 조합하여 다음 값을 반환한다.

| 응답 필드 | 데이터 출처 및 규칙 |
| --- | --- |
| `id` | `ROAD_GUESTBOOK.id` |
| `userNickname` | `ROAD_GUESTBOOK.user_id`로 연결된 `USER.nickname` |
| `locationAlias` | `ROAD_GUESTBOOK.location_alias` |
| `distanceMeter` | 공통 거리 모듈의 계산 결과 |
| `durationMinutes` | 공통 거리 모듈의 계산 결과 |
| `visitedAt` | `ROAD_GUESTBOOK.visited_at`, `YYYY-MM-DD` 형식 |
| `contentImageUrls` | `ROAD_GUESTBOOK.content_img_url` |
| `contentWriting` | `ROAD_GUESTBOOK.content_writing` |
| `contentAudioUrls` | `ROAD_GUESTBOOK.content_audio_url` |
| `contentWeather` | `ROAD_GUESTBOOK.content_weather` |
| `contentColorCode` | `ROAD_GUESTBOOK.content_color_code` |

- 사진, 글, 오디오, 날씨 또는 색상 코드가 저장되어 있지 않으면 해당 응답 필드를 생략하지 않고 `null`로 반환한다.
- `content_img_url`과 `content_audio_url`이 빈 배열로 저장되어 있더라도 API 응답에서는 `null`로 정규화한다.
- 저장된 콘텐츠가 있으면 값과 배열 순서를 변경하지 않고 그대로 반환한다.
- 작성일은 `created_at`이나 `saved_at`이 아니라 `visited_at`을 기준으로 반환한다.

## 6. 처리 순서

1. 필수 Query의 누락 여부, 타입, 허용된 `targetType`, `targetId` 범위와 사용자 좌표 범위를 검증한다.
2. `get_current_user_id()`로 Bearer 액세스 토큰과 사용자 존재 여부를 검증한다.
3. 인증에 실패하면 데이터 조회를 진행하지 않고 `401 UNAUTHORIZED_USER`를 반환한다.
4. `targetType`에 따라 삭제되지 않은 조회 대상을 찾는다.
5. 조회 대상이 없으면 `404 MAP_MODAL_TARGET_NOT_FOUND`를 반환한다.
6. 사용자 좌표와 대상 좌표로 거리와 예상 이동 시간을 계산한다.
7. `LOCATION`이면 삭제되지 않은 전체 방명록 개수와 최신 방명록 최대 3개를 조회한다.
8. 장소 방명록의 작성자와 연결된 공통 미션 정보를 함께 조회하여 응답을 조합한다.
9. `ROAD_GUESTBOOK`이면 작성자 정보와 저장된 콘텐츠를 조합한다.
10. 대상 유형에 맞는 응답을 `200 OK`로 반환한다.

장소의 최신 방명록을 조회할 때 작성자와 미션을 방명록마다 반복 조회하지 않도록 JOIN 또는 일괄 조회를 사용하여 N+1 문제를 방지한다. 이 API는 조회 전용이므로 DB 데이터를 생성하거나 변경하지 않는다.

## 7. 오류 처리

### 400 `INVALID_REQUEST`

다음 경우 공통 요청 오류를 반환한다.

- 필수 Query가 누락된 경우
- `targetType`이 `LOCATION | ROAD_GUESTBOOK` 중 하나가 아닌 경우
- `targetId`가 정수가 아니거나 1보다 작은 경우
- 사용자 위도 또는 경도가 숫자가 아닌 경우
- 사용자 위도가 `-90~90` 범위를 벗어난 경우
- 사용자 경도가 `-180~180` 범위를 벗어난 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

FastAPI의 Query 및 Enum 검증 실패를 기본 `422 Validation Error`로 그대로 반환하지 않고 프로젝트의 공통 예외 형식인 `400 INVALID_REQUEST`로 변환한다.

### 401 `UNAUTHORIZED_USER`

다음 경우 현재 사용자를 확인할 수 없음 오류를 반환한다.

- `Authorization` 헤더가 없는 경우
- 헤더가 `Bearer {accessToken}` 형식이 아닌 경우
- 액세스 토큰에 해당하는 사용자가 존재하지 않는 경우

```json
{
  "code": "UNAUTHORIZED_USER"
}
```

사용자 인증이 실패하면 장소, 방명록과 거리 정보를 조회하거나 응답하지 않는다.

### 404 `MAP_MODAL_TARGET_NOT_FOUND`

다음 경우 조회 대상 없음 오류를 반환한다.

- `targetType = LOCATION`인데 `targetId`에 해당하는 장소가 존재하지 않는 경우
- `targetType = ROAD_GUESTBOOK`인데 `targetId`에 해당하는 길바닥 방명록이 존재하지 않는 경우
- 조회 대상이 소프트 딜리트된 경우

```json
{
  "code": "MAP_MODAL_TARGET_NOT_FOUND"
}
```

장소는 존재하지만 장소 방명록이 없는 경우에는 `404`가 아니라 `guestbooksCount = 0`, `guestbooks = []`인 `200 OK`를 반환한다.

### 500 `INTERNAL_SERVER_ERROR`

DB 조회, 거리 계산 또는 응답 구성 중 예상하지 못한 오류가 발생하면 공통 서버 오류를 반환한다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```

# 지도 장소 상세 조회 비즈니스 룰

## 1. 요청과 화면 진입 전제

- HTTP 메서드: `GET`
- 엔드포인트: `/api/v1/map/locations/{locationId}`
- Request Query와 Body는 받지 않는다.
- `locationId`는 `LOCATION.id`다.
- 현재 사용자는 Authorization Bearer 토큰의 `get_current_user_id()`로 식별한다.
- 상세 화면은 지도 모달을 거쳐서 진입한다고 전제한다.

지도 모달 조회에서 이미 전달한 다음 정보는 상세 응답에서 중복 반환하지 않는다.

- 장소 이름
- 장소 카테고리
- 사용자와 장소 사이의 거리
- 예상 이동 시간

## 2. 장소 기본 정보와 TourAPI 상세 설명

`LOCATION.id = locationId`인 장소를 조회한다. 장소가 존재하지 않으면 `404 LOCATION_NOT_FOUND`를 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `locationAddress` | `LOCATION.location_address` |
| `locationDescription` | TourAPI `detailCommon2` 응답의 `overview` |

TourAPI 호출에는 `LOCATION.content_id`를 사용한다. `overview`는 프론트가 그대로 표시할 수 있는 일반 문자열로 정리한 후 반환한다.

1. HTML 엔티티를 일반 문자로 변환한다.
2. HTML 태그를 제거한다.
3. 연속된 공백과 줄바꿈을 하나의 공백으로 정리한다.
4. 앞뒤 공백을 제거한다.
5. 정리한 결과가 빈 문자열이면 `null`을 반환한다.

TourAPI에 `overview`가 없거나 상세 설명 조회에 실패하더라도 장소 상세 조회 전체를 실패시키지 않고 `locationDescription = null`로 반환한다.

## 3. 임시 추천 미션

추천 로직은 지도 서비스에서 직접 작성하지 않고 별도 추천 모듈로 분리한다. 구현 시 `app/map/mission_recommender.py`에서 담당하며, 정식 추천 정책이 적용되기 전까지 다음 임시 규칙을 사용한다.

- 추천 대상은 보물찾기와 협동 미션이다.
- 현재 장소에 연결된 미션도 추천 후보에 포함한다.
- 현재 사용자가 이미 완료한 미션은 추천 후보에서 제외한다.
- 남은 후보에서 중복 없이 무작위로 최대 3개를 선택한다.
- 요청할 때마다 추천 결과가 달라져도 된다.
- 후보가 3개보다 적으면 존재하는 후보만 반환한다.
- 후보가 없으면 `nearbyMissions = []`를 반환한다.

완료 여부는 지도 홈 조회에서 사용하는 사용자별 미션 완료 판정 규칙과 동일하게 판단한다. 보물찾기는 현재 사용자의 `COMPLETED` 진행도, 협동 미션은 현재 사용자의 삭제되지 않은 `ACCEPTED` 참가자 데이터와 삭제되지 않은 `COMPLETED` 진행도를 기준으로 한다.

각 추천 미션은 다음 값만 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `nearbyMissions[].id` | `TREASURE_MISSION.id` 또는 `COOPERATIVE_MISSION.id` |
| `nearbyMissions[].missionType` | `TREASURE` 또는 `COOPERATIVE` |
| `nearbyMissions[].missionTitle` | 세부 미션의 `mission_id`로 연결된 `MISSION.mission_title` |

`nearbyMissions[].id`는 공통 `MISSION.id`가 아니라 `missionType`에 해당하는 유형별 세부 미션 ID다.

## 4. 장소 방명록 전체 조회

다음 조건을 만족하는 방명록을 개수 제한과 페이지네이션 없이 모두 반환한다.

```text
GUESTBOOK.location_id = LOCATION.id
AND GUESTBOOK.deleted_at IS NULL
```

방명록은 다음 순서로 정렬한다.

```text
GUESTBOOK.visited_at DESC,
GUESTBOOK.id DESC
```

- 최신 여부는 `created_at`이나 `saved_at`이 아니라 `visited_at`을 기준으로 판단한다.
- `visited_at`이 같으면 `id`가 큰 방명록을 먼저 반환한다.
- 조회된 방명록이 없으면 `guestbooks = []`를 반환한다.

각 방명록은 다음 값을 반환한다.

| 응답 필드 | 데이터 출처 및 규칙 |
| --- | --- |
| `guestbooks[].id` | `GUESTBOOK.id` |
| `guestbooks[].missionTitle` | `GUESTBOOK.mission_id`로 연결된 `MISSION.mission_title` |
| `guestbooks[].representativeImageUrl` | `GUESTBOOK.content_img_url` 배열의 첫 번째 URL |
| `guestbooks[].userNickname` | `GUESTBOOK.user_id`로 연결된 `USER.nickname` |
| `guestbooks[].visitedAt` | `GUESTBOOK.visited_at`, `YYYY-MM-DD` 형식 |
| `guestbooks[].contentWriting` | `GUESTBOOK.content_writing` |

- 방명록이 미션을 참조하지 않으면 `missionTitle = null`을 반환한다.
- 이미지 배열이 `null`이거나 비어 있으면 `representativeImageUrl = null`을 반환한다.
- 이미지가 있으면 배열의 첫 번째 URL을 그대로 반환한다.
- 글이 없으면 `contentWriting = null`을 반환한다.
- `GUESTBOOK.mission_id`는 유형별 세부 미션 ID가 아니라 공통 `MISSION.id`를 참조한다.

## 5. 현재 장소의 미션

하나의 장소에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다. 다음 두 조건에 해당하는 미션을 함께 조회한다.

```text
TREASURE_MISSION.location_id = LOCATION.id
OR COOPERATIVE_MISSION.location_id = LOCATION.id
```

- 조회 결과가 없으면 `locationMission = null`을 반환한다.
- 하나만 조회되면 해당 미션을 반환한다.
- 데이터 이상으로 둘 이상 조회되면 유형과 관계없이 유형별 세부 미션 ID를 기준으로 `id ASC` 정렬한 첫 번째 미션만 반환한다.

| 응답 필드 | 데이터 출처 |
| --- | --- |
| `locationMission.id` | `TREASURE_MISSION.id` 또는 `COOPERATIVE_MISSION.id` |
| `locationMission.missionType` | `TREASURE` 또는 `COOPERATIVE` |

`locationMission.id`는 공통 `MISSION.id`가 아니라 `missionType`에 해당하는 유형별 세부 미션 ID다.

## 6. 처리 순서

1. `locationId`의 타입과 범위를 검증한다.
2. Bearer 토큰으로 현재 사용자를 식별한다.
3. `LOCATION.id = locationId`인 장소를 조회한다.
4. 장소가 없으면 `404 LOCATION_NOT_FOUND`를 반환한다.
5. `LOCATION.content_id`로 TourAPI `detailCommon2`의 `overview`를 조회하고 일반 문자열로 정리한다.
6. 별도 추천 모듈로 현재 사용자가 완료하지 않은 보물찾기·협동 미션을 최대 3개 무작위 선택한다.
7. 장소를 참조하는 삭제되지 않은 전체 방명록과 작성자·미션 정보를 일괄 조회한다.
8. 장소에 직접 연결된 미션을 조회하고 첫 번째 미션을 선택한다.
9. 응답을 조합하여 `200 OK`를 반환한다.

작성자와 미션을 방명록마다 반복 조회하지 않도록 JOIN 또는 일괄 조회를 사용하여 N+1 문제를 방지한다. 이 API는 조회 전용이므로 DB 데이터를 생성하거나 변경하지 않는다.

## 7. 오류 처리

### 400 `INVALID_REQUEST`

`locationId`가 정수가 아니거나 1보다 작은 경우 공통 요청 오류를 반환한다.

```json
{
  "code": "INVALID_REQUEST"
}
```

FastAPI의 Path 검증 실패를 기본 `422 Validation Error`로 그대로 반환하지 않고 프로젝트 공통 형식인 `400 INVALID_REQUEST`로 변환한다.

### 404 `LOCATION_NOT_FOUND`

`locationId`에 해당하는 장소가 존재하지 않는 경우 반환한다.

```json
{
  "code": "LOCATION_NOT_FOUND"
}
```

### 500 `INTERNAL_SERVER_ERROR`

DB 조회, 추천 미션 조회 또는 응답 구성 중 예상하지 못한 오류가 발생하면 공통 서버 오류를 반환한다. TourAPI 상세 설명 조회 실패는 `locationDescription = null`로 처리하므로 `500`으로 변환하지 않는다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```

# 지도 검색 결과 조회 비즈니스 룰

## 1. 요청

- HTTP 메서드: `GET`
- 엔드포인트: `/api/v1/map/search`
- Request Path와 Body는 받지 않는다.
- `Authorization: Bearer {accessToken}` 헤더는 필수다.
- 현재 사용자는 공통 의존성 `get_current_user_id()`로 식별하고 실제 사용자 존재 여부를 검증한다.

| Query 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `keyword` | string | O | `LOCATION.location_title`에서 검색할 키워드 |
| `userLatitude` | number | O | 현재 사용자 위치의 위도 |
| `userLongitude` | number | O | 현재 사용자 위치의 경도 |

- 프론트는 한글 조합 중인 글자에는 호출하지 않고 `성`, `성산`, `성산일`처럼 한글 음절이 완성될 때마다 호출한다.
- 한글 조합 완료 여부는 프론트가 판단하며 백엔드는 전달된 `keyword`를 검색어로 사용한다.
- 백엔드는 `keyword`의 앞뒤 공백을 제거한다.
- 공백 제거 후 한 글자 이상인 검색어만 허용한다.
- 위도와 경도는 프론트에서 임의로 반올림하지 않고 GPS 또는 지도 SDK에서 얻은 정밀도를 최대한 유지하여 전달한다.

## 2. 장소명 포함 검색

검색은 TourAPI 키워드 검색이나 미션 제목 검색이 아니라 `LOCATION.location_title`을 기준으로 수행한다.

```text
LOCATION.location_title CONTAINS trimmed_keyword
```

- 검색어가 장소 이름의 시작, 중간 또는 끝에 포함되어 있으면 모두 조회한다.
- 검색 결과의 개수 제한과 페이지네이션은 적용하지 않는다.
- 조건을 만족하는 `LOCATION`을 전부 조회한다.
- 검색 조건은 문자열을 직접 SQL에 이어 붙이지 않고 파라미터 바인딩을 사용한다.

## 3. 검색 로직 분리

현재는 키워드가 포함된 장소를 전부 반환하지만 추후 추천·검색 정책을 독립적으로 교체할 수 있도록 검색과 분류 로직을 함수로 분리한다.

1. `_search_locations_by_keyword()`는 장소 제목에 검색어가 포함된 전체 `LOCATION` 후보를 조회한다.
2. `_build_recommended_locations()`는 후보 중 미션이 연결되지 않은 장소를 골라 `recommendedLocations` 응답을 만든다.
3. `_build_mission_locations()`는 후보 중 보물찾기 또는 협동 미션이 연결된 장소를 골라 `missionLocations` 응답을 만든다.

- 두 응답 구성 함수에 검색·추천 기준을 직접 섞지 않는다.
- 추후 정책을 적용할 때 각 함수 내부의 선별 기준만 교체할 수 있어야 한다.
- 키워드 후보 조회 결과와 장소별 미션 연결 정보는 가능한 한 일괄 조회하여 동일한 장소를 반복 조회하지 않는다.

## 4. 추천 장소 분류

검색된 장소에 보물찾기와 협동 미션이 모두 연결되어 있지 않으면 `recommendedLocations`에 포함한다.

각 장소는 다음 값을 반환한다.

| 응답 필드 | 데이터 출처 및 규칙 |
| --- | --- |
| `locationId` | `LOCATION.id` |
| `locationTitle` | `LOCATION.location_title` |
| `locationCategory` | `LOCATION.location_category` |
| `representativeImageUrl` | TourAPI `firstimage` |
| `distanceMeter` | 현재 사용자 위치에서 장소까지의 직선거리(m) |

- 장소 ID는 TourAPI 콘텐츠 ID가 아니라 내부 `LOCATION.id`를 반환한다.
- 추천 장소 검색 결과가 없으면 `recommendedLocations = []`를 반환한다.

## 5. 참여 가능한 미션 장소 분류

검색된 장소에 보물찾기 또는 협동 미션이 연결되어 있으면 `missionLocations`에 포함한다.

하나의 장소에는 보물찾기 또는 협동 미션이 최대 하나만 존재한다고 전제한다. 현재 사용자의 미션 완료 여부와 관계없이 키워드 조건을 만족하고 미션이 연결된 장소를 모두 반환한다.

각 장소는 다음 값을 반환한다.

| 응답 필드 | 데이터 출처 및 규칙 |
| --- | --- |
| `locationId` | `LOCATION.id` |
| `missionId` | `TREASURE_MISSION.id` 또는 `COOPERATIVE_MISSION.id` |
| `missionType` | `TREASURE` 또는 `COOPERATIVE` |
| `locationTitle` | `LOCATION.location_title` |
| `missionTitle` | 세부 미션의 `mission_id`로 연결된 `MISSION.mission_title` |
| `representativeImageUrl` | TourAPI `firstimage` |
| `distanceMeter` | 현재 사용자 위치에서 미션 장소까지의 직선거리(m) |

- `missionId`는 공통 `MISSION.id`가 아니라 `missionType`에 해당하는 유형별 세부 미션 ID다.
- 미션 장소 검색 결과가 없으면 `missionLocations = []`를 반환한다.

## 6. 장소 대표 이미지

두 배열의 `representativeImageUrl`은 동일한 규칙으로 구성한다.

1. `LOCATION.content_id`로 기존 KTO 서비스 모듈을 호출한다.
2. TourAPI 응답의 `firstimage` URL을 반환한다.
3. `firstimage`가 없거나 특정 장소의 이미지 조회에 실패하면 `null`을 반환한다.

특정 장소의 이미지 조회 실패로 전체 검색 API를 실패시키지 않는다. 지도 검색 서비스에 TourAPI HTTP 호출 코드를 중복 구현하지 않고 기존 KTO 서비스 모듈을 사용한다.

## 7. 거리와 정렬

사용자 위치와 각 장소의 좌표로 거리를 계산한다.

```python
distance_meter = calculate_distance_meter(
    userLatitude,
    userLongitude,
    location.my,
    location.mx,
)
```

- `distanceMeter`는 `app/common/distance.py`의 `calculate_distance_meter()` 결과를 사용한다.
- 지도 검색 서비스에 거리 공식을 중복 구현하지 않는다.
- `recommendedLocations`와 `missionLocations`는 각각 `distanceMeter ASC`로 정렬한다.
- 거리가 같으면 `locationId ASC`로 정렬하여 응답 순서를 고정한다.

## 8. 빈 검색 결과

검색 결과가 없더라도 오류로 처리하지 않고 `200 OK`를 반환한다.

```json
{
  "recommendedLocations": [],
  "missionLocations": []
}
```

- 미션 없는 장소만 조회되면 `missionLocations`만 빈 배열이다.
- 미션 장소만 조회되면 `recommendedLocations`만 빈 배열이다.
- 응답 키는 검색 결과 존재 여부와 관계없이 항상 포함한다.

## 9. 처리 순서

1. 필수 Query의 누락 여부, 타입, 검색어와 사용자 좌표 범위를 검증한다.
2. `get_current_user_id()`로 Bearer 액세스 토큰과 사용자 존재 여부를 검증한다.
3. 검색어의 앞뒤 공백을 제거한다.
4. `_search_locations_by_keyword()`로 장소 제목에 검색어가 포함된 전체 장소를 조회한다.
5. 조회된 장소와 연결된 보물찾기·협동 미션 및 공통 미션 제목을 일괄 조회한다.
6. `_build_recommended_locations()`와 `_build_mission_locations()`로 장소를 분류한다.
7. 각 장소의 TourAPI `firstimage`를 조회한다.
8. 공통 거리 모듈로 사용자와 각 장소 사이의 `distanceMeter`를 계산한다.
9. 두 배열을 각각 거리와 장소 ID 기준으로 정렬한다.
10. 응답을 조합하여 `200 OK`를 반환한다.

이 API는 조회 전용이므로 DB 데이터를 생성하거나 변경하지 않는다. 장소별 미션과 공통 미션 제목을 반복 조회하지 않도록 JOIN 또는 일괄 조회를 사용하여 N+1 문제를 방지한다.

## 10. 오류 처리

### 400 `INVALID_REQUEST`

다음 경우 공통 요청 오류를 반환한다.

- 필수 Query가 누락된 경우
- `keyword`가 문자열이 아닌 경우
- 앞뒤 공백을 제거한 `keyword`가 빈 문자열인 경우
- 사용자 위도 또는 경도가 숫자가 아닌 경우
- 사용자 위도가 `-90~90` 범위를 벗어난 경우
- 사용자 경도가 `-180~180` 범위를 벗어난 경우

```json
{
  "code": "INVALID_REQUEST"
}
```

FastAPI의 Query 검증 실패를 기본 `422 Validation Error`로 그대로 반환하지 않고 프로젝트 공통 형식인 `400 INVALID_REQUEST`로 변환한다.

### 401 `UNAUTHORIZED_USER`

다음 경우 현재 사용자를 확인할 수 없음 오류를 반환한다.

- `Authorization` 헤더가 없는 경우
- 헤더가 `Bearer {accessToken}` 형식이 아닌 경우
- 액세스 토큰에 해당하는 사용자가 존재하지 않는 경우

```json
{
  "code": "UNAUTHORIZED_USER"
}
```

인증이 실패하면 장소 검색, TourAPI 이미지 조회와 거리 계산을 수행하지 않는다.

### 500 `INTERNAL_SERVER_ERROR`

DB 조회, 거리 계산 또는 응답 구성 중 예상하지 못한 오류가 발생하면 공통 서버 오류를 반환한다. 특정 장소의 TourAPI 이미지 조회 실패는 `representativeImageUrl = null`로 처리하므로 전체 검색을 `500`으로 실패시키지 않는다.

```json
{
  "code": "INTERNAL_SERVER_ERROR"
}
```
