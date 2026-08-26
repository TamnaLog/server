"""보물 찾기 도메인 공통 상수.

반경 값은 서비스 로직에 숫자로 직접 쓰지 않고 이 모듈을 참조한다.
(app/treasure_mission/docs/BUSINESS_RULES.md - 1. 반경 상수)

두 값 모두 API 응답으로 내보내지 않는다. 보물 표시/인식 반경은 프론트에서 관리한다.
"""

# 미션 장소를 중심으로 보물 좌표를 생성할 수 있는 최대 반경(m)
TREASURE_APPEAR_RADIUS_METER = 100

# 사용자가 보물을 발견한 것으로 인식하는 반경(m)
TREASURE_DETECTION_RADIUS_METER = 20
