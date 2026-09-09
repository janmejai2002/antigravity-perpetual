# Unregister Antigravity Perpetual Supervisor Auto-Start
[CmdletBinding()]
param(
    [string]$TaskName = "AntigravityPerpetualSupervisor"
)

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [-] Unregistering Antigravity Perpetual Supervisor Auto-Start" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Remove Scheduled Task
try {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host " [+] Removed Scheduled Task '$TaskName'." -ForegroundColor Green
} catch {}

# 2. Remove Registry Run Key
try {
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $TaskName -ErrorAction SilentlyContinue
    Write-Host " [+] Removed User Logon Registry entry '$TaskName'." -ForegroundColor Green
} catch {}

Write-Host "==================================================================" -ForegroundColor Cyan
