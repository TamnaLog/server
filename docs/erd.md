erDiagram
USER {
	bigint id PK "NOT NULL"
	json expectation "NULL, json: {categories: string[]}"
	varchar_50 transportation "NULL, Enum: WALK | BUS | CAR | BICYCLE"
	varchar_50 travel_style "NULL, Enum: RIGHT HERE | NEAR AROUND | NEAR DESTINATION"
	bigint ar_character_id FK "NOT NULL"
	json user_type_detail "NOT NULL, json: {user_type: string, type_description: string, hashtags: string[]}"
	varchar_20 nickname "NULL"
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
	bigint user_id FK "NOT NULL"
	datetime saved_at "NOT NULL"
	int steps_count "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

MISSION {
	bigint id PK "NOT NULL"
	varchar_50 mission_type "NOT NULL, Enum: CULTURE | COOPERATIVE | TREASURE"
	varchar_50 mission_title "NOT NULL"
	varchar_200 description "NOT NULL"
	int duration_time "NOT NULL"
	json reward_detail "NOT NULL, json: {ar_character: string, point: int, coupon_location: string, coupon_price: int}"
	json step_detail "NOT NULL, json: {step: int, step_title: string, description: string}"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

LOCATION {
	bigint id PK "NOT NULL"
	varchar_20 location_title "NOT NULL"
	varchar_100 location_address "NOT NULL"
	varchar_20 location_category "NOT NULL"
	double mx "NOT NULL"
	double my "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

CULTURE_MISSION {
	bigint mission_id PK, FK "NOT NULL"
	int quiz_count "NOT NULL"
	json quiz_detail "NOT NULL, json: {quiz_index: int, img_url: string, question: string, answer: string}"
}

CULTURE_MISSION_PROGRESS {
	bigint id PK "NOT NULL"
	bigint culture_mission_id FK "NOT NULL"
	bigint user_id FK "NOT NULL"
	varchar_20 mission_status "NOT NULL, Enum: INPROGRESS, COMPLETED"
	int current_quiz_num "NOT NULL, DEFAULT: 0"
	int correct_number "NOT NULL, DEFAULT: 0"
	datetime completed_at "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

COOPERATIVE_MISSION {
	bigint mission_id PK, FK "NOT NULL"
	int member_capacity "NOT NULL"
	bigint location_id FK "NOT NULL"
}

COOPERATIVE_MISSION_ROLE {
	bigint id PK "NOT NULL"
	bigint cooperative_mission_id FK "NOT NULL"
	varchar_50 role_title "NOT NULL"
	varchar_200 role_description "NOT NULL"
	varchar_200 role_complete_comment "NOT NULL"
	varchar_10 item_name "NOT NULL"
	int total_item_count "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

COOPERATIVE_MISSION_MEMBER_PROGRESS {
	bigint id PK "NOT NULL"
	bigint cooperative_mission_role_id FK "NOT NULL"
	bigint user_id FK "NOT NULL"
	int current_step "NOT NULL, DEFAULT: 0"
	int current_item_count "NOT NULL, DEFAULT: 0"
	json item_img_url "NULL, json: {url: string[]}"
	varchar_20 mission_status "NOT NULL, Enum: INPROGRESS, COMPLETED"
	datetime completed_at "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

TREASURE_MISSION {
	bigint mission_id PK, FK "NOT NULL"
	int treasure_count "NOT NULL"
}

TREASURE_MISSION_ITEM {
	bigint id PK "NOT NULL"
	bigint treasure_mission_id FK "NOT NULL"
	bigint location_id FK "NOT NULL"
	int item_index "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

TREASURE_MISSION_PROGRESS {
	bigint id PK "NOT NULL"
	bigint treasure_mission_id FK "NOT NULL"
	bigint user_id FK "NOT NULL"
	json current_found_item_idx "NOT NULL, json: {idx: int[]}"
	varchar_20 mission_status "NOT NULL, Enum: INPROGRESS, COMPLETED"
	json picture_with_character "NULL, json: {url: string[]}"
	datetime completed_at "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

GUESTBOOK {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	bigint location_id FK "NULL"
	date visited_at "NOT NULL"
	json content_img_url "NULL, json: {url: string[]}"
	varchar_500 content_writing "NULL"
	json content_audio_url "NULL, json: {url: string[]}"
	varchar_20 content_weather "NULL"
	varchar_20 content_color "NULL"
	datetime saved_at "NOT NULL"
	varchar_50 mission_title "NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

ACQUIRED_AR_CHARACTER {
    bigint id PK "NOT NULL"
    bigint ar_character_id FK "NOT NULL"
    bigint user_id FK "NOT NULL"
    varchar_20 acquired_in "NOT NULL"
    date acquired_at "NOT NULL"
    datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
    datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

AR_CHARACTER {
	bigint id PK "NOT NULL"
	varchar_50 character_name "NOT NULL"
	varchar_200 character_description "NOT NULL"
	varchar_200 acquire_condition "NOT NULL"
	varchar_100 character_img_url "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

TRAVEL_ENDING_CONTENT {
	bigint id PK "NOT NULL"
	bigint user_id FK "NOT NULL"
	varchar_100 content_img_url "NOT NULL"
	datetime created_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
	datetime updated_at "NOT NULL, DEFAULT: CURRENT_TIMESTAMP"
}

USER ||--|| USER_SETTING : has
USER ||--o{ STEP_COUNT : records
USER ||--o{ CULTURE_MISSION_PROGRESS : progresses
CULTURE_MISSION ||--o{ CULTURE_MISSION_PROGRESS : has
USER ||--o{ COOPERATIVE_MISSION_MEMBER_PROGRESS : participates
COOPERATIVE_MISSION ||--o{ COOPERATIVE_MISSION_ROLE : has
COOPERATIVE_MISSION_ROLE ||--o{ COOPERATIVE_MISSION_MEMBER_PROGRESS : tracks
USER ||--o{ TREASURE_MISSION_PROGRESS : progresses
TREASURE_MISSION ||--o{ TREASURE_MISSION_PROGRESS : has
USER ||--o{ GUESTBOOK : writes
USER ||--o{ ACQUIRED_AR_CHARACTER : acquires
AR_CHARACTER ||--o{ ACQUIRED_AR_CHARACTER : is_acquired
AR_CHARACTER ||--o{ USER : represents
USER ||--o{ TRAVEL_ENDING_CONTENT : has
MISSION ||--|| CULTURE_MISSION : is
MISSION ||--|| COOPERATIVE_MISSION : is
MISSION ||--|| TREASURE_MISSION : is
LOCATION ||--o{ COOPERATIVE_MISSION : hosts
LOCATION ||--o{ GUESTBOOK : visited_at
TREASURE_MISSION ||--o{ TREASURE_MISSION_ITEM : has
LOCATION ||--o{ TREASURE_MISSION_ITEM : contains
