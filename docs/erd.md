```mermaid
erDiagram
USER {
	bigint id PK "NOT NULL"
	json expectation "NULL, json: string[]"
	json transportation "NULL, json: string[]"
	json travel_style "NULL, json: string[]"
	bigint user_travel_style_id FK "NULL"
	bigint ar_character_id FK "NULL"
	varchar_20 nickname "NULL"
	int point "NOT NULL, DEFAULT: 0"
	int target_step "NOT NULL, DEFAULT: 10000"
    char_64 access_token_hash UK "NOT NULL, UNIQUE"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

USER_TRAVEL_STYLE {
	bigint id PK "NOT NULL"
	varchar_20 user_type "NOT NULL"
	varchar_200 type_description "NOT NULL"
	json hashtags "NOT NULL, json: string[]"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

USER_SETTING {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	boolean push_notification "NOT NULL, DEFAULT: TRUE"
	boolean near_mission_notification "NOT NULL, DEFAULT: TRUE"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

STEP_COUNT {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL, UNIQUE"
	datetime saved_at "NOT NULL, UNIQUE"
	int steps_count "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

MISSION {
	bigint id PK "NOT NULL"
	varchar_50 mission_type "NOT NULL, Enum: CULTURE | COOPERATIVE | TREASURE"
	varchar_50 mission_title "NOT NULL"
	varchar_200 description "NOT NULL"
	json step_detail "NOT NULL, json: {step: int, step_title: string, description: string}"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

LOCATION {
	bigint id PK "NOT NULL"
	bigint content_id "NOT NULL"
	varchar_20 location_title "NOT NULL"
	varchar_100 location_address "NOT NULL"
	varchar_20 location_category "NOT NULL"
	int radius "NOT NULL"
	double mx "NOT NULL"
	double my "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

VISITED_LOCATION {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	bigint location_id FK "NOT NULL"
	datetime visited_at "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

GPS {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	double mx "NOT NULL"
	double my "NOT NULL"
	datetime saved_at "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

CULTURE_MISSION {
	bigint id PK "NOT NULL"
	bigint mission_id FK "NOT NULL"
	int quiz_total_count "NOT NULL"
	json quiz_detail "NOT NULL, json: {quiz_index: int, img_url: string | null, question: string, options: string[] | null, answer: string, hint: string, explanation: string}"
	json reward_detail "NOT NULL, json: {ar_character_id: int, point: int, coupon_location: string, coupon_price: int}"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

CULTURE_MISSION_PROGRESS {
	bigint id PK "NOT NULL"
	bigint culture_mission_id FK "NOT NULL"
	bigint user_id FK "NOT NULL"
	varchar_20 mission_status "NOT NULL, Enum: IN_PROGRESS, COMPLETED"
	int current_quiz_index "NOT NULL, DEFAULT: 1"
	int correct_number "NOT NULL, DEFAULT: 0"
	boolean ar_character_reward_granted "NOT NULL, DEFAULT: FALSE"
	boolean point_reward_granted "NOT NULL, DEFAULT: FALSE"
	boolean coupon_reward_granted "NOT NULL, DEFAULT: FALSE"
	datetime completed_at "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

COOPERATIVE_MISSION {
	bigint id PK "NOT NULL"
	bigint mission_id FK "NOT NULL"
	bigint location_id FK "NOT NULL"
	json reward_detail "NOT NULL, json: {ar_character_id: int, point: int, coupon_location: string, coupon_price: int}"
    datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

COOPERATIVE_MISSION_PROGRESS {
    bigint id PK "NOT NULL"
    bigint cooperative_mission_id FK "NOT NULL"
    int current_step "NOT NULL, DEFAULT: 1"
    varchar_20 mission_status "NOT NULL, Enum: IN_PROGRESS, COMPLETED"
    varchar_100 team_token "NOT NULL, UNIQUE"
    boolean ar_character_reward_granted "NOT NULL, DEFAULT: FALSE"
    boolean point_reward_granted "NOT NULL, DEFAULT: FALSE"
    boolean coupon_reward_granted "NOT NULL, DEFAULT: FALSE"
    datetime completed_at "NULL"
    datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime deleted_at "NULL"
}

COOPERATIVE_ROLE_CARD {
	bigint id PK "NOT NULL"
	varchar_20 role_name "NOT NULL"
	varchar_200 role_description "NOT NULL"
	json location_to_find "NOT NULL, json: string[]"
    datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

COOPERATIVE_MISSION_PARTICIPANT {
    bigint id PK "NOT NULL"
    bigint cooperative_mission_progress_id FK "NOT NULL"
    bigint user_id FK "NOT NULL"
	varchar_20 participant_status "NOT NULL, Enum: PENDING | ACCEPTED"
    varchar_20 participant_role "NOT NULL, Enum: HOST | MEMBER"
    datetime joined_at "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime deleted_at "NULL"
}

COOPERATIVE_ROLE_PROGRESS {
    bigint id PK "NOT NULL"
    bigint participant_id FK "NOT NULL"
    bigint cooperative_role_card_id FK "NOT NULL"
    varchar_500 item_img_url "NULL"
    varchar_20 progress_status "NOT NULL, Enum: IN_PROGRESS, COMPLETED"
    datetime completed_at "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime deleted_at "NULL"
}

TREASURE_MISSION {
	bigint id PK "NOT NULL"
	bigint mission_id FK "NOT NULL"
	bigint location_id FK "NOT NULL"
	int item_total_count "NOT NULL"
	json reward_detail "NOT NULL, json: {ar_character_id: int, point: int, coupon_location: string, coupon_price: int}"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

TREASURE_MISSION_PROGRESS {
	bigint id PK "NOT NULL"
	bigint treasure_mission_id FK "NOT NULL"
	bigint user_id FK "NOT NULL"
	json item_detail "NOT NULL, json: [{index: int, mx: float, my: float}]"
	json current_found_item_idx "NOT NULL, json: int[]"
	int current_step "NOT NULL, DEFAULT: 1"
	varchar_20 mission_status "NOT NULL, Enum: IN_PROGRESS, COMPLETED"
	boolean ar_character_reward_granted "NOT NULL, DEFAULT: FALSE"
	boolean point_reward_granted "NOT NULL, DEFAULT: FALSE"
	boolean coupon_reward_granted "NOT NULL, DEFAULT: FALSE"
	datetime completed_at "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

GUESTBOOK {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	bigint location_id FK "NOT NULL"
	date visited_at "NOT NULL"
	json content_img_url "NULL, json: string[]"
	varchar_500 content_writing "NULL"
	json content_audio_url "NULL, json: string[]"
	varchar_50 audio_title "NULL"
	varchar_20 content_weather "NULL"
	decimal(4,1) content_temperature_celsius "NULL"
	varchar_20 content_color_code "NULL"
	datetime saved_at "NOT NULL"
	bigint mission_id FK "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime deleted_at "NULL"
}

GUESTBOOK_LIKE {
    bigint id PK "NOT NULL"
    bigint guestbook_id FK "NOT NULL, UNIQUE"
    bigint user_id FK "NOT NULL, UNIQUE"
    datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime deleted_at "NULL"
}

ROAD_GUESTBOOK {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	bigint location_id FK "NULL"
	varchar_100 location_alias "NOT NULL"
	date visited_at "NOT NULL"
	json content_img_url "NULL, json: string[]"
	varchar_500 content_writing "NULL"
	json content_audio_url "NULL, json: string[]"
	varchar_50 audio_title "NULL"
	varchar_20 content_weather "NULL"
	decimal(4,1) content_temperature_celsius "NULL"
	varchar_20 content_color_code "NULL"
	double mx "NOT NULL"
	double my "NOT NULL"
	datetime saved_at "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime deleted_at "NULL"
}

ROAD_GUESTBOOK_LIKE {
    bigint id PK "NOT NULL"
    bigint road_guestbook_id FK "NOT NULL, UNIQUE"
    bigint user_id FK "NOT NULL, UNIQUE"
    datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime deleted_at "NULL"
}

ACQUIRED_AR_CHARACTER {
    bigint id PK "NOT NULL"
    bigint ar_character_id FK "NOT NULL"
    bigint user_id FK "NOT NULL"
    bigint acquired_mission_id FK "NOT NULL"
    datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

AR_CHARACTER {
	bigint id PK "NOT NULL"
	varchar_50 character_name "NOT NULL"
	varchar_200 character_description "NOT NULL"
	varchar_200 character_story_title "NOT NULL"
	varchar_200 acquire_condition "NOT NULL"
	varchar_500 character_img_url "NOT NULL"
	json hashtags "NOT NULL, json: string[]"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

TRAVEL_ENDING_CONTENT {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	varchar_500 travel_summary "NULL"
	boolean visited_place "NOT NULL"
	boolean missions "NOT NULL"
	boolean pictures "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

PICTURE_WITH_CHARACTER {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	varchar_500 picture_url "NOT NULL"
	datetime saved_at "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}


USER_TRAVEL_STYLE o|--o{ USER : has

USER ||--o| USER_SETTING : has
USER ||--o{ STEP_COUNT : records
USER ||--o{ VISITED_LOCATION : visits
USER ||--o{ GPS : records
USER ||--o{ CULTURE_MISSION_PROGRESS : progresses
USER ||--o{ COOPERATIVE_MISSION_PARTICIPANT : joins
USER ||--o{ TREASURE_MISSION_PROGRESS : progresses
USER ||--o{ GUESTBOOK : writes
USER ||--o{ ROAD_GUESTBOOK : writes
USER ||--o{ GUESTBOOK_LIKE : likes
USER ||--o{ ROAD_GUESTBOOK_LIKE : likes
USER ||--o{ ACQUIRED_AR_CHARACTER : acquires
USER ||--o{ TRAVEL_ENDING_CONTENT : owns
USER ||--o{ PICTURE_WITH_CHARACTER : has

LOCATION ||--o{ VISITED_LOCATION : visited_by
LOCATION ||--o{ GUESTBOOK : contains
LOCATION o|--o{ ROAD_GUESTBOOK : references
LOCATION ||--o{ COOPERATIVE_MISSION : hosts
LOCATION ||--o{ TREASURE_MISSION : hosts

GUESTBOOK ||--o{ GUESTBOOK_LIKE : liked_by
ROAD_GUESTBOOK ||--o{ ROAD_GUESTBOOK_LIKE : liked_by

MISSION ||--o{ CULTURE_MISSION : categorizes
MISSION ||--o{ COOPERATIVE_MISSION : categorizes
MISSION ||--o{ TREASURE_MISSION : categorizes
MISSION o|--o{ GUESTBOOK : relates_to
MISSION ||--o{ ACQUIRED_AR_CHARACTER : rewards

CULTURE_MISSION ||--o{ CULTURE_MISSION_PROGRESS : tracks

COOPERATIVE_MISSION ||--o{ COOPERATIVE_MISSION_PROGRESS : tracks
COOPERATIVE_MISSION_PROGRESS ||--o{ COOPERATIVE_MISSION_PARTICIPANT : has
COOPERATIVE_MISSION_PARTICIPANT ||--o| COOPERATIVE_ROLE_PROGRESS : assigned
COOPERATIVE_ROLE_CARD ||--o{ COOPERATIVE_ROLE_PROGRESS : assigned_as

TREASURE_MISSION ||--o{ TREASURE_MISSION_PROGRESS : tracks

AR_CHARACTER ||--o{ ACQUIRED_AR_CHARACTER : acquired_as
AR_CHARACTER o|--o{ USER : assigned_to
```
