param()

Write-Host @"

╔════════════════════════════════════════════════════════════════════════════╗
║                  TrustLayer Backend Startup                               ║
║                                                                            ║
║  This script will:                                                         ║
║  1. Change to the backend folder                                          ║
║  2. Kill any stale processes on port 8000                                 ║
║  3. Start a clean backend server                                          ║
║                                                                            ║
║  Press Ctrl+C to stop the server.                                         ║
╚════════════════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

$BACKEND_ROOT = 'C:\Users\olani\TrustLayer'
Set-Location $BACKEND_ROOT
Write-Host "[1/4] Backend folder: $BACKEND_ROOT" -ForegroundColor Green

Write-Host "[2/4] Cleaning port 8000..." -ForegroundColor Yellow
$staleProcs = netstat -ano | Select-String ':8000' | Select-String 'LISTENING'
if ($staleProcs) {
    $staleProcs | ForEach-Object {
        $pid = ($_ -split '\s+')[-1]
        taskkill /PID $pid /F /T 2>$null
        Write-Host "  ✓ Killed $pid" -ForegroundColor DarkGreen
    }
    Start-Sleep -Seconds 2
}

Write-Host "[3/4] Setting environment..." -ForegroundColor Yellow
$env:DATABASE_URL = 'sqlite:///./dev.db'
$env:REDIS_URL = ''
$env:ENVIRONMENT = 'development'

Write-Host "[4/4] Starting server..." -ForegroundColor Green
Write-Host @"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 LOGS (read these if something fails):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"@ -ForegroundColor Cyan

& .\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
