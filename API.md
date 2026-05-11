# TrustLayer API Reference

**Base URL:** `https://caravan-tweed-pointy.ngrok-free.dev`

All requests and responses use `Content-Type: application/json`.

---

## Authentication

TrustLayer uses two separate auth schemes depending on the caller:

| Caller | Scheme | How to get a token |
|---|---|---|
| B2C users (frontend) | Bearer JWT | `POST /auth/login` |
| B2B businesses (API clients) | Bearer API key | Provided out-of-band |

Pass the token in every protected request:
```
Authorization: Bearer <token>
```

---

## Demo credentials

### B2C login (frontend users)

| Email | Password | User |
|---|---|---|
| `adaeze@trustlayer.demo` | `demo1234` | Adaeze Okonkwo — low risk, score ~78 |
| `emeka@trustlayer.demo` | `demo1234` | Emeka Eze — high risk, score ~8 |

### B2B API keys (business clients)

| Key | Business |
|---|---|
| `biz_key_kwikloans_demo` | KwikLoans |
| `biz_key_fastcredit_demo` | FastCredit |

---

## Endpoints

### `POST /auth/login`

Get a JWT for a B2C user. No auth required.

**Request**
```json
{
  "email": "adaeze@trustlayer.demo",
  "password": "demo1234"
}
```

**Response `200`**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_id": "usr_adaeze001"
}
```

**Errors**

| Status | Reason |
|---|---|
| `401` | Wrong email or password |

---

### `POST /onboard`

Register a new user. Calls Dojah in parallel to verify BVN, NIN, liveness, phone, and AML. BVN and NIN are SHA-256 hashed before storage — raw values are never saved.

No auth required.

**Request**
```json
{
  "bvn": "22222222222",
  "nin": "70123456789",
  "phone": "09011111111",
  "first_name": "Adaeze",
  "last_name": "Okonkwo",
  "email": "adaeze@trustlayer.demo",
  "selfie_base64": "<base64-encoded image>"
}
```

**Response `200`**
```json
{
  "user_id": "3b4d1034-36df-475e-b806-ab449b61b742",
  "kyc_status": "verified",
  "identity_confidence": 0.94,
  "flags": []
}
```

`kyc_status` values: `verified` | `failed` | `blocked`

`flags` contains human-readable reasons for any failed checks, e.g. `"BVN name mismatch"`, `"Liveness check failed"`, `"NIN flagged on watchlist"`.

**Errors**

| Status | Reason |
|---|---|
| `422` | Missing or invalid request fields |

---

### `GET /user/{user_id}`

Returns the authenticated user's profile. Auth: Bearer JWT.

`user_id` can be either the UUID (`3b4d1034-...`) or the handle (`usr_adaeze001`).

**Headers**
```
Authorization: Bearer <jwt>
```

**Response `200`**
```json
{
  "user_id": "usr_adaeze001",
  "first_name": "Adaeze",
  "last_name": "Okonkwo",
  "email": "adaeze@trustlayer.demo",
  "phone": "09011111111",
  "location": "Surulere, Lagos",
  "kyc_status": "verified",
  "identity_confidence": 0.94,
  "joined": "2025-09-12T00:00:00",
  "nin_masked": "•••• •••• ****",
  "bvn_masked": "•••• •••• ****"
}
```

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid JWT |
| `403` | JWT user does not match the requested `user_id` |
| `404` | User not found |

---

### `POST /score`

Compute a trust score for a user. Auth: Bearer API key (B2B businesses only).

**Headers**
```
Authorization: Bearer biz_key_kwikloans_demo
```

**Request**
```json
{
  "user_id": "usr_adaeze001"
}
```

**Response `200`**
```json
{
  "trust_score": 78,
  "risk_level": "low",
  "recommendation": "approve",
  "reliability_score": 88,
  "authenticity_score": 94,
  "drivers": [
    "Transaction failure rate → +99 pts",
    "Dispute history → +22 pts",
    "Bounced payments (90 days) → +20 pts"
  ],
  "signals_used": [
    "squad_history",
    "telco_data",
    "kyc"
  ]
}
```

| Field | Description |
|---|---|
| `trust_score` | 0–100. Overall trust score. |
| `risk_level` | `low` (≥75) \| `medium` (≥50) \| `high` (<50) \| `blocked` |
| `recommendation` | `approve` \| `review` \| `decline` |
| `reliability_score` | 0–100. Derived from Squad transaction history and telco signals. |
| `authenticity_score` | 0–100. Derived from Dojah KYC signals (BVN confidence, liveness, NIN status). |
| `drivers` | Top 3 SHAP-derived factors explaining the score in plain English. |
| `signals_used` | Which data sources contributed to this score. |

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid API key |
| `404` | User not found |

---

### `GET /score-history/{user_id}`

Returns the user's trust score over time for trajectory charts. Auth: Bearer JWT.

**Headers**
```
Authorization: Bearer <jwt>
```

**Response `200`**
```json
{
  "user_id": "usr_adaeze001",
  "history": [
    { "score": 58, "computed_at": "2025-09-13T18:21:19" },
    { "score": 62, "computed_at": "2025-10-13T18:21:19" },
    { "score": 66, "computed_at": "2025-11-12T18:21:19" },
    { "score": 70, "computed_at": "2026-01-11T18:21:19" },
    { "score": 74, "computed_at": "2026-03-12T18:21:19" },
    { "score": 78, "computed_at": "2026-05-10T18:21:19" }
  ],
  "current_score": 78,
  "change_since_start": 20
}
```

If fewer than 2 real score records exist, synthetic history is generated and returned (not saved). Real records are deduplicated to one per calendar day.

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid JWT |
| `403` | JWT user does not match `user_id` |
| `404` | User not found |

---

### `GET /activity/{user_id}`

Returns all events that have affected the user's trust score — Squad transactions and consent actions, merged and sorted newest first. Auth: Bearer JWT.

**Headers**
```
Authorization: Bearer <jwt>
```

**Response `200`**
```json
{
  "user_id": "usr_adaeze001",
  "events": [
    {
      "id": "evt_c6d7aa38",
      "description": "Card payment processed",
      "source": "SQUAD",
      "source_type": "transaction",
      "timestamp": "2026-05-11T17:48:44",
      "score_impact": 4,
      "type": "transaction"
    },
    {
      "id": "con_7a2f91bc",
      "description": "Consent granted to kwik_loans",
      "source": "Consent",
      "source_type": "consent",
      "timestamp": "2026-05-09T10:00:00",
      "score_impact": null,
      "type": "consent"
    }
  ]
}
```

| Field | Description |
|---|---|
| `score_impact` | Positive integer for successful transactions, negative for failed. `null` for consent events. |
| `type` | `transaction` \| `consent` |
| `source_type` | `transaction` \| `consent` |

Squad events are limited to the 50 most recent.

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid JWT |
| `403` | JWT user does not match `user_id` |
| `404` | User not found |

---

### `GET /reports/{user_id}`

Returns the list of generated reports for the user. Auth: Bearer JWT.

**Headers**
```
Authorization: Bearer <jwt>
```

**Response `200`**
```json
{
  "reports": [
    {
      "id": "3862046f-3293-47c9-a13a-be618f8f591b",
      "title": "Verified Trust Report — Renmoney",
      "report_type": "verified_trust_report",
      "recipient_name": "Renmoney",
      "pages": 6,
      "status": "pending",
      "created_at": "2026-05-10T00:00:00",
      "file_url": null
    },
    {
      "id": "370fa208-983e-4a0b-9fc9-3fd4ded97eae",
      "title": "Verified Trust Report — May 2026",
      "report_type": "verified_trust_report",
      "recipient_name": "Sterling MFB",
      "pages": 6,
      "status": "ready",
      "created_at": "2026-05-08T00:00:00",
      "file_url": null
    }
  ]
}
```

`status` values: `ready` | `pending` | `generating`

`report_type` values: `verified_trust_report` | `identity_snapshot`

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid JWT |
| `403` | JWT user does not match `user_id` |
| `404` | User not found |

---

### `POST /report/initiate-payment`

Creates a pending report record and initiates a Squad payment (₦500) to unlock it. Auth: Bearer JWT.

When Squad fires the payment webhook, the report status automatically advances from `pending` → `generating` → `ready`.

**Headers**
```
Authorization: Bearer <jwt>
```

**Request**
```json
{
  "user_id": "usr_adaeze001",
  "report_type": "verified_trust_report",
  "recipient_id": "sterling_mfb"
}
```

`recipient_id` is optional. `report_type`: `verified_trust_report` | `identity_snapshot`

**Response `200`**
```json
{
  "report_id": "abc12345-...",
  "checkout_url": "https://checkout.squadco.com/...",
  "txn_ref": "report_abc12345-...",
  "amount": 500
}
```

Redirect the user to `checkout_url` to complete payment. After successful payment, poll `GET /reports/{user_id}` until `status` changes to `ready` (usually within 5–10 seconds).

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid JWT |
| `403` | JWT user does not match `user_id` |
| `404` | User not found |

---

### `POST /consent`

Grant or revoke a business's access to the user's data signals. Auth: Bearer JWT.

**Headers**
```
Authorization: Bearer <jwt>
```

**Request**
```json
{
  "business_id": "kwik_loans",
  "action": "grant",
  "signals": ["trust_score", "squad_history"],
  "expires_days": 30
}
```

`action`: `grant` | `revoke`

Available signals: `trust_score` | `squad_history` | `telco_data` | `kyc`

`expires_days` is ignored when `action` is `revoke`.

**Response `200`**
```json
{
  "user_id": "3b4d1034-...",
  "business_id": "kwik_loans",
  "granted_signals": ["trust_score", "squad_history"],
  "denied_signals": [],
  "revoked": false
}
```

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid JWT |

---

### `GET /consent/{user_id}`

Returns all active (non-revoked, non-expired) consent records for the user. Auth: Bearer JWT.

**Headers**
```
Authorization: Bearer <jwt>
```

**Response `200`** — array of consent objects
```json
[
  {
    "user_id": "3b4d1034-...",
    "business_id": "kwik_loans",
    "granted_signals": ["trust_score", "squad_history"],
    "denied_signals": [],
    "revoked": false
  }
]
```

**Errors**

| Status | Reason |
|---|---|
| `401` | Missing or invalid JWT |
| `403` | JWT user does not match `user_id` |

---

### `POST /webhook/squad`

Receives Squad payment event callbacks. This endpoint is called by Squad — not by the frontend.

No auth header. Validated via HMAC-SHA512 signature in the `x-squad-encrypted-body` header.

Always returns `200 {"status": "ok"}` regardless of outcome — Squad retries on any non-200.

On a valid `charge_successful` event:
- Stores a `SquadEvent` record
- If `transaction_ref` starts with `report_`, marks the report as `generating` and queues generation
- Queues a background `recompute_score` Celery task

---

### `GET /health`

Health check. No auth required.

**Response `200`**
```json
{
  "status": "ok",
  "db": "connected",
  "service": "TrustLayer API"
}
```

`status` is `degraded` (not `ok`) if the database is unreachable.

---

## Typical frontend flows

### Login and show dashboard
```
POST /auth/login          → get JWT + user_id
GET  /user/{user_id}      → profile panel
GET  /score-history/{id}  → trajectory chart
GET  /activity/{id}       → activity feed
GET  /reports/{id}        → reports list
```

### Score a user (B2B, server-side)
```
POST /score   → trust_score, risk_level, recommendation, drivers
```

### Generate a report
```
POST /report/initiate-payment   → checkout_url
  (user completes Squad payment)
  (Squad fires webhook → report status: generating → ready)
GET  /reports/{user_id}         → poll until status == "ready"
```

### Manage consent
```
POST /consent  { action: "grant", ... }    → grant access
POST /consent  { action: "revoke", ... }   → revoke access
GET  /consent/{user_id}                    → list active grants
```

---

## Interactive docs

FastAPI auto-generates interactive Swagger UI at:
```
https://caravan-tweed-pointy.ngrok-free.dev/docs
```

All endpoints can be tested directly from the browser there — no curl needed.
