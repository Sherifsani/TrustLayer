# Squad Webhook Test - Send Simulated Payment Events
# 
# This script sends test webhook payloads to your local backend
# Usage: .\tests\test_webhook.ps1
#
# Make sure backend is running on http://127.0.0.1:8000

param(
    [string]$Email = "adaeze@trustlayer.demo",
    [int]$Amount = 100000,
    [string]$Backend = "http://127.0.0.1:8000"
)

Write-Host "🚀 SQUAD WEBHOOK TEST" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host "Backend: $Backend"
Write-Host "Email: $Email"
Write-Host "Amount: $Amount kobo (~₦$($Amount/100))"
Write-Host ""

# Load environment variables
$env_file = "$PSScriptRoot\..\. env.local"
if (Test-Path $env_file) {
    Get-Content $env_file | ForEach-Object {
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            if (-not (Get-Item "env:$key" -ErrorAction SilentlyContinue)) {
                New-Item "env:$key" -Value $value -Force > $null
            }
        }
    }
}

$SQUAD_SECRET = $env:SQUAD_SECRET_KEY
if (-not $SQUAD_SECRET) {
    $SQUAD_SECRET = "sandbox_sk_test_key_please_replace_with_real_key"
    Write-Host "⚠️  SQUAD_SECRET_KEY not set in .env.local" -ForegroundColor Yellow
    Write-Host "   Using placeholder: $SQUAD_SECRET" -ForegroundColor Yellow
}

# Create payload
$txn_ref = "SQTEST_$(Get-Date -Format 'yyyyMMddHHmmss')_$([math]::Floor([math]::Random() * 10000))"

$payload = @{
    Event = "charge_successful"
    TransactionRef = $txn_ref
    Body = @{
        amount = $Amount
        transaction_ref = $txn_ref
        transaction_status = "Success"
        email = $Email
        transaction_type = "Card"
        merchant_amount = $Amount
        created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fff")
    }
} | ConvertTo-Json

Write-Host "📧 Payload:" -ForegroundColor Green
Write-Host $payload
Write-Host ""

# Calculate signature
$body_bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
$secret_bytes = [System.Text.Encoding]::UTF8.GetBytes($SQUAD_SECRET)
$hmac = New-Object System.Security.Cryptography.HMACSHA512 @(,$secret_bytes)
$hash = $hmac.ComputeHash($body_bytes)
$signature = [System.BitConverter]::ToString($hash) -replace '-', ''
$signature = $signature.ToLower()

Write-Host "🔐 Signature:" -ForegroundColor Green
Write-Host $signature.Substring(0, 32) + "..."
Write-Host ""

# Send to backend
Write-Host "📤 Sending webhook..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod `
        -Method POST `
        -Uri "$Backend/webhook/squad" `
        -Body $payload `
        -ContentType 'application/json' `
        -Headers @{
            'x-squad-encrypted-body' = $signature
        } `
        -ErrorAction Stop

    Write-Host "✅ SUCCESS (200 OK)" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 2)
    Write-Host ""
    Write-Host "📋 Transaction Ref: $txn_ref" -ForegroundColor Cyan
    Write-Host "   Check database: SELECT * FROM squad_events WHERE txn_ref='$txn_ref'" -ForegroundColor Gray
    
} catch {
    Write-Host "❌ FAILED" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔍 Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Is backend running? Test: curl http://127.0.0.1:8000/health" -ForegroundColor Yellow
    Write-Host "2. Check backend logs for errors" -ForegroundColor Yellow
    Write-Host "3. Verify SQUAD_SECRET_KEY in .env.local" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 60
Write-Host "Next: Check database and backend logs"
Write-Host ""
