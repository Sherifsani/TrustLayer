# 🚀 TrustLayer: Complete Startup Guide

## What You Now Have Running

```
✓ Backend (FastAPI)      → http://127.0.0.1:8000
✓ Frontend (React/Vite)  → http://127.0.0.1:5173
✓ Database (SQLite)      → dev.db
✓ Demo Users             → usr_adaeze001, usr_emeka001
```

---

## 📋 How to Start Everything (3 Simple Steps)

### Terminal 1: Start the Backend

```powershell
Set-Location C:\Users\olani\TrustLayer
$env:DATABASE_URL='sqlite:///./dev.db'
$env:REDIS_URL=''
$env:ENVIRONMENT='development'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

**What you'll see:**
```
INFO:     Started server process [17536]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

✓ **Backend is ready. Leave this terminal running.**

---

### Terminal 2: Start the Frontend

```powershell
Set-Location C:\Users\olani\TrustLayer_Client
pnpm dev -- --host 127.0.0.1 --port 5173
```

**What you'll see:**
```
$ vite "--host" "127.0.0.1" "--port" "5173"

  VITE v6.4.2  ready in 1070 ms

  ➜  Local:   http://127.0.0.1:5173/
  ➜  press h + enter to show help
```

✓ **Frontend is ready. Leave this terminal running.**

---

### Terminal 3: Open Your Browser

```
http://127.0.0.1:5173
```

✓ **You can now use the app!**

---

## 🧪 Test the Integration

### Try Onboarding

1. Open http://127.0.0.1:5173 in browser
2. Click **"Start sign-up as Individual"** or navigate to `/user/onboarding`
3. Fill in the form (auto-populated with demo data):
   - First Name: Adaeze
   - Last Name: Okonkwo
   - BVN: 22222222222
   - NIN: 70123456789
   - Phone: 09011111111
   - Email: adaeze@trustlayer.demo
   - Selfie: Upload any image
4. Click **Submit**

### What Happens Behind the Scenes

```
Browser → Frontend sends POST http://127.0.0.1:8000/onboard
          ↓
          Backend receives request
          ↓
          Calls Dojah (KYC verification)
          ↓
          Saves user to database
          ↓
          Returns: {"user_id": "...", "kyc_status": "verified", ...}
          ↓
Frontend receives response → Stores user_id in localStorage → Redirects
```

### Where to See the Response

**Terminal 1 (Backend logs):**
```
POST /onboard 200 OK
```

**Browser Console (F12 → Console):**
```
API Response: {
  user_id: "6c78c64f-d9d9-4c73-833d-e34eafa8fe03",
  kyc_status: "verified",
  identity_confidence: 0.95,
  flags: []
}
```

---

## 🔧 Troubleshooting: What If Something Goes Wrong?

### Problem: "Port 8000 already in use"

```powershell
Get-Process | Where-Object { $_.ProcessName -eq 'python' } | Kill -Force
```

Then restart the backend.

### Problem: "Can't connect to backend from frontend"

**Check 1: Backend is running?**
```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

**Check 2: Frontend .env is correct?**
```powershell
cat C:\Users\olani\TrustLayer_Client\.env
```

Should show:
```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_DATA_MODE=demo
VITE_ENVIRONMENT='development'
```

**Check 3: CORS error in browser?**

This usually means:
- ENVIRONMENT is not set to 'development'
- Or the backend crashed (look at Terminal 1 logs)

### Problem: "DOJAH_APP_ID not set" error in logs

Add to `.env.local`:
```
DOJAH_APP_ID=6a01c2e7b1db697d39c60408
DOJAH_PRIVATE_KEY=test_sk_HC3uLNbUGQ0SOENn6nvbT2Q8O
```

Or set in PowerShell before starting backend:
```powershell
$env:DOJAH_APP_ID='6a01c2e7b1db697d39c60408'
$env:DOJAH_PRIVATE_KEY='test_sk_HC3uLNbUGQ0SOENn6nvbT2Q8O'
```

### Problem: "no such table: users" error

Run migrations:
```powershell
Set-Location C:\Users\olani\TrustLayer
.\.venv\Scripts\python.exe -m alembic upgrade head
```

---

## 📚 Understanding the Code

### Frontend Code Flow

```
src/pages/landing.tsx
  ↓ User clicks "Start sign-up as Individual"
  ↓
src/pages/user/onboarding.tsx
  ├─ Form fields (first_name, bvn, nin, phone, email, selfie_base64)
  ├─ useMutation(onboardUser) from @tanstack/react-query
  ├─ Calls src/lib/trustlayer-api.ts → onboardUser()
  ├─ which does: POST http://127.0.0.1:8000/onboard
  ↓
src/lib/data-mode.tsx
  ├─ Checks if isDemo = true
  ├─ Uses localStorage to store user_id
  ↓
Frontend redirects to src/pages/user/overview.tsx
  ├─ Now calls POST /score with user_id
  ├─ Shows trust score in TrustMeter component
```

### Backend Code Flow

```
api/main.py
  ├─ Creates FastAPI app with CORS middleware
  ├─ Sets allow_origins=["*"] if ENVIRONMENT='development'
  ↓
api/routes/onboard.py
  ├─ Receives POST /onboard request
  ├─ Calls asyncio.gather() for 5 KYC checks:
  │  ├─ dojah.verify_bvn()
  │  ├─ dojah.lookup_nin()
  │  ├─ dojah.liveness_check()
  │  ├─ dojah.check_phone()
  │  └─ dojah.screen_aml()
  ├─ Calculates kyc_status (verified/failed/blocked)
  ├─ Creates User record in database
  ├─ Returns OnboardResponse JSON
  ↓
Database: db/session.py
  ├─ Saves to users table via SQLAlchemy ORM
  ├─ Uses dev.db (SQLite file)
```

---

## 🎯 What Each Environment Variable Does

| Variable | What It Controls | Dev Value | Why |
|----------|------------------|-----------|-----|
| `DATABASE_URL` | Where data is saved | `sqlite:///./dev.db` | SQLite is fast for local dev |
| `REDIS_URL` | Background job queue | (empty) | Skip Redis for speed |
| `ENVIRONMENT` | Dev vs production | `development` | Enables permissive CORS for localhost |
| `DOJAH_APP_ID` | KYC service ID | From `.env.local` | Required for identity verification |
| `DOJAH_PRIVATE_KEY` | KYC API secret | From `.env.local` | Auth for Dojah API calls |

**Why ENVIRONMENT='development' is critical:**

Without it, CORS fails because:
```python
# api/main.py
allow_origins = ["*"] if ENVIRONMENT == "development" else ["https://trustlayer.app"]
```

So if you forget `ENVIRONMENT='development'`, the browser blocks cross-origin requests.

---

## 📂 File Organization (Quick Reference)

```
BACKEND LOGIC
├── api/routes/onboard.py       ← POST /onboard handler
├── api/routes/score.py         ← POST /score handler
├── integrations/dojah.py       ← External KYC API calls
├── ml/scoring_model.pkl        ← ML model for scoring
└── db/session.py               ← Database connection

FRONTEND CODE
├── src/lib/trustlayer-api.ts   ← API client (calls backend)
├── src/lib/data-mode.tsx       ← Demo/mock toggle
├── src/pages/user/onboarding.tsx ← Sign-up form
├── src/pages/user/overview.tsx ← Dashboard (shows score)
└── .env                        ← API_BASE_URL=http://127.0.0.1:8000

CONFIGURATION
├── TrustLayer/.env.local       ← Backend secrets
├── TrustLayer_Client/.env      ← Frontend config
└── alembic.ini                 ← Database migration config
```

---

## 🚨 Error Reading Guide

### If Backend Logs Show This...

**Error 1: `sqlite3.OperationalError: no such table: users`**
```
→ Database not initialized
→ Fix: Run alembic upgrade head
```

**Error 2: `KeyError: 'DOJAH_APP_ID'`**
```
→ KYC credentials not set
→ Fix: Add to .env.local or set in PowerShell
```

**Error 3: `error while attempting to bind on address ('127.0.0.1', 8000)`**
```
→ Port already in use
→ Fix: Kill old Python processes
```

**Error 4: `ModuleNotFoundError: No module named 'api'`**
```
→ Wrong working directory
→ Fix: Must be in C:\Users\olani\TrustLayer, not TrustLayer_Client
```

---

## ✅ Checklist: Is Everything Working?

- [ ] Backend responds to `http://127.0.0.1:8000/health` with `{"status":"ok","db":"connected"}`
- [ ] Frontend loads at `http://127.0.0.1:5173`
- [ ] Can click "Start sign-up" button
- [ ] Form appears with pre-filled demo data
- [ ] Submit form (watch Backend Terminal 1 for logs)
- [ ] See onboarding success or error message
- [ ] Check Browser Console (F12) for the API response

---

## 🎓 What You Now Understand

1. **Backend** is a Python FastAPI server that:
   - Receives HTTP requests like `/onboard` and `/score`
   - Calls external services (Dojah for KYC)
   - Saves data to SQLite database
   - Returns JSON responses

2. **Frontend** is a React app that:
   - Shows forms and displays
   - Makes HTTP requests to backend
   - Handles the responses
   - Stores data in localStorage

3. **Environment Variables** control behavior:
   - `ENVIRONMENT='development'` = local testing (permissive CORS)
   - `DATABASE_URL='sqlite:///'` = SQLite database (fast local)
   - `REDIS_URL=''` = disabled (not needed for fast dev)

4. **Logs are your friend**:
   - All errors print to the terminal
   - Read the Python traceback
   - It tells you exactly what went wrong and where

---

## 🔄 Next Steps

1. ✅ Start backend (Terminal 1)
2. ✅ Start frontend (Terminal 2)
3. ✅ Test onboarding flow
4. 📍 **You are here** → Iterate and build
5. Fix any bugs using the error reading guide above
6. When ready: Deploy to Railway or Docker

---

**Questions? Check the logs. Errors? Read the traceback. You've got this! 🎉**
