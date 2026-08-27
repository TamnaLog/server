## 익명 사용자 발급
- http 메서드: post
- domain: auth
- endpoint: /api/v1/auth/anonymous

### API 설명

앱이 기기 보안 저장소에서 기존 액세스 토큰을 찾을 수 없을 때 익명 사용자를 최초 발급받기 위해 호출한다.

백엔드는 새로운 `USER` 데이터와 예측하기 어려운 액세스 토큰을 생성한다. 토큰 원문은 응답으로 한 번만 반환하고, DB에는 원문을 SHA-256으로 변환한 해시만 저장한다.

프론트는 응답받은 `accessToken`을 기기 보안 저장소에 보관하고, 이후 인증이 필요한 모든 API 요청의 `Authorization` 헤더에 Bearer 토큰으로 전달한다.

이 API는 아직 사용자 토큰이 없는 상태에서 호출하므로 `Authorization` 헤더를 요구하지 않는다.

---

### 요청 Query

없음

---

### 요청 Path

없음

---

### 요청 Body

없음

요청 예시

```http
POST /api/v1/auth/anonymous
```

---

### 정상 응답 데이터

Status Code : 201

새로운 익명 사용자와 액세스 토큰을 생성한 경우

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `accessToken` | string | 이후 API 요청에서 현재 사용자를 식별할 액세스 토큰 원문 |
| `tokenType` | string | 인증 헤더에 사용할 토큰 타입. 항상 `Bearer` |

```json
{
  "accessToken": "tS9o62fIY_f9D7CqTKEQWtu7d9wwGnJqfR4QZ8LslXo",
  "tokenType": "Bearer"
}
```

이후 API 요청 예시

```http
Authorization: Bearer tS9o62fIY_f9D7CqTKEQWtu7d9wwGnJqfR4QZ8LslXo
```

---

### 오류 응답 데이터

별도로 정의하는 오류 응답은 없다.

사용자 또는 토큰 생성 중 예상하지 못한 오류가 발생하면 공통 `500 INTERNAL_SERVER_ERROR` 응답을 반환한다.
