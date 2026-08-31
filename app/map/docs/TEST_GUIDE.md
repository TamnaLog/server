# 지도 도메인 테스트 가이드

## 테스트 대상

| API | 테스트 파일 |
| --- | --- |
| `GET /api/v1/map/contents` (지도 홈 조회) | `app/map/tests/test_get_map_contents.py` |
| `GET /api/v1/map/modals` (지도 모달 조회) | `app/map/tests/test_get_map_modal.py` |
| `GET /api/v1/map/locations/{locationId}` (지도 장소 상세 조회) | `app/map/tests/test_get_location_detail.py` |
| `GET /api/v1/map/search` (지도 검색 결과 조회) | `app/map/tests/test_search_map.py` |
| TourAPI 상세 설명(`overview`) 정리 | `app/map/tests/test_location_overview.py` |

## 테스트 의도

지도 홈 조회는 **틀려도 눈에 잘 안 띄는 실수**가 세 종류 있다.

첫째, **조회 영역 판정**이다.
지도를 회전하면 화면 네 꼭짓점이 위도·경도 축과 나란하지 않다.
이때 "위도 범위 AND 경도 범위"로만 거르면 화면 밖 데이터가 섞여 들어온다.
DB에서는 범위로 후보만 좁히고 실제 사각형 안인지 다시 판정하는데,
이 두 번째 판정이 빠져도 **축에 나란한 화면에서는 결과가 똑같아서** 테스트가 통과해 버린다.
그래서 마름모 화면을 따로 만들어 "범위 안이지만 사각형 밖"인 좌표를 준비했다.

둘째, **현재 사용자 기준 판정**이다.
`isCompleted`와 `hasWrittenGuestbook`은 토큰으로 식별한 사용자의 이력을 봐야 한다.
사용자 조건을 빼먹어도 **테스트 데이터에 사용자가 한 명뿐이면 결과가 같다.**
그래서 비교용 사용자를 하나 더 두고 "다른 사람의 완료 이력/방명록"이 섞이지 않는지 확인한다.

셋째, **`isClustered = true`일 때 하지 말아야 할 일**이다.
좌표만 내려주면 되는데 미션·진행도·방명록·TourAPI를 조회하면 응답은 똑같이 맞고 성능만 나빠진다.
응답만 봐서는 알 수 없으므로 TourAPI 스텁이 **호출된 `content_id`를 기록**하게 해서
클러스터링일 때 호출 횟수가 0인지 직접 확인한다.

## 주요 검증 항목

### 1. 지도에 표시할 장소

`locations`는 **조회 영역 안의 장소를 걸러내지 않고 모두** 담는다.

- 미션도 방명록도 없는 장소도 나온다. 두 미션은 `null`, `guestbooksCount`는 `0`이다.
- 방명록이 모두 삭제돼도 장소는 남고 개수만 `0`이 된다.
- `isClustered = true`에서도 똑같이 모든 장소의 좌표가 나온다.
- 화면 밖 장소만 빠진다.

### 2. `isClustered = false` (상세)

- 장소 응답 10개 필드를 **통째로 비교**한다.
  (`id` / `locationTitle` / `latitude` / `longitude` / `distanceMeter` / `durationMinutes` /
  `treasureMission` / `cooperativeMission` / `guestbooksCount` / `representativeImageUrl`)
- **거리와 예상 시간**은 `app/common/distance.py`를 직접 호출한 값과 같아야 한다.
  사용자 좌표를 장소와 같게 주면 `distanceMeter`가 0이 되는 것으로 실제 반영을 확인한다.
- 보물찾기와 협동 미션이 **둘 다 있는 장소**는 두 객체가 모두 채워진다.
  없는 유형은 필드를 생략하지 않고 `null`이다.
- 방명록 개수는 **삭제된 방명록을 빼고**, **그 장소의 방명록만** 센다.
- 길바닥 방명록은 `content_img_url`의 **첫 번째** URL을 대표 이미지로 쓴다.
  배열이 없거나 비어 있으면 `null`. 삭제된 길바닥 방명록은 응답에서 빠진다.
- TourAPI가 이미지를 못 주면 `representativeImageUrl: null`이고 **전체 조회는 200**이다.
- 조회 결과가 없어도 200이고 `{"locations": [], "roadGuestbooks": []}`.

### 3. 미션 완료 여부 (`isCompleted`)

보물찾기:

- `COMPLETED` 진행도가 있으면 `true`, `IN_PROGRESS`만 있으면 `false`.
- **다른 사용자의 완료 이력은 반영하지 않는다.**
- 진행 이력이 여러 개면 **완료가 하나라도 있으면** `true`.

협동 미션은 진행도에 사용자가 없어 참가자를 거쳐 판단한다. 다음은 모두 `false`여야 한다.

- 진행 중인 방 / 다른 사용자의 방
- 수락되지 않은(`PENDING`) 참가자
- **소프트 삭제된 방** / **나간(소프트 삭제된) 참가자**

### 4. 미션 방명록 작성 여부 (`hasWrittenGuestbook`)

- **미완료면 조회하지 않고 `null`이다.** (완료해야만 `true`/`false`가 나온다)
- 완료 + 해당 미션 방명록 있음 → `true`, 완료 + 없음 → `false`.
- `GUESTBOOK.mission_id`는 세부 미션 id가 아니라 공통 `MISSION.id`라
  **장소와 미션을 함께** 봐야 한다. 다음은 모두 `false`다.
  - 다른 사용자의 방명록 / 삭제된 방명록
  - 미션을 참조하지 않는(`mission_id`가 `null`인) 방명록
  - **다른 장소의 방명록**
- 한 장소에 두 유형의 미션이 있을 때 **다른 유형의 방명록이 섞이지 않는다.**

### 5. `isClustered = true` (좌표만)

- 장소와 길바닥 방명록 모두 `latitude` / `longitude` **두 키만** 있는지 확인한다.
- **TourAPI를 한 번도 호출하지 않는다.** (스텁에 기록된 호출 목록이 비어 있어야 한다)
- 반대로 `isClustered = false`에서는 **화면 안 장소 수만큼** 호출한다.
  (화면 밖 장소는 조회하지 않으므로 호출되지 않는다)
- 클러스터링이어도 삭제된 길바닥 방명록은 빠진다.

### 6. 회전한 화면

마름모 화면 `(33.50,126.95) → (33.45,127.00) → (33.40,126.95) → (33.45,126.90)` 으로 확인한다.

- 마름모 한가운데 장소는 나오고, **위도·경도 범위 안이지만 모서리 밖**인 장소는 안 나온다.
  (영역 판정을 빼면 이 테스트가 깨진다)
- **경계선 위의 좌표도 포함**한다. 꼭짓점 3곳과 변 위 2곳을 각각 확인한다.
  변 위의 점은 ray casting만으로는 바깥으로 판정되므로,
  경계선 검사를 빼면 이 테스트가 깨진다.

### 7. 400 `INVALID_REQUEST`

- 필수 Query 누락 (꼭짓점 / `userLatitude` / `userLongitude` / `isClustered`)
- 위도가 숫자가 아니거나 `-90~90` 밖, 경도가 `-180~180` 밖 (**사용자 좌표 포함**)
- `isClustered`를 boolean으로 해석할 수 없음
- **네 꼭짓점이 영역을 만들지 못하는 경우** — 네 점이 모두 같거나 한 직선 위에 있을 때

### 8. 401 `UNAUTHORIZED_USER`

이 API는 현재 사용자 기준으로 미션 완료 여부를 판단하므로 인증이 필요하다.

- `Authorization` 헤더가 없거나 토큰의 사용자가 없으면 401.
- Swagger 문서에도 401이 붙는다. (400/500과 함께)

# 지도 모달 조회

## 테스트 의도

모달 조회는 **`targetType`에 따라 완전히 다른 응답**을 준다.
그래서 두 응답 형태를 각각 통째로 비교하고, 두 유형이 서로 섞이지 않는지도 확인한다.

`LOCATION` 응답에는 장소에 연결된 **미션 한 건**도 들어간다.
여기서 중요한 건 미션이 배열이 아니라 **단일 객체 또는 `null`**이라는 점,
그리고 `rewardDetail`이 미션 홈의 `remainingReward`와 **반대 방향**이라는 점이다.
남은 보상만 주는 게 아니라 **전부 주고 `isReceived`로만 구분**한다.
받은 보상을 `null`로 지워버리는 실수를 잡으려고, 세 보상을 모두 지급한 상태에서도
상세 정보가 그대로 남아 있는지 확인한다.

특히 틀리기 쉬운 세 가지가 있다.

첫째, **"최신"의 기준**이다.
방명록에는 `created_at` / `saved_at` / `visited_at`이 다 있는데 명세는 `visited_at` 기준이다.
테스트 데이터를 순진하게 만들면 세 값의 순서가 같아져서 무엇으로 정렬하든 통과한다.
그래서 **저장은 나중에 했지만 방문일은 더 과거인** 방명록을 일부러 만들어 둔다.

둘째, **`guestbooksCount`가 목록 길이가 아니라는 점**이다.
목록은 최대 3개인데 개수는 전체다. 방명록을 3개 이하만 만들면 둘이 같아져서 구분되지 않는다.
그래서 5개를 만들어 개수 5 / 목록 3을 확인한다.

셋째, **`isCompleted`와 `isReceived`가 서로 독립**이라는 점이다.
"완료했으면 보상도 받았겠지"라고 묶어 버리기 쉬워서, 완료했지만 아직 못 받은 경우와
받았지만 완료로 잡히지 않는 경우를 따로 만든다.
보상 수령 여부는 진행도 **이력 전체의 OR**라서, 서로 다른 진행도에서 종류별로 나눠 지급한
데이터를 만들어 "가장 최근 진행도 하나만 본" 구현을 걸러낸다.

## 주요 검증 항목

### 1. `targetType = LOCATION`

- 응답 8개 필드를 **통째로 비교**한다.
  (`id` / `locationTitle` / `locationCategory` / `distanceMeter` / `durationMinutes` /
  `mission` / `guestbooksCount` / `guestbooks`)
- **정렬**: `visited_at DESC`, 같으면 `id DESC`. 최대 3개.
  - 저장 시각이 더 최신이어도 방문일이 과거면 뒤로 간다.
- **`guestbooksCount`는 전체 개수**다. 방명록 5개면 개수 5, 목록 3.
- 삭제된 방명록은 **개수와 목록 양쪽에서** 빠진다.
- 다른 장소의 방명록은 섞이지 않는다.
- 방명록이 없어도 404가 아니라 **200 + 개수 0 + 빈 배열**이다.
- 대표 이미지는 배열 첫 번째 URL. `null`이거나 빈 배열이면 `null`.
- `mission_id`가 없으면 `missionTitle`은 `null`. (`GUESTBOOK.mission_id`는 공통 `MISSION.id`)
- 거리·시간은 `app/common/distance.py` 결과와 같다. 사용자 좌표가 장소와 같으면 0.

### 2. 장소 미션 (`mission`)

- 연결된 미션이 없으면 `mission`은 `null`이다. (404가 아니다)
- 보물찾기 / 협동 미션 각각 **단일 객체**로 반환하고, `missionId`는 공통 `MISSION.id`가 아니라
  **유형별 세부 미션 id**다. `missionTitle`은 세부 미션이 참조하는 `MISSION.mission_title`.
- 다른 장소에 붙은 미션은 섞이지 않는다.
- `rewardDetail`은 수령 여부와 관계없이 AR 캐릭터 / 포인트 / 쿠폰을 모두 담는다.
  **미션에 설정되지 않은 항목만** `null`이다.
- 이미 받은 보상도 상세 정보를 지우지 않고 `isReceived`만 `true`가 된다.

#### 완료 여부 (`isCompleted`)

- 진행도가 없거나 `IN_PROGRESS`만 있으면 `false`, 완료 이력이 하나라도 있으면 `true`.
  (가장 최근 진행도가 `IN_PROGRESS`여도 과거에 완료했으면 `true`)
- 다른 사용자의 완료 이력은 반영되지 않는다.
- 완료했어도 보상을 안 받았으면 `isReceived`는 `false`다. (둘은 독립)

#### 보상 수령 여부 (`isReceived`)

- 진행도 이력이 없으면 세 보상 모두 `false`.
- 서로 다른 진행도에서 각각 지급된 보상은 **종류별 OR**로 판정한다.
  (1번 진행도 캐릭터 + 2번 진행도 쿠폰 → 캐릭터·쿠폰 `true`, 포인트만 `false`)
- 협동 미션은 **삭제되지 않은 `ACCEPTED` 참가자**로 연결된 **삭제되지 않은 진행도**만 본다.
  삭제된 참가자 / `PENDING` 참가자 / 삭제된 진행도는 완료·보상 이력 모두에서 빠진다.
- **조회 전용**: 모달을 호출해도 진행도의 보상 지급 여부와 사용자 포인트가 그대로다.

### 3. `targetType = ROAD_GUESTBOOK`

- 응답 11개 필드를 **통째로 비교**한다.
- 콘텐츠가 없으면 **키를 생략하지 않고 `null`**이다. (사진/글/오디오/날씨/색상 5종 모두 확인)
- **빈 배열로 저장돼 있어도 `null`로 정규화**한다. (`content_img_url` / `content_audio_url`)
- 값이 있으면 배열 순서를 바꾸지 않는다.
- 작성일은 `saved_at`이 아니라 `visited_at` 기준이다.

### 4. 404 `MAP_MODAL_TARGET_NOT_FOUND`

- 장소 / 길바닥 방명록이 없을 때
- 길바닥 방명록이 **소프트 삭제**됐을 때
- **`targetType`과 다른 테이블에 같은 id가 있어도** 조회 결과로 쓰지 않는다.
  (장소 39는 있지만 `ROAD_GUESTBOOK`으로 39를 조회하면 404, 그 반대도 마찬가지)

### 5. 400 `INVALID_REQUEST`

- 필수 Query 4개 중 하나라도 누락
- `targetType`이 `LOCATION | ROAD_GUESTBOOK`이 아님 (**소문자도 거부**)
- `targetId`가 정수가 아니거나 1보다 작음
- 사용자 위도·경도가 숫자가 아니거나 범위 밖

### 6. 401 `UNAUTHORIZED_USER`

미션의 완료·보상 수령 여부가 사용자별로 갈리므로 토큰으로 사용자를 식별해야 한다.

- `Authorization` 헤더가 없거나 토큰의 사용자가 없으면 401.
- Swagger 문서 응답은 200/400/401/404/500이다.

# 지도 장소 상세 조회

## 테스트 의도

상세 조회에서 조심할 곳은 세 군데다.

첫째, **모달에서 이미 준 값을 다시 주면 안 된다.**
장소명·분류·거리·예상 시간은 상세 응답에 없어야 한다.
필드를 하나씩 확인하면 "없어야 할 게 생긴" 경우를 놓치므로 **응답 키 집합을 통째로** 비교한다.

둘째, **방명록에 개수 제한이 없다.**
모달 조회는 최대 3개인데 상세는 전부다. 같은 정렬 규칙을 쓰지만 자르면 안 된다.
그래서 10개를 넣고 10개가 다 오는지 확인한다.

셋째, **`locationMission`은 유형과 무관하게 세부 미션 id가 가장 작은 하나**다.
보물찾기 5 / 협동 3이면 협동이 나온다. 유형 우선순위로 착각해 보물찾기를 먼저 고르면 틀린다.

추천 미션은 랜덤이라 값 자체가 아니라 **후보 안에 있는지 / 제외돼야 할 게 빠졌는지**로 본다.

## 주요 검증 항목

### 1. 정상 응답

- 응답 키는 **정확히 5개**다.
  (`locationAddress` / `locationDescription` / `nearbyMissions` / `guestbooks` / `locationMission`)
- `locationDescription`은 TourAPI 결과다. 조회하지 못하면 `null`이고 전체 조회는 200이다.
- 상세 설명 조회에는 그 장소의 `content_id`를 쓴다.

### 2. 방명록

- **개수 제한 없이 전부** 반환한다. (10개 넣으면 10개)
- 정렬은 `visited_at DESC`, 같으면 `id DESC`.
  저장 시각이 더 최신이어도 방문일이 과거면 뒤로 간다.
- 삭제된 방명록과 다른 장소의 방명록은 빠진다.
- 이미지 배열이 없거나 비어 있으면 `representativeImageUrl`은 `null`.
- 미션을 참조하지 않으면 `missionTitle`은 `null`.

### 3. `locationMission`

- 미션이 없으면 `null`.
- 유형 하나만 있으면 그 미션.
- **두 유형이 다 있으면 세부 미션 id가 작은 쪽**. (보물찾기 5 / 협동 3 → 협동)
- 같은 유형이 둘 이상이어도 id가 작은 쪽.
- 다른 장소의 미션은 잡히지 않는다.

### 4. `nearbyMissions` (임시 추천)

- 후보가 없으면 빈 배열.
- 반환값은 DB에 있는 미션 중 하나여야 한다. (id / 유형 / 제목 조합으로 확인)
- **최대 3개**이고 같은 미션이 두 번 나오지 않는다.
- **현재 사용자가 완료한 미션은 빠진다.** (보물찾기 / 협동 각각)
- 완료로 보지 않는 경우는 추천에 남는다.
  - 보물찾기: 진행 중 / 다른 사용자의 완료
  - 협동: 진행 중인 방 / 다른 사용자의 방 / `PENDING` 참가자 / 삭제된 방 / 나간 참가자
- **지금 보고 있는 장소의 미션도 후보**이고, 다른 장소의 미션도 후보다.

### 5. TourAPI `overview` 정리

상세 조회 API 테스트는 이 함수를 스텁으로 막기 때문에 정리 규칙이 검증되지 않는다.
그래서 HTTP 호출만 대신하고 정리 로직은 실제로 태우는 테스트를 따로 뒀다.

- HTML 태그 제거, HTML 엔티티 변환, 연속 공백·줄바꿈 축약, 앞뒤 공백 제거
- 명세 순서가 **엔티티 변환 → 태그 제거**라 `&lt;b&gt;`도 태그로 보고 지운다.
- 정리 결과가 비면(`""` / 공백만 / 태그만 / `overview` 없음 / 문자열이 아님) `null`.
- TourAPI 조회 자체에 실패해도 `null`.

### 6. 404 / 400 / 401

- 장소가 없으면 **404 `LOCATION_NOT_FOUND`**
- `locationId`가 정수가 아니거나 1보다 작으면 **400 `INVALID_REQUEST`**
- 인증 헤더가 없거나 토큰의 사용자가 없으면 **401 `UNAUTHORIZED_USER`**

# 지도 검색 결과 조회

## 테스트 의도

검색은 **"어떻게 찾는가"와 "어디에 넣는가"** 두 가지가 각각 틀릴 수 있다.

찾는 쪽에서 조심할 건 두 가지다.
하나는 **부분 일치**다. 검색어가 이름의 앞에만 있는 데이터로 테스트하면
`startswith`로 잘못 구현해도 통과한다. 그래서 앞·중간·끝을 각각 확인한다.
다른 하나는 **LIKE 와일드카드**다. 검색어의 `%`와 `_`를 이스케이프하지 않으면
사용자가 `%`를 치는 순간 전체 장소가 쏟아진다. 평범한 한글 검색어로는 절대 안 걸린다.

넣는 쪽은 **한 장소가 두 배열에 동시에 들어가면 안 된다**는 점이다.
미션이 생기면 추천에서 빠지고 미션 장소로 옮겨가야 한다.
분류 조건을 잘못 쓰면 양쪽에 다 들어가는데, 배열을 따로 보면 눈치채기 어렵다.

## 주요 검증 항목

### 1. 분류

- 미션이 없는 장소는 `recommendedLocations`, 있는 장소는 `missionLocations`.
- 두 배열의 응답 필드를 각각 **통째로** 비교한다.
- **미션이 생기면 추천에서 빠지고 미션 장소로 옮겨간다.** (양쪽 동시 포함 방지)
- 두 유형이 다 연결되면 **세부 미션 id가 작은 쪽** 하나만 쓴다.
  (장소 상세의 `locationMission`과 같은 기준)

### 2. 검색어 매칭

- 검색어가 이름의 **앞·중간·끝** 어디에 있어도 찾는다.
- 앞뒤 공백은 지우고 검색한다.
- **`%`와 `_`는 글자 그대로 찾는다.** (`contains(..., autoescape=True)`)
  `%`로 검색하면 이름에 `%`가 든 장소만 나와야 한다.
- 한 글자 검색어도 허용한다.
- 개수 제한과 페이지네이션이 없다. (22곳 넣으면 22곳)

### 3. 거리와 정렬

- `distanceMeter`는 `app/common/distance.py` 결과와 같다.
- 두 배열 각각 **`distanceMeter ASC`**, 거리가 같으면 **`locationId ASC`**.

### 4. 대표 이미지

- TourAPI `firstimage`. 조회하지 못하면 `null`이고 전체 검색은 200이다.
- 검색된 장소 수만큼만 호출한다. (검색되지 않은 장소는 호출하지 않는다)

### 5. 빈 결과

- 결과가 없어도 200이고 두 키 모두 빈 배열이다.
- 한쪽만 비는 경우도 확인한다.

### 6. 400 / 401

- 필수 Query 누락, 사용자 좌표가 숫자가 아니거나 범위 밖
- **빈 검색어와 공백만 있는 검색어**는 400 (공백 제거 후 한 글자 이상이어야 한다)
- 인증 헤더가 없거나 토큰의 사용자가 없으면 401
- **인증에 실패하면 TourAPI를 호출하지 않는다.** (스텁 호출 기록이 비어 있어야 한다)

## 실행 방법

```bash
# 최초 1회
pip install -r requirements-dev.txt

# 전체 테스트
pytest

# 지도 도메인만
pytest app/map

# 특정 테스트만
pytest app/map/tests/test_get_map_contents.py -k 회전
pytest app/map/tests/test_get_map_contents.py -k 경계선
pytest app/map/tests/test_get_map_contents.py -k 클러스터링
pytest app/map/tests/test_get_map_contents.py -k 완료
pytest app/map/tests/test_get_map_modal.py -k 최신
pytest app/map/tests/test_get_map_modal.py -k 길바닥
pytest app/map/tests/test_get_location_detail.py -k 추천
pytest app/map/tests/test_location_overview.py
pytest app/map/tests/test_search_map.py -k 검색어
pytest app/map/tests/test_search_map.py -k 정렬
```

DB는 SQLite 인메모리를 사용하므로 MySQL이 떠 있지 않아도 실행된다.
공통 픽스처(`client`, `db_session`)는 루트 `conftest.py`에 있다.

- `users`: 현재 사용자와 **비교용 다른 사용자** 한 명.
  "다른 사람의 이력이 섞이지 않는지" 검증에 쓴다.
- `map_data`: 장소 4곳을 만든다.
  미션 2종이 다 있는 장소 / 방명록만 있는 장소 / **빈 장소** / **화면 밖 장소**.
  빈 장소는 "아무것도 없어도 미션 `null`·개수 `0`으로 나오는지" 확인용이다.
- 완료 이력은 `_add_treasure_progress()` / `_add_cooperative_progress()`로 붙인다.
  두 함수 모두 상태·사용자·소프트 삭제 여부를 인자로 받아 "완료로 보지 않는 경우"를 만든다.
- 방명록은 `_add_guestbook()` / `_add_road_guestbook()`로 필요한 테스트에서만 붙인다.
- 조회 영역 판정 테스트는 `_add_location()`으로 좌표만 다른 장소를 만든다.

TourAPI 호출은 `stub_location_image` 픽스처(autouse)가 가로챈다.
이 픽스처는 **호출된 `content_id` 목록을 반환**하므로,
"호출했는지" 자체를 검증하는 테스트는 픽스처를 인자로 받아 그 목록을 확인한다.

모달 조회 테스트는 `modal_data` 픽스처로 장소 2곳·사용자 2명·미션 1개를 만들고,
방명록은 `_add_guestbook()` / `_add_road_guestbook()`으로 테스트마다 직접 붙인다.
두 헬퍼 모두 방문일과 콘텐츠, 소프트 삭제 여부를 인자로 받는다.

장소 상세 테스트는 `detail_data` 픽스처로 장소 2곳·사용자 2명·공통 미션 2개를 만들고,
세부 미션은 `_add_treasure_mission()` / `_add_cooperative_mission()`으로 테스트마다 붙인다.
(세부 미션 id를 보물찾기 5 / 협동 3으로 둬서 "id가 작은 쪽"을 유형 우선순위와 구분한다)
TourAPI 상세 설명은 `stub_overview` 픽스처(autouse)가 가로채고, 호출된 `content_id`를 기록한다.

검색 테스트는 `search_data` 픽스처로 검색어가 들어간 장소 4곳(미션 있는 곳 2 / 없는 곳 2)과
검색어가 안 들어간 장소 1곳을 만든다. 좌표는 모두 같게 둬서 "거리가 같을 때 id 순"을 확인한다.

정책이 바뀔 로직은 서비스 밖 모듈로 나가 있다. 기준을 갈아끼울 때는 이 파일들만 보면 된다.

| 모듈 | 담당 |
| --- | --- |
| `app/map/viewport.py` | 조회 영역(회전한 화면) 판정 |
| `app/map/mission_recommender.py` | 장소 상세의 근처 추천 미션 (임시 랜덤) |
| `app/map/search_classifier.py` | 검색 결과의 추천 장소 / 미션 장소 선별 |
| `app/map/mission_completion.py` | 사용자별 미션 완료 판정 (홈 조회 `isCompleted`와 공용) |
| `app/map/location_missions.py` | 장소별 세부 미션 일괄 조회 (홈 조회·검색 공용) |

검색 응답의 대표 이미지는 서비스가 아니라 `search_classifier`가 조회하므로,
검색 테스트의 TourAPI 스텁은 `search_classifier`를 대상으로 건다.
서비스를 거치지 않고 `Viewport.contains()`만 따로 확인하고 싶으면 이 모듈을 직접 쓰면 된다.
