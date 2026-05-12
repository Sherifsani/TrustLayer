# Report Payment Flow Test Script
# Usage: .\tests\test_report_flow.ps1

param(
    [string]$Email = "adaeze@trustlayer.demo",
    [string]$Password = "demo1234",
    [string]$ReportType = "verified_trust_report",
    [string]$Backend = "http://127.0.0.1:8000"
)

Write-Host "`n" + "=" * 60
Write-Host "REPORT PAYMENT FLOW TEST"
Write-Host "=" * 60
Write-Host "Backend: $Backend"
Write-Host "Email: $Email"
Write-Host "Report Type: $ReportType"
Write-Host ""

# ============================================================================
# STEP 1: Login
# ============================================================================
Write-Host "[1/5] Logging in..." -ForegroundColor Cyan
try {
    $loginBody = @{ email = $Email; password = $Password } | ConvertTo-Json
    $loginResp = Invoke-RestMethod -Method POST `
        -Uri "$Backend/auth/login" `
        -Body $loginBody `
        -ContentType 'application/json' `
        -ErrorAction Stop

    $token = $loginResp.access_token
    $user_id = $loginResp.user_id
    
    Write-Host "[OK] Logged in successfully" -ForegroundColor Green
    Write-Host "     User ID: $user_id"
    Write-Host "     Token: $($token.Substring(0, 30))..."
}
catch {
    Write-Host "[FAILED] Login error:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# ============================================================================
# STEP 2: Initiate Payment
# ============================================================================
Write-Host "[2/5] Initiating report payment..." -ForegroundColor Cyan
try {
    $paymentBody = @{
        user_id = $user_id
        report_type = $ReportType
        recipient_id = ""
    } | ConvertTo-Json

    $paymentResp = Invoke-RestMethod -Method POST `
        -Uri "$Backend/report/initiate-payment" `
        -Body $paymentBody `
        -ContentType 'application/json' `
        -Headers @{ Authorization = "Bearer $token" } `
        -ErrorAction Stop

    $report_id = $paymentResp.report_id
    $checkout_url = $paymentResp.checkout_url
    $txn_ref = $paymentResp.txn_ref
    $amount = $paymentResp.amount

    Write-Host "[OK] Payment initiated" -ForegroundColor Green
    Write-Host "     Report ID: $report_id"
    Write-Host "     Amount: N$amount"
    Write-Host "     Txn Ref: $txn_ref"
    
    if ($checkout_url) {
        Write-Host "     Checkout URL: $($checkout_url.Substring(0, 60))..."
    }
    else {
        Write-Host "     [WARN] Checkout URL empty (using dev mode or API error)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[FAILED] Payment initiation error:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# ============================================================================
# STEP 3: Simulate Webhook (DEV MODE)
# ============================================================================
Write-Host "[3/5] Simulating payment success webhook (dev mode)..." -ForegroundColor Cyan
try {
    $webhookResp = Invoke-RestMethod -Method POST `
        -Uri "$Backend/report/test-payment-webhook?report_id=$report_id" `
        -Body "{}" `
        -ContentType 'application/json' `
        -Headers @{ Authorization = "Bearer $token" } `
        -ErrorAction Stop

    Write-Host "[OK] Webhook simulated" -ForegroundColor Green
    Write-Host "     Response: $($webhookResp.status)"
    Write-Host "     Report Status: $($webhookResp.report_status)"
}
catch {
    Write-Host "[FAILED] Webhook simulation error:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)"
    Write-Host "   [INFO] This is expected if backend is not in development mode"
    Write-Host "   [INFO] For production, use real Squad payments"
    exit 1
}
Write-Host ""

# ============================================================================
# STEP 4: Wait for Generation
# ============================================================================
Write-Host "[4/5] Waiting for report generation..." -ForegroundColor Cyan
Write-Host "     (Celery task running in background)"
$waitTime = 3
for ($i = $waitTime; $i -gt 0; $i--) {
    Write-Host "     $i seconds..." -NoNewline
    Start-Sleep -Seconds 1
    Write-Host "`r" -NoNewline
}
Write-Host "     Waited $waitTime seconds" -ForegroundColor Green
Write-Host ""

# ============================================================================
# STEP 5: Fetch Report Status
# ============================================================================
Write-Host "[5/5] Fetching report status..." -ForegroundColor Cyan
try {
    $reportsResp = Invoke-RestMethod -Method GET `
        -Uri "$Backend/reports/$user_id" `
        -Headers @{ Authorization = "Bearer $token" } `
        -ErrorAction Stop

    if ($reportsResp.reports.Count -gt 0) {
        $report = $reportsResp.reports[0]
        
        Write-Host "[OK] Report found" -ForegroundColor Green
        Write-Host "     Title: $($report.title)"
        Write-Host "     Type: $($report.report_type)"
        Write-Host "     Status: $($report.status)"
        
        if ($report.file_url) {
            Write-Host "     File URL: $($report.file_url.Substring(0, 50))..."
        }
        
        Write-Host ""
        if ($report.status -eq "ready") {
            Write-Host "[SUCCESS] Report is ready to download!" -ForegroundColor Green
            Write-Host "           You can now download from: $($report.file_url)"
        }
        elseif ($report.status -eq "generating") {
            Write-Host "[PENDING] Report is still generating..." -ForegroundColor Yellow
            Write-Host "          Try again in a few seconds"
        }
        else {
            Write-Host "[INFO] Report status: $($report.status)" -ForegroundColor Cyan
        }
    }
    else {
        Write-Host "[WARN] No reports found" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[FAILED] Fetch reports error:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)"
    exit 1
}
Write-Host ""

# ============================================================================
# Summary
# ============================================================================
Write-Host "=" * 60
Write-Host "TEST COMPLETE" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Check backend logs for any errors"
Write-Host "2. Verify report status is 'ready'"
Write-Host "3. Try downloading the report from frontend"
Write-Host ""
Write-Host "For real Squad payments:"
Write-Host "1. Use checkout_url to open Squad checkout modal"
Write-Host "2. Complete payment on Squad"
Write-Host "3. Squad webhooks will trigger report generation"
Write-Host ""
