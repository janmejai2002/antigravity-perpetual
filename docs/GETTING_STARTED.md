# Getting Started with Antigravity Perpetual 🚀

This guide provides an end-to-end walkthrough for setting up, configuring, and running **Antigravity Perpetual** on your computer.

---

## ⏱️ Fast-Track: 30-Second Setup

If you already have Python 3.10+ installed, open PowerShell and run:

```powershell
# 1. Clone the repository
git clone https://github.com/janmejai2002/antigravity-perpetual.git
cd antigravity-perpetual

# 2. Run the automated bootstrap launcher
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

The script automatically validates dependencies, engages Win32 Away Mode persistence, checks your Antigravity Tools bridge, and opens the live HUD at **`http://127.0.0.1:8765/`**.

---

## 🛠️ Step 1: System Requirements & Silicon Check

- **Operating System**: Windows 11 (22H2 / 23H2 / 24H2) or Windows 10.
  *(Linux and macOS are also supported in simulated persistence mode).*
- **Python**: Version `3.10`, `3.11`, `3.12`, or `3.13`.
- **Silicon (Optional Acceleration)**: Intel Lunar Lake Core Ultra Series 2 (e.g. Core Ultra 7 256V) equipped with Intel AI Boost NPU 4000 (47 TOPS INT8).
  *(If an NPU is not detected, Antigravity Perpetual automatically operates in CPU/cloud mode without any errors).*

Verify your Python installation:
```powershell
python --version
```

---

## ⛽ Step 2: Connecting Your Google Pro Accounts

Antigravity Perpetual pools across multiple Google Pro / Gemini accounts to give you **1,080 RPM** and **12,000,000 TPM** combined capacity:

1. Launch **[`antigravity-tools`](https://github.com/lbjlaq/antigravity-tools)** (the local gateway application).
2. Inside Antigravity Tools, log into your 3 Google Pro accounts.
3. Antigravity Tools will bind locally to **`http://127.0.0.1:8045`**.
4. Antigravity Perpetual will automatically detect and bridge to this port:
   ```powershell
   perpetual status
   ```
   You will see:
   ```
   [Antigravity Tools] : ONLINE (4.6.9) @ http://127.0.0.1:8045
   ```

---

## 💻 Step 3: Windows 11 Power & Lid Configuration

To allow your laptop to run unattended for days with the lid closed:

1. Press `Win + R`, type `control powercfg.cpl`, and hit Enter.
2. In the left sidebar, click **"Choose what closing the lid does"**.
3. Under **"When I close the lid"**:
   - Set **"Plugged in"** to **`Do nothing`**.
4. Click **Save changes**.

> **How Away Mode Works**:
> Antigravity Perpetual sets Win32 execution state `0x80000041` (`ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED`).
> This tells Windows:
> - Display backlight can safely power off or dim to save energy and protect the screen.
> - CPU, RAM, Wi-Fi networking, and NPU silicon remain at **100% compute capacity**.

---

## 🖥️ Step 4: Reading the Live Supervisor HUD

Once you launch `perpetual run` (or double-click `scripts\run.bat`), navigate to:
👉 **[`http://127.0.0.1:8765/`](http://127.0.0.1:8765/)**

The dashboard provides real-time telemetry across three main pillars:

### Column 1: Multi-Account Quota Reservoir
- **Account Alpha (Pro 1)**: Primary active account. Shows rolling 1-minute RPM and token consumption.
- **Account Beta (Pro 2)**: Secondary standby account. Automatically engages when Alpha hits 85% RPM or encounters a 429.
- **Account Gamma (Pro 3)**: Tertiary burst reserve.
- **rtk Token Compression**: Live metric showing active token savings (**70% to 92%**).

### Column 2: Silicon & Hardware Health
- **NPU Latency**: Microsecond benchmark for local vector embeddings (**1.99 ms** on Intel Lunar Lake).
- **Vision Inference**: Real-time FPS for Direct3D 11 screen capture (**1,320+ FPS**).
- **Thermal Telemetry**: Live CPU temperature with automatic throttle protection if thermals exceed 80°C.
- **Battery Status**: Confirms AC power connection.

### Column 3: Task DAG State Machine
- Displays current epoch and completed steps (`host_persistence`, `quota_pool`, `hardware_rig`).
- Verifies that SQLite WAL atomic checkpoints and instant `<250ms` rollbacks are active.

---

## 🔄 Step 5: How Coding Agents Connect

Any agent or tool that sends OpenAI-compatible or Gemini-compatible requests can point to either:
- **Port `8765`** (`http://127.0.0.1:8765/api/forward`): Managed directly by Antigravity Perpetual with automated rotation and token logging.
- **Port `8045`** (`http://127.0.0.1:8045/v1`): Antigravity Tools gateway monitored and rate-paced by the supervisor.

Terminal commands (`git diff`, `pytest`, `cargo`, `npm`) executed by the agent are automatically compressed via `rtk` before being sent into the model context.

---

## 🌙 Step 6: Multi-Day Unattended Operation

When leaving your workstation:
1. Ensure your laptop is plugged into AC power.
2. Launch `perpetual run`.
3. Close the lid or let the display power down.
4. The watchdog silence killer will automatically recover tasks if deadlocks occur, and daily quotas will automatically reset at **00:00 PST (12:30 PM IST)**.
