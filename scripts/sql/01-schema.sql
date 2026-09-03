-- =====================================================================
-- 잠깐, 제주 - 테이블 생성 DDL
-- 기준: docs/erd.md
-- 대상: MySQL 8.x / InnoDB / utf8mb4
--
-- 실행 예시)
--   mysql -h 127.0.0.1 -u tour -p tour < scripts/sql/01-schema.sql
-- =====================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `PICTURE_WITH_CHARACTER`;
DROP TABLE IF EXISTS `TRAVEL_ENDING_CONTENT`;
DROP TABLE IF EXISTS `ACQUIRED_AR_CHARACTER`;
DROP TABLE IF EXISTS `AR_CHARACTER`;
DROP TABLE IF EXISTS `ROAD_GUESTBOOK_LIKE`;
DROP TABLE IF EXISTS `ROAD_GUESTBOOK`;
DROP TABLE IF EXISTS `GUESTBOOK_LIKE`;
DROP TABLE IF EXISTS `GUESTBOOK`;
DROP TABLE IF EXISTS `TREASURE_MISSION_PROGRESS`;
DROP TABLE IF EXISTS `TREASURE_MISSION`;
DROP TABLE IF EXISTS `COOPERATIVE_ROLE_PROGRESS`;
DROP TABLE IF EXISTS `COOPERATIVE_MISSION_PARTICIPANT`;
DROP TABLE IF EXISTS `COOPERATIVE_ROLE_CARD`;
DROP TABLE IF EXISTS `COOPERATIVE_MISSION_PROGRESS`;
DROP TABLE IF EXISTS `COOPERATIVE_MISSION`;
DROP TABLE IF EXISTS `CULTURE_MISSION_PROGRESS`;
DROP TABLE IF EXISTS `CULTURE_MISSION`;
DROP TABLE IF EXISTS `GPS`;
DROP TABLE IF EXISTS `VISITED_LOCATION`;
DROP TABLE IF EXISTS `MISSION`;
DROP TABLE IF EXISTS `LOCATION`;
DROP TABLE IF EXISTS `STEP_COUNT`;
DROP TABLE IF EXISTS `USER_SETTING`;
DROP TABLE IF EXISTS `USER`;
DROP TABLE IF EXISTS `USER_TRAVEL_STYLE`;

SET FOREIGN_KEY_CHECKS = 1;


-- ---------------------------------------------------------------------
-- 사용자
-- ---------------------------------------------------------------------

CREATE TABLE `USER_TRAVEL_STYLE` (
    `id`               BIGINT       NOT NULL AUTO_INCREMENT,
    `user_type`        VARCHAR(20)  NOT NULL                COMMENT '여행 유형명',
    `type_description` VARCHAR(200) NOT NULL                COMMENT '유형 설명',
    `hashtags`         JSON         NOT NULL                COMMENT 'string[]',
    `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '여행 유형 마스터';

CREATE TABLE `USER` (
    `id`                   BIGINT      NOT NULL AUTO_INCREMENT,
    `expectation`          JSON        NULL                 COMMENT 'string[] 여행 기대 항목',
    `transportation`       JSON        NULL                 COMMENT 'string[] 이동수단',
    `travel_style`         JSON        NULL                 COMMENT 'string[] 자투리 시간 여행 방식',
    `user_travel_style_id` BIGINT      NULL                 COMMENT '진단된 여행 유형',
    `ar_character_id`      BIGINT      NULL                 COMMENT '배정된 AR 캐릭터',
    `nickname`             VARCHAR(20) NULL,
    `point`                INT         NOT NULL DEFAULT 0,
    `target_step`          INT         NOT NULL DEFAULT 10000  COMMENT '하루 목표 걸음 수',
    `access_token_hash`    CHAR(64)    NOT NULL                COMMENT '액세스 토큰 해시(SHA-256 hex)',
    `created_at`           DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`           DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user__access_token_hash` (`access_token_hash`),
    KEY `idx_user__travel_style` (`user_travel_style_id`),
    KEY `idx_user__ar_character` (`ar_character_id`),
    CONSTRAINT `fk_user__travel_style`
        FOREIGN KEY (`user_travel_style_id`) REFERENCES `USER_TRAVEL_STYLE` (`id`)
        ON DELETE SET NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '사용자';

CREATE TABLE `USER_SETTING` (
    `id`                        BIGINT   NOT NULL AUTO_INCREMENT,
    `user_id`                   BIGINT   NOT NULL,
    `push_notification`         BOOLEAN  NOT NULL DEFAULT TRUE,
    `near_mission_notification` BOOLEAN  NOT NULL DEFAULT TRUE,
    `created_at`                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_setting__user` (`user_id`),
    CONSTRAINT `fk_user_setting__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '사용자 알림 설정';

CREATE TABLE `STEP_COUNT` (
    `id`          BIGINT   NOT NULL AUTO_INCREMENT,
    `user_id`     BIGINT   NOT NULL,
    `saved_at`    DATETIME NOT NULL,
    `steps_count` INT      NOT NULL,
    `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    -- 사용자별 기록 날짜당 한 행만 둔다. (`saved_at` 은 기록 날짜의 KST 자정)
    -- 조회에 쓰던 (user_id, saved_at) 인덱스 역할도 이 유니크 키가 대신한다.
    UNIQUE KEY `uk_step_count__user_saved_at` (`user_id`, `saved_at`),
    CONSTRAINT `fk_step_count__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '걸음 수 기록';


-- ---------------------------------------------------------------------
-- 장소 / 미션
-- ---------------------------------------------------------------------

CREATE TABLE `LOCATION` (
    `id`                BIGINT       NOT NULL AUTO_INCREMENT,
    `content_id`        BIGINT       NOT NULL                COMMENT 'TourAPI contentId',
    `location_title`    VARCHAR(20)  NOT NULL,
    `location_address`  VARCHAR(100) NOT NULL,
    `location_category` VARCHAR(20)  NOT NULL,
    `radius`            INT          NOT NULL                COMMENT '인증 반경(m)',
    `mx`                DOUBLE       NOT NULL                COMMENT '경도(longitude)',
    `my`                DOUBLE       NOT NULL                COMMENT '위도(latitude)',
    `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_location__content_id` (`content_id`),
    KEY `idx_location__coord` (`mx`, `my`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '장소';

CREATE TABLE `MISSION` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT,
    `mission_type`  VARCHAR(50)  NOT NULL                COMMENT 'CULTURE | COOPERATIVE | TREASURE',
    `mission_title` VARCHAR(50)  NOT NULL,
    `description`   VARCHAR(200) NOT NULL,
    `step_detail`   JSON         NOT NULL                COMMENT '[{step, step_title, description}]',
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_mission__type` (`mission_type`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '미션 공통';

CREATE TABLE `VISITED_LOCATION` (
    `id`          BIGINT   NOT NULL AUTO_INCREMENT,
    `user_id`     BIGINT   NOT NULL,
    `location_id` BIGINT   NOT NULL,
    `visited_at`  DATETIME NOT NULL,
    `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_visited_location__user` (`user_id`, `visited_at`),
    KEY `idx_visited_location__location` (`location_id`),
    CONSTRAINT `fk_visited_location__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_visited_location__location`
        FOREIGN KEY (`location_id`) REFERENCES `LOCATION` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '방문한 장소';

CREATE TABLE `GPS` (
    `id`         BIGINT   NOT NULL AUTO_INCREMENT,
    `user_id`    BIGINT   NOT NULL,
    `mx`         DOUBLE   NOT NULL                COMMENT '경도(longitude)',
    `my`         DOUBLE   NOT NULL                COMMENT '위도(latitude)',
    `saved_at`   DATETIME NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_gps__user_saved_at` (`user_id`, `saved_at`),
    CONSTRAINT `fk_gps__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '사용자 위치 기록';


-- ---------------------------------------------------------------------
-- 문화 미션
-- ---------------------------------------------------------------------

CREATE TABLE `CULTURE_MISSION` (
    `id`               BIGINT   NOT NULL AUTO_INCREMENT,
    `mission_id`       BIGINT   NOT NULL,
    `quiz_total_count` INT      NOT NULL,
    `quiz_detail`      JSON     NOT NULL                COMMENT '[{quiz_index, img_url, question, options, answer, hint, explanation}]',
    `reward_detail`    JSON     NOT NULL                COMMENT '{ar_character_id, point, coupon_location, coupon_price}',
    `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_culture_mission__mission` (`mission_id`),
    CONSTRAINT `fk_culture_mission__mission`
        FOREIGN KEY (`mission_id`) REFERENCES `MISSION` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '문화 미션';

CREATE TABLE `CULTURE_MISSION_PROGRESS` (
    `id`                 BIGINT      NOT NULL AUTO_INCREMENT,
    `culture_mission_id` BIGINT      NOT NULL,
    `user_id`            BIGINT      NOT NULL,
    `mission_status`     VARCHAR(20) NOT NULL                COMMENT 'IN_PROGRESS | COMPLETED',
    `current_quiz_index` INT         NOT NULL DEFAULT 1,
    `correct_number`     INT         NOT NULL DEFAULT 0,
    `ar_character_reward_granted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'AR 캐릭터 보상 지급 여부',
    `point_reward_granted`        BOOLEAN NOT NULL DEFAULT FALSE COMMENT '포인트 보상 지급 여부',
    `coupon_reward_granted`       BOOLEAN NOT NULL DEFAULT FALSE COMMENT '쿠폰 보상 지급 여부',
    `completed_at`       DATETIME    NULL,
    `created_at`         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_culture_progress__user` (`user_id`, `mission_status`),
    KEY `idx_culture_progress__mission` (`culture_mission_id`),
    CONSTRAINT `fk_culture_progress__mission`
        FOREIGN KEY (`culture_mission_id`) REFERENCES `CULTURE_MISSION` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_culture_progress__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '문화 미션 진행도';


-- ---------------------------------------------------------------------
-- 협동 미션
-- ---------------------------------------------------------------------

CREATE TABLE `COOPERATIVE_MISSION` (
    `id`               BIGINT   NOT NULL AUTO_INCREMENT,
    `mission_id`       BIGINT   NOT NULL,
    `location_id`      BIGINT   NOT NULL,
    `reward_detail`    JSON     NOT NULL                COMMENT '{ar_character_id, point, coupon_location, coupon_price}',
    `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_cooperative_mission__mission` (`mission_id`),
    KEY `idx_cooperative_mission__location` (`location_id`),
    CONSTRAINT `fk_cooperative_mission__mission`
        FOREIGN KEY (`mission_id`) REFERENCES `MISSION` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cooperative_mission__location`
        FOREIGN KEY (`location_id`) REFERENCES `LOCATION` (`id`) ON DELETE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '협동 미션';

CREATE TABLE `COOPERATIVE_MISSION_PROGRESS` (
    `id`                     BIGINT       NOT NULL AUTO_INCREMENT,
    `cooperative_mission_id` BIGINT       NOT NULL,
    `current_step`           INT          NOT NULL DEFAULT 1,
    `mission_status`         VARCHAR(20)  NOT NULL                COMMENT 'IN_PROGRESS | COMPLETED',
    `team_token`             VARCHAR(100) NOT NULL                COMMENT '팀 단위 초대 토큰',
    `ar_character_reward_granted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'AR 캐릭터 보상 지급 여부',
    `point_reward_granted`        BOOLEAN NOT NULL DEFAULT FALSE COMMENT '포인트 보상 지급 여부',
    `coupon_reward_granted`       BOOLEAN NOT NULL DEFAULT FALSE COMMENT '쿠폰 보상 지급 여부',
    `completed_at`           DATETIME     NULL,
    `created_at`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`             DATETIME     NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cooperative_progress__team_token` (`team_token`),
    KEY `idx_cooperative_progress__mission` (`cooperative_mission_id`),
    CONSTRAINT `fk_cooperative_progress__mission`
        FOREIGN KEY (`cooperative_mission_id`) REFERENCES `COOPERATIVE_MISSION` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '협동 미션 진행도(방)';

CREATE TABLE `COOPERATIVE_ROLE_CARD` (
    `id`               BIGINT       NOT NULL AUTO_INCREMENT,
    `role_name`        VARCHAR(20)  NOT NULL,
    `role_description` VARCHAR(200) NOT NULL,
    `location_to_find` JSON         NOT NULL                COMMENT 'string[]',
    `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '협동 미션 역할 카드';

CREATE TABLE `COOPERATIVE_MISSION_PARTICIPANT` (
    `id`                              BIGINT       NOT NULL AUTO_INCREMENT,
    `cooperative_mission_progress_id` BIGINT       NOT NULL,
    `user_id`                         BIGINT       NOT NULL,
    `participant_status`              VARCHAR(20)  NOT NULL                COMMENT 'PENDING | ACCEPTED',
    `participant_role`                VARCHAR(20)  NOT NULL                COMMENT 'HOST | MEMBER',
    `joined_at`                       DATETIME     NULL,
    `created_at`                      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`                      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`                      DATETIME     NULL,
    PRIMARY KEY (`id`),
    KEY `idx_participant__progress` (`cooperative_mission_progress_id`),
    KEY `idx_participant__user` (`user_id`),
    CONSTRAINT `fk_participant__progress`
        FOREIGN KEY (`cooperative_mission_progress_id`) REFERENCES `COOPERATIVE_MISSION_PROGRESS` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_participant__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '협동 미션 참여자';

CREATE TABLE `COOPERATIVE_ROLE_PROGRESS` (
    `id`                       BIGINT       NOT NULL AUTO_INCREMENT,
    `participant_id`           BIGINT       NOT NULL,
    `cooperative_role_card_id` BIGINT       NOT NULL,
    `item_img_url`             VARCHAR(500) NULL,
    `progress_status`          VARCHAR(20)  NOT NULL                COMMENT 'IN_PROGRESS | COMPLETED',
    `completed_at`             DATETIME     NULL,
    `created_at`               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`               DATETIME     NULL,
    PRIMARY KEY (`id`),
    KEY `idx_role_progress__participant` (`participant_id`),
    KEY `idx_role_progress__role_card` (`cooperative_role_card_id`),
    CONSTRAINT `fk_role_progress__participant`
        FOREIGN KEY (`participant_id`) REFERENCES `COOPERATIVE_MISSION_PARTICIPANT` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_role_progress__role_card`
        FOREIGN KEY (`cooperative_role_card_id`) REFERENCES `COOPERATIVE_ROLE_CARD` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '협동 미션 역할 진행도';


-- ---------------------------------------------------------------------
-- 보물 찾기 미션
-- ---------------------------------------------------------------------

CREATE TABLE `TREASURE_MISSION` (
    `id`               BIGINT   NOT NULL AUTO_INCREMENT,
    `mission_id`       BIGINT   NOT NULL,
    `location_id`      BIGINT   NOT NULL,
    `item_total_count` INT      NOT NULL,
    `reward_detail`    JSON     NOT NULL                COMMENT '{ar_character_id, point, coupon_location, coupon_price}',
    `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_treasure_mission__mission` (`mission_id`),
    KEY `idx_treasure_mission__location` (`location_id`),
    CONSTRAINT `fk_treasure_mission__mission`
        FOREIGN KEY (`mission_id`) REFERENCES `MISSION` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_treasure_mission__location`
        FOREIGN KEY (`location_id`) REFERENCES `LOCATION` (`id`) ON DELETE RESTRICT
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '보물 찾기 미션';

CREATE TABLE `TREASURE_MISSION_PROGRESS` (
    `id`                     BIGINT      NOT NULL AUTO_INCREMENT,
    `treasure_mission_id`    BIGINT      NOT NULL,
    `user_id`                BIGINT      NOT NULL,
    `item_detail`            JSON        NOT NULL                COMMENT '[{index, mx, my}] 진행도별 보물 좌표',
    `current_found_item_idx` JSON        NOT NULL                COMMENT 'int[]',
    `current_step`           INT         NOT NULL DEFAULT 1      COMMENT '진행 단계. 1 | 2 | 3 (3 = 완료)',
    `mission_status`         VARCHAR(20) NOT NULL                COMMENT 'IN_PROGRESS | COMPLETED',
    `ar_character_reward_granted` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'AR 캐릭터 보상 지급 여부',
    `point_reward_granted`        BOOLEAN NOT NULL DEFAULT FALSE COMMENT '포인트 보상 지급 여부',
    `coupon_reward_granted`       BOOLEAN NOT NULL DEFAULT FALSE COMMENT '쿠폰 보상 지급 여부',
    `completed_at`           DATETIME    NULL,
    `created_at`             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_treasure_progress__user` (`user_id`, `mission_status`),
    KEY `idx_treasure_progress__mission` (`treasure_mission_id`),
    CONSTRAINT `fk_treasure_progress__mission`
        FOREIGN KEY (`treasure_mission_id`) REFERENCES `TREASURE_MISSION` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_treasure_progress__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '보물 찾기 진행도';


-- ---------------------------------------------------------------------
-- 방명록
-- ---------------------------------------------------------------------

CREATE TABLE `GUESTBOOK` (
    `id`                 BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`            BIGINT       NOT NULL,
    `location_id`        BIGINT       NOT NULL,
    `visited_at`         DATE         NOT NULL,
    `content_img_url`    JSON         NULL                    COMMENT 'string[]',
    `content_writing`    VARCHAR(500) NULL,
    `content_audio_url`  JSON         NULL                    COMMENT 'string[]',
    `audio_title`        VARCHAR(50)  NULL                    COMMENT '녹음 파일 제목',
    `content_weather`    VARCHAR(20)  NULL,
    `content_temperature_celsius` DECIMAL(4,1) NULL           COMMENT '섭씨 기온',
    `content_color_code` VARCHAR(20)  NULL,
    `saved_at`           DATETIME     NOT NULL,
    `mission_id`         BIGINT       NULL,
    `created_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`         DATETIME     NULL,
    PRIMARY KEY (`id`),
    KEY `idx_guestbook__user_visited_at` (`user_id`, `visited_at`),
    KEY `idx_guestbook__location` (`location_id`),
    KEY `idx_guestbook__mission` (`mission_id`),
    CONSTRAINT `fk_guestbook__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_guestbook__location`
        FOREIGN KEY (`location_id`) REFERENCES `LOCATION` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_guestbook__mission`
        FOREIGN KEY (`mission_id`) REFERENCES `MISSION` (`id`) ON DELETE SET NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '장소 방명록';

CREATE TABLE `GUESTBOOK_LIKE` (
    `id`           BIGINT   NOT NULL AUTO_INCREMENT,
    `guestbook_id` BIGINT   NOT NULL,
    `user_id`      BIGINT   NOT NULL,
    `created_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `deleted_at`   DATETIME NULL,
    PRIMARY KEY (`id`),
    -- 한 사용자는 한 방명록에 좋아요를 한 행으로만 갖는다.
    -- 취소는 행 삭제가 아니라 `deleted_at` 소프트 삭제이고, 다시 누르면 같은 행을 되살린다.
    UNIQUE KEY `uk_guestbook_like__guestbook_user` (`guestbook_id`, `user_id`),
    KEY `idx_guestbook_like__user` (`user_id`),
    CONSTRAINT `fk_guestbook_like__guestbook`
        FOREIGN KEY (`guestbook_id`) REFERENCES `GUESTBOOK` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_guestbook_like__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '장소 방명록 좋아요';

CREATE TABLE `ROAD_GUESTBOOK` (
    `id`                 BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`            BIGINT       NOT NULL,
    `location_id`        BIGINT       NULL,
    `location_alias`     VARCHAR(100) NOT NULL                COMMENT '사용자가 붙인 장소 이름',
    `visited_at`         DATE         NOT NULL,
    `content_img_url`    JSON         NULL                    COMMENT 'string[]',
    `content_writing`    VARCHAR(500) NULL,
    `content_audio_url`  JSON         NULL                    COMMENT 'string[]',
    `audio_title`        VARCHAR(50)  NULL                    COMMENT '녹음 파일 제목',
    `content_weather`    VARCHAR(20)  NULL,
    `content_temperature_celsius` DECIMAL(4,1) NULL           COMMENT '섭씨 기온',
    `content_color_code` VARCHAR(20)  NULL,
    `mx`                 DOUBLE       NOT NULL                COMMENT '경도(longitude)',
    `my`                 DOUBLE       NOT NULL                COMMENT '위도(latitude)',
    `saved_at`           DATETIME     NOT NULL,
    `created_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`         DATETIME     NULL,
    PRIMARY KEY (`id`),
    KEY `idx_road_guestbook__user_visited_at` (`user_id`, `visited_at`),
    KEY `idx_road_guestbook__location` (`location_id`),
    CONSTRAINT `fk_road_guestbook__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_road_guestbook__location`
        FOREIGN KEY (`location_id`) REFERENCES `LOCATION` (`id`) ON DELETE SET NULL
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '길 위의 방명록';

CREATE TABLE `ROAD_GUESTBOOK_LIKE` (
    `id`                BIGINT   NOT NULL AUTO_INCREMENT,
    `road_guestbook_id` BIGINT   NOT NULL,
    `user_id`           BIGINT   NOT NULL,
    `created_at`        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `deleted_at`        DATETIME NULL,
    PRIMARY KEY (`id`),
    -- 한 사용자는 한 방명록에 좋아요를 한 행으로만 갖는다.
    -- 취소는 행 삭제가 아니라 `deleted_at` 소프트 삭제이고, 다시 누르면 같은 행을 되살린다.
    UNIQUE KEY `uk_road_guestbook_like__guestbook_user` (`road_guestbook_id`, `user_id`),
    KEY `idx_road_guestbook_like__user` (`user_id`),
    CONSTRAINT `fk_road_guestbook_like__guestbook`
        FOREIGN KEY (`road_guestbook_id`) REFERENCES `ROAD_GUESTBOOK` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_road_guestbook_like__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '길 위의 방명록 좋아요';


-- ---------------------------------------------------------------------
-- AR 캐릭터 / 여행 마무리
-- ---------------------------------------------------------------------

CREATE TABLE `AR_CHARACTER` (
    `id`                    BIGINT       NOT NULL AUTO_INCREMENT,
    `character_name`        VARCHAR(50)  NOT NULL,
    `character_description` VARCHAR(200) NOT NULL,
    `character_story_title` VARCHAR(200) NOT NULL                COMMENT '캐릭터 이야기 제목',
    `acquire_condition`     VARCHAR(200) NOT NULL,
    `character_img_url`     VARCHAR(500) NOT NULL,
    `hashtags`              JSON         NOT NULL                COMMENT 'string[]',
    `created_at`            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = 'AR 캐릭터 마스터';

-- USER.ar_character_id FK 는 AR_CHARACTER 생성 이후에 추가한다.
ALTER TABLE `USER`
    ADD CONSTRAINT `fk_user__ar_character`
        FOREIGN KEY (`ar_character_id`) REFERENCES `AR_CHARACTER` (`id`)
        ON DELETE SET NULL;

CREATE TABLE `ACQUIRED_AR_CHARACTER` (
    `id`                  BIGINT   NOT NULL AUTO_INCREMENT,
    `ar_character_id`     BIGINT   NOT NULL,
    `user_id`             BIGINT   NOT NULL,
    `acquired_mission_id` BIGINT   NOT NULL,
    `created_at`          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_acquired__user_character` (`user_id`, `ar_character_id`),
    KEY `idx_acquired__character` (`ar_character_id`),
    KEY `idx_acquired__mission` (`acquired_mission_id`),
    CONSTRAINT `fk_acquired__character`
        FOREIGN KEY (`ar_character_id`) REFERENCES `AR_CHARACTER` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_acquired__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_acquired__mission`
        FOREIGN KEY (`acquired_mission_id`) REFERENCES `MISSION` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '획득한 AR 캐릭터';

CREATE TABLE `TRAVEL_ENDING_CONTENT` (
    `id`             BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`        BIGINT       NOT NULL,
    `travel_summary` VARCHAR(500) NULL,
    `visited_place`  BOOLEAN      NOT NULL DEFAULT FALSE,
    `missions`       BOOLEAN      NOT NULL DEFAULT FALSE,
    `pictures`       BOOLEAN      NOT NULL DEFAULT FALSE,
    `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_travel_ending__user` (`user_id`),
    CONSTRAINT `fk_travel_ending__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '여행 마무리 엽서';

CREATE TABLE `PICTURE_WITH_CHARACTER` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT,
    `user_id`     BIGINT       NOT NULL,
    `picture_url` VARCHAR(500) NOT NULL,
    `saved_at`    DATETIME     NOT NULL,
    `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_picture__user_saved_at` (`user_id`, `saved_at`),
    CONSTRAINT `fk_picture__user`
        FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = 'AR 캐릭터와 찍은 사진';
