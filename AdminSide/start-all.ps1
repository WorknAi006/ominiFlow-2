# Omniflow Stack Starter
$ErrorActionPreference = "Continue"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "     Starting Omniflow Stack...         " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. PostgreSQL
$pgPort = Get-NetTCPConnection -LocalPort 5433 -State Listen -ErrorAction SilentlyContinue
if (-not $pgPort) {
    Write-Host "[1/5] Starting PostgreSQL (port 5433)..." -ForegroundColor Yellow
    Start-Process -FilePath "C:\Users\ADMIN\pgsql\pgsql\bin\postgres.exe" -ArgumentList "-D", "`"C:\Users\ADMIN\pgsql\data`"", "-p", "5433" -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[1/5] PostgreSQL is already running on port 5433." -ForegroundColor Green
}

# 2. Redis
$redisPort = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
if (-not $redisPort) {
    Write-Host "[2/5] Starting Redis (port 6379)..." -ForegroundColor Yellow
    $redisExe = "C:\Users\ADMIN\AppData\Local\Microsoft\WinGet\Packages\taizod1024.redis-windows-fork_Microsoft.Winget.Source_8wekyb3d8bbwe\Redis-8.10.1-Windows-x64-msys2\redis-server.exe"
    Start-Process -FilePath $redisExe -WindowStyle Hidden
    Start-Sleep -Seconds 1
} else {
    Write-Host "[2/5] Redis is already running on port 6379." -ForegroundColor Green
}

# 3. Backend (FastAPI)
$backendPort = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $backendPort) {
    Write-Host "[3/5] Starting FastAPI Backend (http://127.0.0.1:8000)..." -ForegroundColor Yellow
    $backendDir = Join-Path $PSScriptRoot "backend"
    $pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"
    Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -WorkingDirectory $backendDir
    Start-Sleep -Seconds 2
} else {
    Write-Host "[3/5] FastAPI Backend is already running on port 8000." -ForegroundColor Green
}

# 4. Frontend (Next.js Main App)
$frontendPort = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if (-not $frontendPort) {
    Write-Host "[4/5] Starting Frontend App (http://localhost:3000)..." -ForegroundColor Yellow
    $frontendDir = Join-Path $PSScriptRoot "frontend"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev" -WorkingDirectory $frontendDir
} else {
    Write-Host "[4/5] Frontend App is already running on port 3000." -ForegroundColor Green
}

# 5. Admin (Next.js Admin Portal)
$adminPort = Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue
if (-not $adminPort) {
    Write-Host "[5/5] Starting Admin Portal (http://localhost:3001)..." -ForegroundColor Yellow
    $adminDir = Join-Path $PSScriptRoot "admin"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev" -WorkingDirectory $adminDir
} else {
    Write-Host "[5/5] Admin Portal is already running on port 3001." -ForegroundColor Green
}

Write-Host "`n=========================================" -ForegroundColor Green
Write-Host " Omniflow stack is online and ready!    " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host " - Frontend:    http://localhost:3000" -ForegroundColor White
Write-Host " - Admin:       http://localhost:3001" -ForegroundColor White
Write-Host " - Backend API: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host " - PostgreSQL:  127.0.0.1:5433" -ForegroundColor White
Write-Host " - Redis:       127.0.0.1:6379" -ForegroundColor White
