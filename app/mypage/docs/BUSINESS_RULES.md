## 마이페이지 조회

### 사용자 프로필

- 모든 사용자별 데이터는 액세스 토큰으로 식별한 현재 사용자만을 기준으로 조회한다.
- 여행 스타일은 `USER.user_travel_style_id`로 연결된 `USER_TRAVEL_STYLE`의 `user_type`과 `hashtags`를 사용한다. 연결된 여행 스타일이 없으면 여행 스타일 전체를 `null`로 처리한다.
- 대표 캐릭터는 `USER.ar_character_id`로 결정하고, 획득 여부는 `ACQUIRED_AR_CHARACTER` 존재 여부로 별도 판정한다. 온보딩에서 배정됐지만 획득 기록이 없는 캐릭터도 대표 캐릭터가 될 수 있으며 이 경우 도감에서는 미획득 상태다.

### 요약 수치

- 방문 장소 수는 현재 사용자의 `VISITED_LOCATION.location_id`를 중복 제거해 집계한다. 같은 장소에 방문 기록이 여러 건 있어도 한 곳으로 계산한다.
- 완료 미션 수는 문화·보물찾기·협동 미션의 `COMPLETED` 진행도 수를 합산한다.
- 문화·보물찾기 미션은 진행도의 `user_id`가 현재 사용자와 일치하는 행만 집계한다.
- 협동 미션은 현재 사용자의 참가 행이 `participant_status = ACCEPTED`이고 `deleted_at IS NULL`인 경우만 집계하며, 삭제된 협동 진행도는 제외한다.

### 진행 중인 미션

- `mission_status = IN_PROGRESS`인 진행도만 사용한다. 협동 미션은 완료 집계와 동일하게 현재 사용자의 삭제되지 않은 `ACCEPTED` 참가 행이 연결된 진행도만 포함한다.
- 문화 미션의 현재 진행 수는 `current_quiz_index`, 전체 진행 수는 `quiz_total_count`를 사용한다.
- 보물찾기 미션의 현재 진행 수는 `current_found_item_idx` 배열의 원소 수, 전체 진행 수는 `item_total_count`를 사용한다.
- 협동 미션의 현재 진행 수는 `current_step`, 전체 진행 수는 공통 `MISSION.step_detail` 배열의 원소 수를 사용한다.

### AR 캐릭터 도감

- 도감은 `AR_CHARACTER` 전체를 기준으로 구성하고, 현재 사용자의 `(user_id, ar_character_id)` 획득 기록 존재 여부로 각 캐릭터의 획득 상태를 판정한다.
- 획득 날짜는 `ACQUIRED_AR_CHARACTER.created_at`을 KST의 `YYYY-MM-DD`로 변환한다.
- 획득 장소는 획득 기록의 `acquired_mission_id`에서 유형별 미션을 거쳐 연결된 `LOCATION.location_title`을 사용한다. 장소 연결이 없는 문화 미션이거나 장소를 확인할 수 없으면 `null`로 처리한다.
- 캐릭터별 획득 가능 미션은 각 유형별 미션의 `reward_detail.ar_character_id`가 캐릭터 ID와 같은 항목으로 구성한다.
- 획득 가능 미션은 내부 공통 `MISSION.id ASC`로 정렬한 뒤 최대 3개만 사용한다. 외부에 노출하는 미션 ID는 공통 ID가 아니라 해당 유형별 세부 미션 ID다.
- 획득 가능 미션이 없으면 빈 배열을 사용한다. 캐릭터 획득 여부는 획득 가능 미션 목록의 존재 여부나 미션 완료 여부로 추론하지 않는다.
- 전체 도감과 미션 정보를 캐릭터마다 반복 조회하지 않고 일괄 조회하여 N+1 쿼리를 방지한다.

## 사용자 정보 변경

### 교체 범위와 검증

- 요청은 부분 갱신이 아니라 현재 프로필 전체를 교체한다. 다섯 필드 중 하나라도 누락되면 유효하지 않은 요청으로 처리한다.
- 닉네임은 앞뒤 공백을 제거한 값을 저장한다. 정규화한 결과가 1~20자가 아니면 `400 Bad Request`이며, 다른 사용자와의 중복은 허용한다.
- 세 선택 배열은 빈 배열을 허용한다. 각 배열 안에 같은 enum 값이 두 번 이상 있거나 허용되지 않은 값이 있으면 `400 Bad Request`로 처리한다.
- 목표 걸음 수는 bool이나 소수가 아닌 정수만 허용하며 `1 <= targetStepCount <= 100000`을 만족하지 않으면 `400 Bad Request`로 처리한다.

### 저장과 재배정

- `categories`, `transportation`, `travelStyle`은 각각 `USER.expectation`, `USER.transportation`, `USER.travel_style`을 요청값으로 교체하고 `targetStepCount`는 `USER.target_step`에 저장한다.
- 선택 배열은 요청값을 그대로 저장한다. 빈 배열이 온 컬럼은 `NULL`로 바꾸지 않고 빈 배열로 저장한다.
- 변경된 세 선택 배열을 온보딩 도메인의 기존 매칭 모듈에 전달해 `USER.user_travel_style_id`와 `USER.ar_character_id`를 모두 다시 결정한다. 마이페이지 도메인에 별도의 매칭 로직을 복제하지 않는다.
- 세 선택 배열이 모두 비어 있으면 온보딩 건너뛰기와 동일하게 `user_travel_style_id = NULL`로 두고 기본 AR 캐릭터를 배정한다. 이때도 선택값 세 컬럼은 빈 배열로 저장한다. 일부 배열만 비어 있으면 빈 배열을 포함한 전체 선택값으로 일반 매칭을 수행한다.
- 재배정된 캐릭터는 대표 캐릭터만 변경한다. `ACQUIRED_AR_CHARACTER`를 생성하거나 삭제하지 않는다.
- 현재 온보딩 매칭 모듈은 임시 랜덤 구현이므로 같은 프로필 값으로 다시 저장해도 여행 유형과 캐릭터가 달라질 수 있다. 추후 매칭 알고리즘 변경은 온보딩 모듈 내부에서만 수행한다.
- 사용자 필드 갱신과 두 매칭 결과 반영은 하나의 트랜잭션으로 처리한다. 검증이나 매칭이 실패하면 전체 변경을 롤백하며 커밋 후에만 성공으로 처리한다.
