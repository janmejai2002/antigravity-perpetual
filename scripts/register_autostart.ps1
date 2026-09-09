# Register Antigravity Perpetual Supervisor for Persistent Auto-Start on Logon
[CmdletBinding()]
param(
    [string]$TaskName = "AntigravityPerpetualSupervisor",
    [string]$PythonExe = "C:\Python313\pythonw.exe",
    [string]$WorkingDir = "c:\Users\Janmejai\Documents\antigravity\jolly-meitner\antigravity-perpetual",
    [switch]$StartNow
)

$ErrorActionPreference = "Continue"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [+] Registering Antigravity Perpetual Supervisor Auto-Start" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    $found = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($found) { $PythonExe = $found }
}

$Arguments = "-m antigravity_perpetual.cli run"
Write-Host " [*] Service Name     : $TaskName"
Write-Host " [*] Executable       : $PythonExe"
Write-Host " [*] Arguments        : $Arguments"
Write-Host " [*] Working Dir      : $WorkingDir"

$registeredScheduledTask = $false

# 1. Attempt Scheduled Task registration (preferred for background persistence & restart on failure)
try {
    $Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $Arguments -WorkingDirectory $WorkingDir
    $TriggerLogon = New-ScheduledTaskTrigger -AtLogOn
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Days 0) `
        -Priority 4
    
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    $task = Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $TriggerLogon -Settings $Settings -User $env:USERNAME -ErrorAction Stop
    if ($task) {
        $registeredScheduledTask = $true
        Write-Host " [+] Registered persistent Windows Scheduled Task '$TaskName'." -ForegroundColor Green
    }
} catch {
    Write-Host " [!] Scheduled Task requires elevation ($($_.Exception.Message)). Falling back to User Logon Registry..." -ForegroundColor Yellow
}

# 2. Register to HKCU:\Software\Microsoft\Windows\CurrentVersion\Run
$runVal = "`"$PythonExe`" $Arguments"
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $TaskName -Value $runVal
Write-Host " [+] Registered User Logon Registry (HKCU Run) successfully." -ForegroundColor Green

if ($StartNow) {
    if ($registeredScheduledTask) {
        Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Write-Host " [+] Scheduled task started." -ForegroundColor Green
    } else {
        Start-Process -FilePath $PythonExe -ArgumentList $Arguments -WorkingDirectory $WorkingDir -WindowStyle Hidden
        Write-Host " [+] Background process started." -ForegroundColor Green
    }
}

Write-Host "==================================================================" -ForegroundColor Cyan
