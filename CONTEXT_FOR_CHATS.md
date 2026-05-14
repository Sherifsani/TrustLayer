# TrustLayer Mono Integration — Full Context for Future Chats

## 🎯 What We're Building

An **AI trust-scoring platform for Nigerian fintechs** that:
1. **Onboards users** via KYC (Dojah) + selfie verification
2. **Links financial accounts** via Mono Connect widget
3. **Calculates trust score** (0-850) based on transaction history, income stability, and financial patterns
4. **Displays dashboard** with visualized trust scores and financial signals

**Competition:** Squad Hackathon 3.0, Challenge 01 — Proof of Life (judged on AI depth, API integration, solution design, demo quality)

---

## ✅ What's Implemented

### Backend (FastAPI + Python 3.11)
**Core Endpoints:**
- `POST /onboard` — User KYC + verification (Dojah integration)
- `GET /api/user/credit-profile` — Fetches trust score + financial signals
- `POST /mono/create-session` — Creates Mono Connect session (mock or real)
- `POST /mono/exchange-token` — Exchanges Mono auth code for account ID, persists to DB
- `GET /mock-mono-widget` — Local testing widget (returns HTML form)
- `POST /webhook/mono` — Webhook handler stub

**Database (PostgreSQL):**
- `users` table + `mono_account_id` column (stores linked account)
- `trust_scores` table (historical scores)
- Alembic migrations set up and applied

**ML Pipeline:**
- `ml/credit_scoring.py` — Calculates trust score from financial signals
- Formula: `(tx_volume/120 * 40%) + (income_consistency * 35%) + (avg_balance/500000 * 25%)`
- Outputs 300–850 trust score range with component breakdowns

**Integrations:**
- `integrations/mono.py` — Mono API calls + sandbox mock fallback
- `integrations/squad.py` — Squad payment integration (stub)
- `integrations/dojah.py` — KYC verification

### Frontend (React + TypeScript + Vite)
**Pages:**
- `/onboarding` — Step-by-step form with Mono bank link (Step 3)
- `/user/overview` — Dashboard displaying trust score gauge (animated, 300-850 range)
- `/mono-callback` — Redirect target after Mono widget approval

**Mono Widget Integration:**
- Uses real `@mono.co/connect.js` v2.2.0 (not mock)
- Flows: Click "Connect" → Session created → Widget opens in popup → User approves → Code exchanged → Account saved to DB → Dashboard updates

**UI Components:**
- `<TrustMeter>` — Animated gauge showing score (Framer Motion)
- Component breakdown display (transaction volume, income consistency, average balance)

---

## 🔧 Tech Stack Summary

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | FastAPI | 0.95+ |
| Language | Python | 3.11 |
| Database | PostgreSQL | 14 |
| Frontend | React | 18.3.1 |
| Build | Vite | 6.4.2 |
| Styling | Tailwind CSS | 3+ |
| HTTP (Backend) | httpx (async) | - |
| ORM | SQLAlchemy | - |
| Migrations | Alembic | - |
| Task Queue | Celery (optional for now) | - |
| Message Broker | Redis (optional for now) | - |

---

## 🚀 Local Development Setup

### Prerequisites
- Python 3.11 with venv
- Node.js 18+
- PostgreSQL running on localhost:5432
- PowerShell (Windows)

### Install & Run

**Terminal 1 — Backend (Uvicorn on http://127.0.0.1:8000):**
```powershell
Set-Location C:\Users\olani\TrustLayer
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend (Vite on http://localhost:5173):**
```powershell
Set-Location C:\Users\olani\TrustLayer_Client
pnpm dev -- --host 127.0.0.1 --port 5173
```

**Terminal 3 — Database setup (one-time):**
```powershell
Set-Location C:\Users\olani\TrustLayer
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe db/seed.py
```

### Environment Variables

**TrustLayer/.env** (backend):
```
# Mono — Sandbox Mode Enabled
MONO_PUBLIC_KEY=test_pk_okgk9v0wq6imu1vdx0w5
MONO_SECRET_KEY=test_sk_mgfr12crvtl0x6825mem
MONO_BASE_URL=https://api.withmono.com
MONO_SANDBOX_MODE=true          # ← CRITICAL: Enables mock fallback

# Database
DATABASE_URL=postgresql://postgres:password@127.0.0.1:5432/trustlayer
REDIS_URL=redis://127.0.0.1:6379/0   # (optional, can leave blank)

# API Config
BACKEND_BASE_URL=http://127.0.0.1:8000
FRONTEND_BASE_URL=http://127.0.0.1:5173
ENVIRONMENT=development
SECRET_KEY=change-me-in-production

# Dojah (optional for now — leave blank for demo)
DOJAH_APP_ID=
DOJAH_PRIVATE_KEY=

# Squad
SQUAD_SECRET_KEY=sandbox_sk_test
SQUAD_BASE_URL=https://sandbox-api-d.squadco.com
```

**TrustLayer_Client/.env** (frontend):
```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_MONO_PUBLIC_KEY=test_pk_okgk9v0wq6imu1vdx0w5
```

---

## 🔴 Critical Fixes Applied (May 14, 2026)

### Issue: CORS Error + 500 on POST /mono/create-session
**Root Cause:** `MONO_SANDBOX_MODE` not set; backend tried real Mono API calls with invalid credentials (401 error).

**Solution:**
1. Added `MONO_SANDBOX_MODE=true` to `.env`
2. Updated `integrations/mono.py`:
   - `create_connect_session()` now checks `MONO_SANDBOX_MODE` first (was checking `if not MONO_SECRET_KEY`)
   - `exchange_code_for_account()` simplified: if sandbox, return mock account immediately
3. Removed DB dependency from `POST /mono/create-session` endpoint (was blocking on DB connection in error cases)

**Files Modified:**
- `.env` — Added MONO_SANDBOX_MODE=true
- `integrations/mono.py` — Fixed sandbox checks
- `api/routes/mono.py` — Removed db dependency from create_session

---

## 📊 Database Schema

```python
# users
id: UUID (PK)
first_name, last_name: str
email, phone: str
bvn_hash, nin_hash: str (SHA-256)
kyc_status: str (pending|verified|failed|blocked)
mono_account_id: str (nullable, set after exchange-token)
created_at: datetime

# trust_scores
id: UUID (PK)
user_id: UUID (FK)
score: int (0-850)
risk_level: str (low|medium|high|blocked)
drivers: JSON (list of explanation strings)
signals_used: JSON
computed_at: datetime

# consents (optional, partial impl)
id: UUID (PK)
user_id: UUID (FK)
business_id: str
granted_signals, denied_signals: JSON
```

---

## 🔄 User Flow (Current)

1. **Onboarding Page** (`/onboarding`)
   - User fills form (name, email, BVN, NIN, phone, selfie)
   - User clicks "Connect" on bank row (Step 3)
   
2. **Backend: Create Session**
   - `POST /mono/create-session` → Creates mock session ID → Returns session URL
   
3. **Frontend: Open Widget**
   - `MonoConnect` widget instantiated with session_id
   - Popup opens (mock or real Mono Connect)
   
4. **User Approves in Widget**
   - Widget's `onSuccess` callback fires with `{code}`
   
5. **Backend: Exchange Code**
   - `POST /mono/exchange-token` with code → Calls `exchange_code_for_account(code)`
   - Returns mock account ID (e.g., `mock_account_xyz`)
   - Persists `mono_account_id` to `users` table
   
6. **Frontend: Navigate to Dashboard**
   - User clicks to go to `/user/overview`
   
7. **Dashboard: Fetch Credit Profile**
   - `GET /api/user/credit-profile?user_handle=usr_adaeze001`
   - Backend fetches statement + income from Mono (or mock)
   - Calculates trust score via ML pipeline
   - Returns `{trust_score: 609, signals: {...}, component_scores: {...}}`
   
8. **Display Score**
   - TrustMeter animated gauge displays 609/850
   - Component breakdown shown (transaction volume %, income consistency %, balance %)

---

## 🧪 Quick Testing

**Smoke Test (Python):**
```powershell
.\.venv\Scripts\python.exe -c "
from fastapi.testclient import TestClient
from api.main import app
c = TestClient(app)

# Test create session
r = c.post('/mono/create-session', json={'user_handle':'usr_adaeze001'})
print('create-session:', r.status_code, r.json())

# Test exchange token
e = c.post('/mono/exchange-token', json={'code':'test_code','user_handle':'usr_adaeze001'})
print('exchange-token:', e.status_code, e.json())

# Test credit profile
p = c.get('/api/user/credit-profile?user_handle=usr_adaeze001')
print('credit-profile:', p.status_code, p.json())
"
```

**Browser Test:**
1. Open http://localhost:5173/onboarding
2. Fill form and click "Connect" on bank row
3. Mono widget should appear
4. Click "Approve & Return" button (mock widget)
5. Browser should show success toast
6. Navigate to dashboard — trust score should display

---

## 📁 Key File Locations

**Backend:**
- `api/main.py` — FastAPI app + CORS middleware
- `api/routes/mono.py` — Mono endpoints
- `integrations/mono.py` — Mono API client + mocks
- `ml/credit_scoring.py` — Trust score calculation
- `api/models/db_models.py` — SQLAlchemy ORM models
- `api/models/schemas.py` — Pydantic request/response models
- `.env` — Environment variables

**Frontend:**
- `src/pages/user/onboarding.tsx` — Onboarding form with Mono widget
- `src/pages/user/overview.tsx` — Dashboard with score display
- `src/pages/mono-callback.tsx` — Redirect handler
- `src/components/trust-meter.tsx` — Animated gauge component
- `.env` — Frontend env vars

**Database:**
- `db/session.py` — SessionLocal + dependency
- `db/migrations/` — Alembic migration files

---

## 🔒 Important Security Notes

- **Never store raw BVN/NIN** — Always SHA-256 hash before DB write
- **CORS middleware** — Explicitly whitelisted origins in development:
  - http://localhost:5173
  - http://127.0.0.1:5173
  - http://localhost:8000
  - http://127.0.0.1:8000
- **Sandbox mode** — `MONO_SANDBOX_MODE=true` ensures mock fallback on API errors (critical for demo stability)
- **Request validation** — All endpoints use Pydantic models for request parsing

---

## 🎬 Demo Checklist

- [ ] Backend running (http://127.0.0.1:8000/health returns `{status: ok}`)
- [ ] Frontend running (http://localhost:5173 loads)
- [ ] Database connected (migrations applied, demo user seeded)
- [ ] Mono public key set in `.env`
- [ ] `MONO_SANDBOX_MODE=true`
- [ ] Click "Connect" on onboarding → Mono widget appears
- [ ] Widget approval → Dashboard shows trust score (609 for demo user)
- [ ] No CORS errors in browser console

---

## 🐛 Known Limitations / TODOs

- **Mono webhook** — Endpoint exists but not fully integrated (real webhook handler stub)
- **Consent graph** — UI complete, backend simplified for demo
- **Bank statement upload** — UI ready, real Dojah calls mocked for speed
- **Celery/Redis** — Set up but disabled for fast local dev (can enable if needed)
- **Production deployment** — Railway.toml exists, but not yet deployed

---

## 💡 Next Steps (If Continuing)

1. **After demo works:**
   - Deploy to Railway (edit railway.toml, set real env vars)
   - Replace mock Mono calls with real API (remove `MONO_SANDBOX_MODE`)
   - Set up real ngrok tunnel for Squad webhooks
   - Integrate Celery for background score recompute

2. **For production:**
   - Move secrets to Railway environment variables
   - Set `ENVIRONMENT=production` (locks CORS to trustlayer.app)
   - Use real Mono, Squad, Dojah credentials
   - Enable monitoring + logging aggregation

---

## 📞 Support

**Error: CORS error on /mono/create-session?**
- Check `.env` has `MONO_SANDBOX_MODE=true`
- Check `ENVIRONMENT=development`
- Check backend is running on http://127.0.0.1:8000

**Error: 500 on any endpoint?**
- Check backend terminal for traceback
- Run smoke test to isolate which function is failing
- Verify all required env vars are set

**Frontend won't load?**
- Ensure `VITE_API_BASE_URL` points to running backend
- Check browser console for errors
- Verify both frontend and backend are running

---

**Last Updated:** May 14, 2026  
**Status:** Mono integration complete, CORS fixed, ready for demo  
