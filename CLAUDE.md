# CLAUDE.md — TrustLayer codebase context

This file tells Claude everything it needs to know to help build TrustLayer effectively. Read this before writing any code.

---

## What TrustLayer is

An AI-powered trust scoring API for Nigerian fintechs. Businesses call `POST /score` with a user ID and get back a 0–100 trust score, a fraud risk level, and SHAP-derived explanations — all powered by Squad payment data, Dojah KYC, and Mono telco signals.

Two products:
- **B2B** — fintechs, lenders, and employers query the API to make risk decisions before money moves
- **B2C** — users view their own trust score and download reports, paying via Squad

---

## Hackathon context

- **Competition:** Squad Hackathon 3.0 · Challenge 01 — Proof of Life
- **Judging criteria:** AI Technical Depth (30%) · Squad API Integration (20%) · Solution Design (15%) · Presentation & Demo (15%) · Problem Relevance (15%) · Impact Potential (10% bonus)
- **Demo constraint:** 5-minute live demo. Squad payment → webhook → score update loop must work live on screen.

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI · Python 3.11 · Uvicorn |
| Database | PostgreSQL · SQLAlchemy · Alembic |
| Task queue | Celery · Redis |
| ML | GradientBoostingClassifier · scikit-learn · SHAP · pandas · numpy |
| Frontend | React · Tailwind CSS (separate repo) |
| KYC | Dojah API |
| Payments | Squad API |
| Telco | Mono Telco API (mocked in sandbox) |
| Tunnel | ngrok-alpine on Docker |

---

## Environment variables

All secrets live in `.env`. Never hardcode them. Always load via `python-dotenv`.

```
# Dojah
DOJAH_APP_ID            # 6a01c2e7b1db697d39c60408
DOJAH_PUBLIC_KEY        # test_pk_... — used for client-side calls
DOJAH_PRIVATE_KEY       # test_sk_... — used in Authorization header for all API calls
DOJAH_BASE_URL          # https://sandbox.dojah.io (sandbox) | https://api.dojah.io (production)

# Squad
SQUAD_SECRET_KEY        # sandbox_sk_... — used in Authorization header
SQUAD_PUBLIC_KEY        # sandbox_pk_... — used for frontend checkout modal
SQUAD_BASE_URL          # https://sandbox-api-d.squadco.com
SQUAD_WEBHOOK_URL       # https://<ngrok-url>/webhook/squad

# Mono (mocked)
MONO_SECRET_KEY         # leave blank for hackathon
MONO_BASE_URL           # https://api.withmono.com

# Database
DATABASE_URL            # postgresql://user:pass@localhost:5432/trustlayer

# Redis
REDIS_URL               # redis://localhost:6379/0

# App
SECRET_KEY              # JWT secret — generate with: python -c "import secrets; print(secrets.token_hex(32))"
ENVIRONMENT             # development | production

# Dev tunnel
NGROK_URL               # https://caravan-tweed-pointy.ngrok-free.dev (changes on restart)
```

---

## Project structure

```
trustlayer/
├── api/
│   ├── main.py               # FastAPI app, routers registered here
│   ├── routes/
│   │   ├── onboard.py        # POST /onboard
│   │   ├── score.py          # POST /score
│   │   ├── report.py         # GET /report/:user_id
│   │   ├── webhook.py        # POST /webhook/squad
│   │   └── consent.py        # POST /consent · GET /consent/:user_id
│   ├── models/
│   │   ├── schemas.py        # Pydantic request/response models
│   │   └── db_models.py      # SQLAlchemy ORM models
│   └── dependencies.py       # Auth, DB session, API key validation
│
├── ml/
│   ├── pipeline.py           # Main scoring orchestrator — called by POST /score
│   ├── scoring_model.py      # GradientBoostingClassifier load + predict + SHAP explain
│   ├── anomaly_detector.py   # Isolation Forest load + predict
│   ├── generate_data.py      # Synthetic training data (800 profiles)
│   ├── train.py              # Train both models, save .pkl files
│   └── models/               # Saved .pkl files (gitignored)
│
├── integrations/
│   ├── dojah.py              # All Dojah API calls
│   ├── squad.py              # All Squad API calls
│   └── mono.py               # Mono telco (mocked for hackathon)
│
├── db/
│   ├── session.py            # get_db() dependency
│   └── migrations/           # Alembic
│
├── tests/
│   ├── test_score.py
│   ├── test_webhook.py
│   └── test_onboard.py
│
└── dashboard/                # React frontend — separate repo, ignore for now
```

---

## Database schema

Four tables. Do not add columns without updating the Pydantic schemas too.

```python
# users
id: UUID (primary key)
bvn_hash: str          # SHA-256 of BVN — never store raw BVN
nin_hash: str          # SHA-256 of NIN
phone: str
email: str
kyc_status: str        # pending | verified | failed | blocked
identity_confidence: float
created_at: datetime

# squad_events
id: UUID
user_id: UUID (FK → users)
txn_ref: str
amount: int            # kobo
txn_type: str          # Card | Transfer | Bank | Ussd | VirtualAccount
status: str            # Success | Failed | Abandoned
created_at: datetime

# trust_scores
id: UUID
user_id: UUID (FK → users)
score: int             # 0–100
risk_level: str        # low | medium | high | blocked
drivers: JSON          # list of driver strings
signals_used: JSON     # list of signal sources used
computed_at: datetime

# consents
id: UUID
user_id: UUID (FK → users)
business_id: str
granted_signals: JSON  # ["trust_score", "squad_history", "telco_data"]
denied_signals: JSON
granted_at: datetime
expires_at: datetime
revoked: bool
```

---

## API endpoints

### POST /onboard
- Accepts: bvn, nin, phone, selfie_base64, first_name, last_name, email
- Calls Dojah in parallel: verify_bvn, lookup_nin, liveness_check, check_phone, screen_aml
- Hashes BVN and NIN before storing (SHA-256)
- Returns: user_id, kyc_status, identity_confidence, flags

### POST /score
- Auth: Bearer token (business API key)
- Accepts: user_id
- Checks consent record for requesting business before returning data
- Calls ml/pipeline.py → compute_trust_score(user_id)
- Returns: trust_score, risk_level, recommendation, drivers, signals_used

### POST /webhook/squad
- No auth (validated by x-squad-encrypted-body signature header)
- Receives Squad charge_successful event
- Stores event in squad_events table
- Triggers Celery task: recompute_score.delay(user_id)
- Always returns 200 {"status": "ok"} — Squad retries on non-200

### GET /report/:user_id
- Auth: user JWT
- Only returns if a Squad payment has been confirmed for this user
- Returns full score breakdown as JSON

### POST /consent
- Auth: user JWT
- Accepts: business_id, action (grant|revoke), signals[], expires_days
- Upserts consent record

---

## External integrations

### Dojah (integrations/dojah.py)

Base URL: `https://sandbox.dojah.io` (sandbox) · `https://api.dojah.io` (production)

Auth headers for every request:
```python
headers = {
    "AppId": os.getenv("DOJAH_APP_ID"),
    "Authorization": os.getenv("DOJAH_PRIVATE_KEY"),
    "Content-Type": "application/json"
}
```

Functions to implement:
```python
verify_bvn(bvn, first_name, last_name) -> dict
lookup_nin(nin) -> dict
liveness_check(selfie_base64, bvn) -> dict
analyse_bank_statement(pdf_base64) -> dict
check_phone(phone_number) -> dict
screen_aml(first_name, last_name, dob) -> dict
```

Sandbox test values:
- BVN: `22222222222`
- NIN: `70123456789`
- Phone: `09011111111`
- OTP: `1234`

### Squad (integrations/squad.py)

Base URL: `https://sandbox-api-d.squadco.com`

Auth header for every request:
```python
headers = {
    "Authorization": f"Bearer {os.getenv('SQUAD_SECRET_KEY')}",
    "Content-Type": "application/json"
}
```

Functions to implement:
```python
initiate_payment(amount_kobo, email, ref, callback_url) -> dict
verify_transaction(txn_ref) -> dict
transfer(bank_code, account_number, amount_kobo, ref) -> dict
lookup_account(bank_code, account_number) -> dict
```

Webhook validation: Squad sends `x-squad-encrypted-body` header. Validate by HMAC-SHA512 of the raw request body using `SQUAD_SECRET_KEY`. Reject any webhook that fails validation — but still return 200 to avoid Squad retrying indefinitely.

Webhook payload shape:
```json
{
  "Event": "charge_successful",
  "TransactionRef": "SQTEST...",
  "Body": {
    "amount": 10000,
    "transaction_ref": "...",
    "transaction_status": "Success",
    "email": "user@email.com",
    "transaction_type": "Card",
    "merchant_amount": 10000,
    "created_at": "2025-08-24T15:26:38.994"
  }
}
```

### Mono (integrations/mono.py)

Mocked for the hackathon. Do not make any real API calls — return synthetic data only:

```python
def get_telco_data(phone: str, network: str) -> dict:
    return {
        "topup_count_30d": 8,
        "avg_topup_amount": 500,
        "data_plan_tier": "1GB_weekly",
        "borrow_repaid_ontime": True,
        "account_age_months": 24
    }
```

---

## ML pipeline

### Scoring model (ml/scoring_model.py)

Algorithm: `GradientBoostingClassifier` from scikit-learn
Output: `predict_proba()[:, 1]` probability × 100 = trust score (0–100)
Saved at: `ml/models/trust_model.pkl`

15 input features:
```python
FEATURE_NAMES = [
    # Dojah KYC
    "bvn_confidence",      # float 0–1
    "nin_watchlisted",     # int 0|1
    "liveness_score",      # float 0–1
    "doc_authentic",       # int 0|1
    "phone_name_match",    # int 0|1

    # Squad signals
    "txn_count_90d",       # int
    "avg_txn_amount",      # float (naira)
    "txn_failure_rate",    # float 0–1
    "channel_diversity",   # int (unique txn types)
    "dispute_count",       # int

    # Mono telco
    "topup_frequency",     # int per month
    "telco_borrow_repaid", # int 0|1

    # Dojah statement
    "income_stability",    # float 0–1
    "bounce_count_90d",    # int
    "aml_risk_level",      # int 0|1|2
]
```

Hard rules applied before model (override output entirely):
- `nin_watchlisted == 1` → score = 0, risk = "blocked"
- `liveness_score < 0.5` → score capped at 20, risk = "high"
- `aml_risk_level == 2` → score = 0, risk = "blocked"

Missing data handling: if a signal source is unavailable, set all its features to 0.5 (neutral). Never penalise a user for missing data.

SHAP explainability: use `shap.TreeExplainer`. Return top 3 features by absolute SHAP value as human-readable driver strings. Always translate using `FEATURE_DISPLAY_NAMES` — never return raw feature names.

```python
FEATURE_DISPLAY_NAMES = {
    "bvn_confidence":      "BVN identity confidence",
    "nin_watchlisted":     "NIN watchlist status",
    "liveness_score":      "Liveness check score",
    "doc_authentic":       "Document authenticity",
    "phone_name_match":    "Phone name match",
    "txn_count_90d":       "Transactions in last 90 days",
    "avg_txn_amount":      "Average transaction amount",
    "txn_failure_rate":    "Transaction failure rate",
    "channel_diversity":   "Payment channel diversity",
    "dispute_count":       "Dispute history",
    "topup_frequency":     "Airtime top-up frequency",
    "telco_borrow_repaid": "Telco credit repayment",
    "income_stability":    "Income stability",
    "bounce_count_90d":    "Bounced payments (90 days)",
    "aml_risk_level":      "AML risk screening",
}
```

### Anomaly detector (ml/anomaly_detector.py)

Algorithm: `IsolationForest` from scikit-learn (unsupervised)
Saved at: `ml/models/anomaly_model.pkl`

Input features: transaction timeline signals (velocity, amount variance, time-of-day distribution)

If `predict() == -1` (anomaly detected):
- Apply 0.7 multiplier to base score
- Append "Unusual transaction pattern detected" to drivers list

### Scoring pipeline (ml/pipeline.py)

Single async function called by POST /score. Orchestration order:

```python
async def compute_trust_score(user_id: str, business_id: str) -> TrustScore:
    # 1. Check consent record for requesting business
    # 2. Collect features in parallel via asyncio.gather
    #    (squad signals from DB, dojah from cache/API, mono mock)
    # 3. Apply hard rules — return early if blocked
    # 4. Run GradientBoostingClassifier → base_score
    # 5. Run IsolationForest → apply anomaly multiplier if needed
    # 6. Run shap.TreeExplainer → top 3 drivers → translate to plain English
    # 7. Save result to trust_scores table
    # 8. Return TrustScore pydantic object
```

---

## Demo test users

Pre-seed these in the database before the demo. Never create them live during the demo.

**Adaeze Okafor** — `user_id: usr_adaeze001`
- Score: 78 · Risk: low · Recommendation: approve
- BVN confidence: 0.97 · Liveness: 0.91 · 23 Squad txns · 0 disputes
- Anomaly detector: clean — approve button fires Squad Transfer API

**Emeka Eze** — `user_id: usr_emeka001`
- Score: 31 · Risk: high · Recommendation: decline
- Liveness: 0.42 · Transaction velocity spike (15 txns in 48h) · AML flag
- Anomaly detector: fires — transfer blocked, fraud flag shown in drivers

---

## Coding conventions

- All API responses use snake_case JSON
- All monetary amounts in **kobo** when calling Squad, **naira** in display
- Never store raw BVN or NIN — always SHA-256 hash before writing to DB
- All Dojah and Squad calls wrapped in try/except — return graceful degraded result if external API fails, never crash the scoring pipeline
- Async everywhere in the API layer (`async def`, `await`, `httpx.AsyncClient`)
- Pydantic models for every request and response — no raw dicts crossing route boundaries
- Environment variables via `python-dotenv` — never hardcode keys
- Import order: stdlib → third party → local

---

## What's mocked for the hackathon

| Feature | Status | Notes |
|---|---|---|
| Mono telco data | Mocked | Returns synthetic response, no real API call |
| ML training data | Synthetic | 800 generated profiles — acknowledged to judges |
| Bank statement upload | Real Dojah call | Pre-load response for demo speed |
| Consent graph enforcement | Partial | UI complete, backend simplified |

Tell judges these are mocked and explain what the real integration looks like. Do not hide it.

---

## ngrok setup (development)

ngrok is running as ngrok-alpine on Docker.

Current tunnel URL: `https://caravan-tweed-pointy.ngrok-free.dev`
Squad webhook URL set to: `https://caravan-tweed-pointy.ngrok-free.dev/webhook/squad`

**Important:** URL changes on every ngrok container restart (free plan).
After each restart: get new URL → update `.env` NGROK_URL → update Squad dashboard webhook URL.

```bash
# Get current tunnel URL
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'

# Inspect incoming webhooks (browser)
open http://localhost:4040
```

---

## Key things to get right

1. **Dojah auth** — use `DOJAH_PRIVATE_KEY` in the `Authorization` header and `DOJAH_APP_ID` in the `AppId` header. Never mix these up.
2. **Squad webhook signature validation** — validate `x-squad-encrypted-body` via HMAC-SHA512 before processing. Return 200 even on failure to prevent Squad retry loops.
3. **SHAP drivers in plain English** — always use `FEATURE_DISPLAY_NAMES` to translate. Never return raw feature names like `txn_count_90d`.
4. **Score always has drivers** — never return a score without at least 1 driver sentence.
5. **Transfer API only fires after account lookup** — always call `/payout/account/lookup` before `/payout/transfer`.
6. **Celery for score recompute** — webhook handler stores the event and dispatches a Celery task. Score recomputation is never synchronous in the webhook response path.
7. **SHA-256 BVN/NIN** — hash before any DB write, no exceptions.