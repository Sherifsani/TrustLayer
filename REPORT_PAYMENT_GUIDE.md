# Report Payment Integration Guide

## 📋 What's Implemented

The complete report generation workflow with Squad payments is ready:

```
User clicks "Generate Report"
    ↓
POST /report/initiate-payment
    ├─ Create Report record (status="pending")
    ├─ Call Squad /transaction/initiate
    ├─ Return checkout_url + txn_ref
    └─ Response: { report_id, checkout_url, txn_ref, amount }
    ↓
Frontend opens Squad checkout modal
    ↓
User completes payment on Squad
    ↓
Squad sends webhook: POST /webhook/squad
    ├─ Validate signature
    ├─ Create SquadEvent record
    ├─ Detect txn_ref starts with "report_"
    ├─ Update Report status to "generating"
    └─ Dispatch generate_report Celery task
    ↓
Celery task (async):
    ├─ Generate PDF
    ├─ Save file_url
    ├─ Update Report status to "ready"
    └─ Trigger score recomputation
    ↓
Frontend fetches GET /reports/{user_id}
    ├─ See Report with status="ready"
    ├─ Download file from file_url
    └─ Report ready to view
```

---

## 🚀 Quick Start

### Step 1: Start Backend

```powershell
Set-Location C:\Users\olani\TrustLayer
$env:DATABASE_URL='sqlite:///./dev.db'
$env:REDIS_URL=''
$env:ENVIRONMENT='development'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

### Step 2: Test Endpoint (DEV MODE)

For development, there's a test endpoint that simulates Squad's webhook:

```powershell
# First, get a token
$email = "adaeze@trustlayer.demo"
$password = "demo1234"
$loginBody = @{ email=$email; password=$password } | ConvertTo-Json
$loginResp = Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/auth/login" `
  -Body $loginBody -ContentType 'application/json'
$token = $loginResp.access_token

# Then, initiate report payment
$user_id = "6bfcb4a2-6f24-465a-9b1c-15a70c3d3bfa"  # Adaeze's UUID
$paymentBody = @{
  user_id = $user_id
  report_type = "verified_trust_report"
  recipient_id = ""
} | ConvertTo-Json

$paymentResp = Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/report/initiate-payment" `
  -Body $paymentBody `
  -ContentType 'application/json' `
  -Headers @{ Authorization = "Bearer $token" }

Write-Host "Report ID: $($paymentResp.report_id)"
Write-Host "Checkout URL: $($paymentResp.checkout_url)"
Write-Host "Transaction Ref: $($paymentResp.txn_ref)"
Write-Host "Amount: ₦$($paymentResp.amount)"

# Save report_id for next step
$report_id = $paymentResp.report_id
```

### Step 3: Simulate Payment Success (DEV MODE)

```powershell
# This simulates Squad's webhook without needing real payment
$testWebhookBody = @{} | ConvertTo-Json
$testResp = Invoke-RestMethod -Method POST `
  -Uri "http://127.0.0.1:8000/report/test-payment-webhook?report_id=$report_id" `
  -Body $testWebhookBody `
  -ContentType 'application/json' `
  -Headers @{ Authorization = "Bearer $token" }

Write-Host "Webhook response: $($testResp | ConvertTo-Json)"
```

### Step 4: Check Report Status

```powershell
# Wait 3 seconds for Celery task to complete (or longer if slow)
Start-Sleep -Seconds 3

# Fetch reports
$reportsResp = Invoke-RestMethod -Method GET `
  -Uri "http://127.0.0.1:8000/reports/$user_id" `
  -Headers @{ Authorization = "Bearer $token" }

Write-Host "Reports: $($reportsResp | ConvertTo-Json -Depth 5)"
# Should show: status = "ready" and file_url with generated PDF
```

---

## 🧪 Complete Test Script

Here's a full test script for the entire flow:

```powershell
# Save as .\tests\test_report_flow.ps1

param(
    [string]$Email = "adaeze@trustlayer.demo",
    [string]$Password = "demo1234",
    [string]$ReportType = "verified_trust_report"
)

$baseUrl = "http://127.0.0.1:8000"

Write-Host "=== Report Payment Flow Test ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Login
Write-Host "[1/5] Logging in as $Email..." -ForegroundColor Green
$loginBody = @{ email=$Email; password=$Password } | ConvertTo-Json
$loginResp = Invoke-RestMethod -Method POST -Uri "$baseUrl/auth/login" `
  -Body $loginBody -ContentType 'application/json' -ErrorAction Stop
$token = $loginResp.access_token
$user_id = $loginResp.user_id
Write-Host "       User ID: $user_id"
Write-Host "       Token: $($token.Substring(0, 30))..."
Write-Host ""

# Step 2: Initiate Payment
Write-Host "[2/5] Initiating report payment..." -ForegroundColor Green
$paymentBody = @{
  user_id = $user_id
  report_type = $ReportType
  recipient_id = ""
} | ConvertTo-Json

$paymentResp = Invoke-RestMethod -Method POST -Uri "$baseUrl/report/initiate-payment" `
  -Body $paymentBody -ContentType 'application/json' `
  -Headers @{ Authorization = "Bearer $token" } -ErrorAction Stop

$report_id = $paymentResp.report_id
Write-Host "       Report ID: $report_id"
Write-Host "       Amount: ₦$($paymentResp.amount)"
Write-Host "       Checkout URL: $($paymentResp.checkout_url.Substring(0, 50))..."
Write-Host ""

# Step 3: Simulate Payment Success
Write-Host "[3/5] Simulating payment success webhook..." -ForegroundColor Green
$webhookResp = Invoke-RestMethod -Method POST `
  -Uri "$baseUrl/report/test-payment-webhook?report_id=$report_id" `
  -Body "{}"-ContentType 'application/json' `
  -Headers @{ Authorization = "Bearer $token" } -ErrorAction Stop
Write-Host "       Status: $($webhookResp.status)"
Write-Host ""

# Step 4: Wait for Generation
Write-Host "[4/5] Waiting for report generation (Celery task)..." -ForegroundColor Green
Write-Host "       Waiting 3 seconds..."
Start-Sleep -Seconds 3
Write-Host ""

# Step 5: Fetch Report
Write-Host "[5/5] Fetching generated report..." -ForegroundColor Green
$reportsResp = Invoke-RestMethod -Method GET `
  -Uri "$baseUrl/reports/$user_id" `
  -Headers @{ Authorization = "Bearer $token" } -ErrorAction Stop

if ($reportsResp.reports.Count -gt 0) {
    $report = $reportsResp.reports[0]
    Write-Host "       Report Title: $($report.title)"
    Write-Host "       Status: $($report.status)"
    Write-Host "       File URL: $($report.file_url)"
    if ($report.status -eq "ready") {
        Write-Host "       [SUCCESS] Report is ready!" -ForegroundColor Green
    } elseif ($report.status -eq "generating") {
        Write-Host "       [PENDING] Report still generating (Celery task running)..." -ForegroundColor Yellow
    } else {
        Write-Host "       [STATUS] Current status: $($report.status)" -ForegroundColor Yellow
    }
} else {
    Write-Host "       No reports found" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
```

---

## 🔄 Real Squad Integration (Production)

When using real Squad payments:

### 1. Update Environment

```
SQUAD_SECRET_KEY=sandbox_sk_<real_key>
SQUAD_PUBLIC_KEY=sandbox_pk_<real_key>
SQUAD_WEBHOOK_URL=https://your-domain.com/webhook/squad
```

### 2. Open Checkout in Frontend

The `checkout_url` returned from `/report/initiate-payment` should be:
- Opened in Squad's checkout modal on the frontend
- Or opened as a new window/tab
- Squad handles the rest (payment, 3D secure, etc)

### 3. Webhook Flow

When payment succeeds:
1. Squad sends `POST /webhook/squad` with `txn_ref="report_<report_id>"`
2. Backend webhook handler detects the `report_` prefix
3. Report status changes to `generating`
4. Celery task `generate_report` is dispatched
5. Report generation happens asynchronously
6. Frontend polls `/reports/{user_id}` and shows status progress

### 4. Frontend Integration

```typescript
// Pseudocode for frontend

// After initiate-payment
const response = await fetch('/report/initiate-payment', { ... })
const { checkout_url, report_id } = response

// Open Squad checkout
window.open(checkout_url, 'Squad Payment', 'width=500,height=700')

// Poll for status every 2 seconds
const pollInterval = setInterval(async () => {
  const reports = await fetch(`/reports/${user_id}`, { ... })
  const report = reports.find(r => r.id === report_id)
  
  if (report.status === 'ready') {
    clearInterval(pollInterval)
    downloadReport(report.file_url)
  } else if (report.status === 'generating') {
    showSpinner('Generating report...')
  } else if (report.status === 'pending') {
    showSpinner('Waiting for payment...')
  }
}, 2000)
```

---

## 📊 Database Flow

### Reports Table

```sql
-- New report created in pending status
INSERT INTO reports (id, user_id, title, status)
VALUES (uuid, user_uuid, 'Verified Trust Report — May 2026', 'pending')

-- After Squad webhook received
UPDATE reports SET status = 'generating' WHERE id = report_uuid

-- After Celery task completes
UPDATE reports SET status = 'ready', file_url = 'https://...' WHERE id = report_uuid
```

### Squad Events Table

```sql
-- Squad webhook stores payment
INSERT INTO squad_events (id, user_id, txn_ref, amount, status)
VALUES (
  uuid,
  user_uuid,
  'report_<report_uuid>',
  50000,           -- 500 kobo = ₦500
  'Success'
)
```

---

## 🛠️ Files Modified

- `api/routes/reports.py` - Enhanced with logging, error handling, test endpoint
- `.env.local` - Added Squad credentials (was already there)

---

## 🐛 Troubleshooting

### "Checkout URL is empty"

**Log to check**:
```
Report payment: Squad response for report_<uuid>: {...}
```

Look at what Squad actually returns. It might be:
- `{ "data": { "checkout_url": "..." } }` (nested)
- `{ "checkout_url": "..." }` (flat)
- `{ "link": "..." }` (different field name)

The code handles all three. If still empty:
1. Verify `SQUAD_SECRET_KEY` is correct
2. Verify `SQUAD_BASE_URL` points to sandbox
3. Check Squad dashboard for API errors

### "Report stuck in generating"

**Cause**: Celery task failed  
**Check**: 
- Is Redis running? `redis-cli ping`
- Backend logs for `generate_report` task errors
- For dev: REDIS_URL can be empty (task will fail silently)

**Fix**:
- Use test endpoint in dev: `POST /report/test-payment-webhook?report_id=<uuid>`
- This simulates webhook without Celery

### "Report not found after payment"

**Check**:
1. Report was created: `SELECT * FROM reports WHERE user_id = '<uuid>'`
2. Webhook was received: `SELECT * FROM squad_events WHERE txn_ref LIKE 'report_%'`
3. Check backend logs for webhook processing errors

---

## ✅ Success Checklist

- [ ] Backend running on :8000
- [ ] User can login
- [ ] `POST /report/initiate-payment` returns checkout_url
- [ ] `POST /report/test-payment-webhook` succeeds (dev mode)
- [ ] Report status changes from pending → generating → ready
- [ ] `GET /reports/{user_id}` shows ready reports
- [ ] Real Squad payments work with webhook

---

**Status**: ✅ Ready for Testing  
**Last Updated**: May 12, 2026
