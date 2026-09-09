# Antigravity Perpetual: Troubleshooting & Diagnostics 🛠️

This document outlines solutions to common edge cases, environment quirks, and diagnostic procedures.

---

## 📋 Quick Diagnostic Command

Before troubleshooting individual components, run the built-in diagnostic scan:

```powershell
perpetual status
```

This will print an instant health audit of:
- Host operating system and Win32 execution flags
- Thermal telemetry and throttle limits
- Battery state and AC power connection
- Antigravity Tools bridge connectivity (`:8045`)
- Intel Lunar Lake NPU status (`:8765`)

---

## 1. PowerShell: "Execution of scripts is disabled on this system"

### Symptom:
When running `scripts\bootstrap.ps1`, you see:
```
File C:\...\bootstrap.ps1 cannot be loaded because running scripts is disabled on this system.
```

### Cause:
Windows PowerShell restricts script execution by default (`Restricted` policy).

### Solution:
Run the script with an explicit bypass flag:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```
Or set the execution policy for your current user:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 2. Port Collision: `[Errno 10048] address already in use`

### Symptom:
Uvicorn or the supervisor fails because port `8765` is already bound by another process.

### Cause:
Another instance of `antigravity-perpetual` or `lunarnpu.server` is already listening on port 8765.

### Solution:
Antigravity Perpetual automatically detects occupied ports and rebinds to the next available port (e.g. `8766`).
Alternatively, you can manually specify a different port:
```powershell
perpetual run --port 8080
```
Or locate and terminate the process occupying port 8765:
```powershell
# Find process ID on port 8765
Get-NetTCPConnection -LocalPort 8765 | Select-Object OwningProcess, State

# Stop process (replace 12345 with PID)
Stop-Process -Id 12345 -Force
```

---

## 3. "Antigravity Tools Bridge: Standalone Mode"

### Symptom:
`perpetual status` outputs:
```
[!] Antigravity Tools Bridge : Standalone mode (Connection refused)
```

### Cause:
The `antigravity-tools` desktop application is not running or listening on `127.0.0.1:8045`.

### Solution:
1. Launch **Antigravity Tools** from your Start Menu or install directory (`antigravity-tools.exe`).
2. Verify that it is listening on port 8045:
   ```powershell
   Get-NetTCPConnection -LocalPort 8045 -ErrorAction SilentlyContinue
   ```
3. If Antigravity Tools is not running, Antigravity Perpetual will run in **standalone quota mode**, managing accounts via direct configuration.

---

## 4. "Lunar Lake NPU: Standby / Fallback Mode"

### Symptom:
`perpetual status` shows the NPU as offline, and embeddings fall back to CPU.

### Cause:
Either the local machine does not have an Intel Core Ultra (Series 2) Lunar Lake processor, or the OpenVINO NPU driver service has not been initialized.

### Solution:
- If you are on a non-Lunar Lake PC: **No action needed**. The system automatically runs on CPU/cloud without errors.
- If you are on an Intel Lunar Lake laptop:
  1. Ensure the Intel NPU driver (32.0.100.3110 or newer) is installed via Windows Update or Intel Driver & Support Assistant.
  2. Start the NPU runtime:
     ```powershell
     python -m lunarnpu.server
     ```

---

## 5. Laptop Enters Sleep Despite Away Mode

### Symptom:
The laptop goes into deep sleep when the lid is closed or after 30 minutes of inactivity.

### Cause:
Windows power policy for lid closure is set to "Sleep" instead of "Do nothing".

### Solution:
1. Open Windows Power Options (`control powercfg.cpl`).
2. Click **"Choose what closing the lid does"**.
3. Set **"When I close the lid (Plugged in)"** to **`Do nothing`**.
4. Keep the laptop connected to AC power. When on battery below 15%, the supervisor allows sleep to preserve battery longevity.

---

## 6. HTTP 429 `RESOURCE_EXHAUSTED` Errors

### Symptom:
An account hits a temporary rate limit.

### Behavior:
This is expected under heavy burst traffic and is handled automatically:
1. The **Circuit Breaker** catches the 429 and immediately trips that account to `OPEN`.
2. Traffic shifts to Account 2 or 3 in `<5ms`.
3. The throttled account enters a dynamic cooldown with **Full Jitter Exponential Backoff**:
   $$T = \min(1800\text{s}, T_0 \cdot 2^{\text{failures}}) \pm \text{rand}$$
4. You do not need to restart anything; the account automatically re-enters rotation once cooled down.

---

## 7. Generating a Bug Report / Diagnostic Dump

If you encounter an issue not covered here, capture your diagnostic state:

```powershell
perpetual status > diagnostic_report.txt
python -m pytest >> diagnostic_report.txt
```
Attach `diagnostic_report.txt` to a new issue on GitHub at:
👉 **[`https://github.com/janmejai2002/antigravity-perpetual/issues`](https://github.com/janmejai2002/antigravity-perpetual/issues)**
