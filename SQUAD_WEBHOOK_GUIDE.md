# Squad Webhook Integration Guide

## ✅ Status: Fully Implemented

The Squad webhook is **completely integrated** into TrustLayer. This guide shows you how to test and use it.

---

## 📋 What the Webhook Does

1. **Receives Payment Events** from Squad when a user pays
2. **Validates Signature** to ensure it's really from Squad (HMAC-SHA512)
3. **Stores Transaction** in `squad_events` table for payment history
4. **Triggers Score Recomputation** via Celery async task
5. **Returns 200 OK** immediately (Squad won't retry indefinitely)

```
Squad Payment (₦1,000) 
    ↓
  HTTPS POST to your ngrok URL
    ↓
/webhook/squad endpoint
    ↓
    ├─ Validate signature (HMAC-SHA512)
    ├─ Parse JSON payload
    ├─ Find user by email
    ├─ Save to squad_events table
    ├─ Dispatch recompute_score Celery task
    └─ Return 200 {"status": "ok"}
    ↓
Celery task runs async (or skipped if Redis down)
    ↓
Trust score recalculated with new transaction data
```

---

## 🔧 Configuration

### 1. Environment Variables (.env.local)

```bash
# Squad API
SQUAD_SECRET_KEY=sandbox_sk_...         # From Squad dashboard
SQUAD_PUBLIC_KEY=sandbox_pk_...         # For frontend checkout
SQUAD_BASE_URL=https://sandbox-api-d.squadco.com
SQUAD_WEBHOOK_URL=https://<ngrok>/webhook/squad

# Webhook tunnel
NGROK_URL=https://blatancy-shale-deliverer.ngrok-free.dev
```

### 2. Squad Dashboard Setup

- Go to Squad Sandbox Dashboard
- Settings → Webhooks
- URL: `https://your-ngrok-url.ngrok-free.dev/webhook/squad`
- Event: `charge_successful`
- Save

### 3. Backend Requirements

✅ Already done:
- Route: `/api/routes/webhook.py` → `POST /webhook/squad`
- Database: `squad_events` table in schema
- Celery task: `recompute_score.delay()` in `api/celery_app.py`
- Models: `SquadWebhookPayload` and `SquadWebhookBody` in schemas

---

## 🧪 Testing

### Test 1: Signature Validation

```powershell
# Run the test suite
cd C:\Users\olani\TrustLayer
.\.venv\Scripts\python.exe tests/test_webhook_integration.py
```

Expected output:
```
✅ Signature validation test passed!
✅ Payload parsing test passed!
✅ User lookup test passed!
✅ Transaction history test passed!
✅ Database storage test passed!
✅ Complete webhook flow test passed!

📊 RESULTS: 6 passed, 0 failed
```

### Test 2: Send Simulated Webhook

```powershell
# Send test webhook to backend
cd C:\Users\olani\TrustLayer
.\tests\test_webhook.ps1 -Email "adaeze@trustlayer.demo" -Amount 100000
```

This will:
1. Generate a valid HMAC-SHA512 signature
2. POST to `http://127.0.0.1:8000/webhook/squad`
3. Show the response

Expected response:
```json
{
  "status": "ok"
}
```

### Test 3: Check Database

```powershell
# Connect to SQLite database
cd C:\Users\olani\TrustLayer
$db_path = "dev.db"

# List recent transactions
sqlite3 $db_path "SELECT txn_ref, amount, txn_type, status, created_at FROM squad_events ORDER BY created_at DESC LIMIT 5;"
```

---

## 🔐 Security

### Signature Validation

Every webhook is signed with HMAC-SHA512:

```python
# Squad sends this header
x-squad-encrypted-body: abcd1234...

# Backend verifies like this
import hmac, hashlib
secret = SQUAD_SECRET_KEY
expected = hmac.new(secret.encode(), body_bytes, hashlib.sha512).hexdigest()
is_valid = hmac.compare_digest(expected, received_signature)
```

**Always** reject webhooks with invalid signatures (they may be forged).

✅ **Our implementation**: Always returns 200 even on invalid signature (to prevent Squad retry loops), but logs a warning.

### What We Validate

| Check | Method |
|-------|--------|
| Signature | HMAC-SHA512 of raw request body |
| Event type | Must be `charge_successful` |
| Status | Must be `transaction_status: "Success"` |
| Email | User must exist in database |

---

## 📊 Database Schema

### squad_events table

```sql
CREATE TABLE squad_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    txn_ref TEXT NOT NULL UNIQUE,
    amount INTEGER NOT NULL,                    -- in kobo
    txn_type TEXT,                              -- "Card", "Transfer", etc
    status TEXT,                                -- "Success", "Failed", etc
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Example Query

```sql
-- Get all payments for a user
SELECT * FROM squad_events 
WHERE user_id = '6bfcb4a2-6f24-465a-9b1c-15a70c3d3bfa'
ORDER BY created_at DESC;

-- Get total amount paid by user
SELECT 
    user_id, 
    COUNT(*) as txn_count,
    SUM(amount) as total_kobo
FROM squad_events
WHERE status = 'Success'
GROUP BY user_id;
```

---

## 🔄 Integration with Score Calculation

When webhook is received:

```python
# 1. Store transaction
event = SquadEvent(
    user_id=user_id,
    txn_ref=txn_ref,
    amount=amount,
    txn_type=txn_type,
    status="Success"
)
db.add(event)
db.commit()

# 2. Trigger score recompute (async, doesn't block response)
recompute_score.delay(str(user.id), business_id="system")
```

The `recompute_score` task will:
- Query `squad_events` for recent transactions
- Extract features (txn_count_90d, avg_txn_amount, etc)
- Pass to ML scoring pipeline
- Update `trust_scores` table with new score
- Calculate SHAP drivers

---

## 🚀 Production Checklist

- [ ] Update `.env.local` with real Squad credentials
- [ ] Update Squad dashboard webhook URL with production ngrok/domain
- [ ] Test webhook with sandbox payment
- [ ] Monitor backend logs for errors
- [ ] Set up Redis for Celery (or keep REDIS_URL empty for dev)
- [ ] Add monitoring/alerting for webhook failures
- [ ] Document Squad credentials securely
- [ ] Test full flow: Payment → Webhook → Score Update

---

## ❌ Troubleshooting

### "Invalid signature" warning in logs

**Cause**: Webhook payload doesn't match signature
**Fix**: 
1. Verify `SQUAD_SECRET_KEY` is correct
2. Check Squad dashboard webhook URL is set to your ngrok URL
3. Ensure ngrok URL hasn't changed (restart ngrok to get new URL)

### "No user found for email" in logs

**Cause**: Email in webhook doesn't match a user in database
**Fix**:
1. Onboard a user with that email first via `/onboard` endpoint
2. Use demo email: `adaeze@trustlayer.demo` for testing

### "Failed to dispatch recompute_score task"

**Cause**: Redis/Celery not running (expected in dev)
**Fix**: 
1. This is OK during development - the webhook still succeeds
2. For production, set up Redis: `redis://localhost:6379/0`
3. Start Celery: `celery -A api.celery_app worker --loglevel=info`

### Webhook returns 500 error

**Cause**: Unhandled exception in webhook handler
**Fix**:
1. Check backend logs (terminal where uvicorn is running)
2. Look for Python traceback
3. Common issues:
   - Database not initialized: Run `alembic upgrade head`
   - Missing environment variables: Check `.env.local`
   - User not found: Onboard user first

---

## 📝 Webhook Payload Format

### Request (From Squad)

```json
{
  "Event": "charge_successful",
  "TransactionRef": "SQADJFKAS...",
  "Body": {
    "amount": 100000,
    "transaction_ref": "SQADJFKAS...",
    "transaction_status": "Success",
    "email": "user@email.com",
    "transaction_type": "Card",
    "merchant_amount": 100000,
    "created_at": "2026-05-12T12:00:00.000"
  }
}
```

### Headers (From Squad)

```
Authorization: Bearer <token> (optional, for verify)
Content-Type: application/json
x-squad-encrypted-body: abcd1234...ef567890  (HMAC-SHA512 hex)
```

### Response (From TrustLayer)

```json
{
  "status": "ok"
}
```

**Always returns 200**, even if:
- Signature invalid
- Email not found
- Database error
- Celery task failed

This prevents Squad from retrying indefinitely, but all errors are logged.

---

## 🔗 Related Files

- Webhook handler: [api/routes/webhook.py](api/routes/webhook.py)
- Squad integration: [integrations/squad.py](integrations/squad.py)
- Database models: [api/models/db_models.py](api/models/db_models.py)
- Schemas: [api/models/schemas.py](api/models/schemas.py)
- Celery tasks: [api/celery_app.py](api/celery_app.py)
- ML pipeline: [ml/pipeline.py](ml/pipeline.py)

---

## 📚 Reference

### How to Test Locally

1. **Start backend**:
   ```powershell
   Set-Location C:\Users\olani\TrustLayer
   $env:DATABASE_URL='sqlite:///./dev.db'
   $env:REDIS_URL=''
   $env:ENVIRONMENT='development'
   .\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

2. **Run webhook tests**:
   ```powershell
   .\.venv\Scripts\python.exe tests/test_webhook_integration.py
   ```

3. **Send test webhook**:
   ```powershell
   .\tests\test_webhook.ps1
   ```

4. **Monitor backend logs** - Look for:
   - `POST /webhook/squad 200 OK` (success)
   - Any Python tracebacks (errors)
   - Celery task dispatch logs

### How Squad Payment Flow Works

```
1. User on frontend clicks "Buy Report" ($10)
   ↓
2. Frontend calls Squad checkout API (SQUAD_PUBLIC_KEY)
   ↓
3. User enters card details and completes payment
   ↓
4. Squad charges card successfully
   ↓
5. Squad sends POST to /webhook/squad with payment data
   ↓
6. TrustLayer webhook handler processes and returns 200
   ↓
7. Report generation triggered (Celery task)
   ↓
8. User sees "Report ready" on frontend
```

---

## Next Steps

1. ✅ Verify Squad credentials in `.env.local`
2. ✅ Run webhook tests: `python tests/test_webhook_integration.py`
3. ✅ Send test webhook: `.\tests\test_webhook.ps1`
4. ✅ Monitor backend logs
5. 🔄 Test with real Squad payment in sandbox
6. 🚀 Deploy to production with real Squad credentials

---

**Last Updated**: May 12, 2026  
**Status**: Fully Implemented & Tested ✅
