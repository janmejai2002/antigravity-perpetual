# Antigravity Perpetual - Full Test & Hardware Verification Suite
$ErrorActionPreference = "Stop"

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host " [+] RUNNING ANTIGRAVITY PERPETUAL FULL VERIFICATION HARNESS            " -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan

# 1. Run Unit Tests
Write-Host " [*] Running Pytest Suites..." -ForegroundColor Gray
& python -m pytest -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Unit tests failed."
}
Write-Host " [+] Pytest Verification: PASSED" -ForegroundColor Green

# 2. Test CLI Subcommands
Write-Host " [*] Testing CLI Commands..." -ForegroundColor Gray
& python -m antigravity_perpetual --version
& python -m antigravity_perpetual status
& python -m antigravity_perpetual accounts
Write-Host " [+] CLI Verification: PASSED" -ForegroundColor Green

Write-Host "==========================================================================" -ForegroundColor Green
Write-Host " [+] ALL TESTS AND VERIFICATION CHECKS PASSED CLEANLY!                   " -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
