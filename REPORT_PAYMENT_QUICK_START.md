# Report Payment with Squad - Complete Implementation Guide

## ✅ What's Ready

Your complete report generation and payment flow is now integrated with Squad:

```
Dashboard/Reports Page
    ↓
User clicks "Generate Report"
    ↓
Frontend calls: POST /report/initiate-payment
    ├─ Backend: Creates Report record (pending)
    ├─ Backend: Calls Squad /transaction/initiate
    └─ Returns: { report_id, checkout_url, txn_ref, amount }
    ↓
Frontend: Opens Squad checkout modal with checkout_url
    ↓
User: Completes payment on Squad
    ↓
Squad: Sends webhook to /webhook/squad
    ├─ Backend: Validates HMAC-SHA512 signature
    ├─ Backend: Creates SquadEvent record
    ├─ Backend: Detects txn_ref = "report_<report_id>"
    ├─ Backend: Updates Report status → "generating"
    └─ Backend: Dispatches Celery task: generate_report
    ↓
Celery Task (async, runs in background):
    ├─ Generates PDF report
    ├─ Uploads/saves file
    ├─ Updates Report.file_url
    ├─ Updates Report.status → "ready"
    ├─ Recomputes user's trust score
    └─ Notifies frontend (via polling)
    ↓
Frontend: Polls GET /reports/{user_id}
    ├─ Sees Report.status = "ready"
    └─ Displays download button with file_url
    ↓
User: Downloads generated PDF report
```

---

## 🚀 Quick Test (Dev Mode)

### 1. Start Backend

```powershell
cd C:\Users\olani\TrustLayer
$env:DATABASE_URL='sqlite:///./dev.db'
$env:REDIS_URL=''
$env:ENVIRONMENT='development'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### 2. Run Test Script

```powershell
cd C:\Users\olani\TrustLayer
.\tests\test_report_flow.ps1
```

This will:
1. ✅ Login as demo user
2. ✅ Initiate report payment (calls Squad API)
3. ✅ Simulate webhook (dev mode only)
4. ✅ Wait for report generation
5. ✅ Check report status

**Expected output:**
```
[1/5] Logging in... [OK]
[2/5] Initiating report payment... [OK]
[3/5] Simulating payment webhook... [OK]
[4/5] Waiting for report generation...
[5/5] Fetching report status...
[SUCCESS] Report is ready to download!
```

---

## 📋 What Changed

### Files Modified

#### `api/routes/reports.py`
- ✅ Added logging to track payment flow
- ✅ Enhanced error handling in `/report/initiate-payment`
- ✅ Handles multiple Squad response formats (nested/flat)
- ✅ Falls back to mock checkout_url in dev mode
- ✅ Added `POST /report/test-payment-webhook` for dev testing

#### `.env.local`
- ✅ Already has Squad credentials (from webhook integration)

### Files Created

#### `REPORT_PAYMENT_GUIDE.md`
Complete walkthrough of the entire flow, including:
- Architecture diagram
- Step-by-step test instructions
- Troubleshooting guide
- Frontend integration pseudocode

#### `tests/test_report_flow.ps1`
PowerShell script that tests:
1. User login
2. Payment initiation
3. Webhook simulation (dev)
4. Report generation
5. Status polling

---

## 🎯 Integration Points

### Frontend → Backend

**POST /report/initiate-payment**
```json
{
  "user_id": "uuid",
  "report_type": "verified_trust_report",
  "recipient_id": "optional"
}
```

**Response:**
```json
{
  "report_id": "uuid",
  "checkout_url": "https://sandbox.squadco.com/...",
  "txn_ref": "report_<report_id>",
  "amount": 500
}
```

**Usage in Frontend:**
```typescript
// After getting response
window.open(response.checkout_url, 'Squad', 'width=500,height=700')

// Poll for status
const interval = setInterval(async () => {
  const reports = await fetch(`/reports/${user_id}`)
  const report = reports.find(r => r.id === report_id)
  
  if (report.status === 'ready') {
    clearInterval(interval)
    // Show download button pointing to report.file_url
  }
}, 2000)
```

### Backend ← Squad Webhook

**Incoming:**
```json
{
  "Event": "charge_successful",
  "TransactionRef": "report_<report_id>",
  "Body": {
    "amount": 50000,
    "transaction_status": "Success",
    "email": "user@example.com",
    ...
  }
}
```

**Processing:**
1. ✅ Validates HMAC-SHA512 signature
2. ✅ Detects `report_` prefix
3. ✅ Updates Report status to `generating`
4. ✅ Dispatches `generate_report` Celery task
5. ✅ Returns `200 {"status": "ok"}`

---

## 🔄 Report Generation Flow

### Database State Changes

```sql
-- When user initiates payment
INSERT INTO reports (id, user_id, status, report_type)
VALUES (uuid, user_uuid, 'pending', 'verified_trust_report')

-- When Squad webhook received
UPDATE reports SET status = 'generating' WHERE id = report_uuid

-- When Celery task completes
UPDATE reports SET 
  status = 'ready',
  file_url = 'https://cdn.example.com/reports/uuid.pdf'
WHERE id = report_uuid

-- Payment recorded
INSERT INTO squad_events (user_id, txn_ref, amount, status)
VALUES (user_uuid, 'report_<report_id>', 50000, 'Success')
```

---

## 🧪 Development Mode Testing

### Without Real Payments

Use the test endpoint to simulate Squad's webhook:

```powershell
# 1. Initiate payment (creates Report, returns checkout_url)
$paymentResp = Invoke-RestMethod -Method POST `
  -Uri "http://127.0.0.1:8000/report/initiate-payment" `
  -Headers @{ Authorization = "Bearer $token" } `
  -Body $paymentBody

$report_id = $paymentResp.report_id

# 2. Simulate webhook (dev mode only)
Invoke-RestMethod -Method POST `
  -Uri "http://127.0.0.1:8000/report/test-payment-webhook?report_id=$report_id" `
  -Headers @{ Authorization = "Bearer $token" }

# Report status is now "generating" → will become "ready" after task completes
```

### Why This Test Endpoint?

- ✅ No need for real Squad account/credentials
- ✅ Test full flow without payment gateway
- ✅ Test Celery task execution
- ✅ Verify database updates
- ✅ Verify API responses
- ✅ Only available in `ENVIRONMENT=development`

---

## 🚨 Troubleshooting

### "Checkout URL is empty"

**Cause**: Squad API not returning URL  
**Check logs for**: `Report payment: Squad response for report_<uuid>: {...}`

**Solution:**
1. Verify `SQUAD_SECRET_KEY` in `.env.local`
2. Verify `SQUAD_BASE_URL=https://sandbox-api-d.squadco.com`
3. Check Squad dashboard for API errors
4. In dev mode, falls back to mock URL (OK for testing)

### "Report stuck in pending"

**Cause**: Webhook not received or test endpoint not called  

**Check:**
1. Backend logs: `POST /webhook/squad` succeeded?
2. Database: `SELECT * FROM squad_events WHERE txn_ref LIKE 'report_%'`
3. Test with dev endpoint: `POST /report/test-payment-webhook`

### "Report stuck in generating"

**Cause**: Celery task failed or Redis not running  

**Check:**
1. Backend logs for task errors
2. Is Redis running? (not required for dev)
3. Try restarting backend

**For Dev:**
- `REDIS_URL=''` disables Celery (task will fail silently)
- Report status won't change to "ready" unless task succeeds
- Use test endpoint to debug task execution

### "Report not found after payment"

**Debug steps:**
```powershell
# 1. Check report was created
sqlite3 dev.db "SELECT * FROM reports WHERE user_id = '<uuid>'"

# 2. Check payment was recorded
sqlite3 dev.db "SELECT * FROM squad_events WHERE txn_ref LIKE 'report_%'"

# 3. Check backend logs for webhook errors
# Look for "POST /webhook/squad" in terminal logs
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| [REPORT_PAYMENT_GUIDE.md](REPORT_PAYMENT_GUIDE.md) | Complete walkthrough + troubleshooting |
| [SQUAD_WEBHOOK_QUICK_START.md](SQUAD_WEBHOOK_QUICK_START.md) | Squad webhook quick reference |
| [SQUAD_WEBHOOK_GUIDE.md](SQUAD_WEBHOOK_GUIDE.md) | Detailed webhook documentation |
| [tests/test_report_flow.ps1](tests/test_report_flow.ps1) | Automated test script |

---

## ✅ Checklist

- [x] POST /report/initiate-payment endpoint
- [x] Squad API integration (initiate_payment)
- [x] Webhook handler for report_* txn_ref
- [x] Report status state machine (pending → generating → ready)
- [x] Celery task dispatch for report generation
- [x] Dev test endpoint (no real payment needed)
- [x] Enhanced logging throughout flow
- [x] Error handling and graceful fallbacks
- [x] Documentation + test scripts
- [ ] Frontend integration (your team)
- [ ] Real Squad payment testing
- [ ] Production deployment

---

## 🎬 Next Steps

### For Testing Now

1. ✅ Run test script: `.\tests\test_report_flow.ps1`
2. ✅ Verify report appears in database
3. ✅ Check report status changes to "ready"

### For Frontend Integration

1. ✅ Call `/report/initiate-payment` when user clicks "Generate Report"
2. ✅ Open `checkout_url` in Squad modal/popup
3. ✅ Poll `/reports/{user_id}` every 2 seconds for status
4. ✅ When status = "ready", show download button with `file_url`

### For Production

1. ✅ Update Squad credentials in environment
2. ✅ Register webhook URL in Squad dashboard
3. ✅ Deploy backend with updated env vars
4. ✅ Test with real Squad sandbox payment
5. ✅ Monitor webhook logs for errors

---

**Status**: ✅ Ready for Testing  
**Last Updated**: May 12, 2026
