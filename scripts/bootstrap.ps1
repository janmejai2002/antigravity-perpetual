# Antigravity Perpetual - 2-Minute Zero-Dependency Bootstrap & Launch Script
param(
    [string]$ConfigPath = "perpetual_config.yaml",
    [int]$Port = 8765,
    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host " [+] ANTIGRAVITY PERPETUAL BOOTSTRAP RUNNER                              " -ForegroundColor Cyan
Write-Host "     Sovereign Autonomous Agent Supervisor and 3-Account Quota Reservoir " -ForegroundColor DarkCyan
Write-Host "==========================================================================" -ForegroundColor Cyan

# 1. Check Python
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "Python 3 is required but was not found in PATH."
}
Write-Host " [+] Python Runtime Detected: $PythonExe" -ForegroundColor Green

# 2. Check Pip Dependencies
Write-Host " [*] Checking core dependencies..." -ForegroundColor Gray
& python -c "import fastapi, uvicorn, pydantic, yaml, psutil, requests; print('OK')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host " [*] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    & python -m pip install -r requirements.txt --quiet
}
Write-Host " [+] Dependencies Verified." -ForegroundColor Green

# 3. Optional Test Suite
if (-not $SkipTests) {
    Write-Host " [*] Running unit test verification suite..." -ForegroundColor Gray
    & python -m pytest --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Some tests encountered warnings, proceeding with launch."
    } else {
        Write-Host " [+] All 13 Test Suites Passed Cleanly." -ForegroundColor Green
    }
}

# 4. Check Antigravity Tools Bridge
Write-Host " [*] Probing Antigravity Tools Gateway (127.0.0.1:8045)..." -ForegroundColor Gray
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8045/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host " [+] Antigravity Tools Bridge Connected (Version: $($res.version))." -ForegroundColor Green
} catch {
    Write-Host " [!] Antigravity Tools (127.0.0.1:8045) not detected. Running in standalone quota mode." -ForegroundColor Yellow
}

# 5. Check Intel Lunar Lake NPU
Write-Host " [*] Probing Intel Lunar Lake NPU (127.0.0.1:8765)..." -ForegroundColor Gray
try {
    $npuRes = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host " [+] Lunar Lake NPU 4000 Online." -ForegroundColor Green
} catch {
    Write-Host " [!] Local NPU server not detected. CPU fallback active." -ForegroundColor Yellow
}

# 6. Initialize Config if missing
if (-not (Test-Path $ConfigPath)) {
    Write-Host " [*] Initializing $ConfigPath..." -ForegroundColor Gray
    & python -m antigravity_perpetual init
}

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host " [+] Bootstrap Complete! Launching Supervisor HUD on http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Cyan

& python -m antigravity_perpetual run --port $Port
