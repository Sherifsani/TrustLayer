# TrustLayer

> AI-powered trust scoring API for Nigerian fintechs — fusing KYC, financial signals, and telco data into a single explainable score.

---

## What it does

TrustLayer tells Nigerian fintechs, lenders, and employers whether a person is who they say they are and whether they're likely to be financially reliable — before any money moves.

A single `POST /score` request returns a **0–100 trust score**, a fraud risk level, and the top 3 reasons behind the score — powered by Squad payment data, Dojah KYC verification, and Mono telco signals.

---

## Architecture

```
User
 │
 ├── B2C Consumer Portal (React)
 │     └── view score · download report · manage consents
 │
 └── B2B Risk Officer Dashboard (React)
       └── loan queue · score breakdown · approve/decline

        │
        ▼
   TrustLayer API (FastAPI)
   ┌─────────────────────────────────────┐
   │  POST /onboard                      │
   │  POST /score                        │
   │  GET  /report/:user_id              │
   │  POST /webhook/squad                │
   │  POST /consent                      │
   │  GET  /consent/:user_id             │
   └─────────────────────────────────────┘
        │
        ├── Dojah         (KYC · liveness · document auth · AML)
        ├── Squad         (payments · webhooks · transfer gate)
        ├── Mono          (telco signals · credit history)
        │
        └── ML Pipeline
              ├── XGBoost scoring model + SHAP explainability
              └── Isolation Forest anomaly detector
```

---

## Features

| Feature | Description |
|---|---|
| KYC & identity verification | BVN + NIN validation via Dojah with confidence scores |
| Liveness check | Selfie-based deepfake detection and face match to BVN photo |
| Trust score (0–100) | Single score computed from all available signals |
| Score explainability | Top 3 SHAP-derived drivers in plain English |
| Squad financial signals | Transaction frequency, volume, failure rate, dispute history |
| Telco behaviour analysis | Airtime top-up patterns and mobile borrowing repayment |
| Bank statement analysis | Income stability, bounce count, spending categories via Dojah |
| Document authentication | Forgery detection on IDs and utility bills |
| Anomaly detection | Isolation Forest flags unusual transaction patterns |
| Pre-disbursement fraud gate | AI score gates Squad Transfer API call |
| Real-time score updates | Score recomputes on every Squad webhook event |
| Consent graph | Users control which businesses see which signals |
| B2C consumer portal | View score, history, download report via Squad payment |
| B2B risk officer dashboard | Loan queue, score breakdown, approve/decline with transfer gate |

---

## Tech stack

| Layer | Technology |
|---|---|
| API | Python · FastAPI · Uvicorn |
| Database | PostgreSQL · SQLAlchemy · Alembic |
| Task queue | Celery · Redis |
| ML | XGBoost · scikit-learn · SHAP · pandas · numpy |
| Frontend | React · Tailwind CSS |
| KYC / identity | Dojah API |
| Payments | Squad API |
| Telco data | Mono Telco API |
| Tunnelling (dev) | ngrok |

---

## Project structure

```
trustlayer/
├── api/
│   ├── main.py               # FastAPI app entry point
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
│   ├── pipeline.py           # Main scoring orchestrator
│   ├── scoring_model.py      # XGBoost model + SHAP explainability
│   ├── anomaly_detector.py   # Isolation Forest
│   ├── generate_data.py      # Synthetic training data generator
│   ├── train.py              # Training script
│   └── models/
│       ├── trust_model.pkl   # Trained XGBoost model
│       └── anomaly_model.pkl # Trained Isolation Forest
│
├── integrations/
│   ├── dojah.py              # BVN · NIN · liveness · statement · AML
│   ├── squad.py              # Payments · verify · transfer · webhook
│   └── mono.py               # Telco signals (mocked for hackathon)
│
├── db/
│   ├── session.py            # DB connection and session factory
│   └── migrations/           # Alembic migration files
│
├── dashboard/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── B2BDashboard.jsx   # Risk officer view
│   │   │   ├── B2CPortal.jsx      # Consumer score view
│   │   │   └── ConsentManager.jsx # Consent graph UI
│   │   └── components/
│   │       ├── ScoreGauge.jsx
│   │       ├── DriversList.jsx
│   │       └── LoanQueue.jsx
│   └── package.json
│
├── tests/
│   ├── test_score.py
│   ├── test_webhook.py
│   └── test_onboard.py
│
├── .env.example              # Environment variable template
├── docker-compose.yml
├── requirements.txt
├── README.md
└── CLAUDE.md
```

---

## Environment variables

Copy `.env.example` to `.env` and fill in all values before running.

```env
# Squad
SQUAD_SECRET_KEY=sandbox_sk_...
SQUAD_BASE_URL=https://sandbox-api-d.squadco.com

# Dojah
DOJAH_APP_ID=...
DOJAH_SECRET_KEY=...
DOJAH_BASE_URL=https://api.dojah.io

# Mono
MONO_SECRET_KEY=...
MONO_BASE_URL=https://api.withmono.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/trustlayer

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# App
SECRET_KEY=your-jwt-secret
ENVIRONMENT=development
```

---

## Getting started

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis
- Docker (for ngrok)
- Node.js 18+ (for dashboard)

### Install

```bash
# Clone and enter project
git clone https://github.com/yourteam/trustlayer
cd trustlayer

# Python dependencies
pip install -r requirements.txt

# Run DB migrations
alembic upgrade head

# Train ML models
python ml/generate_data.py
python ml/train.py

# Start API
uvicorn api.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A api.celery_app worker --loglevel=info
```

### Webhook tunnel (development)

```bash
# Run ngrok
docker run --net=host \
  -e NGROK_AUTHTOKEN=your_token \
  ngrok/ngrok:alpine \
  http 8000

# Get your public URL
curl http://localhost:4040/api/tunnels | jq '.tunnels[0].public_url'
```

Paste `https://your-url.ngrok-free.app/webhook/squad` into the Squad sandbox dashboard under **Merchant Settings → API & Webhooks → Test Webhook URL**.

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

---

## API reference

### POST /onboard
Verify a user's identity via Dojah KYC.

**Request**
```json
{
  "bvn": "22222222222",
  "nin": "70123456789",
  "phone": "09011111111",
  "selfie_base64": "...",
  "first_name": "Adaeze",
  "last_name": "Okafor",
  "email": "adaeze@email.com"
}
```

**Response**
```json
{
  "user_id": "usr_abc123",
  "kyc_status": "verified",
  "identity_confidence": 0.94,
  "flags": []
}
```

---

### POST /score
Compute a trust score for a user. Called by B2B businesses.

**Headers:** `Authorization: Bearer {business_api_key}`

**Request**
```json
{ "user_id": "usr_abc123" }
```

**Response**
```json
{
  "user_id": "usr_abc123",
  "trust_score": 74,
  "risk_level": "low",
  "recommendation": "approve",
  "drivers": [
    "23 transactions in 90 days → +12 pts",
    "No dispute history → +8 pts",
    "1 failed payment → −5 pts"
  ],
  "signals_used": ["squad", "dojah_kyc", "mono_telco"],
  "computed_at": "2025-08-24T10:22:33Z"
}
```

**Risk bands**
| Score | Risk | Recommendation |
|---|---|---|
| 75–100 | Low | Auto approve |
| 50–74 | Medium | Human review |
| 0–49 | High | Decline |

---

### POST /webhook/squad
Receives Squad transaction events. Updates user financial signal profile and triggers score recompute.

**Called by Squad automatically** — do not call manually.

---

### POST /consent
Grant or revoke data access for a specific business.

**Request**
```json
{
  "user_id": "usr_abc123",
  "business_id": "biz_kwikloans",
  "action": "grant",
  "signals": ["trust_score", "squad_history"],
  "expires_days": 90
}
```

---

## Scoring model

TrustLayer runs two AI models:

**1. XGBoost trust scoring model**
- 15 input features across KYC, Squad, telco, and document signals
- SHAP explainability on every prediction
- Hard rules applied before model: watchlisted NIN → score 0, liveness < 0.5 → score capped at 20

**2. Isolation Forest anomaly detector**
- Unsupervised, trained on normal transaction timelines
- Flags velocity spikes, round-number deposits, identity mismatches
- Applies 30% penalty to base score when anomaly is detected

**Sandbox test users**

| User | Score | Profile |
|---|---|---|
| Adaeze Okafor | 78 | Verified KYC · 23 Squad txns · no flags |
| Emeka Eze | 31 | Liveness failed · transaction spike · AML flag |

---

## Revenue model

| Channel | Model | Price |
|---|---|---|
| B2B per query | Pay per score call | ₦1,500 / query |
| B2B subscription | Monthly flat rate | ₦50,000 / month |
| B2C report download | Squad payment gate | ₦500 / report |

---

## Sandbox credentials

**Dojah test values**
```
BVN:   22222222222
NIN:   70123456789
Phone: 09011111111
OTP:   1234
```

**Squad test cards**
See Squad sandbox dashboard → Sandbox → Test Cards

---

## Team
Squad Hackathon 3.0 · Challenge 01 — Proof of Life