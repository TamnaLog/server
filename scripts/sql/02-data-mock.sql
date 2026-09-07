-- =====================================================================
-- 잠깐, 제주 - 목업 데이터
-- 선행: scripts/sql/01-schema.sql
--
-- 실행 예시)
--   mysql -h 127.0.0.1 -u tour -p tour < scripts/sql/02-data-mock.sql
--
-- 데이터 방침
--   - 사용자: id=1 이 "나"(로그인 고정 사용자). id=2~6 은 협동 미션 팀원 5명.
--   - 하루 목표 걸음 수(USER.target_step)는 기본값 10000 이고 2명만 다른 값을 둔다.
--   - LOCATION 은 scripts/insert_location.py 로 별도 저장하며 이 파일에서는 변경하지 않는다.
--   - 나머지 콘텐츠 성격의 테이블(MISSION / *_MISSION / AR_CHARACTER)은 채운다.
--   - 홈 조회 예시 응답을 위해 사용자 1의 문화/협동/보물찾기 진행도를 각각 1건씩 둔다.
--   - USER_TRAVEL_STYLE 은 온보딩 응답 예시와 맞는 여행 유형 데이터를 둔다.
--   - 방명록(GUESTBOOK / ROAD_GUESTBOOK)과 GPS, 걸음 수(STEP_COUNT)는 데이터가 있어야 하므로 채운다.
--   - 좋아요(GUESTBOOK_LIKE / ROAD_GUESTBOOK_LIKE)는 개수가 방명록마다 다르게 보이도록
--     사용자마다 본인 글을 제외한 다른 사용자의 글에 좋아요를 누른다.
--     (본인 방명록에는 좋아요를 누를 수 없다)
--   - 여행 마무리 엽서(TRAVEL_ENDING_CONTENT)는 완성된 엽서 이미지 URL 만 갖는 테이블이라
--     사용자 1 의 엽서 2건만 둔다.
--   - 좌표는 전부 제주도 기준. mx = 경도(longitude), my = 위도(latitude).
-- =====================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE `PICTURE_WITH_CHARACTER`;
TRUNCATE TABLE `TRAVEL_ENDING_CONTENT`;
TRUNCATE TABLE `ACQUIRED_AR_CHARACTER`;
TRUNCATE TABLE `AR_CHARACTER`;
TRUNCATE TABLE `ROAD_GUESTBOOK_LIKE`;
TRUNCATE TABLE `ROAD_GUESTBOOK`;
TRUNCATE TABLE `GUESTBOOK_LIKE`;
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

-- access_token_hash 는 액세스 토큰 원문의 SHA-256 이다. (원문은 DB에 저장하지 않는다)
-- 목업 사용자의 토큰 원문은 'test-user-{id}-token' 이라고 가정하고 넣은 값이다.
-- 그래서 아래 헤더로 목업 사용자를 그대로 호출할 수 있다.
--     Authorization: Bearer test-user-1-token   -> 1번 사용자
--     Authorization: Bearer test-user-2-token   -> 2번 사용자 (이하 6번까지 동일)
INSERT INTO `USER`
    (`id`, `expectation`, `transportation`, `travel_style`, `user_travel_style_id`,
     `ar_character_id`, `nickname`, `point`, `target_step`, `access_token_hash`)
VALUES
    (1, '["PHOTO", "LOCAL", "NATURE"]', '["WALK", "BUS"]', '["RIGHT_HERE", "NEAR_AROUND"]', 1, NULL, '몽글몽글파도', 1200, 10000,
     '680aac6fc35fae2feece55508a4c21c2b49c69c292ad76a814b7742d7a08fddb'),

    (2, '["CAFE", "WALKING"]', '["CAR"]', '["NEAR_DESTINATION"]', 2, NULL, '한라봉주스', 300, 8000,
     'c1d8de760790698435231bef2ea0d71cee9b997502052bd1ca97cfd07620a9ff'),

    (3, '["NATURE", "CULTURE"]', '["WALK"]', '["RIGHT_HERE"]', 3, NULL, '오름러버', 450, 10000,
     'da05fa4b4bb194c93c0de926b0faa619e5fa1a1e2e1ef7f31f09df8e4936366e'),

    (4, '["PHOTO", "CAFE"]', '["BICYCLE"]', '["NEAR_AROUND"]', 1, NULL, '바다필름', 0, 10000,
     'e132a395928a9716062b43a418dbb5f7bafc3eeb1f6143f90929f852e05cb2ba'),

    (5, '["LOCAL", "CULTURE"]', '["BUS", "WALK"]', '["NEAR_AROUND", "NEAR_DESTINATION"]', 2, NULL, '돌담산책', 780, 12000,
     '80114cadbd96fcb6f060357fdad912c4120533a57bbab039d4e71560198d26a3'),

    (6, '["WALKING", "NATURE"]', '["CAR", "WALK"]', '["RIGHT_HERE"]', 3, NULL, '귤빛노을', 150, 10000,
     '522ff314a6bf385a26c8b9031bb0377e74bf5875821ed3dd9e74cf67daef00aa');


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
-- ---------------------------------------------------------------------
-- STEP_COUNT : 걸음 수 6건 (사용자 1 이 5일치, 사용자 2 가 1일치)
-- saved_at 은 저장 시각이 아니라 기록 대상 날짜의 KST 자정이다.
-- 사용자별 날짜당 한 행만 존재한다. (user_id + saved_at 유니크)
-- 목표 걸음 수는 기록이 아니라 사용자 설정값이라 USER.target_step 에 있다.
-- ---------------------------------------------------------------------

INSERT INTO `STEP_COUNT`
    (`id`, `user_id`, `saved_at`, `steps_count`)
VALUES
    (1, 1, '2026-08-18T00:00:00', 12480),
    (2, 1, '2026-08-19T00:00:00', 9037),
    (3, 1, '2026-08-20T00:00:00', 15220),
    (4, 1, '2026-08-21T00:00:00', 7415),
    (5, 1, '2026-08-22T00:00:00', 10863),

    (6, 2, '2026-08-22T00:00:00', 6120);
-- ---------------------------------------------------------------------


-- ---------------------------------------------------------------------
-- VISITED_LOCATION : 사용자별 일반 방명록 3건과 동일한 장소·방문 날짜 (총 18건)
-- ---------------------------------------------------------------------

INSERT INTO `VISITED_LOCATION`
    (`id`, `user_id`, `location_id`, `visited_at`)
VALUES
    (1, 1, 452, '2026-08-18T11:00:00'),
    (2, 1, 545, '2026-08-19T11:00:00'),
    (3, 1, 68, '2026-08-20T11:00:00'),
    (4, 2, 441, '2026-08-18T11:00:00'),
    (5, 2, 266, '2026-08-19T11:00:00'),
    (6, 2, 160, '2026-08-20T11:00:00'),
    (7, 3, 161, '2026-08-18T11:00:00'),
    (8, 3, 142, '2026-08-19T11:00:00'),
    (9, 3, 184, '2026-08-20T11:00:00'),
    (10, 4, 115, '2026-08-18T11:00:00'),
    (11, 4, 692, '2026-08-19T11:00:00'),
    (12, 4, 460, '2026-08-20T11:00:00'),
    (13, 5, 607, '2026-08-18T11:00:00'),
    (14, 5, 444, '2026-08-19T11:00:00'),
    (15, 5, 456, '2026-08-20T11:00:00'),
    (16, 6, 346, '2026-08-18T11:00:00'),
    (17, 6, 454, '2026-08-19T11:00:00'),
    (18, 6, 488, '2026-08-20T11:00:00');


-- ---------------------------------------------------------------------
-- MISSION : 미션 유형별 공통 데이터 3개 (CULTURE / COOPERATIVE / TREASURE)
-- step_detail   : [{step, step_title, description}]
-- ---------------------------------------------------------------------

INSERT INTO `MISSION`
    (`id`, `mission_type`, `mission_title`, `description`, `step_detail`)
VALUES
    (1, 'CULTURE', '제주 문화 퀴즈',
     '제주의 퀴즈를 맞춰보세요.',
     '[{"step": 1, "step_title": "퀴즈 시작하기", "description": "제주 방언, 엔터, 역사에 대한 퀴즈를 풀어보세요."}, {"step": 2, "step_title": "3문제 풀기", "description": "각 문제마다 보기 중 정답을 선택하세요."}, {"step": 3, "step_title": "정답 확인", "description": "문제를 다 풀면 결과를 확인할 수 있어요."}]'),

    (2, 'COOPERATIVE', '함께 키우는 귤나무',
     '일행과 역할을 나눠 귤나무를 완성해보세요!',
     '[{"step": 1, "step_title": "일행 초대하기", "description": "함께할 일행을 초대해요."}, {"step": 2, "step_title": "역할 배분받기", "description": "참여한 각자에게 고유한 성장 역할을 배분받아요."}, {"step": 3, "step_title": "재료 찾으러 가기", "description": "근처 장소로 이동해 배분받은 재료를 촬영해요."}, {"step": 4, "step_title": "보상받기", "description": "귤나무를 완성하고 미션 보상을 받아요."}]'),

    (3, 'TREASURE', '보물 찾기',
     '주변에 숨겨진 AR 보물을 찾아보세요.',
     '[{"step": 1, "step_title": "출발지 확인", "description": "보물찾기를 시작할 출발지와 주변 환경을 확인해요."}, {"step": 2, "step_title": "보물 위치 찾기", "description": "지도와 AR 화면을 따라 숨겨진 보물의 위치를 찾아요."}, {"step": 3, "step_title": "보상 받기", "description": "모든 보물을 찾고 미션 보상을 받아요."}]');


-- ---------------------------------------------------------------------
-- CULTURE_MISSION : 퀴즈 상세
-- ---------------------------------------------------------------------

INSERT INTO `CULTURE_MISSION`
    (`id`, `mission_id`, `quiz_total_count`, `quiz_detail`, `reward_detail`)
VALUES
    (1, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주어로 할아버지는 무엇일까요?", "options": ["하르방", "하라범", "하르봉", "하르범"], "answer": "하르방", "hint": "제주의 돌하르방을 떠올려 보세요.", "explanation": "제주어에서 할아버지를 뜻하는 대표적인 표현은 하르방입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주를 배경으로 여러 인물의 삶을 옴니버스 형식으로 담아낸 노희경 작가의 드라마는 무엇일까요?", "options": ["우리들의 블루스", "우도의 봄", "갯마을 차차차", "도깨비"], "answer": "우리들의 블루스", "hint": "제목에 제주 바다를 연상시키는 색상이 들어가요.", "explanation": "우리들의 블루스는 제주를 배경으로 여러 인물의 삶을 옴니버스 형식으로 그린 드라마입니다."},
        {"quiz_index": 3, "img_url": null, "question": "하영은 제주 방언으로 어떤 뜻일까요?", "options": ["많이", "천천히", "조용히", "따뜻하게"], "answer": "많이", "hint": "수량이 넉넉하다는 의미로 사용해요.", "explanation": "하영은 제주 방언으로 많이라는 뜻입니다."}
    ]',
    '{"ar_character_id": 1, "point": 100, "coupon_location": "도라지식당", "coupon_price": 1000}'),

    (2, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "만장굴은 어떤 종류의 동굴일까요?", "options": ["용암동굴", "석회동굴", "해식동굴", "빙하동굴"], "answer": "용암동굴", "hint": "흐르던 용암이 만든 길이에요.", "explanation": "만장굴은 흐르던 용암이 굳으면서 속이 비어 만들어진 용암동굴입니다."},
        {"quiz_index": 2, "img_url": null, "question": "만장굴의 총 길이는 약 몇 킬로미터일까요?", "options": ["약 2km", "약 5km", "약 7.4km", "약 12km"], "answer": "약 7.4km", "hint": "10km는 넘지 않아요.", "explanation": "만장굴의 총 길이는 약 7.4km이며 일부 구간만 공개되어 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "만장굴 공개 구간 끝에 있는 유명한 구조물은?", "options": ["용암석주", "종유석", "석순", "주상절리"], "answer": "용암석주", "hint": "높이 7.6m로 세계 최대급이에요.", "explanation": "공개 구간 끝에는 높이 약 7.6m의 용암석주가 있습니다."}
    ]',
    '{"ar_character_id": 2, "point": 100, "coupon_location": "성산해촌", "coupon_price": 2000}'),

    (3, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "해녀가 물질할 때 사용하는 부표를 무엇이라 부를까요?", "options": ["테왁", "빗창", "망사리", "물허벅"], "answer": "테왁", "hint": "물 위에 떠 있는 둥근 도구예요.", "explanation": "테왁은 해녀가 물 위에서 몸을 의지하는 부표로, 아래에 망사리를 답니다."},
        {"quiz_index": 2, "img_url": null, "question": "해녀가 숨을 참았다 내쉴 때 내는 소리를 무엇이라 할까요?", "options": ["숨비소리", "물비소리", "바당소리", "허벅소리"], "answer": "숨비소리", "hint": "휘파람 같은 소리예요.", "explanation": "물 밖으로 나오며 참았던 숨을 내쉬는 소리를 숨비소리라고 합니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 해녀문화가 유네스코 인류무형문화유산이 된 해는?", "options": ["2012년", "2014년", "2016년", "2018년"], "answer": "2016년", "hint": "2010년대 후반이에요.", "explanation": "제주 해녀문화는 2016년 유네스코 인류무형문화유산으로 등재되었습니다."}
    ]',
    '{"ar_character_id": 3, "point": 150, "coupon_location": "돔베돈", "coupon_price": 3000}'),

    (4, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 전통 떡으로 팥고물을 묻힌 것은?", "options": ["오메기떡", "빙떡", "상외떡", "돌래떡"], "answer": "오메기떡", "hint": "동문시장 대표 간식이에요.", "explanation": "오메기떡은 차조로 만든 제주 전통 떡으로 팥고물을 입혀 먹습니다."},
        {"quiz_index": 2, "img_url": null, "question": "메밀 전병에 무채를 넣어 말아 먹는 제주 음식은?", "options": ["빙떡", "몸국", "고기국수", "갈치조림"], "answer": "빙떡", "hint": "얇게 부친 메밀 전병이에요.", "explanation": "빙떡은 메밀 전병에 삶은 무채를 넣어 돌돌 말아 먹는 제주 향토 음식입니다."},
        {"quiz_index": 3, "img_url": null, "question": "돼지 육수에 모자반을 넣어 끓인 제주 국은?", "options": ["몸국", "접짝뼈국", "각재기국", "성게국"], "answer": "몸국", "hint": "모자반을 제주말로 몸이라 해요.", "explanation": "몸국은 돼지 육수에 모자반을 넣고 끓인 제주 잔치 음식입니다."}
    ]',
    '{"ar_character_id": 4, "point": 100, "coupon_location": "금강민물장어", "coupon_price": 3000}'),

    (5, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주의 전통 대문 역할을 하는 것은?", "options": ["정낭", "테왁", "물허벅", "방사탑"], "answer": "정낭", "hint": "세 개의 나무를 걸쳐 놓아요.", "explanation": "정낭은 제주 전통 가옥의 출입 여부를 알리던 나무 대문입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 전통 가옥의 바람을 막아주는 낮은 돌담을 무엇이라 하나요?", "options": null, "answer": "울담", "hint": "집의 울타리 역할을 하는 담입니다.", "explanation": "울담은 제주 가옥 주변을 둘러 강한 바람을 막아주는 돌담입니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 전통 가옥의 특징으로 알맞은 것은?", "options": ["바람에 대비한 낮은 지붕", "눈을 위한 높은 지붕", "큰 유리창", "지하 출입구"], "answer": "바람에 대비한 낮은 지붕", "hint": "제주는 바람이 강한 섬이에요.", "explanation": "제주 전통 가옥은 강한 바람에 견디도록 지붕이 낮고 단단하게 묶여 있습니다."}
    ]',
    '{"ar_character_id": 5, "point": 100, "coupon_location": "성읍칠십리식당", "coupon_price": 2000}'),

    (6, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주를 상징하는 화산암은 무엇일까요?", "options": ["현무암", "대리암", "화강암", "석회암"], "answer": "현무암", "hint": "검고 구멍이 많은 돌이에요.", "explanation": "제주에는 화산 활동으로 만들어진 현무암이 널리 분포합니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주에서 작은 화산체를 부르는 말은 무엇인가요?", "options": null, "answer": "오름", "hint": "제주 곳곳에서 볼 수 있는 봉우리예요.", "explanation": "오름은 제주에서 한라산 주변의 독립된 소화산체를 부르는 말입니다."},
        {"quiz_index": 3, "img_url": null, "question": "주상절리는 용암이 식으면서 주로 어떤 모양으로 갈라진 지형일까요?", "options": ["기둥 모양", "원형 호수", "모래 언덕", "동굴 천장"], "answer": "기둥 모양", "hint": "수직으로 늘어선 돌기둥을 떠올려 보세요.", "explanation": "주상절리는 용암이 식고 수축하면서 다각형 기둥 형태로 갈라진 지형입니다."}
    ]',
    '{"ar_character_id": 6, "point": 120, "coupon_location": "표선세화해녀의집", "coupon_price": 2000}'),

    (7, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주도의 가장 높은 산은?", "options": ["한라산", "성산일출봉", "산방산", "송악산"], "answer": "한라산", "hint": "대한민국에서 가장 높은 산이기도 해요.", "explanation": "한라산은 제주도 중앙에 있는 대한민국 최고봉입니다."},
        {"quiz_index": 2, "img_url": null, "question": "한라산 정상의 화구호 이름은 무엇인가요?", "options": null, "answer": "백록담", "hint": "흰 사슴에 관한 이름이에요.", "explanation": "한라산 정상에는 화산 활동으로 형성된 화구호 백록담이 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "한라산이 위치한 제주도의 중심 행정구역은?", "options": ["제주시와 서귀포시", "제주시만", "서귀포시만", "우도면"], "answer": "제주시와 서귀포시", "hint": "산을 기준으로 제주가 남북으로 나뉘어요.", "explanation": "한라산 일대는 제주시와 서귀포시에 걸쳐 있습니다."}
    ]',
    '{"ar_character_id": 7, "point": 150, "coupon_location": "왕일번지식당", "coupon_price": 3000}'),

    (8, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "성산일출봉은 어떤 지형일까요?", "options": ["응회구", "빙하호", "사구", "석회동굴"], "answer": "응회구", "hint": "바닷속 화산 분출과 관련 있어요.", "explanation": "성산일출봉은 수중 화산 분출로 만들어진 응회구입니다."},
        {"quiz_index": 2, "img_url": null, "question": "성산일출봉에서 이름처럼 유명한 자연현상은 무엇인가요?", "options": null, "answer": "일출", "hint": "해가 떠오르는 모습이에요.", "explanation": "성산일출봉은 동쪽 바다에서 떠오르는 일출을 감상하는 명소입니다."},
        {"quiz_index": 3, "img_url": null, "question": "성산일출봉이 있는 제주 동쪽 지역은?", "options": ["성산읍", "애월읍", "한림읍", "대정읍"], "answer": "성산읍", "hint": "장소 이름에 답이 있어요.", "explanation": "성산일출봉은 서귀포시 성산읍에 있습니다."}
    ]',
    '{"ar_character_id": 8, "point": 150, "coupon_location": "오조해녀의집", "coupon_price": 3000}'),

    (9, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 4·3 사건을 기억하고 추모하는 대표 공간은?", "options": ["제주4·3평화공원", "용두암", "천지연폭포", "협재해수욕장"], "answer": "제주4·3평화공원", "hint": "이름에 사건의 명칭이 들어가요.", "explanation": "제주4·3평화공원은 희생자를 추모하고 사건의 역사를 알리는 공간입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 4·3 희생자를 기리는 공원의 이름을 쓰세요.", "options": null, "answer": "제주4·3평화공원", "hint": "평화라는 단어가 포함됩니다.", "explanation": "제주4·3평화공원에는 기념관과 위령 공간이 마련되어 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 4·3을 기억하는 태도로 가장 알맞은 것은?", "options": ["희생자를 추모하고 역사를 배우기", "사건을 오락으로 소비하기", "기록을 훼손하기", "사실을 확인하지 않기"], "answer": "희생자를 추모하고 역사를 배우기", "hint": "기억과 평화의 의미를 생각해 보세요.", "explanation": "제주 4·3의 역사와 희생자를 존중하며 평화의 가치를 배우는 태도가 중요합니다."}
    ]',
    '{"ar_character_id": 9, "point": 120, "coupon_location": "제주뚝배기", "coupon_price": 2000}'),

    (10, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주의 전통 옹기를 굽던 가마를 무엇이라 하나요?", "options": ["굴가마", "도가니", "불턱", "정지"], "answer": "굴가마", "hint": "땅의 경사를 따라 길게 만든 가마예요.", "explanation": "제주 옹기는 경사진 지형을 이용한 굴가마에서 구웠습니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 전통 옹기의 주재료를 쓰세요.", "options": null, "answer": "흙", "hint": "제주에서 얻은 점토를 사용해요.", "explanation": "제주 옹기는 제주 지역의 흙을 빚고 구워 만듭니다."},
        {"quiz_index": 3, "img_url": null, "question": "옹기의 주요 용도로 알맞은 것은?", "options": ["음식과 물 저장", "금속 제련", "집의 기둥", "배의 돛"], "answer": "음식과 물 저장", "hint": "생활용 그릇을 떠올려 보세요.", "explanation": "옹기는 물과 곡식, 장류 등 생활 식품을 저장하는 데 사용됐습니다."}
    ]',
    '{"ar_character_id": 10, "point": 100, "coupon_location": "진미명가", "coupon_price": 2000}'),

    (11, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주에서 말을 기르던 넓은 들판을 흔히 무엇이라 하나요?", "options": ["목장", "염전", "갯벌", "다랑논"], "answer": "목장", "hint": "말과 소를 방목하는 곳이에요.", "explanation": "제주의 중산간 지역에는 말을 방목하던 목장 문화가 발달했습니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 토종말을 부르는 이름을 쓰세요.", "options": null, "answer": "제주마", "hint": "지역 이름과 동물을 합친 말이에요.", "explanation": "제주마는 제주 환경에 적응해 온 토종 말 품종입니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주마가 잘 적응한 환경은?", "options": ["제주 중산간 초지", "사막", "열대 우림", "빙하 지대"], "answer": "제주 중산간 초지", "hint": "오름 주변의 넓은 풀밭이에요.", "explanation": "제주마는 바람이 강한 제주 중산간 초지 환경에 잘 적응했습니다."}
    ]',
    '{"ar_character_id": 11, "point": 120, "coupon_location": "삼대국수회관", "coupon_price": 2000}'),

    (12, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 돌담의 주재료는?", "options": ["현무암", "벽돌", "대리석", "목재"], "answer": "현무암", "hint": "제주에서 흔히 볼 수 있는 검은 돌이에요.", "explanation": "제주 돌담은 주변에서 쉽게 구할 수 있는 현무암을 쌓아 만듭니다."},
        {"quiz_index": 2, "img_url": null, "question": "밭의 경계를 두르는 제주 돌담을 무엇이라 하나요?", "options": null, "answer": "밭담", "hint": "밭과 담을 합친 말이에요.", "explanation": "밭담은 밭의 경계를 구분하고 바람과 가축으로부터 작물을 보호합니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 돌담에 틈이 많은 이유는?", "options": ["바람이 통과하게 하려고", "물을 가두려고", "빛을 막으려고", "돌이 부족해서"], "answer": "바람이 통과하게 하려고", "hint": "강한 바람의 힘을 분산해요.", "explanation": "돌담의 틈으로 바람을 통과시켜 담이 무너지는 것을 줄입니다."}
    ]',
    '{"ar_character_id": 1, "point": 100, "coupon_location": "어장군", "coupon_price": 2000}'),

    (13, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주에서 용천수가 솟는 해안 마을의 물을 무엇이라 부르나요?", "options": ["산물", "온천", "우물", "저수지"], "answer": "산물", "hint": "땅에서 솟아난 물이라는 뜻이에요.", "explanation": "제주에서는 땅에서 솟아나는 용천수를 산물이라고 부르기도 합니다."},
        {"quiz_index": 2, "img_url": null, "question": "해녀들이 물질 전후 몸을 녹이고 쉬던 공간은 무엇인가요?", "options": null, "answer": "불턱", "hint": "불을 피우던 자리예요.", "explanation": "불턱은 해녀들이 불을 피워 몸을 녹이고 작업을 준비하던 공동체 공간입니다."},
        {"quiz_index": 3, "img_url": null, "question": "용천수가 제주 생활문화에서 중요했던 이유는?", "options": ["식수와 생활용수로 사용해서", "금속을 생산해서", "소금을 만들지 못하게 해서", "바람을 막아서"], "answer": "식수와 생활용수로 사용해서", "hint": "섬에서 마실 물은 매우 중요해요.", "explanation": "지표수가 적은 제주에서 용천수는 중요한 식수와 생활용수였습니다."}
    ]',
    '{"ar_character_id": 2, "point": 100, "coupon_location": "삼성혈해물탕", "coupon_price": 2000}'),

    (14, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 민요로 널리 알려진 노래는?", "options": ["오돌또기", "아리랑", "강강술래", "쾌지나칭칭나네"], "answer": "오돌또기", "hint": "제주 흥겨운 가락을 대표해요.", "explanation": "오돌또기는 제주 지역을 대표하는 흥겨운 민요입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주의 대표적인 민요 제목을 하나 쓰세요.", "options": null, "answer": "오돌또기", "hint": "다섯 글자의 제주 민요예요.", "explanation": "오돌또기는 제주를 대표하는 민요 중 하나입니다."},
        {"quiz_index": 3, "img_url": null, "question": "민요가 전해지는 방식으로 가장 알맞은 것은?", "options": ["사람들이 부르며 구전", "기계가 자동 생성", "법률로만 기록", "그림으로만 전달"], "answer": "사람들이 부르며 구전", "hint": "입에서 입으로 이어져요.", "explanation": "민요는 지역 공동체가 함께 부르며 세대를 거쳐 구전되어 왔습니다."}
    ]',
    '{"ar_character_id": 3, "point": 120, "coupon_location": "제주미향", "coupon_price": 2000}'),

    (15, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주의 대표 감귤 품종으로 겨울에 많이 먹는 것은?", "options": ["온주밀감", "사과", "복숭아", "배"], "answer": "온주밀감", "hint": "껍질을 손으로 쉽게 벗길 수 있어요.", "explanation": "온주밀감은 제주에서 널리 재배되는 대표적인 감귤 품종입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주를 대표하는 겨울 과일을 쓰세요.", "options": null, "answer": "감귤", "hint": "주황색 과일이에요.", "explanation": "감귤은 제주의 기후와 농업문화를 상징하는 대표 과일입니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 감귤밭에서 돌담이 하는 역할은?", "options": ["바람을 줄여 나무를 보호", "바닷물을 끌어오기", "햇빛을 완전히 차단", "나무를 이동시키기"], "answer": "바람을 줄여 나무를 보호", "hint": "제주의 강한 바람을 생각해 보세요.", "explanation": "감귤밭 돌담은 강한 바람을 줄여 감귤나무와 열매를 보호합니다."}
    ]',
    '{"ar_character_id": 4, "point": 150, "coupon_location": "도남오거리식당", "coupon_price": 3000}'),

    (16, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주도의 가장 높은 산은 무엇일까요?", "options": ["한라산", "설악산", "지리산", "북한산"], "answer": "한라산", "hint": "제주 한가운데 자리한 산이에요.", "explanation": "한라산은 해발 1,947m로 대한민국에서 가장 높은 산입니다."},
        {"quiz_index": 2, "img_url": null, "question": "한라산 정상의 화구호 이름은 무엇일까요?", "options": ["백록담", "천지", "주산지", "세량지"], "answer": "백록담", "hint": "흰 사슴에 관한 전설이 전해져요.", "explanation": "한라산 정상에는 화산 활동으로 형성된 백록담이 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "한라산은 어느 국립공원에 속할까요?", "options": ["한라산국립공원", "다도해해상국립공원", "지리산국립공원", "설악산국립공원"], "answer": "한라산국립공원", "hint": "산 이름이 그대로 들어가요.", "explanation": "한라산 일대는 한라산국립공원으로 지정되어 보호받고 있습니다."}
    ]', '{"ar_character_id": 5, "point": 120, "coupon_location": "하영 흑돼지구이집", "coupon_price": 2000}'),

    (17, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 해안에서 바람을 이용해 물고기를 잡던 전통 시설은?", "options": ["원담", "정낭", "불턱", "테왁"], "answer": "원담", "hint": "돌로 둥글게 둘러 만든 시설이에요.", "explanation": "원담은 밀물과 썰물의 차이를 이용해 고기를 잡던 제주 전통 어로 시설입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 바다에서 가장 큰 조수 차가 나타나는 때는?", "options": ["사리", "조금", "정오", "한낮"], "answer": "사리", "hint": "음력 보름과 그믐 무렵이에요.", "explanation": "사리에는 밀물과 썰물의 수위 차가 크게 나타납니다."},
        {"quiz_index": 3, "img_url": null, "question": "원담의 주재료는 무엇일까요?", "options": ["현무암", "철", "유리", "대나무"], "answer": "현무암", "hint": "제주 해안의 검은 돌이에요.", "explanation": "원담은 제주 해안에서 쉽게 구할 수 있는 현무암을 쌓아 만들었습니다."}
    ]', '{"ar_character_id": 6, "point": 180, "coupon_location": "흑돈가 제주", "coupon_price": 3000}'),

    (18, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주의 대표적인 화산 지형인 작은 산을 무엇이라 하나요?", "options": ["오름", "고원", "분지", "협곡"], "answer": "오름", "hint": "제주 곳곳에서 볼 수 있어요.", "explanation": "오름은 제주에서 독립된 소형 화산체를 부르는 말입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 오름의 꼭대기에 흔히 볼 수 있는 지형은?", "options": ["분화구", "빙하", "삼각주", "갯벌"], "answer": "분화구", "hint": "화산 활동의 흔적이에요.", "explanation": "많은 오름 정상에는 화산 분출로 만들어진 분화구가 남아 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "오름 탐방 시 지켜야 할 행동은?", "options": ["지정 탐방로 이용", "식물 채취", "쓰레기 투기", "출입 제한 구역 진입"], "answer": "지정 탐방로 이용", "hint": "자연을 보호하는 방법이에요.", "explanation": "오름의 생태를 보호하려면 지정된 탐방로를 이용해야 합니다."}
    ]', '{"ar_character_id": 7, "point": 150, "coupon_location": "수희식당", "coupon_price": 2500}'),

    (19, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 전통 물항아리를 등에 지고 나르던 도구는?", "options": ["물허벅", "테왁", "빗창", "정낭"], "answer": "물허벅", "hint": "물을 담는 둥근 옹기예요.", "explanation": "물허벅은 제주 여성들이 물을 길어 나를 때 사용한 옹기입니다."},
        {"quiz_index": 2, "img_url": null, "question": "물허벅을 운반할 때 등에 받치던 바구니는?", "options": ["물구덕", "망사리", "차롱", "테우리"], "answer": "물구덕", "hint": "대나무로 짠 운반 도구예요.", "explanation": "물구덕은 물허벅을 등에 안정적으로 지기 위한 대나무 바구니입니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주에서 물을 귀하게 여긴 주된 이유는?", "options": ["지표수가 부족해서", "비가 오지 않아서", "강이 너무 많아서", "물이 얼어서"], "answer": "지표수가 부족해서", "hint": "화산암 지질을 생각해 보세요.", "explanation": "물이 화산암층 아래로 잘 스며들어 지표수가 부족했기 때문입니다."}
    ]', '{"ar_character_id": 8, "point": 100, "coupon_location": "바그다드", "coupon_price": 1500}'),

    (20, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 목축 문화를 상징하는 말 관리인을 무엇이라 불렀을까요?", "options": ["테우리", "잠녀", "심방", "훈장"], "answer": "테우리", "hint": "소와 말을 돌보던 사람이에요.", "explanation": "테우리는 제주에서 소와 말을 방목하고 관리하던 목동을 뜻합니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주마가 주로 방목되던 지역은?", "options": ["중산간 초지", "해저", "도심 지하", "모래사장"], "answer": "중산간 초지", "hint": "해안과 한라산 사이 지역이에요.", "explanation": "제주마는 풀이 풍부한 중산간 초지에서 주로 방목되었습니다."},
        {"quiz_index": 3, "img_url": null, "question": "목축지 경계를 표시하는 제주 돌담은?", "options": ["잣성", "밭담", "산담", "원담"], "answer": "잣성", "hint": "한라산 중산간에 이어진 돌담이에요.", "explanation": "잣성은 말과 소의 방목 범위를 구분하기 위해 중산간에 쌓은 돌담입니다."}
    ]', '{"ar_character_id": 9, "point": 200, "coupon_location": "라지마할", "coupon_price": 3500}'),

    (21, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 신화에서 농경의 여신으로 알려진 인물은?", "options": ["자청비", "설문대할망", "삼승할망", "영등할망"], "answer": "자청비", "hint": "세경본풀이의 주인공이에요.", "explanation": "자청비는 제주 세경본풀이에 등장하는 농경의 여신입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주를 만들었다고 전해지는 거대한 여신은?", "options": ["설문대할망", "자청비", "영등할망", "오늘이"], "answer": "설문대할망", "hint": "한라산과 관련된 창조 설화예요.", "explanation": "설문대할망은 제주섬과 한라산을 만들었다고 전해지는 거대한 여신입니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 신들의 이야기를 풀어내는 무속 서사시는?", "options": ["본풀이", "판소리", "가사", "시조"], "answer": "본풀이", "hint": "신의 근본을 풀어낸다는 뜻이에요.", "explanation": "본풀이는 신의 내력과 이야기를 노래로 전하는 제주 무속 서사시입니다."}
    ]', '{"ar_character_id": 10, "point": 250, "coupon_location": "올래국수", "coupon_price": 4000}'),

    (22, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주에서 바람의 신을 맞이하는 대표적인 민속 행사는?", "options": ["영등굿", "단오제", "강릉농악", "은산별신제"], "answer": "영등굿", "hint": "음력 2월에 열려요.", "explanation": "영등굿은 바람의 신 영등할망을 맞고 보내며 풍요를 기원하는 제주 굿입니다."},
        {"quiz_index": 2, "img_url": null, "question": "영등할망이 제주에 머문다고 전해지는 달은?", "options": ["음력 2월", "음력 5월", "음력 8월", "음력 12월"], "answer": "음력 2월", "hint": "봄바람이 시작되는 무렵이에요.", "explanation": "제주에서는 음력 2월을 영등달이라 부르며 영등할망을 맞이합니다."},
        {"quiz_index": 3, "img_url": null, "question": "영등굿에서 주로 기원하는 것은?", "options": ["풍어와 안전", "폭설", "가뭄", "전쟁"], "answer": "풍어와 안전", "hint": "바다에서 일하는 사람들의 바람이에요.", "explanation": "해녀와 어민들은 영등굿을 통해 풍어와 바다에서의 안전을 기원합니다."}
    ]', '{"ar_character_id": 11, "point": 180, "coupon_location": "소라횟집", "coupon_price": 3000}'),

    (23, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 전통 초가집의 지붕을 묶는 줄은?", "options": ["집줄", "닻줄", "빨랫줄", "낚싯줄"], "answer": "집줄", "hint": "강한 바람에 지붕이 날리지 않게 해요.", "explanation": "제주 초가의 지붕은 새끼로 만든 집줄을 바둑판처럼 엮어 단단히 묶었습니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 초가집 지붕의 주재료는?", "options": ["띠풀", "철판", "기와", "유리"], "answer": "띠풀", "hint": "제주 들판에서 자라는 풀이에요.", "explanation": "제주 초가 지붕은 바람에 강한 띠풀을 두껍게 덮어 만들었습니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 초가가 낮게 지어진 이유는?", "options": ["강풍에 견디기 위해", "눈을 쌓기 위해", "햇빛을 막기 위해", "배를 보관하기 위해"], "answer": "강풍에 견디기 위해", "hint": "제주는 바람이 강해요.", "explanation": "건물 높이를 낮추면 강한 바람이 가하는 힘을 줄일 수 있습니다."}
    ]', '{"ar_character_id": 1, "point": 130, "coupon_location": "해녀촌", "coupon_price": 2000}'),

    (24, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주에서 제사를 지낼 때 음식을 담는 대나무 그릇은?", "options": ["차롱", "테왁", "물구덕", "정낭"], "answer": "차롱", "hint": "네모난 대나무 바구니예요.", "explanation": "차롱은 음식을 담아 운반하거나 보관하던 제주 전통 대나무 바구니입니다."},
        {"quiz_index": 2, "img_url": null, "question": "차롱의 주재료는 무엇일까요?", "options": ["대나무", "현무암", "무쇠", "유리"], "answer": "대나무", "hint": "가늘게 쪼개 엮어요.", "explanation": "차롱은 대나무를 가늘게 쪼개 촘촘하게 엮어 만듭니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 전통 공예를 보존하는 올바른 방법은?", "options": ["기술을 배우고 기록하기", "도구를 폐기하기", "완성품을 훼손하기", "재료를 무단 채취하기"], "answer": "기술을 배우고 기록하기", "hint": "다음 세대에 전하는 방법이에요.", "explanation": "전통 공예 기술을 배우고 기록하면 지역의 생활문화를 이어갈 수 있습니다."}
    ]', '{"ar_character_id": 2, "point": 100, "coupon_location": "은희네해장국", "coupon_price": 2000}'),

    (25, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주의 대표적인 해안 폭포로 바다로 직접 떨어지는 곳은?", "options": ["정방폭포", "천지연폭포", "엉또폭포", "비룡폭포"], "answer": "정방폭포", "hint": "서귀포 해안에 있어요.", "explanation": "정방폭포는 물줄기가 바다 가까이 직접 떨어지는 제주 대표 폭포입니다."},
        {"quiz_index": 2, "img_url": null, "question": "정방폭포가 위치한 도시는?", "options": ["서귀포시", "제주시", "부산시", "강릉시"], "answer": "서귀포시", "hint": "제주 남쪽 도시예요.", "explanation": "정방폭포는 제주특별자치도 서귀포시에 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "폭포 탐방 시 안전한 행동은?", "options": ["지정된 길 이용", "젖은 바위에서 뛰기", "난간 넘기", "통제구역 진입"], "answer": "지정된 길 이용", "hint": "미끄러운 지형을 주의해야 해요.", "explanation": "폭포 주변은 미끄러우므로 지정된 탐방로와 안전 수칙을 따라야 합니다."}
    ]', '{"ar_character_id": 3, "point": 160, "coupon_location": "비지곶식당", "coupon_price": 3000}'),

    (26, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 서쪽의 대표적인 섬으로 산방산 앞바다에 있는 섬은?", "options": ["가파도", "마라도", "비양도", "차귀도"], "answer": "가파도", "hint": "청보리로 유명해요.", "explanation": "가파도는 산방산 남쪽 바다에 있으며 청보리밭으로 잘 알려져 있습니다."},
        {"quiz_index": 2, "img_url": null, "question": "가파도의 봄철 대표 농작물은?", "options": ["청보리", "인삼", "사과", "밤"], "answer": "청보리", "hint": "섬을 초록빛으로 물들여요.", "explanation": "가파도에서는 봄마다 넓은 청보리밭을 볼 수 있습니다."},
        {"quiz_index": 3, "img_url": null, "question": "대한민국 최남단 섬으로 알려진 곳은?", "options": ["마라도", "우도", "비양도", "가파도"], "answer": "마라도", "hint": "가파도보다 더 남쪽이에요.", "explanation": "마라도는 대한민국의 최남단 섬으로 알려져 있습니다."}
    ]', '{"ar_character_id": 4, "point": 220, "coupon_location": "광양해장국집", "coupon_price": 4000}'),

    (27, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주 바닷가에서 소금을 만들던 밭은?", "options": ["염전", "목장", "다랑논", "과수원"], "answer": "염전", "hint": "바닷물을 증발시켜요.", "explanation": "염전은 바닷물을 햇볕과 바람으로 증발시켜 소금을 얻는 곳입니다."},
        {"quiz_index": 2, "img_url": null, "question": "소금을 만드는 데 중요한 자연 요소는?", "options": ["햇빛과 바람", "눈과 얼음", "용암과 불", "안개와 서리"], "answer": "햇빛과 바람", "hint": "물을 증발시키는 요소예요.", "explanation": "강한 햇빛과 바람은 바닷물의 수분을 빠르게 증발시킵니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 전통 소금 생산과 관련된 자원은?", "options": ["바닷물", "용천수", "빗물", "지하 광석"], "answer": "바닷물", "hint": "섬을 둘러싼 물이에요.", "explanation": "제주에서는 주변 바다의 바닷물을 활용해 소금을 생산했습니다."}
    ]', '{"ar_character_id": 5, "point": 140, "coupon_location": "모이세해장국", "coupon_price": 2500}'),

    (28, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주에서 무덤 주변을 두르는 돌담은?", "options": ["산담", "밭담", "잣성", "원담"], "answer": "산담", "hint": "묘를 뜻하는 제주말과 담이 합쳐졌어요.", "explanation": "산담은 무덤을 보호하고 영역을 표시하기 위해 둘러쌓은 돌담입니다."},
        {"quiz_index": 2, "img_url": null, "question": "산담 입구에 세우는 돌기둥은?", "options": ["정주석", "망주석", "비석", "장승"], "answer": "정주석", "hint": "정낭을 걸기도 했어요.", "explanation": "산담 입구의 정주석에는 정낭을 걸어 출입을 표시하기도 했습니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 돌담 문화의 공통 재료는?", "options": ["현무암", "화강암", "석회암", "사암"], "answer": "현무암", "hint": "검은 화산석이에요.", "explanation": "제주 돌담은 화산 활동으로 생긴 현무암을 주로 사용합니다."}
    ]', '{"ar_character_id": 6, "point": 170, "coupon_location": "삼다도횟집", "coupon_price": 3000}'),

    (29, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주에서 음력 정월대보름 무렵 들불을 놓던 풍습과 관련된 축제는?", "options": ["들불축제", "유채꽃축제", "감귤축제", "칠십리축제"], "answer": "들불축제", "hint": "오름의 묵은 풀을 태우는 풍습에서 시작됐어요.", "explanation": "제주들불축제는 목축지의 해묵은 풀을 태우던 방애 풍습을 현대적으로 재현한 축제입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주들불축제로 유명한 오름은?", "options": ["새별오름", "다랑쉬오름", "용눈이오름", "아부오름"], "answer": "새별오름", "hint": "애월읍에 있는 오름이에요.", "explanation": "새별오름은 제주들불축제가 열리는 대표 장소입니다."},
        {"quiz_index": 3, "img_url": null, "question": "전통 들불 풍습의 목적은?", "options": ["해충 제거와 새 풀 돋기", "바닷물 증발", "집 짓기", "물고기 잡기"], "answer": "해충 제거와 새 풀 돋기", "hint": "목축지를 관리하는 방법이에요.", "explanation": "묵은 풀을 태우면 해충을 줄이고 가축이 먹을 새 풀이 돋는 데 도움이 됐습니다."}
    ]', '{"ar_character_id": 7, "point": 230, "coupon_location": "가시식당", "coupon_price": 4500}'),

    (30, 1, 3, '[
        {"quiz_index": 1, "img_url": null, "question": "제주의 전통 시장에서 흔히 맛볼 수 있는 국수는?", "options": ["고기국수", "냉면", "막국수", "쫄면"], "answer": "고기국수", "hint": "돼지고기 육수를 사용해요.", "explanation": "고기국수는 돼지고기 육수와 수육을 올려 먹는 제주 대표 음식입니다."},
        {"quiz_index": 2, "img_url": null, "question": "제주 향토 음식 몸국의 몸은 무엇을 뜻할까요?", "options": ["모자반", "미역", "톳", "다시마"], "answer": "모자반", "hint": "갈색 해조류예요.", "explanation": "제주어로 모자반을 몸이라 하며 돼지 육수에 넣어 몸국을 끓입니다."},
        {"quiz_index": 3, "img_url": null, "question": "제주 빙떡 속에 주로 들어가는 재료는?", "options": ["무채", "감자", "팥", "고구마"], "answer": "무채", "hint": "메밀 전병에 넣어 말아요.", "explanation": "빙떡은 메밀 전병에 양념한 무채를 넣어 말아 만든 제주 음식입니다."}
    ]', '{"ar_character_id": 8, "point": 200, "coupon_location": "고불락", "coupon_price": 4000}');


-- ---------------------------------------------------------------------
-- COOPERATIVE_MISSION : 카름스테이 장소 목록 앞 12개에 배정
-- ---------------------------------------------------------------------

INSERT INTO `COOPERATIVE_MISSION`
    (`id`, `mission_id`, `location_id`, `reward_detail`)
VALUES
(1,  2, 452,  '{"ar_character_id": 1, "point": 100, "coupon_location": "도라지식당", "coupon_price": 1000}'),
    (2,  2, 545,  '{"ar_character_id": 2, "point": 120, "coupon_location": "성산해촌", "coupon_price": 1500}'),
    (3,  2, 68,  '{"ar_character_id": 3, "point": 150, "coupon_location": "돔베돈", "coupon_price": 2000}'),
    (4,  2, 441,  '{"ar_character_id": 4, "point": 180, "coupon_location": "금강민물장어", "coupon_price": 2500}'),
    (5,  2, 266,  '{"ar_character_id": 5, "point": 200, "coupon_location": "성읍칠십리식당", "coupon_price": 3000}'),
    (6,  2, 160,  '{"ar_character_id": 6, "point": 220, "coupon_location": "표선세화해녀의집", "coupon_price": 3500}'),
    (7,  2, 161,  '{"ar_character_id": 7, "point": 250, "coupon_location": "왕일번지식당", "coupon_price": 4000}'),
    (8,  2, 142,  '{"ar_character_id": 8, "point": 130, "coupon_location": "오조해녀의집", "coupon_price": 2000}'),
    (9,  2, 184,  '{"ar_character_id": 9, "point": 160, "coupon_location": "제주뚝배기", "coupon_price": 2500}'),
    (10, 2, 115, '{"ar_character_id": 10, "point": 190, "coupon_location": "진미명가", "coupon_price": 3000}'),
    (11, 2, 692, '{"ar_character_id": 11, "point": 210, "coupon_location": "삼대국수회관", "coupon_price": 3500}'),
    (12, 2, 460, '{"ar_character_id": 1, "point": 240, "coupon_location": "어장군", "coupon_price": 4000}');


-- ---------------------------------------------------------------------
-- COOPERATIVE_ROLE_CARD : 모든 협동 미션에서 공통으로 사용하는 역할 카드 6종
-- ---------------------------------------------------------------------

INSERT INTO `COOPERATIVE_ROLE_CARD`
    (`id`, `role_name`, `role_description`, `location_to_find`)
VALUES
    (1, '땅지기',
     '귤나무가 뿌리를 내릴 건강한 땅을 찾고 비료를 주는 역할입니다. 제주의 화산토는 귤나무가 자라기에 최적의 환경을 제공합니다. 흙의 기운이 느껴지는 장소를 찾아 땅의 상태를 기록하세요. 좋은 땅이 있어야 귤나무가 뿌리를 깊이 내릴 수 있습니다.',
     '["화산토", "흙길", "밭", "퇴비 주변"]'),
    (2, '물지기',
     '귤나무에 생명을 불어넣는 물을 찾는 역할입니다. 제주는 화산암 지형 특성상 빗물이 지하로 스며들어 용천수로 솟아오릅니다. 물의 기운이 느껴지는 장소를 찾아 기록하세요. 귤나무는 적절한 수분 없이는 자랄 수 없습니다.',
     '["용천수", "물길", "연못", "젖은 돌 주변"]'),
    (3, '빛지기',
     '귤이 달콤하게 익으려면 충분한 햇빛이 필요합니다. 제주의 햇살이 잘 드는 양지바른 장소를 찾아 기록하세요. 빛이 충분해야 귤나무가 광합성을 하고 열매를 맺을 수 있습니다.',
     '["양지바른 길", "햇살 드는 공터", "남향 돌담", "빛이 비치는 나무 아래"]'),
    (4, '바람지기',
     '제주는 바람의 섬입니다. 하지만 강한 바람은 어린 귤나무에게 해가 될 수 있습니다. 바람을 막아줄 수 있는 돌담, 낮은 언덕, 건물 사이 골목 등 아늑한 장소를 찾아 기록하세요. 제주 돌담이 귤밭을 감싸는 데는 이유가 있습니다.',
     '["돌담", "낮은 언덕 뒤", "건물 사이 골목", "방풍림"]'),
    (5, '이웃지기',
     '귤나무 혼자서는 자랄 수 없습니다. 주변 생태계와 어우러져야 건강하게 자랍니다. 귤나무 주변에 함께 살아갈 수 있는 자연이 있는 장소를 찾아 기록하세요. 제주의 꽃, 풀, 나무와 곤충의 흔적이 귤나무의 이웃이 됩니다.',
     '["꽃밭", "풀숲", "주변 나무", "곤충의 흔적"]'),
    (6, '수확지기',
     '귤나무의 열매를 거두는 마지막 역할입니다. 제주 사람들의 손길이 느껴지는 장소, 오래된 감귤 농장 흔적, 수확의 기억이 담긴 공간을 찾아 기록하세요. 귤나무는 사람의 손길이 닿아야 비로소 완성됩니다.',
     '["감귤 농장", "귤 창고", "수확 도구", "오래된 과수원"]');


-- ---------------------------------------------------------------------
-- TREASURE_MISSION : 카름스테이 장소 목록 뒤 12개에 배정
-- 보물 좌표는 진행도 생성 시 사용자 위치를 기준으로 정해진다.
-- ---------------------------------------------------------------------

INSERT INTO `TREASURE_MISSION`
    (`id`, `mission_id`, `location_id`, `item_total_count`, `reward_detail`)
VALUES
(1,  3, 607, 3, '{"ar_character_id": 8,  "point": 150, "coupon_location": "도라지식당", "coupon_price": 3000}'),
    (2,  3, 444, 3, '{"ar_character_id": 9,  "point": 180, "coupon_location": "성산해촌", "coupon_price": 3500}'),
    (3,  3, 456, 3, '{"ar_character_id": 10, "point": 200, "coupon_location": "돔베돈", "coupon_price": 4000}'),
    (4,  3, 346, 3, '{"ar_character_id": 11, "point": 120, "coupon_location": "금강민물장어", "coupon_price": 2000}'),
    (5,  3, 454, 3, '{"ar_character_id": 1,  "point": 160, "coupon_location": "성읍칠십리식당", "coupon_price": 3000}'),
    (6,  3, 488, 3, '{"ar_character_id": 2,  "point": 220, "coupon_location": "표선세화해녀의집", "coupon_price": 4500}'),
    (7,  3, 12, 3, '{"ar_character_id": 3,  "point": 140, "coupon_location": "왕일번지식당", "coupon_price": 2500}'),
    (8,  3, 594, 3, '{"ar_character_id": 4,  "point": 190, "coupon_location": "오조해녀의집", "coupon_price": 3500}'),
    (9,  3, 499, 3, '{"ar_character_id": 5,  "point": 250, "coupon_location": "제주뚝배기", "coupon_price": 5000}'),
    (10, 3, 297, 3, '{"ar_character_id": 6,  "point": 130, "coupon_location": "진미명가", "coupon_price": 2000}'),
    (11, 3, 123, 3, '{"ar_character_id": 7,  "point": 170, "coupon_location": "삼대국수회관", "coupon_price": 3000}'),
    (12, 3, 133, 3, '{"ar_character_id": 8,  "point": 210, "coupon_location": "어장군", "coupon_price": 4000}');


-- ---------------------------------------------------------------------
-- CULTURE_MISSION_PROGRESS : 홈 조회 예시용 진행 중 미션 1건
-- ---------------------------------------------------------------------

INSERT INTO `CULTURE_MISSION_PROGRESS`
    (`id`, `culture_mission_id`, `user_id`, `mission_status`,
     `current_quiz_index`, `correct_number`,
     `ar_character_reward_granted`, `point_reward_granted`, `coupon_reward_granted`,
     `completed_at`)
VALUES
    (1, 1, 1, 'IN_PROGRESS', 2, 1, FALSE, FALSE, FALSE, NULL);


-- ---------------------------------------------------------------------
-- COOPERATIVE_MISSION_PROGRESS : 홈 조회 예시용 진행 중 미션 1건
-- 현재 사용자는 참여자 테이블을 통해 진행 중인 협동 미션과 연결된다.
-- ---------------------------------------------------------------------

INSERT INTO `COOPERATIVE_MISSION_PROGRESS`
    (`id`, `cooperative_mission_id`, `current_step`, `mission_status`,
     `team_token`,
     `ar_character_reward_granted`, `point_reward_granted`, `coupon_reward_granted`,
     `completed_at`, `deleted_at`)
VALUES
    (1, 1, 2, 'IN_PROGRESS', 'mock-team-token-1', FALSE, FALSE, FALSE, NULL, NULL);

INSERT INTO `COOPERATIVE_MISSION_PARTICIPANT`
    (`id`, `cooperative_mission_progress_id`, `user_id`,
     `participant_status`, `participant_role`, `joined_at`, `deleted_at`)
VALUES
    (1, 1, 1, 'ACCEPTED', 'HOST',   '2026-08-20 10:00:00', NULL),
    (2, 1, 2, 'ACCEPTED', 'MEMBER', '2026-08-20 10:05:00', NULL),
    (3, 1, 3, 'PENDING',  'MEMBER', NULL,                  NULL);


-- ---------------------------------------------------------------------
-- TREASURE_MISSION_PROGRESS : 홈 조회 예시용 진행 중 미션 1건
-- ---------------------------------------------------------------------

-- current_step : 1 | 2 | 3 (3 = 완료)
-- item_detail : 진행도 생성 시 사용자 위치 방향의 반원 안에서 확정된 보물 좌표
INSERT INTO `TREASURE_MISSION_PROGRESS`
    (`id`, `treasure_mission_id`, `user_id`, `item_detail`, `current_found_item_idx`, `current_step`,
     `mission_status`,
     `ar_character_reward_granted`, `point_reward_granted`, `coupon_reward_granted`,
     `completed_at`)
VALUES
    (1, 1, 1, '[
        {"index": 1, "mx": 126.5535, "my": 33.2470},
        {"index": 2, "mx": 126.5544, "my": 33.2462},
        {"index": 3, "mx": 126.5551, "my": 33.2468}
    ]',
    '[1, 2]', 2, 'IN_PROGRESS', FALSE, FALSE, FALSE, NULL);


-- ---------------------------------------------------------------------
-- AR_CHARACTER : 제주 테마 캐릭터 + 기본 캐릭터
-- ---------------------------------------------------------------------

INSERT INTO `AR_CHARACTER`
    (`id`, `character_name`, `character_description`, `character_story_title`,
     `acquire_condition`, `character_img_url`, `hashtags`)
VALUES
    (1,  '자청비 모티브 탐험가',
     '제주의 오래된 이야기에서 온 씨앗과 여행 지도를 들고 새로운 순간을 발견하는 기록 탐험가입니다.',
     '씨앗을 심는 여행자의 첫 기록',
     '온보딩에서 기록형 여행 스타일을 선택하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/jacheongbi-explorer.png',
     '["#인생사진", "#로컬 탐방", "#자연", "#혼자 여행"]'),
    (2,  '동굴빛 용암이',
     '만장굴의 검은 용암길 사이에서 반짝이는 빛을 따라다니는 작은 동굴 안내자입니다.',
     '검은 용암길에서 빛을 만난 날',
     '만장굴 문화 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/yongami.png',
     '["#용암동굴", "#만장굴", "#지질"]'),
    (3,  '숨비 바다친구',
     '우도 바다의 숨비소리를 따라 여행자에게 바다 이야기를 들려주는 해녀 친구입니다.',
     '숨비소리를 따라간 우도의 하루',
     '우도 해녀 문화 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/sumbi.png',
     '["#해녀", "#우도", "#제주바다"]'),
    (4,  '오메기 시장요정',
     '동문시장 골목에서 따뜻한 간식 냄새를 따라 나타나는 먹거리 요정입니다.',
     '골목 끝에서 만난 따뜻한 한 입',
     '동문시장 문화 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/omegi.png',
     '["#먹거리", "#동문시장", "#제주간식"]'),
    (5,  '협재 파도지기',
     '협재 바다의 에메랄드빛 파도를 지키며 팀의 사진 미션을 응원하는 캐릭터입니다.',
     '에메랄드빛 파도를 함께 지킨 날',
     '협재 협동 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/hyeopjae-wave.png',
     '["#바다", "#협재", "#협동"]'),
    (6,  '동백 정원사',
     '카멜리아힐의 동백꽃 사이를 돌보며 여행자의 색깔 찾기를 도와주는 정원사입니다.',
     '동백꽃 사이에서 색을 찾는 시간',
     '카멜리아힐 협동 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/dongbaek.png',
     '["#동백", "#꽃", "#카멜리아힐"]'),
    (7,  '노을 조랑이',
     '한담해안의 노을빛을 등에 얹고 천천히 산책하는 제주 조랑말 친구입니다.',
     '노을을 등에 얹고 걷는 해안길',
     '한담해안 협동 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/noeul-jorang.png',
     '["#조랑말", "#노을", "#애월"]'),
    (8,  '천지연 물방울',
     '천지연폭포 물보라에서 톡 튀어나와 시원한 길을 알려주는 물방울 캐릭터입니다.',
     '물보라 너머에 숨겨둔 보물',
     '천지연 보물 찾기 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/mulbangul.png',
     '["#폭포", "#천지연", "#물"]'),
    (9,  '쇠소깍 물빛이',
     '쇠소깍의 깊은 물빛 속에서 장난스럽게 보물 위치를 알려주는 계곡 친구입니다.',
     '깊은 물빛이 알려준 자리',
     '쇠소깍 보물 찾기 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/soesokkak.png',
     '["#계곡", "#쇠소깍", "#물빛"]'),
    (10, '어리목 숲노루',
     '한라산 어리목 숲길에서 조용히 길을 안내하는 수줍은 제주 노루 친구입니다.',
     '어리목 숲길의 조용한 안내자',
     '어리목 보물 찾기 미션을 완료하면 만날 수 있어요.',
     'https://cdn.jamkkan-jeju.dev/ar/noru.png',
     '["#노루", "#한라산", "#숲길"]'),
    (11, '돌멍이',
     '처음 제주 여행을 시작한 사용자 곁을 지켜주는 귀여운 기본 캐릭터입니다.',
     '제주에서의 첫 걸음을 함께한 돌멩이',
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
-- GUESTBOOK : 사용자 1~6 각각 3건, 총 18건. 제공된 테스트 이미지·오디오 사용
-- id=10 은 소프트 삭제된 행 (deleted_at 필터 테스트용)
-- ---------------------------------------------------------------------

INSERT INTO `GUESTBOOK`
    (`id`, `user_id`, `location_id`, `visited_at`, `content_img_url`, `content_writing`,
     `content_audio_url`, `audio_title`, `content_weather`, `content_temperature_celsius`,
     `content_color_code`, `saved_at`, `mission_id`, `deleted_at`)
VALUES
    (1, 1, 452, '2026-08-18', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, NULL, NULL, 'SUNNY', 27, '#FFD8A8', '2026-08-18T12:00:00', NULL, NULL),
    (2, 1, 545, '2026-08-19', NULL, '천천히 둘러보니 작은 풍경도 새롭게 느껴졌다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 2', 'CLOUDY', 27, '#FFD8A8', '2026-08-19T12:00:00', NULL, NULL),
    (3, 1, 68, '2026-08-20', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '다음 여행에도 다시 찾아오고 싶은 곳이다.', NULL, NULL, 'WINDY', 27, '#FFD8A8', '2026-08-20T12:00:00', NULL, NULL),
    (4, 2, 441, '2026-08-18', NULL, NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 4', 'SUNNY', 27, '#FFD8A8', '2026-08-18T12:00:00', NULL, NULL),
    (5, 2, 266, '2026-08-19', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '천천히 둘러보니 작은 풍경도 새롭게 느껴졌다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 5', 'CLOUDY', 27, '#FFD8A8', '2026-08-19T12:00:00', NULL, NULL),
    (6, 2, 160, '2026-08-20', NULL, '다음 여행에도 다시 찾아오고 싶은 곳이다.', NULL, NULL, 'WINDY', 27, '#FFD8A8', '2026-08-20T12:00:00', NULL, NULL),
    (7, 3, 161, '2026-08-18', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 7', 'SUNNY', 27, '#FFD8A8', '2026-08-18T12:00:00', NULL, NULL),
    (8, 3, 142, '2026-08-19', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '천천히 둘러보니 작은 풍경도 새롭게 느껴졌다.', NULL, NULL, 'CLOUDY', 27, '#FFD8A8', '2026-08-19T12:00:00', NULL, NULL),
    (9, 3, 184, '2026-08-20', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, NULL, NULL, 'WINDY', 27, '#FFD8A8', '2026-08-20T12:00:00', NULL, NULL),
    (10, 4, 115, '2026-08-18', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '잠시 머물며 오늘의 여행을 기억했다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 10', 'SUNNY', 27, '#FFD8A8', '2026-08-18T12:00:00', NULL, NULL),
    (11, 4, 692, '2026-08-19', NULL, '천천히 둘러보니 작은 풍경도 새롭게 느껴졌다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 11', 'CLOUDY', 27, '#FFD8A8', '2026-08-19T12:00:00', NULL, NULL),
    (12, 4, 460, '2026-08-20', NULL, NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 12', 'WINDY', 27, '#FFD8A8', '2026-08-20T12:00:00', NULL, NULL),
    (13, 5, 607, '2026-08-18', NULL, '잠시 머물며 오늘의 여행을 기억했다.', NULL, NULL, 'SUNNY', 27, '#FFD8A8', '2026-08-18T12:00:00', NULL, NULL),
    (14, 5, 444, '2026-08-19', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 14', 'CLOUDY', 27, '#FFD8A8', '2026-08-19T12:00:00', NULL, NULL),
    (15, 5, 456, '2026-08-20', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '다음 여행에도 다시 찾아오고 싶은 곳이다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 15', 'WINDY', 27, '#FFD8A8', '2026-08-20T12:00:00', NULL, NULL),
    (16, 6, 346, '2026-08-18', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, NULL, NULL, 'SUNNY', 27, '#FFD8A8', '2026-08-18T12:00:00', NULL, NULL),
    (17, 6, 454, '2026-08-19', NULL, NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 17', 'CLOUDY', 27, '#FFD8A8', '2026-08-19T12:00:00', NULL, NULL),
    (18, 6, 488, '2026-08-20', NULL, '다음 여행에도 다시 찾아오고 싶은 곳이다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '여행 중 남긴 소리 18', 'WINDY', 27, '#FFD8A8', '2026-08-20T12:00:00', NULL, NULL);


-- ---------------------------------------------------------------------
-- GUESTBOOK_LIKE : 활성 45건 + 취소 15건. 글마다 활성 좋아요 0~5개
-- 방명록마다 좋아요 수가 다르게 보이도록 사용자 1~6 것을 섞었다.
--   방명록 3 = 4개, 방명록 1 = 3개, 방명록 7 = 2개, 방명록 2/9 = 1개, 방명록 4/5/6/8 = 0개
-- 취소된 좋아요는 deleted_at 필터 검증용이며 활성 개수에서 제외한다.
-- 동일한 (방명록 id, 사용자 id) 쌍은 중복하지 않는다.
-- 한 사용자가 같은 방명록에 두 행을 가질 수 없다. (guestbook_id + user_id 유니크)
-- ---------------------------------------------------------------------

INSERT INTO `GUESTBOOK_LIKE`
    (`id`, `guestbook_id`, `user_id`, `created_at`, `deleted_at`)
VALUES
    (1, 1, 2, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (2, 2, 2, '2026-08-22T13:00:00', NULL),
    (3, 2, 3, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (4, 3, 2, '2026-08-22T13:00:00', NULL),
    (5, 3, 3, '2026-08-22T13:00:00', NULL),
    (6, 3, 4, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (7, 4, 3, '2026-08-22T13:00:00', NULL),
    (8, 4, 4, '2026-08-22T13:00:00', NULL),
    (9, 4, 5, '2026-08-22T13:00:00', NULL),
    (10, 4, 6, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (11, 5, 3, '2026-08-22T13:00:00', NULL),
    (12, 5, 4, '2026-08-22T13:00:00', NULL),
    (13, 5, 5, '2026-08-22T13:00:00', NULL),
    (14, 5, 6, '2026-08-22T13:00:00', NULL),
    (15, 5, 1, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (16, 6, 3, '2026-08-22T13:00:00', NULL),
    (17, 6, 4, '2026-08-22T13:00:00', NULL),
    (18, 6, 5, '2026-08-22T13:00:00', NULL),
    (19, 6, 6, '2026-08-22T13:00:00', NULL),
    (20, 6, 1, '2026-08-22T13:00:00', NULL),
    (21, 7, 4, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (22, 8, 4, '2026-08-22T13:00:00', NULL),
    (23, 8, 5, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (24, 9, 4, '2026-08-22T13:00:00', NULL),
    (25, 9, 5, '2026-08-22T13:00:00', NULL),
    (26, 9, 6, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (27, 10, 5, '2026-08-22T13:00:00', NULL),
    (28, 10, 6, '2026-08-22T13:00:00', NULL),
    (29, 10, 1, '2026-08-22T13:00:00', NULL),
    (30, 10, 2, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (31, 11, 5, '2026-08-22T13:00:00', NULL),
    (32, 11, 6, '2026-08-22T13:00:00', NULL),
    (33, 11, 1, '2026-08-22T13:00:00', NULL),
    (34, 11, 2, '2026-08-22T13:00:00', NULL),
    (35, 11, 3, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (36, 12, 5, '2026-08-22T13:00:00', NULL),
    (37, 12, 6, '2026-08-22T13:00:00', NULL),
    (38, 12, 1, '2026-08-22T13:00:00', NULL),
    (39, 12, 2, '2026-08-22T13:00:00', NULL),
    (40, 12, 3, '2026-08-22T13:00:00', NULL),
    (41, 13, 6, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (42, 14, 6, '2026-08-22T13:00:00', NULL),
    (43, 14, 1, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (44, 15, 6, '2026-08-22T13:00:00', NULL),
    (45, 15, 1, '2026-08-22T13:00:00', NULL),
    (46, 15, 2, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (47, 16, 1, '2026-08-22T13:00:00', NULL),
    (48, 16, 2, '2026-08-22T13:00:00', NULL),
    (49, 16, 3, '2026-08-22T13:00:00', NULL),
    (50, 16, 4, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (51, 17, 1, '2026-08-22T13:00:00', NULL),
    (52, 17, 2, '2026-08-22T13:00:00', NULL),
    (53, 17, 3, '2026-08-22T13:00:00', NULL),
    (54, 17, 4, '2026-08-22T13:00:00', NULL),
    (55, 17, 5, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (56, 18, 1, '2026-08-22T13:00:00', NULL),
    (57, 18, 2, '2026-08-22T13:00:00', NULL),
    (58, 18, 3, '2026-08-22T13:00:00', NULL),
    (59, 18, 4, '2026-08-22T13:00:00', NULL),
    (60, 18, 5, '2026-08-22T13:00:00', NULL);


-- ---------------------------------------------------------------------
-- ROAD_GUESTBOOK : 사용자 1~6 각각 3건, 총 18건. 제공된 테스트 이미지·오디오 사용
-- location_id 가 NULL 인 행은 등록된 장소가 아닌 곳
-- ---------------------------------------------------------------------

INSERT INTO `ROAD_GUESTBOOK`
    (`id`, `user_id`, `location_id`, `location_alias`, `visited_at`, `content_img_url`, `content_writing`,
     `content_audio_url`, `audio_title`, `content_weather`, `content_temperature_celsius`,
     `content_color_code`, `mx`, `my`, `saved_at`, `deleted_at`)
VALUES
    (1, 1, NULL, '돌담길 쉼터 1', '2026-08-18', NULL, '잠시 머물며 오늘의 여행을 기억했다.', NULL, NULL, 'SUNNY', 27, '#FFE8CC', 126.5450, 33.4520, '2026-08-18T12:00:00', NULL),
    (2, 1, NULL, '해안길 산책 자리 1', '2026-08-19', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 2', 'CLOUDY', 27, '#FFE8CC', 126.5470, 33.4640, '2026-08-19T12:00:00', NULL),
    (3, 1, NULL, '골목길 작은 쉼터 1', '2026-08-20', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '목적지 없이 걸으니 마음이 편안해졌다.', NULL, NULL, 'WINDY', 27, '#FFE8CC', 126.5490, 33.4760, '2026-08-20T12:00:00', NULL),
    (4, 2, NULL, '돌담길 쉼터 2', '2026-08-18', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, NULL, NULL, 'SUNNY', 27, '#FFE8CC', 126.5600, 33.4540, '2026-08-18T12:00:00', NULL),
    (5, 2, NULL, '해안길 산책 자리 2', '2026-08-19', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '길에서 마주친 풍경이 오늘의 기억이 되었다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 5', 'CLOUDY', 27, '#FFE8CC', 126.5620, 33.4660, '2026-08-19T12:00:00', NULL),
    (6, 2, NULL, '골목길 작은 쉼터 2', '2026-08-20', NULL, '목적지 없이 걸으니 마음이 편안해졌다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 6', 'WINDY', 27, '#FFE8CC', 126.5640, 33.4780, '2026-08-20T12:00:00', NULL),
    (7, 3, NULL, '돌담길 쉼터 3', '2026-08-18', NULL, NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 7', 'SUNNY', 27, '#FFE8CC', 126.5750, 33.4560, '2026-08-18T12:00:00', NULL),
    (8, 3, NULL, '해안길 산책 자리 3', '2026-08-19', NULL, '길에서 마주친 풍경이 오늘의 기억이 되었다.', NULL, NULL, 'CLOUDY', 27, '#FFE8CC', 126.5770, 33.4680, '2026-08-19T12:00:00', NULL),
    (9, 3, NULL, '골목길 작은 쉼터 3', '2026-08-20', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 9', 'WINDY', 27, '#FFE8CC', 126.5790, 33.4800, '2026-08-20T12:00:00', NULL),
    (10, 4, NULL, '돌담길 쉼터 4', '2026-08-18', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '잠시 머물며 오늘의 여행을 기억했다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 10', 'SUNNY', 27, '#FFE8CC', 126.5900, 33.4580, '2026-08-18T12:00:00', NULL),
    (11, 4, NULL, '해안길 산책 자리 4', '2026-08-19', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, NULL, NULL, 'CLOUDY', 27, '#FFE8CC', 126.5920, 33.4700, '2026-08-19T12:00:00', NULL),
    (12, 4, NULL, '골목길 작은 쉼터 4', '2026-08-20', NULL, NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 12', 'WINDY', 27, '#FFE8CC', 126.5940, 33.4820, '2026-08-20T12:00:00', NULL),
    (13, 5, NULL, '돌담길 쉼터 5', '2026-08-18', NULL, '잠시 머물며 오늘의 여행을 기억했다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 13', 'SUNNY', 27, '#FFE8CC', 126.6050, 33.4600, '2026-08-18T12:00:00', NULL),
    (14, 5, NULL, '해안길 산책 자리 5', '2026-08-19', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', NULL, NULL, NULL, 'CLOUDY', 27, '#FFE8CC', 126.6070, 33.4720, '2026-08-19T12:00:00', NULL),
    (15, 5, NULL, '골목길 작은 쉼터 5', '2026-08-20', NULL, '목적지 없이 걸으니 마음이 편안해졌다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 15', 'WINDY', 27, '#FFE8CC', 126.6090, 33.4840, '2026-08-20T12:00:00', NULL),
    (16, 6, NULL, '돌담길 쉼터 6', '2026-08-18', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '잠시 머물며 오늘의 여행을 기억했다.', NULL, NULL, 'SUNNY', 27, '#FFE8CC', 126.6200, 33.4620, '2026-08-18T12:00:00', NULL),
    (17, 6, NULL, '해안길 산책 자리 6', '2026-08-19', NULL, NULL, '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 17', 'CLOUDY', 27, '#FFE8CC', 126.6220, 33.4740, '2026-08-19T12:00:00', NULL),
    (18, 6, NULL, '골목길 작은 쉼터 6', '2026-08-20', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_image.png"]', '목적지 없이 걸으니 마음이 편안해졌다.', '["https://jamkkanjejustorage.blob.core.windows.net/jamkkanjeju/guestbooke_test/test_audio.m4a"]', '산책 중 남긴 소리 18', 'WINDY', 27, '#FFE8CC', 126.6240, 33.4860, '2026-08-20T12:00:00', NULL);


-- ---------------------------------------------------------------------
-- ROAD_GUESTBOOK_LIKE : 활성 45건 + 취소 15건. 글마다 활성 좋아요 0~5개
-- 모든 사용자는 본인 글을 제외한 다른 사용자의 길바닥 방명록에 좋아요를 누른다.
--   방명록 1 = 3개, 방명록 3 = 2개, 방명록 2/4/5 = 0개
-- 취소된 좋아요는 deleted_at 필터 검증용이며 활성 개수에서 제외한다.
-- ---------------------------------------------------------------------

INSERT INTO `ROAD_GUESTBOOK_LIKE`
    (`id`, `road_guestbook_id`, `user_id`, `created_at`, `deleted_at`)
VALUES
    (1, 1, 2, '2026-08-22T13:00:00', NULL),
    (2, 1, 3, '2026-08-22T13:00:00', NULL),
    (3, 1, 4, '2026-08-22T13:00:00', NULL),
    (4, 1, 5, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (5, 2, 2, '2026-08-22T13:00:00', NULL),
    (6, 2, 3, '2026-08-22T13:00:00', NULL),
    (7, 2, 4, '2026-08-22T13:00:00', NULL),
    (8, 2, 5, '2026-08-22T13:00:00', NULL),
    (9, 2, 6, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (10, 3, 2, '2026-08-22T13:00:00', NULL),
    (11, 3, 3, '2026-08-22T13:00:00', NULL),
    (12, 3, 4, '2026-08-22T13:00:00', NULL),
    (13, 3, 5, '2026-08-22T13:00:00', NULL),
    (14, 3, 6, '2026-08-22T13:00:00', NULL),
    (15, 4, 3, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (16, 5, 3, '2026-08-22T13:00:00', NULL),
    (17, 5, 4, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (18, 6, 3, '2026-08-22T13:00:00', NULL),
    (19, 6, 4, '2026-08-22T13:00:00', NULL),
    (20, 6, 5, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (21, 7, 4, '2026-08-22T13:00:00', NULL),
    (22, 7, 5, '2026-08-22T13:00:00', NULL),
    (23, 7, 6, '2026-08-22T13:00:00', NULL),
    (24, 7, 1, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (25, 8, 4, '2026-08-22T13:00:00', NULL),
    (26, 8, 5, '2026-08-22T13:00:00', NULL),
    (27, 8, 6, '2026-08-22T13:00:00', NULL),
    (28, 8, 1, '2026-08-22T13:00:00', NULL),
    (29, 8, 2, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (30, 9, 4, '2026-08-22T13:00:00', NULL),
    (31, 9, 5, '2026-08-22T13:00:00', NULL),
    (32, 9, 6, '2026-08-22T13:00:00', NULL),
    (33, 9, 1, '2026-08-22T13:00:00', NULL),
    (34, 9, 2, '2026-08-22T13:00:00', NULL),
    (35, 10, 5, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (36, 11, 5, '2026-08-22T13:00:00', NULL),
    (37, 11, 6, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (38, 12, 5, '2026-08-22T13:00:00', NULL),
    (39, 12, 6, '2026-08-22T13:00:00', NULL),
    (40, 12, 1, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (41, 13, 6, '2026-08-22T13:00:00', NULL),
    (42, 13, 1, '2026-08-22T13:00:00', NULL),
    (43, 13, 2, '2026-08-22T13:00:00', NULL),
    (44, 13, 3, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (45, 14, 6, '2026-08-22T13:00:00', NULL),
    (46, 14, 1, '2026-08-22T13:00:00', NULL),
    (47, 14, 2, '2026-08-22T13:00:00', NULL),
    (48, 14, 3, '2026-08-22T13:00:00', NULL),
    (49, 14, 4, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (50, 15, 6, '2026-08-22T13:00:00', NULL),
    (51, 15, 1, '2026-08-22T13:00:00', NULL),
    (52, 15, 2, '2026-08-22T13:00:00', NULL),
    (53, 15, 3, '2026-08-22T13:00:00', NULL),
    (54, 15, 4, '2026-08-22T13:00:00', NULL),
    (55, 16, 1, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (56, 17, 1, '2026-08-22T13:00:00', NULL),
    (57, 17, 2, '2026-08-22T14:00:00', '2026-08-23T09:00:00'),
    (58, 18, 1, '2026-08-22T13:00:00', NULL),
    (59, 18, 2, '2026-08-22T13:00:00', NULL),
    (60, 18, 3, '2026-08-22T14:00:00', '2026-08-23T09:00:00');


-- ---------------------------------------------------------------------
-- TRAVEL_ENDING_CONTENT : 여행 마무리 엽서 2건
-- 완성된 엽서 이미지 URL 만 저장한다. (엽서에 담을 항목은 저장하지 않는다)
-- ---------------------------------------------------------------------

-- INSERT INTO `TRAVEL_ENDING_CONTENT`
--     (`id`, `user_id`, `image_url`, `created_at`)
-- VALUES
--     (1, 1, 'https://cdn.jamkkan-jeju.dev/travel-ending/1-1.png', '2026-08-20T21:10:00'),
--     (2, 1, 'https://cdn.jamkkan-jeju.dev/travel-ending/1-2.png', '2026-08-23T20:05:00');
