# 📍 Where You Are Right Now

## Current Status: ✅ EVERYTHING IS WORKING

```
✓ Backend running on http://127.0.0.1:8000
✓ Frontend running on http://127.0.0.1:5173
✓ Database connected (SQLite dev.db)
✓ Demo users seeded
✓ ML models trained
✓ Onboarding endpoint tested and working
✓ CORS configured correctly
```

---

## What Just Happened

I taught you **backend fundamentals** while fixing your actual problems:

### Problem 1: "CORS error on /onboard"
**Root Cause**: Multiple stale uvicorn processes on port 8000  
**Fix**: Killed all old processes, started fresh backend  
**Lesson**: Always check `netstat` or `Get-Process` when "port already in use" happens

### Problem 2: "I don't know how to run or debug the backend"
**Root Cause**: No visibility into backend logs or process management  
**Fix**: Created comprehensive guides (STARTUP_GUIDE.md, BACKEND_MASTERY_GUIDE.md)  
**Lesson**: Backend logs (the terminal) show EVERYTHING. Read them.

### Problem 3: "I don't understand what's running where"
**Root Cause**: No mental model of frontend→backend→database flow  
**Fix**: Explained architecture, data flow, and code organization  
**Lesson**: Frontend calls backend via HTTP, backend talks to database and external services

---

## Files I Created for You

1. **`STARTUP_GUIDE.md`** ← **START HERE**
   - 3-step guide to start everything
   - How to test the integration
   - Full troubleshooting checklist

2. **`BACKEND_MASTERY_GUIDE.md`**
   - Detailed architecture explanation
   - Environment variables explained
   - How to read error logs
   - Common errors and fixes

3. **`START_BACKEND.ps1`**
   - PowerShell script to auto-start backend (for Windows)
   - Kill stale processes, set env vars, start uvicorn

---

## How to Use These Files

### To Start Everything Fresh

Open Terminal and run these 2 commands in separate windows:

**Terminal 1:**
```powershell
Set-Location C:\Users\olani\TrustLayer
$env:DATABASE_URL='sqlite:///./dev.db'
$env:REDIS_URL=''
$env:ENVIRONMENT='development'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2:**
```powershell
Set-Location C:\Users\olani\TrustLayer_Client
pnpm dev -- --host 127.0.0.1 --port 5173
```

**Browser:** `http://127.0.0.1:5173`

### To Debug a Problem

1. **Look at backend logs** (Terminal 1)
   - Read the Python traceback
   - It tells you EXACTLY what failed

2. **Check frontend browser console** (F12)
   - Network tab shows HTTP status and response body

3. **Use the troubleshooting guides**
   - BACKEND_MASTERY_GUIDE.md has error solutions

---

## What the Backend Actually Does

```
Request comes in:
  POST /onboard with { bvn, nin, phone, email, ... }
         ↓
Backend receives (api/routes/onboard.py):
  ├─ Validates request format
  ├─ Calls Dojah KYC API (verify_bvn, lookup_nin, etc)
  ├─ Calculates identity_confidence score
  ├─ Determines kyc_status (verified/failed/blocked)
  ├─ Creates User record in database
  └─ Returns JSON with user_id
         ↓
Frontend receives response:
  ├─ Stores user_id in localStorage
  ├─ Redirects to dashboard
  ├─ Shows "Success!" or error message
```

**If it fails**, it crashes at one of those steps. The traceback in the logs tells you which one.

---

## Key Takeaways

### 1. **Backend Logs Are Your Debugger**
```
✗ Not useful: "CORS error" in browser
✓ Useful: Python traceback in Terminal 1
```

### 2. **Environment Variables Control Behavior**
```
ENVIRONMENT='development'  → CORS allows localhost
ENVIRONMENT='production'   → CORS only allows trustlayer.app
```

### 3. **Port Conflicts Are Common**
```
Kill old processes:
Get-Process | Where-Object { $_.ProcessName -eq 'python' } | Kill -Force
```

### 4. **Database Needs Migrations**
```
First run only:
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### 5. **Read the Error Message**
```
KeyError: 'DOJAH_APP_ID'
  → .env.local is missing DOJAH_APP_ID
ModuleNotFoundError: No module named 'api'
  → You're in wrong directory (must be TrustLayer root)
no such table: users
  → Database migrations not run
```

---

## You're Now Ready To

- ✅ Start the backend yourself
- ✅ Understand what's running where
- ✅ Read and debug error logs
- ✅ Integrate frontend with backend
- ✅ Test endpoints end-to-end
- ✅ Troubleshoot common issues
- ✅ Know when to check .env, database, or backend code

---

## Right Now You Can

### Try These Routes (Backend is running):

```powershell
# Health check
Invoke-WebRequest http://127.0.0.1:8000/health

# Test onboarding
$body = @{bvn='22222222222'; nin='70123456789'; phone='09011111111'; selfie_base64='x'; first_name='Test'; last_name='User'; email='test@demo.com'} | ConvertTo-Json
Invoke-WebRequest -Method Post http://127.0.0.1:8000/onboard -Headers @{'Content-Type'='application/json'} -Body $body

# Get existing user (from seeded demo)
Invoke-WebRequest http://127.0.0.1:8000/user/usr_adaeze001
```

### Next Integrations (Once You're Comfortable)

- [ ] Test `/score` endpoint with a user_id
- [ ] Test `/consent` grant/revoke flow
- [ ] Test `/report` endpoint
- [ ] Test webhook endpoints for Squad transactions
- [ ] Integrate database persistence (currently SQLite, can upgrade to Postgres)

---

## Redis, Celery, Docker (You Can Ignore These For Now)

These run in the Docker environment I set up:
- **Redis** (port 6379): Message broker for background jobs
- **ngrok** (port 4040): Webhook tunneling for local testing
- **Docker Compose**: Multi-service orchestration

**For local fast dev**: Skip these. Use SQLite + no background jobs.

When you need them (later):
- `docker compose up` will start everything
- Check `docker-compose.yml` for configuration

---

## Questions?

**Q: How do I know if the backend is running?**  
A: Try `Invoke-WebRequest http://127.0.0.1:8000/health`

**Q: How do I know if frontend is connected to backend?**  
A: Open F12 (browser dev tools), Network tab, try onboarding, see the POST /onboard request

**Q: How do I see what the backend received?**  
A: Look at Terminal 1 logs, see `POST /onboard 200 OK` or `ERROR: ...`

**Q: How do I change the API URL the frontend uses?**  
A: Edit `TrustLayer_Client/.env`, change `VITE_API_BASE_URL`

**Q: How do I add a new field to the onboarding form?**  
A: Edit `TrustLayer_Client/src/pages/user/onboarding.tsx` (frontend) AND `api/models/schemas.py` (backend schema) + `api/routes/onboard.py` (backend handler)

---

## Summary

You now have:
- ✅ A working backend serving real API endpoints
- ✅ A working frontend calling those endpoints
- ✅ A local SQLite database with demo users
- ✅ ML models trained and ready
- ✅ Understanding of how everything connects
- ✅ Knowledge of how to start, run, and debug

**Next**: Open your browser, go to `http://127.0.0.1:5173`, try the onboarding form, and watch the magic happen in the logs. 🎉

