-- =====================================================================
-- 잠깐, 제주 - 목업 데이터
-- 선행: scripts/sql/01-schema.sql
--
-- 실행 예시)
--   mysql -h 127.0.0.1 -u tour -p tour < scripts/sql/02-data-mock.sql
--
-- 데이터 방침
--   - 사용자: id=1 이 "나"(로그인 고정 사용자). id=2~6 은 협동 미션 팀원 5명.
--   - 콘텐츠 성격의 테이블(LOCATION / MISSION / *_MISSION / AR_CHARACTER)은 채운다.
--   - 진행도(progress) 계열은 비워 둔다.
--   - USER_TRAVEL_STYLE 은 온보딩 응답 예시와 맞는 여행 유형 데이터를 둔다.
--   - 방명록(GUESTBOOK / ROAD_GUESTBOOK)과 GPS 는 데이터가 있어야 하므로 채운다.
--   - 좌표는 전부 제주도 기준. mx = 경도(longitude), my = 위도(latitude).
-- =====================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE `PICTURE_WITH_CHARACTER`;
TRUNCATE TABLE `TRAVEL_ENDING_CONTENT`;
TRUNCATE TABLE `ACQUIRED_AR_CHARACTER`;
TRUNCATE TABLE `AR_CHARACTER`;
TRUNCATE TABLE `ROAD_GUESTBOOK`;
TRUNCATE TABLE `GUESTBOOK`;
TRUNCATE TABLE `TREASURE_MISSION_PROGRESS`;
TRUNCATE TABLE `TREASURE_MISSION`;
TRUNCATE TABLE `COOPERATIVE_ROLE_PROGRESS`;
TRUNCATE TABLE `COOPERATIVE_MISSION_PARTICIPANT`;
TRUNCATE TABLE `COOPERATIVE_ROLE_CARD`;
TRUNCATE TABLE `COOPERATIVE_MISSION_PROGRESS`;
TRUNCATE TABLE `COOPERATIVE_MISSION`;
TRUNCATE TABLE `CULTURE_MISSION_PROGRESS`;
TRUNCATE TABLE `CULTURE_MISSION`;
TRUNCATE TABLE `GPS`;
TRUNCATE TABLE `VISITED_LOCATION`;
TRUNCATE TABLE `MISSION`;
TRUNCATE TABLE `LOCATION`;
TRUNCATE TABLE `STEP_COUNT`;
TRUNCATE TABLE `USER_SETTING`;
TRUNCATE TABLE `USER`;
TRUNCATE TABLE `USER_TRAVEL_STYLE`;

SET FOREIGN_KEY_CHECKS = 1;


-- ---------------------------------------------------------------------
-- USER_TRAVEL_STYLE : 여행 유형 마스터
-- ---------------------------------------------------------------------

INSERT INTO `USER_TRAVEL_STYLE` (`id`, `user_type`, `type_description`, `hashtags`)
VALUES
    (1, '새로운 순간을 담는 기록 탐험가',
     '새로운 장소를 발견하고 사진과 포토스팟으로 순간을 남기는 걸 좋아하는 타입이에요.',
     '["#인생사진", "#로컬 탐방", "#자연", "#혼자 여행"]'),
    (2, '동네 깊숙이 걷는 로컬 탐험가',
     '유명한 관광지보다 골목, 시장, 작은 카페처럼 현지의 분위기가 느껴지는 장소를 좋아하는 타입이에요.',
     '["#로컬 탐방", "#골목 산책", "#시장 구경", "#느린 여행"]'),
    (3, '바람 따라 움직이는 자연 산책가',
     '오름과 숲길, 바다처럼 자연 속에서 천천히 걷고 쉬는 시간을 좋아하는 타입이에요.',
     '["#자연", "#오름", "#바다", "#걷기 여행"]');


-- ---------------------------------------------------------------------
-- USER : id=1 은 나, id=2~6 은 협동 미션 팀원
-- ---------------------------------------------------------------------

INSERT INTO `USER`
    (`id`, `expectation`, `transportation`, `travel_style`, `user_travel_style_id`, `ar_character_id`, `nickname`, `point`)
VALUES
    (1, '["PHOTO", "LOCAL", "NATURE"]', '["WALK", "BUS"]',  '["RIGHT_HERE", "NEAR_AROUND"]',       1, NULL, '몽글몽글파도', 1200),
    (2, '["CAFE", "WALKING"]',          '["CAR"]',          '["NEAR_DESTINATION"]',                2, NULL, '한라봉주스',   300),
    (3, '["NATURE", "CULTURE"]',        '["WALK"]',         '["RIGHT_HERE"]',                      3, NULL, '오름러버',     450),
    (4, '["PHOTO", "CAFE"]',            '["BICYCLE"]',      '["NEAR_AROUND"]',                     1, NULL, '바다필름',     0),
    (5, '["LOCAL", "CULTURE"]',         '["BUS", "WALK"]',  '["NEAR_AROUND", "NEAR_DESTINATION"]',  2, NULL, '돌담산책',    780),
    (6, '["WALKING", "NATURE"]',        '["CAR", "WALK"]',  '["RIGHT_HERE"]',                      3, NULL, '귤빛노을',     150);


-- ---------------------------------------------------------------------
-- USER_SETTING : 사용자 1명당 1행
-- ---------------------------------------------------------------------

INSERT INTO `USER_SETTING`
    (`id`, `user_id`, `push_notification`, `near_mission_notification`)
VALUES
    (1, 1, TRUE,  TRUE),
    (2, 2, TRUE,  TRUE),
    (3, 3, TRUE, TRUE),
    (4, 4, TRUE,  TRUE),
    (5, 5, TRUE,  TRUE),
    (6, 6, TRUE, TRUE);


-- ---------------------------------------------------------------------
-- STEP_COUNT : 데이터 없음 (걸음 수는 앱에서 기록)
-- ---------------------------------------------------------------------


-- ---------------------------------------------------------------------
-- LOCATION : 제주도 장소 10곳
-- ---------------------------------------------------------------------

INSERT INTO `LOCATION`
    (`id`, `content_id`, `location_title`, `location_address`, `location_category`, `radius`, `mx`, `my`)
VALUES
    (1,  126508, '성산일출봉',     '제주특별자치도 서귀포시 성산읍 일출로 284-12',   '자연',     300, 126.9410, 33.4580),
    (2,  126465, '만장굴',         '제주특별자치도 제주시 구좌읍 만장굴길 182',      '자연',     250, 126.7714, 33.5285),
    (3,  126273, '협재해수욕장',   '제주특별자치도 제주시 한림읍 한림로 329-10',     '해변',     400, 126.2396, 33.3940),
    (4,  126445, '천지연폭포',     '제주특별자치도 서귀포시 남성중로 2-15',          '자연',     200, 126.5540, 33.2465),
    (5,  126280, '우도',           '제주특별자치도 제주시 우도면 우도해안길',        '섬',       800, 126.9540, 33.5060),
    (6,  2493296, '카멜리아힐',    '제주특별자치도 서귀포시 안덕면 병악로 166',      '테마파크', 350, 126.3690, 33.2900),
    (7,  126454, '한라산 어리목',  '제주특별자치도 제주시 해안동 1100로 2070-61',    '등산로',   500, 126.4930, 33.3860),
    (8,  126437, '쇠소깍',         '제주특별자치도 서귀포시 하효동 쇠소깍로 104',    '계곡',     250, 126.6270, 33.2540),
    (9,  126295, '제주동문시장',   '제주특별자치도 제주시 관덕로14길 20',            '전통시장', 200, 126.5270, 33.5120),
    (10, 2686931, '한담해안산책로','제주특별자치도 제주시 애월읍 애월리 2530',       '산책로',   300, 126.3760, 33.4620);


-- ---------------------------------------------------------------------
-- MISSION : 10개 (CULTURE 4 / COOPERATIVE 3 / TREASURE 3)
-- reward_detail : {ar_character_id, point, coupon_location, coupon_price}
-- step_detail   : [{step, step_title, description}]
-- ---------------------------------------------------------------------

INSERT INTO `MISSION`
    (`id`, `mission_type`, `mission_title`, `description`, `location_id`, `reward_detail`, `step_detail`)
VALUES
    (1, 'CULTURE', '성산일출봉 화산 이야기',
     '성산일출봉의 형성 과정과 주변 마을 이야기를 퀴즈로 풀어보는 미션입니다.',
     1,
     '{"ar_character_id": 1, "point": 100, "coupon_location": "성산 해맞이 카페", "coupon_price": 2000}',
     '[{"step": 1, "step_title": "장소 도착", "description": "성산일출봉 매표소 앞에서 위치를 인증하세요."}, {"step": 2, "step_title": "퀴즈 풀기", "description": "화산 지형 퀴즈 5문제를 풀어보세요."}, {"step": 3, "step_title": "방명록 남기기", "description": "오늘의 기록을 방명록에 남기면 미션이 끝납니다."}]'),

    (2, 'CULTURE', '만장굴 용암동굴 탐험',
     '세계자연유산 만장굴의 용암 동굴 지형을 배우는 문화 퀴즈 미션입니다.',
     2,
     '{"ar_character_id": 2, "point": 100, "coupon_location": "구좌 당근카페", "coupon_price": 2000}',
     '[{"step": 1, "step_title": "장소 도착", "description": "만장굴 입구에서 위치를 인증하세요."}, {"step": 2, "step_title": "퀴즈 풀기", "description": "용암 동굴 퀴즈 5문제를 풀어보세요."}, {"step": 3, "step_title": "방명록 남기기", "description": "동굴에서 느낀 점을 방명록에 남겨보세요."}]'),

    (3, 'CULTURE', '우도 해녀 문화 배우기',
     '우도 해녀의 삶과 물질 문화를 알아보는 문화 미션입니다.',
     5,
     '{"ar_character_id": 3, "point": 150, "coupon_location": "우도 땅콩아이스크림", "coupon_price": 3000}',
     '[{"step": 1, "step_title": "장소 도착", "description": "우도 하우목동항에서 위치를 인증하세요."}, {"step": 2, "step_title": "퀴즈 풀기", "description": "해녀 문화 퀴즈 5문제를 풀어보세요."}, {"step": 3, "step_title": "방명록 남기기", "description": "우도에서의 하루를 방명록에 남겨보세요."}]'),

    (4, 'CULTURE', '동문시장 제주 먹거리 탐구',
     '제주동문시장의 향토 먹거리와 시장 문화를 알아보는 미션입니다.',
     9,
     '{"ar_character_id": 4, "point": 100, "coupon_location": "동문시장 오메기떡", "coupon_price": 3000}',
     '[{"step": 1, "step_title": "장소 도착", "description": "동문시장 8번 게이트에서 위치를 인증하세요."}, {"step": 2, "step_title": "퀴즈 풀기", "description": "제주 향토 음식 퀴즈 5문제를 풀어보세요."}, {"step": 3, "step_title": "방명록 남기기", "description": "먹거리 사진과 함께 방명록을 남겨보세요."}]'),

    (5, 'COOPERATIVE', '협재 바다 역할 미션',
     '팀원이 각자 역할 카드를 받아 협재해수욕장에서 인증 사진을 모으는 협동 미션입니다.',
     3,
     '{"ar_character_id": 5, "point": 200, "coupon_location": "협재 바다뷰 카페", "coupon_price": 4000}',
     '[{"step": 1, "step_title": "방 만들기", "description": "방장이 방을 만들고 초대 URL을 공유합니다."}, {"step": 2, "step_title": "역할 배정", "description": "참여자가 역할 카드를 하나씩 고릅니다."}, {"step": 3, "step_title": "인증 사진", "description": "각자 역할에 맞는 사진을 찍어 올립니다."}, {"step": 4, "step_title": "미션 완료", "description": "모든 역할이 완료되면 보상이 지급됩니다."}]'),

    (6, 'COOPERATIVE', '카멜리아힐 컬러 헌팅',
     '팀원이 서로 다른 색을 맡아 카멜리아힐에서 사진으로 색을 모으는 협동 미션입니다.',
     6,
     '{"ar_character_id": 6, "point": 200, "coupon_location": "카멜리아힐 가든카페", "coupon_price": 4000}',
     '[{"step": 1, "step_title": "방 만들기", "description": "방장이 방을 만들고 초대 URL을 공유합니다."}, {"step": 2, "step_title": "역할 배정", "description": "참여자가 담당할 색 카드를 고릅니다."}, {"step": 3, "step_title": "인증 사진", "description": "맡은 색이 담긴 사진을 찍어 올립니다."}, {"step": 4, "step_title": "미션 완료", "description": "모든 색이 모이면 보상이 지급됩니다."}]'),

    (7, 'COOPERATIVE', '한담해안 노을 릴레이',
     '한담해안산책로를 구간별로 나눠 걸으며 팀원이 노을 사진을 이어 찍는 협동 미션입니다.',
     10,
     '{"ar_character_id": 7, "point": 250, "coupon_location": "애월 한담 베이커리", "coupon_price": 5000}',
     '[{"step": 1, "step_title": "방 만들기", "description": "방장이 방을 만들고 초대 URL을 공유합니다."}, {"step": 2, "step_title": "구간 배정", "description": "참여자가 담당 구간 카드를 고릅니다."}, {"step": 3, "step_title": "노을 사진", "description": "담당 구간에서 노을 사진을 찍어 올립니다."}, {"step": 4, "step_title": "미션 완료", "description": "모든 구간이 채워지면 보상이 지급됩니다."}]'),

    (8, 'TREASURE', '천지연 숨은 보물 찾기',
     '천지연폭포 산책로에 숨어 있는 AR 보물을 찾아 모으는 미션입니다.',
     4,
     '{"ar_character_id": 8, "point": 150, "coupon_location": "서귀포 올레시장 분식", "coupon_price": 3000}',
     '[{"step": 1, "step_title": "장소 도착", "description": "천지연폭포 입구에서 위치를 인증하세요."}, {"step": 2, "step_title": "보물 찾기", "description": "산책로에 숨은 보물 5개를 찾아보세요."}, {"step": 3, "step_title": "AR 사진", "description": "찾은 캐릭터와 사진을 찍어 저장하세요."}]'),

    (9, 'TREASURE', '쇠소깍 물빛 보물 찾기',
     '쇠소깍 계곡 주변에 흩어진 AR 보물을 찾아 모으는 미션입니다.',
     8,
     '{"ar_character_id": 9, "point": 150, "coupon_location": "하효 감귤빵집", "coupon_price": 3000}',
     '[{"step": 1, "step_title": "장소 도착", "description": "쇠소깍 주차장에서 위치를 인증하세요."}, {"step": 2, "step_title": "보물 찾기", "description": "계곡 주변에 숨은 보물 4개를 찾아보세요."}, {"step": 3, "step_title": "AR 사진", "description": "찾은 캐릭터와 사진을 찍어 저장하세요."}]'),

    (10, 'TREASURE', '어리목 숲길 보물 찾기',
     '한라산 어리목 탐방로 초입에서 AR 보물을 찾아 모으는 미션입니다.',
     7,
     '{"ar_character_id": 10, "point": 200, "coupon_location": "1100고지 휴게소", "coupon_price": 4000}',
     '[{"step": 1, "step_title": "장소 도착", "description": "어리목 탐방안내소에서 위치를 인증하세요."}, {"step": 2, "step_title": "보물 찾기", "description": "숲길에 숨은 보물 6개를 찾아보세요."}, {"step": 3, "step_title": "AR 사진", "description": "찾은 캐릭터와 사진을 찍어 저장하세요."}]');


-- ---------------------------------------------------------------------
-- CULTURE_MISSION : 퀴즈 상세
-- ---------------------------------------------------------------------

INSERT INTO `CULTURE_MISSION` (`mission_id`, `quiz_total_count`, `quiz_detail`)
VALUES
    (1, 5, '[
        {"quiz_index": 1, "img_url": null, "question": "성산일출봉은 어떤 분출로 만들어진 지형일까요?", "options": ["수성화산 분출", "용암 분출", "빙하 침식", "산호 융기"], "answer": "수성화산 분출", "hint": "바닷물과 마그마가 만났어요.", "explanation": "성산일출봉은 얕은 바다에서 일어난 수성화산 분출로 만들어진 응회구입니다."},
        {"quiz_index": 2, "img_url": null, "question": "성산일출봉이 유네스코에 등재된 해는?", "options": ["2005년", "2007년", "2010년", "2012년"], "answer": "2007년", "hint": "제주 화산섬과 용암동굴이 함께 등재됐어요.", "explanation": "2007년 제주 화산섬과 용암동굴의 일부로 세계자연유산에 등재되었습니다."},
        {"quiz_index": 3, "img_url": null, "question": "성산일출봉의 높이는 약 몇 미터일까요?", "options": ["82m", "182m", "282m", "382m"], "answer": "182m", "hint": "200m가 되지 않아요.", "explanation": "성산일출봉의 높이는 약 182m입니다."},
        {"quiz_index": 4, "img_url": null, "question": "성산일출봉 정상에 있는 넓은 지형을 무엇이라 부를까요?", "options": ["분화구", "칼데라", "주상절리", "곶자왈"], "answer": "분화구", "hint": "화산이 폭발한 자리에 남아요.", "explanation": "정상에는 지름 약 600m의 커다란 분화구가 남아 있습니다."},
        {"quiz_index": 5, "img_url": null, "question": "성산일출봉 앞바다에서 물질하던 사람들을 뭐라고 부를까요?", "options": ["해녀", "어부", "뱃사공", "잠수부"], "answer": "해녀", "hint": "제주를 대표하는 여성 잠수인이에요.", "explanation": "성산 지역은 해녀 물질이 활발했던 곳으로 해녀 물질 시연도 열립니다."}
    ]'),

    (2, 5, '[
        {"quiz_index": 1, "img_url": null, "question": "만장굴은 어떤 종류의 동굴일까요?", "options": ["용암동굴", "석회동굴", "해식동굴", "빙하동굴"], "answer": "용암동굴", "hint": "흐르던 용암이 만든 길이에요.", "explanation": "만장굴은 흐르던 용암이 굳으면서 속이 비어 만들어진 용암동굴입니다."},
        {"quiz_index": 2, "img_url": null, "question": "만장굴의 총 길이는 약 몇 킬로미터일까요?", "options": ["약 2km", "약 5km", "약 7.4km", "약 12km"], "answer": "약 7.4km", "hint": "10km는 넘지 않아요.", "explanation": "만장굴의 총 길이는 약 7.4km이며 일부 구간만 공개되어 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "만장굴 공개 구간 끝에 있는 유명한 구조물은?", "options": ["용암석주", "종유석", "석순", "주상절리"], "answer": "용암석주", "hint": "높이 7.6m로 세계 최대급이에요.", "explanation": "공개 구간 끝에는 높이 약 7.6m의 용암석주가 있습니다."},
        {"quiz_index": 4, "img_url": null, "question": "만장굴 안의 연중 온도는 대략 어느 정도일까요?", "options": ["섭씨 1~5도", "섭씨 11~21도", "섭씨 25~30도", "섭씨 30도 이상"], "answer": "섭씨 11~21도", "hint": "여름에 시원하고 겨울에 덜 추워요.", "explanation": "만장굴 내부는 연중 11~21도를 유지해 여름에 특히 시원합니다."},
        {"quiz_index": 5, "img_url": null, "question": "만장굴이 속한 용암동굴계의 이름은?", "options": ["거문오름 용암동굴계", "한라산 동굴계", "성산 동굴계", "산방산 동굴계"], "answer": "거문오름 용암동굴계", "hint": "오름 이름이 붙어 있어요.", "explanation": "만장굴은 거문오름 용암동굴계에 속하며 세계자연유산으로 지정되었습니다."}
    ]'),

    (3, 5, '[
        {"quiz_index": 1, "img_url": null, "question": "해녀가 물질할 때 사용하는 부표를 무엇이라 부를까요?", "options": ["테왁", "빗창", "망사리", "물허벅"], "answer": "테왁", "hint": "물 위에 떠 있는 둥근 도구예요.", "explanation": "테왁은 해녀가 물 위에서 몸을 의지하는 부표로, 아래에 망사리를 답니다."},
        {"quiz_index": 2, "img_url": null, "question": "해녀가 숨을 참았다 내쉴 때 내는 소리를 무엇이라 할까요?", "options": ["숨비소리", "물비소리", "바당소리", "허벅소리"], "answer": "숨비소리", "hint": "휘파람 같은 소리예요.", "explanation": "물 밖으로 나오며 참았던 숨을 내쉬는 소리를 숨비소리라고 합니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 해녀문화가 유네스코 인류무형문화유산이 된 해는?", "options": ["2012년", "2014년", "2016년", "2018년"], "answer": "2016년", "hint": "2010년대 후반이에요.", "explanation": "제주 해녀문화는 2016년 유네스코 인류무형문화유산으로 등재되었습니다."},
        {"quiz_index": 4, "img_url": null, "question": "해녀들이 물질 전후에 몸을 녹이던 공간을 무엇이라 부를까요?", "options": ["불턱", "물턱", "돌턱", "바당집"], "answer": "불턱", "hint": "불을 피우던 곳이에요.", "explanation": "불턱은 해녀들이 불을 피워 몸을 녹이고 물질을 준비하던 돌담 공간입니다."},
        {"quiz_index": 5, "img_url": null, "question": "해녀의 등급 중 가장 깊이 잠수하는 등급은?", "options": ["상군", "중군", "하군", "초군"], "answer": "상군", "hint": "가장 높은 등급이에요.", "explanation": "해녀는 상군, 중군, 하군으로 나뉘며 상군이 가장 깊은 곳에서 물질합니다."}
    ]'),

    (4, 5, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 전통 떡으로 팥고물을 묻힌 것은?", "options": ["오메기떡", "빙떡", "상외떡", "돌래떡"], "answer": "오메기떡", "hint": "동문시장 대표 간식이에요.", "explanation": "오메기떡은 차조로 만든 제주 전통 떡으로 팥고물을 입혀 먹습니다."},
        {"quiz_index": 2, "img_url": null, "question": "메밀 전병에 무채를 넣어 말아 먹는 제주 음식은?", "options": ["빙떡", "몸국", "고기국수", "갈치조림"], "answer": "빙떡", "hint": "얇게 부친 메밀 전병이에요.", "explanation": "빙떡은 메밀 전병에 삶은 무채를 넣어 돌돌 말아 먹는 제주 향토 음식입니다."},
        {"quiz_index": 3, "img_url": null, "question": "돼지 육수에 모자반을 넣어 끓인 제주 국은?", "options": ["몸국", "접짝뼈국", "각재기국", "성게국"], "answer": "몸국", "hint": "모자반을 제주말로 몸이라 해요.", "explanation": "몸국은 돼지 육수에 모자반을 넣고 끓인 제주 잔치 음식입니다."},
        {"quiz_index": 4, "img_url": null, "question": "제주동문시장이 문을 연 시기는 대략 언제일까요?", "options": ["1900년대 초", "1945년 광복 직후", "1970년대", "1990년대"], "answer": "1945년 광복 직후", "hint": "광복과 함께 형성됐어요.", "explanation": "동문시장은 1945년 광복 직후 형성된 제주에서 가장 오래된 상설시장입니다."},
        {"quiz_index": 5, "img_url": null, "question": "제주에서 옥돔을 말려 구워 먹는 방식의 이름은?", "options": ["옥돔구이", "옥돔회", "옥돔탕", "옥돔찜"], "answer": "옥돔구이", "hint": "말린 뒤 굽습니다.", "explanation": "제주에서는 옥돔을 반건조해 구워 먹는 옥돔구이가 대표적인 밥상 반찬입니다."}
    ]');


-- ---------------------------------------------------------------------
-- COOPERATIVE_MISSION : 역할 개수
-- (역할 카드는 방(progress)이 만들어질 때 생성되므로 여기서는 비워 둔다)
-- ---------------------------------------------------------------------

INSERT INTO `COOPERATIVE_MISSION` (`mission_id`, `role_total_count`)
VALUES
    (5, 4),
    (6, 3),
    (7, 5);


-- ---------------------------------------------------------------------
-- TREASURE_MISSION : 보물 좌표 (전부 해당 장소 반경 안)
-- item_detail : [{index, mx, my, radius}]
-- ---------------------------------------------------------------------

INSERT INTO `TREASURE_MISSION` (`mission_id`, `item_total_count`, `item_detail`)
VALUES
    (8, 5, '[
        {"index": 1, "mx": 126.5535, "my": 33.2470, "radius": 25},
        {"index": 2, "mx": 126.5544, "my": 33.2462, "radius": 25},
        {"index": 3, "mx": 126.5551, "my": 33.2468, "radius": 30},
        {"index": 4, "mx": 126.5528, "my": 33.2459, "radius": 30},
        {"index": 5, "mx": 126.5547, "my": 33.2455, "radius": 25}
    ]'),

    (9, 4, '[
        {"index": 1, "mx": 126.6265, "my": 33.2546, "radius": 25},
        {"index": 2, "mx": 126.6274, "my": 33.2538, "radius": 25},
        {"index": 3, "mx": 126.6281, "my": 33.2549, "radius": 30},
        {"index": 4, "mx": 126.6259, "my": 33.2533, "radius": 30}
    ]'),

    (10, 6, '[
        {"index": 1, "mx": 126.4925, "my": 33.3865, "radius": 30},
        {"index": 2, "mx": 126.4936, "my": 33.3858, "radius": 30},
        {"index": 3, "mx": 126.4941, "my": 33.3869, "radius": 35},
        {"index": 4, "mx": 126.4918, "my": 33.3852, "radius": 35},
        {"index": 5, "mx": 126.4947, "my": 33.3847, "radius": 30},
        {"index": 6, "mx": 126.4912, "my": 33.3871, "radius": 30}
    ]');


-- ---------------------------------------------------------------------
-- AR_CHARACTER : 제주 테마 캐릭터 + 기본 캐릭터
-- ---------------------------------------------------------------------

INSERT INTO `AR_CHARACTER`
    (`id`, `character_name`, `character_description`, `acquire_condition`, `character_img_url`, `hashtags`)
VALUES
    (1,  '자청비 모티브 탐험가',
     '제주의 오래된 이야기에서 온 씨앗과 여행 지도를 들고 새로운 순간을 발견하는 기록 탐험가입니다.',
     '온보딩에서 기록형 여행 스타일을 선택하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/jacheongbi-explorer.png',
     '["#인생사진", "#로컬 탐방", "#자연", "#혼자 여행"]'),
    (2,  '동굴빛 용암이',
     '만장굴의 검은 용암길 사이에서 반짝이는 빛을 따라다니는 작은 동굴 안내자입니다.',
     '만장굴 문화 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/yongami.png',
     '["#용암동굴", "#만장굴", "#지질"]'),
    (3,  '숨비 바다친구',
     '우도 바다의 숨비소리를 따라 여행자에게 바다 이야기를 들려주는 해녀 친구입니다.',
     '우도 해녀 문화 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/sumbi.png',
     '["#해녀", "#우도", "#제주바다"]'),
    (4,  '오메기 시장요정',
     '동문시장 골목에서 따뜻한 간식 냄새를 따라 나타나는 먹거리 요정입니다.',
     '동문시장 문화 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/omegi.png',
     '["#먹거리", "#동문시장", "#제주간식"]'),
    (5,  '협재 파도지기',
     '협재 바다의 에메랄드빛 파도를 지키며 팀의 사진 미션을 응원하는 캐릭터입니다.',
     '협재 협동 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/hyeopjae-wave.png',
     '["#바다", "#협재", "#협동"]'),
    (6,  '동백 정원사',
     '카멜리아힐의 동백꽃 사이를 돌보며 여행자의 색깔 찾기를 도와주는 정원사입니다.',
     '카멜리아힐 협동 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/dongbaek.png',
     '["#동백", "#꽃", "#카멜리아힐"]'),
    (7,  '노을 조랑이',
     '한담해안의 노을빛을 등에 얹고 천천히 산책하는 제주 조랑말 친구입니다.',
     '한담해안 협동 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/noeul-jorang.png',
     '["#조랑말", "#노을", "#애월"]'),
    (8,  '천지연 물방울',
     '천지연폭포 물보라에서 톡 튀어나와 시원한 길을 알려주는 물방울 캐릭터입니다.',
     '천지연 보물 찾기 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/mulbangul.png',
     '["#폭포", "#천지연", "#물"]'),
    (9,  '쇠소깍 물빛이',
     '쇠소깍의 깊은 물빛 속에서 장난스럽게 보물 위치를 알려주는 계곡 친구입니다.',
     '쇠소깍 보물 찾기 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/soesokkak.png',
     '["#계곡", "#쇠소깍", "#물빛"]'),
    (10, '어리목 숲노루',
     '한라산 어리목 숲길에서 조용히 길을 안내하는 수줍은 제주 노루 친구입니다.',
     '어리목 보물 찾기 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/noru.png',
     '["#노루", "#한라산", "#숲길"]'),
    (11, '돌멍이',
     '처음 제주 여행을 시작한 사용자 곁을 지켜주는 귀여운 기본 캐릭터입니다.',
     '온보딩에서 나중에 할게요를 선택하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/dolmungii.png',
     '["#기본캐릭터", "#돌멍이", "#제주친구"]');

UPDATE `USER`
SET `ar_character_id` = CASE `id`
    WHEN 1 THEN 1
    WHEN 2 THEN 2
    WHEN 3 THEN 3
    WHEN 4 THEN 1
    WHEN 5 THEN 2
    WHEN 6 THEN 3
END
WHERE `id` IN (1, 2, 3, 4, 5, 6);


-- ---------------------------------------------------------------------
-- GPS : 사용자 1의 제주 이동 기록 10건
-- ---------------------------------------------------------------------

INSERT INTO `GPS` (`id`, `user_id`, `mx`, `my`, `saved_at`)
VALUES
    (1,  1, 126.4930, 33.5070, '2026-08-18T09:10:00'),
    (2,  1, 126.5270, 33.5120, '2026-08-18T11:35:00'),
    (3,  1, 126.7714, 33.5285, '2026-08-18T15:05:00'),
    (4,  1, 126.9410, 33.4580, '2026-08-19T07:45:00'),
    (5,  1, 126.9540, 33.5060, '2026-08-19T12:20:00'),
    (6,  1, 126.6270, 33.2540, '2026-08-20T10:15:00'),
    (7,  1, 126.5540, 33.2465, '2026-08-20T14:40:00'),
    (8,  1, 126.3690, 33.2900, '2026-08-21T11:05:00'),
    (9,  1, 126.2396, 33.3940, '2026-08-21T16:30:00'),
    (10, 1, 126.3760, 33.4620, '2026-08-22T18:50:00');


-- ---------------------------------------------------------------------
-- GUESTBOOK : 10건 (사용자 1이 8건, 다른 사용자 2건)
-- id=10 은 소프트 삭제된 행 (deleted_at 필터 테스트용)
-- ---------------------------------------------------------------------

INSERT INTO `GUESTBOOK`
    (`id`, `user_id`, `location_id`, `visited_at`, `content_img_url`, `content_writing`,
     `content_audio_url`, `content_weather`, `content_color_code`, `saved_at`, `mission_id`, `deleted_at`)
VALUES
    (1, 1, 9,  '2026-08-18',
     '["https://cdn.jamkkan-jeju.dev/guestbook/1-1.jpg"]',
     '동문시장에서 오메기떡 한 봉지 사서 걸었다. 시장 냄새가 여행 시작 같았다.',
     NULL, 'SUNNY', '#FFD8A8', '2026-08-18T12:10:00', 4, NULL),

    (2, 1, 2,  '2026-08-18',
     '["https://cdn.jamkkan-jeju.dev/guestbook/2-1.jpg", "https://cdn.jamkkan-jeju.dev/guestbook/2-2.jpg"]',
     '만장굴 안이 생각보다 훨씬 서늘했다. 용암석주 앞에서 한참 서 있었다.',
     '["https://cdn.jamkkan-jeju.dev/guestbook/2-audio.m4a"]', 'CLOUDY', '#A5D8FF', '2026-08-18T16:00:00', 2, NULL),

    (3, 1, 1,  '2026-08-19',
     '["https://cdn.jamkkan-jeju.dev/guestbook/3-1.jpg"]',
     '새벽에 성산일출봉 올라갔다. 계단은 힘든데 정상에서 본 바다가 다 갚아줬다.',
     NULL, 'SUNNY', '#FFC9C9', '2026-08-19T08:30:00', 1, NULL),

    (4, 1, 5,  '2026-08-19',
     '["https://cdn.jamkkan-jeju.dev/guestbook/4-1.jpg"]',
     '우도 해안길을 천천히 돌았다. 해녀 삼춘이 물질하는 걸 멀리서 봤다.',
     NULL, 'WINDY', '#B2F2BB', '2026-08-19T13:15:00', 3, NULL),

    (5, 1, 8,  '2026-08-20',
     NULL,
     '쇠소깍 물빛이 진짜 검은 초록이었다. 카약 타는 사람들 구경만 하다 왔다.',
     NULL, 'CLOUDY', '#D0BFFF', '2026-08-20T10:50:00', NULL, NULL),

    (6, 1, 4,  '2026-08-20',
     '["https://cdn.jamkkan-jeju.dev/guestbook/6-1.jpg"]',
     '천지연폭포 물소리가 커서 아무 말도 안 하고 서 있었다. 여기 보물 다 찾았다.',
     '["https://cdn.jamkkan-jeju.dev/guestbook/6-audio.m4a"]', 'RAIN', '#99E9F2', '2026-08-20T15:20:00', 8, NULL),

    (7, 1, 6,  '2026-08-21',
     '["https://cdn.jamkkan-jeju.dev/guestbook/7-1.jpg", "https://cdn.jamkkan-jeju.dev/guestbook/7-2.jpg"]',
     '카멜리아힐은 사진 찍을 데가 너무 많았다. 색깔별로 담느라 오래 걸렸다.',
     NULL, 'SUNNY', '#FFDEEB', '2026-08-21T12:00:00', 6, NULL),

    (8, 1, 3,  '2026-08-21',
     '["https://cdn.jamkkan-jeju.dev/guestbook/8-1.jpg"]',
     '협재 바다 색이 비현실적이었다. 발만 담그려다 결국 다 젖었다.',
     NULL, 'SUNNY', '#A5D8FF', '2026-08-21T17:05:00', 5, NULL),

    (9, 2, 10, '2026-08-22',
     '["https://cdn.jamkkan-jeju.dev/guestbook/9-1.jpg"]',
     '한담 산책로에서 노을 봤다. 커피 들고 걷기 딱 좋았다.',
     NULL, 'SUNNY', '#FFEC99', '2026-08-22T19:10:00', NULL, NULL),

    (10, 3, 7, '2026-08-22',
     NULL,
     '어리목 초입만 걷고 내려왔다. 다음엔 정상까지 가보고 싶다.',
     NULL, 'CLOUDY', '#C3FAE8', '2026-08-22T11:40:00', NULL, '2026-08-22T20:00:00');


-- ---------------------------------------------------------------------
-- ROAD_GUESTBOOK : 길 위의 방명록 5건 (사용자 1)
-- location_id 가 NULL 인 행은 등록된 장소가 아닌 곳
-- ---------------------------------------------------------------------

INSERT INTO `ROAD_GUESTBOOK`
    (`id`, `user_id`, `location_id`, `location_alias`, `visited_at`, `content_img_url`, `content_writing`,
     `content_audio_url`, `content_weather`, `content_color_code`, `mx`, `my`, `saved_at`, `deleted_at`)
VALUES
    (1, 1, NULL, '이름 모를 돌담길',      '2026-08-18',
     '["https://cdn.jamkkan-jeju.dev/road/1-1.jpg"]',
     '버스 놓쳐서 걷다가 만난 돌담길. 오히려 여기가 제일 기억에 남는다.',
     NULL, 'SUNNY',  '#FFE8CC', 126.5312, 33.5001, '2026-08-18T10:25:00', NULL),

    (2, 1, NULL, '구좌 당근밭 앞',        '2026-08-18',
     NULL,
     '당근밭 사이 길이 끝없이 이어졌다. 바람 소리만 들렸다.',
     '["https://cdn.jamkkan-jeju.dev/road/2-audio.m4a"]', 'WINDY', '#FFD8A8', 126.7550, 33.5410, '2026-08-18T14:10:00', NULL),

    (3, 1, 5,    '우도 하고수동 가는 길',  '2026-08-19',
     '["https://cdn.jamkkan-jeju.dev/road/3-1.jpg"]',
     '자전거 빌려서 우도 한 바퀴. 오르막에서 후회했지만 내리막에서 다 잊었다.',
     NULL, 'SUNNY',  '#A5D8FF', 126.9612, 33.5104, '2026-08-19T14:35:00', NULL),

    (4, 1, NULL, '표선 가는 해안도로',    '2026-08-20',
     '["https://cdn.jamkkan-jeju.dev/road/4-1.jpg"]',
     '창문 열고 달렸다. 바다 냄새가 계속 따라왔다.',
     NULL, 'CLOUDY', '#D0BFFF', 126.8320, 33.3260, '2026-08-20T17:45:00', NULL),

    (5, 1, 10,   '한담 벤치 두 번째 자리', '2026-08-22',
     '["https://cdn.jamkkan-jeju.dev/road/5-1.jpg", "https://cdn.jamkkan-jeju.dev/road/5-2.jpg"]',
     '노을 지는 거 끝까지 보고 왔다. 여행 마지막 밤이라 더 오래 앉아 있었다.',
     NULL, 'SUNNY',  '#FFC9C9', 126.3771, 33.4615, '2026-08-22T19:40:00', NULL);


-- ---------------------------------------------------------------------
-- 비워 두는 테이블 (사용자 진행 상태 - API 호출로 생성됨)
--   STEP_COUNT
--   VISITED_LOCATION
--   CULTURE_MISSION_PROGRESS
--   COOPERATIVE_MISSION_PROGRESS
--   COOPERATIVE_ROLE_CARD
--   COOPERATIVE_MISSION_PARTICIPANT
--   COOPERATIVE_ROLE_PROGRESS
--   TREASURE_MISSION_PROGRESS
--   ACQUIRED_AR_CHARACTER
--   TRAVEL_ENDING_CONTENT
--   PICTURE_WITH_CHARACTER
-- ---------------------------------------------------------------------
