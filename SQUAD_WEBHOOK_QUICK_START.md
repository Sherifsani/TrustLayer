# Squad Webhook - Quick Start

## ✅ What's Done

Your Squad webhook is **fully integrated and ready to use**. Here's what's implemented:

| Component | Status | Details |
|-----------|--------|---------|
| Webhook route | ✅ | `POST /webhook/squad` - receives payments |
| Signature validation | ✅ | HMAC-SHA512 - verifies Squad sent it |
| Database storage | ✅ | Saves to `squad_events` table |
| Score recomputation | ✅ | Celery task triggered on payment |
| Error handling | ✅ | Always returns 200, never crashes |

---

## 🚀 Quick Test (2 minutes)

### 1. Verify Configuration

```powershell
cd C:\Users\olani\TrustLayer
cat .env.local | Select-String "SQUAD"
```

Expected output:
```
SQUAD_SECRET_KEY=sandbox_sk_...
SQUAD_PUBLIC_KEY=sandbox_pk_...
SQUAD_BASE_URL=https://sandbox-api-d.squadco.com
SQUAD_WEBHOOK_URL=https://blatancy-shale-deliverer.ngrok-free.dev/webhook/squad
```

If keys are missing, update `.env.local` with your real Squad credentials from the Squad dashboard.

### 2. Run Database Test

```powershell
$env:DATABASE_URL='sqlite:///./dev.db'
.\.venv\Scripts\python.exe tests/quick_webhook_test.py
```

Expected output:
```
[OK] Found user: Adaeze Okafor
[OK] Signature validation works
[OK] Stored test transaction
```

### 3. Send Test Webhook

```powershell
.\tests\test_webhook.ps1 -Email "adaeze@trustlayer.demo" -Amount 100000
```

Expected output:
```
[SUCCESS (200 OK)]
Response: {"status": "ok"}
Transaction Ref: SQTEST_...
```

---

## 📝 How to Use in Production

### Step 1: Update Squad Credentials

Edit `.env.local` and add your real credentials:

```
SQUAD_SECRET_KEY=sandbox_sk_your_real_key_here
SQUAD_PUBLIC_KEY=sandbox_pk_your_real_key_here
```

Get these from: Squad Dashboard → Settings → API Keys

### Step 2: Register Webhook URL

1. Go to Squad Dashboard → Settings → Webhooks
2. Add webhook URL: `https://your-ngrok-url.ngrok-free.dev/webhook/squad`
3. Event type: `charge_successful`
4. Save

### Step 3: Test with Real Payment

1. Start backend: 
   ```powershell
   Set-Location C:\Users\olani\TrustLayer
   $env:DATABASE_URL='sqlite:///./dev.db'
   $env:REDIS_URL=''
   $env:ENVIRONMENT='development'
   .\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

2. Make a payment in Squad sandbox
3. Watch backend logs for: `POST /webhook/squad 200 OK`
4. Check database for transaction:
   ```powershell
   sqlite3 dev.db "SELECT * FROM squad_events ORDER BY created_at DESC LIMIT 1;"
   ```

---

## 🔍 What Happens Inside

```
User makes Squad payment ₦1,000
    ↓
Squad sends: POST /webhook/squad
    ├─ Event: "charge_successful"
    ├─ Body: email, amount, txn_ref, etc
    └─ Header: x-squad-encrypted-body (HMAC-SHA512 signature)
    ↓
TrustLayer backend receives:
    ├─ Validates signature
    ├─ Finds user by email
    ├─ Stores in squad_events table
    ├─ Returns 200 immediately
    └─ Dispatches recompute_score Celery task
    ↓
Celery task (async, doesn't block response):
    ├─ Queries squad_events for user's recent transactions
    ├─ Extracts ML features
    ├─ Runs scoring algorithm
    └─ Updates trust_scores table
    ↓
Trust score increased based on payment history
```

---

## 🛠️ Files to Know

| File | Purpose |
|------|---------|
| `api/routes/webhook.py` | Webhook request handler |
| `integrations/squad.py` | Squad API calls + signature validation |
| `api/celery_app.py` | Background task runner |
| `api/models/db_models.py` | SquadEvent database table |
| `tests/quick_webhook_test.py` | Verification script |
| `tests/test_webhook.ps1` | Test webhook sender |
| `SQUAD_WEBHOOK_GUIDE.md` | Full documentation |

---

## ❓ Troubleshooting

### "Invalid signature" in logs

```
WARNING: Squad webhook: invalid signature
```

**Cause**: `SQUAD_SECRET_KEY` doesn't match  
**Fix**: Verify `.env.local` has correct key from Squad dashboard

### "No user found for email"

```
INFO: Squad webhook: no user found for email test@example.com
```

**Cause**: User doesn't exist in database  
**Fix**: Onboard user first via `/onboard` endpoint

### "Failed to dispatch recompute_score task"

```
ERROR: Failed to dispatch recompute_score task
```

**Cause**: Redis not running (OK in dev, needed in production)  
**Fix**: For dev, this is normal - just log the error and continue  
For prod: Start Redis - `redis-server` or Docker container

### Webhook endpoint returns 500

**Fix**: 
1. Check backend terminal for Python traceback
2. Verify database is initialized: `alembic upgrade head`
3. Check environment variables: `$env:DATABASE_URL`, `$env:SQUAD_SECRET_KEY`

---

## 📊 Monitoring

### Check recent transactions

```powershell
sqlite3 dev.db @"
SELECT 
  txn_ref, 
  amount, 
  txn_type, 
  status, 
  created_at 
FROM squad_events 
ORDER BY created_at DESC 
LIMIT 10;
"@
```

### Check webhook errors in logs

Look for patterns in backend terminal:
- `POST /webhook/squad 200 OK` - success
- `invalid signature` - security issue
- `no user found` - user doesn't exist
- `Failed to dispatch` - Celery/Redis issue

---

## 🎯 Success Criteria

✅ Webhook integration is complete when:

1. `tests/quick_webhook_test.py` passes all checks
2. `.\tests\test_webhook.ps1` returns `{"status": "ok"}`
3. Transaction appears in `squad_events` table
4. Backend logs show `POST /webhook/squad 200 OK`
5. Real Squad payment in sandbox triggers webhook

---

**Last Updated**: May 12, 2026  
**Status**: Ready for Production ✅
