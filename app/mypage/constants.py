"""마이페이지 도메인 공통 상수.

명세에 숫자로 못 박혀 있는 값은 검증 코드·프롬프트·조회 조건에 흩어 적지 않고 이 모듈만 참조한다.
(app/mypage/docs/BUSINESS_RULES.md - 여행 마무리 엽서 저장 / 상수와 처리 경계)
"""

# 엽서에 담을 방문 장소 / 완료 미션 / 사진의 카테고리별 최대 선택 개수. (최소는 1개)
MAX_TRAVEL_ENDING_SELECTION_COUNT = 3

# 엽서 한 장을 만들 때마다 차감하는 포인트
TRAVEL_ENDING_CREATION_POINT_COST = 100

# 마이페이지 도감(`arCharacters`)에 노출하는 AR 캐릭터 id 범위. (양끝 포함)
# 대표 캐릭터(`profile.selectedArCharacter`)에는 적용하지 않는다.
# (app/mypage/docs/BUSINESS_RULES.md - 마이페이지 조회 / 캐릭터 ID 노출 범위 제한)
AR_CHARACTER_COLLECTION_MIN_ID = 1
AR_CHARACTER_COLLECTION_MAX_ID = 6
