# 🎓 TrustLayer Backend Mastery Guide

## Quick Status Right Now

**✓ Backend running on http://127.0.0.1:8000**  
**✓ Database: SQLite (dev.db)**  
**✓ Environment: development (permissive CORS)**  

```
Set-Location C:\Users\olani\TrustLayer
$env:DATABASE_URL='sqlite:///./dev.db'
$env:REDIS_URL=''
$env:ENVIRONMENT='development'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

---

## PART 1: Understanding Your Architecture

### What's Running Where?

```
┌─────────────────────────────────────────────────────────┐
│  BROWSER (You)                                          │
│  http://localhost:5173 ← You open this in a browser   │
└────────────┬────────────────────────────────────────────┘
             │
             │ HTTP requests (JSON)
             ↓
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (React + Vite)  :5173                         │
│  C:\Users\olani\TrustLayer_Client                       │
│                                                          │
│  • Shows forms (onboarding, score, etc)                 │
│  • Calls backend API                                     │
│  • Stores data in localStorage                          │
└────────────┬────────────────────────────────────────────┘
             │
             │ HTTP requests (REST API)
             ↓
┌─────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI + Python) :8000                       │
│  C:\Users\olani\TrustLayer                              │
│                                                          │
│  • Routes: /onboard, /score, /consent, /report          │
│  • Database: SQLite (dev.db)                            │
│  • Services: Dojah (KYC), Squad (transactions)          │
│  • ML: scoring_model.pkl, anomaly_model.pkl            │
└──────────────────────────────────────────────────────────┘
```

### The Data Flow: Onboarding Example

```
1. User fills form (first_name, bvn, nin, phone, selfie_base64, email)
   ↓
2. Frontend sends: POST http://127.0.0.1:8000/onboard
   {
     "bvn": "22222222222",
     "nin": "70123456789",
     "phone": "09011111111",
     "selfie_base64": "iVBORw0KGgo...",
     "first_name": "Adaeze",
     "last_name": "Okonkwo",
     "email": "adaeze@trustlayer.demo"
   }
   ↓
3. Backend receives request in api/routes/onboard.py
   ↓
4. Backend calls external KYC services (Dojah):
   - verify_bvn()       → Check BVN against Dojah
   - lookup_nin()       → Check NIN against Dojah
   - liveness_check()   → Verify selfie is real person
   - check_phone()      → Verify phone number
   - screen_aml()       → Check sanctions/watchlist
   ↓
5. Backend calculates kyc_status (verified/failed/blocked)
   ↓
6. Backend SAVES to database: users table
   ↓
7. Backend returns: { user_id, kyc_status, identity_confidence, flags }
   ↓
8. Frontend stores user_id in localStorage
   ↓
9. Frontend redirects to /user/overview
```

---

## PART 2: Backend Code Organization

```
TrustLayer/
├── api/                       ← YOUR API CODE
│   ├── main.py               ← Entry point (FastAPI app)
│   ├── routes/               ← Endpoint handlers
│   │   ├── onboard.py        ← POST /onboard
│   │   ├── score.py          ← POST /score
│   │   ├── consent.py        ← GET/POST /consent
│   │   ├── report.py         ← GET /report
│   │   └── webhook.py        ← Squad webhooks
│   ├── models/
│   │   ├── db_models.py      ← Database tables (User, TrustScore, etc)
│   │   └── schemas.py        ← Request/response formats (Pydantic)
│   ├── celery_app.py         ← Background jobs (we skip this for dev)
│   └── dependencies.py       ← Shared utilities
│
├── db/                        ← DATABASE STUFF
│   ├── session.py            ← SQLAlchemy connection & SessionLocal()
│   ├── seed.py               ← Populate demo users
│   ├── migrations/           ← Alembic schema versions
│   │   ├── env.py
│   │   └── versions/
│   │       ├── ...initial_schema.py
│   │       └── ...add_user_handle.py
│
├── integrations/             ← EXTERNAL SERVICES
│   ├── dojah.py             ← KYC API (verify BVN, NIN, liveness)
│   ├── mono.py              ← Bank linking (future)
│   └── squad.py             ← Transaction API
│
├── ml/                        ← MACHINE LEARNING
│   ├── scoring_model.pkl     ← Trained trust score classifier
│   ├── anomaly_model.pkl     ← Anomaly detector
│   ├── train.py              ← Train models from scratch
│   ├── generate_data.py      ← Create synthetic training data
│   └── pipeline.py           ← Score calculation logic
│
├── .env.local                ← Configuration for dev (secrets, URLs)
├── dev.db                    ← SQLite database (created on first run)
├── requirements.txt          ← Python dependencies
└── alembic.ini              ← Database migration config
```

---

## PART 3: How Backend Starts

### Step 1: `alembic upgrade head`
**What**: Apply all database schema migrations  
**Why**: Creates tables (users, trust_scores, squad_events, etc) if they don't exist  
**Error if skipped**: `no such table: users` when trying to save data  

### Step 2: `python ml/train.py`
**What**: Loads training data, trains ML models  
**Why**: Creates `ml/models/trust_model.pkl` and `anomaly_model.pkl`  
**Error if skipped**: `FileNotFoundError: trust_model.pkl` when calculating scores  
**When to skip**: Only if models already exist and you're iterating fast  

### Step 3: `python db/seed.py`
**What**: Create demo users (usr_adaeze001, usr_emeka001)  
**Why**: You have sample users to test with  
**Error if skipped**: None, but you can't test onboarding with them  

### Step 4: `uvicorn api.main:app --host 127.0.0.1 --port 8000`
**What**: Start the web server  
**Why**: Listen for incoming HTTP requests  
**Error if it fails**: Check `/port already in use` → kill the old process  

---

## PART 4: Understanding Environment Variables

These go in `.env.local` or you set them in PowerShell:

| Variable | Meaning | For Dev | Example |
|----------|---------|---------|---------|
| `DATABASE_URL` | Where data is saved | SQLite file path | `sqlite:///./dev.db` |
| `REDIS_URL` | Background job broker | Empty (disabled) | `` |
| `ENVIRONMENT` | Mode (dev vs production) | `development` | `development` |
| `DOJAH_APP_ID` | Dojah KYC service ID | From .env.local | `6a01c2e7b1db...` |
| `DOJAH_PRIVATE_KEY` | Dojah API secret | From .env.local | `test_sk_...` |

### Why ENVIRONMENT='development' Matters

**api/main.py line 17:**
```python
_env = os.getenv("ENVIRONMENT", "development")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _env == "development" else ["https://trustlayer.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Translation**: 
- If `ENVIRONMENT=development` → Allow all origins `["*"]` (localhost:5173 works)
- If `ENVIRONMENT=production` → Only allow `["https://trustlayer.app"]`

**This is why CORS fails if you forget to set ENVIRONMENT!**

---

## PART 5: Reading Backend Logs

When the backend is running, **everything you need to know is printed to the terminal**.

### Normal Startup Logs

```
INFO:     Started server process [17536]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

✓ **This means the server started successfully.**

### Request Logs (Normal)

```
POST /onboard 200 OK
POST /score 200 OK
GET /health 200 OK
```

✓ **All requests succeeded (200 = success).**

### Error Logs (Something Failed)

```
POST /onboard 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\olani\TrustLayer\api\routes\onboard.py", line 42, in onboard
    bvn_result = await dojah.verify_bvn(payload.bvn, payload.first_name, payload.last_name)
  File "C:\Users\olani\TrustLayer\integrations\dojah.py", line 24, in verify_bvn
    resp = await client.get(
    ...
KeyError: 'DOJAH_APP_ID'
```

❌ **This is the REAL error. The browser sees a 500 and reports "CORS error" but the actual problem is in the logs.**

---

## PART 6: Common Error Messages & Fixes

### Error: "no such table: users"
```
sqlite3.OperationalError: no such table: users
```
**Fix**: Run migrations
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### Error: "DOJAH_APP_ID not set"
```
KeyError: 'DOJAH_APP_ID'
```
**Fix**: Check `.env.local` has it, or set it in PowerShell
```powershell
$env:DOJAH_APP_ID='6a01c2e7b1db697d39c60408'
$env:DOJAH_PRIVATE_KEY='test_sk_HC3uLNbUGQ0SOENn6nvbT2Q8O'
```

### Error: "Port 8000 already in use"
```
ERROR:    error while attempting to bind on address ('127.0.0.1', 8000)
```
**Fix**: Kill the old process
```powershell
Get-Process | Where-Object { $_.ProcessName -eq 'python' } | Kill -Force
```

### Error: "No module named 'api'"
```
ModuleNotFoundError: No module named 'api'
```
**Fix**: You're in the wrong directory. Must be in TrustLayer root:
```powershell
Set-Location C:\Users\olani\TrustLayer
```

### Error: "CORS: No 'Access-Control-Allow-Origin' header"
**This is a SYMPTOM, not the real error.**

**Steps to debug**:
1. Look at the logs (backend terminal)
2. If you see a 500 error, read the traceback
3. The real error is in the traceback

---

## PART 7: How to Troubleshoot Like a Pro

### Flowchart: Something's Not Working

```
❌ Browser shows an error
     ↓
1. Check BACKEND LOGS (the terminal where you started uvicorn)
     ↓
   Do you see a Python traceback?
     ├→ YES: Read it carefully. Fix that specific thing.
     └→ NO: Check if backend is running at all
              (run Invoke-WebRequest http://127.0.0.1:8000/health)
     ↓
2. Check FRONTEND DEV TOOLS (F12 → Console tab)
     ↓
   Do you see an error message?
     ├→ YES: Often tells you what's wrong
     └→ NO: Check Network tab, see what response backend sent
     ↓
3. Check PORT BINDINGS
     ↓
   Is your service on the right port?
     backend: 127.0.0.1:8000
     frontend: 127.0.0.1:5173
     (run: netstat -ano | findstr :8000)
```

### Example: Debugging the /onboard Error

**Step 1: Backend logs showed this traceback?**
```
KeyError: 'DOJAH_APP_ID'
```

**Step 2: This means `.env.local` missing or environment variables not set**

**Step 3: Fix:**
```powershell
# Check if .env.local exists and has DOJAH_APP_ID
cat C:\Users\olani\TrustLayer\.env.local | findstr DOJAH
```

If missing, add to `.env.local`:
```
DOJAH_APP_ID=6a01c2e7b1db697d39c60408
DOJAH_PRIVATE_KEY=test_sk_HC3uLNbUGQ0SOENn6nvbT2Q8O
```

Then restart backend:
```powershell
# Kill old server (Ctrl+C in the terminal)
# Start new one:
Set-Location C:\Users\olani\TrustLayer
$env:DATABASE_URL='sqlite:///./dev.db'
$env:REDIS_URL=''
$env:ENVIRONMENT='development'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

---

## PART 8: Your Current Setup (What You Have)

✓ Backend running on port 8000  
✓ Frontend code in TrustLayer_Client  
✓ Database: SQLite dev.db  
✓ Demo users seeded (usr_adaeze001, usr_emeka001)  
✓ ML models trained  

**To get onboarding working:**
1. Ensure DOJAH_APP_ID and DOJAH_PRIVATE_KEY are set
2. Check backend logs when you submit the form
3. Read the error message
4. Fix it

**Next command to run:**
Test onboarding by submitting the form on http://127.0.0.1:5173

Watch the **backend terminal** for the error message.

