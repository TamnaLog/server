## 주문 상세 조회
- http 메서드: get
- domain: market
- endpoint: /api/v1/users/me/trades/{tradeId}


### API 설명

거래 내역 화면에서 사용자가 특정 거래를 클릭했을 때 호출한다.

`tradeId`를 기준으로 거래 상세 정보와 거래 진행 상태 타임라인을 조회한다.

---

### 처리 정책

- `tradeId`에 해당하는 거래가 존재하면 거래 상태와 상품 정보를 반환한다.
- 현재 사용자가 구매자인 거래만 조회할 수 있다. 로그인 구현 전에는 `trade.buyer_user_id = 1`인 거래만 조회한다.
- 거래 상태가 `PAID`, `SENT`, `SHIPPING`, `DELIVERED`, `COMPLETED` 중 어떤 상태이든 조회할 수 있다.
- 거래가 완료된 이후에도 주문 상세 조회는 가능하다.
- `tradeId`에 해당하는 거래가 존재하지 않거나, 현재 사용자가 구매자인 거래가 아니면 404: TRADE_NOT_FOUND를 반환한다.
- 로그인 구현 전에는 현재 사용자를 항상 id=1로 간주한다.
- 날짜/시간 값은 한국시간 기준 offset 없는 ISO 8601 형식으로 반환한다.
- 각 진행 단계의 시각은 `trade` 테이블의 시간 컬럼을 그대로 사용한다.
    - 결제 완료: `paid_time`
    - 판매자 발송: `sent_time`
    - 배송 중: `shipped_time`
    - 배송 완료: `delivered_time`
    - 구매 확정: `completed_time`
- 아직 도달하지 않은 거래 단계의 시각은 `null`로 반환한다.

---

### 요청 Query

없음

---

### 요청 Path

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `tradeId` | number | O | 조회할 거래 id |

요청 예시: /api/v1/users/me/trades/23

---

### 요청 Body

없음

---

### 정상 응답 데이터

Status Code : 200

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `trade.id` | number | 거래 id |
| `trade.paidTime` | string(date-time) | 결제 완료 시각 |
| `trade.price` | number | 판매글에 등록된 상품 가격 |
| `trade.productImageUrl` | string | null | 마켓 상품 이미지 URL |
| `trade.cube.id` | number | 큐브 id |
| `trade.cube.serialNumber` | string | 큐브 시리얼 번호 |
| `trade.cube.productName` | string | 큐브 상품명 |
| `trade.cube.artistName` | string | 아티스트 이름 |
| `trade.timeline[].status` | string | 거래 단계 상태 코드 |
| `trade.timeline[].label` | string | 화면 표시용 거래 단계 이름 |
| `trade.timeline[].time` | string(date-time) | null | 해당 단계가 기록된 시각 |
| `trade.timeline[].completed` | boolean | 해당 단계 완료 여부 |

```json
{
  "trade": {
    "id": 1,
    "paidTime": "2026-08-05T14:30:00",
    "price": 12500,
    "productImageUrl": "<https://example.com/mock/market-product-001.jpg>",
    "cube": {
      "id": 1,
      "serialNumber": "#012",
      "productName": "RUBY CUBE",
      "artistName": "JENNIE"
    },
    "timeline": [
      {
        "status": "PAID",
        "label": "결제 완료",
        "time": "2026-08-05T14:30:00",
        "completed": true
      },
      {
        "status": "SENT",
        "label": "판매자 발송",
        "time": "2026-08-05T15:09:00",
        "completed": true
      },
      {
        "status": "SHIPPING",
        "label": "배송 중",
        "time": "2026-08-07T09:45:00",
        "completed": true
      },
      {
        "status": "DELIVERED",
        "label": "배송 완료",
        "time": null,
        "completed": false
      },
      {
        "status": "COMPLETED",
        "label": "구매 확정",
        "time": null,
        "completed": false
      }
    ]
  }
}
```

---

### 오류 응답 데이터

Status Code : 404

```json
{
  "code": "TRADE_NOT_FOUND",
  "message": "거래 정보를 찾을 수 없습니다."
}
```