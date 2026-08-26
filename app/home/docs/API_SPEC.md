### API 설명

사용자가 메인 홈 화면에 진입하거나 홈을 새로고침할 때 호출한다. 또한 사용자가 위치를 직접 선택하면 호출한다. 이때는 해당 행정구역의 대표 위도와 경도를 전송한다.

추천 콘텐츠, 진행 중인 미션, 쌓인 방명록 수와 사용자 캐릭터 이미지를 한 번에 조회한다.

요청한 사용자 위치를 기준으로 미션 장소까지의 거리는 미터 단위, 예상 소요 시간은 분 단위로 반환한다.

---

### 요청 Query

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `latitude` | number | O | 현재 위치 또는 사용자가 선택한 위치의 위도 |
| `longitude` | number | O | 현재 위치 또는 사용자가 선택한 위치의 경도 |

요청 예시

```
GET /api/v1/users/me/home?latitude=33.5572&longitude=126.7591
```

---

### 요청 Path

없음

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `missionRecommend` | object[] | 홈에 노출할 추천 미션 목록 |
| `missionRecommend[].missionId` | number | missionType에 해당하는 유형별 세부 미션 id |
| `missionRecommend[].missionType` | string | 미션 유형. `CULTURE | TREASURE | COOPERATIVE` |
| `missionRecommend[].missionTitle` | string | 미션 이름 |
| `missionRecommend[].locationTitle` | string | null | 미션 장소명. 장소가 없는 미션이면 `null` |
| `missionRecommend[].location` | object | null | 미션 장소 좌표. 장소가 없는 미션이면 `null` |
| `missionRecommend[].location.lat` | number | 미션 장소의 위도 |
| `missionRecommend[].location.lng` | number | 미션 장소의 경도 |
| `missionRecommend[].distanceMeter` | number | null | 사용자 위치에서 미션 장소까지의 거리(m). 장소가 없으면 `null` |
| `missionRecommend[].durationMinutes` | number | null | 사용자 위치에서 미션 장소까지의 예상 소요 시간(분). 장소가 없으면 `null` |
| `progressMission` | object[] | 사용자가 진행 중인 미션 목록 |
| `progressMission[].missionId` | number | missionType에 해당하는 유형별 세부 미션 진행 대상 id |
| `progressMission[].missionType` | string | 미션 유형. `CULTURE | TREASURE | COOPERATIVE` |
| `progressMission[].missionTitle` | string | 진행 중인 미션 이름 |
| `progressMission[].locationTitle` | string | null | 미션 장소명. 장소가 없는 미션이면 `null` |
| `progressMission[].distanceMeter` | number | null | 사용자 위치에서 미션 장소까지의 거리(m). 장소가 없으면 `null` |
| `progressMission[].durationMinutes` | number | null | 사용자 위치에서 미션 장소까지의 예상 소요 시간(분). 장소가 없으면 `null` |
| `progressMission[].totalStep` | number | 미션의 전체 단계 수 |
| `progressMission[].currentStep` | number | 사용자가 현재 진행 중인 단계 |
| `guestbookCount` | number | 쌓인 방명록 갯수 |
| `characterImgUrl` | string | null | 사용자에게 배정된 AR 캐릭터 이미지 URL, 없으면 `null` |

```json
{
  "missionRecommend": [
    {
      "missionId": 12,
      "missionType": "TREASURE",
      "missionTitle": "보물 찾기",
      "locationTitle": "새별 오름",
      "location": {
        "lat": 33.3663,
        "lng": 126.3577
      },
      "distanceMeter": 44100,
      "durationMinutes": 58
    },
    {
      "missionId": 16,
      "missionType": "COOPERATIVE",
      "missionTitle": "함께 키우는 귤나무",
      "locationTitle": "종화네 과수원",
      "location": {
        "lat": 33.4507,
        "lng": 126.5707
      },
      "distanceMeter": 23100,
      "durationMinutes": 34
    },
    {
      "missionId": 36,
      "missionType": "CULTURE",
      "missionTitle": "오늘의 제주 퀴즈",
      "locationTitle": null,
      "location": null,
      "distanceMeter": null,
      "durationMinutes": null
    }
  ],
  "progressMission": [
    {
      "missionId": 52,
      "missionType": "TREASURE",
      "missionTitle": "보물 찾기",
      "locationTitle": "오구포구",
      "distanceMeter": 28700,
      "durationMinutes": 41,
      "totalStep": 3,
      "currentStep": 1
    }
  ],
  "guestbookCount": 2,
  "characterImgUrl": "https://example.com/images/characters/jacheongbi.png"
}
```

---

### 오류 응답 데이터

없음

---

### 추가 고려 사항

없음