# Antigravity Perpetual 🚀

[![CI](https://github.com/janmejai2002/antigravity-perpetual/actions/workflows/ci.yml/badge.svg)](https://github.com/janmejai2002/antigravity-perpetual/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![NPU Powered](https://img.shields.io/badge/NPU-Intel%20Lunar%20Lake%2047%20TOPS-cyan.svg)](https://www.intel.com/)
[![Windows 11 AwayMode](https://img.shields.io/badge/Windows%2011-Modern%20Standby%20Persistence-emerald.svg)](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate)

> **Autonomous Multi-Day Agent Supervisor, 3-Account Quota Reservoir & Zero-Sleep Runtime for Google Antigravity, Claude Code, Cursor & AI Coding Agents.**

---

## ⚡ The Problem It Solves

Running autonomous coding agents continuously for days on personal laptops is notoriously fragile:

1. **Laptop Sleep & Modern Standby Murder**: Windows laptops sleep, disconnect Wi-Fi, or enter deep hibernation when unattended or when the display powers down, killing long-running agent tasks midway.
2. **Quota Exhaustion & 429 Bans**: Using a single AI account quickly exhausts Rate-Per-Minute (RPM) and Daily Quotas (RPD), halting development.
3. **Token Bloat**: Huge terminal outputs (`git diff`, `pytest`, compiler dumps) blast 50,000–100,000 uncompressed tokens per step, burning daily token budgets in an hour.
4. **Deadlocks & Silent Hangs**: An agent hanging on an unhandled CLI prompt wastes 8 hours of unattended compute with zero progress.
5. **Idle Silicon**: High-performance Neural Processing Units (NPUs like Intel Lunar Lake 47 TOPS) sit completely idle while expensive cloud tokens are wasted on simple embeddings and test evaluations.

**Antigravity Perpetual** resolves all five bottlenecks into a unified, zero-touch autonomous supervisor.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENT CORE (Autonomous Perpetual Loop)                          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
               [Terminal Diffs & Tests]     │           [Inference / API Requests]
                         ▼                  │                      ▼
         ┌─────────────────────────┐        │        ┌───────────────────────────┐
         │      rtk (v0.48.0)      │        │        │   antigravity_perpetual   │
         │  Token Compression      │        │        │   QuotaRotator &          │
         │  (70% - 92% Reduction)  │        │        │   CircuitBreaker          │
         └────────────┬────────────┘        │        └─────────────┬─────────────┘
                      │                     │                      │
                      └─────────────────────┼──────────────────────┘
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │      Antigravity Tools Bridge (:8045)         │
                    │      Local Gateway (lbjlaq / Tauri v2)        │
                    │      Holds Active Google OAuth Sessions       │
                    └───────┬───────────────┬───────────────┬───────┘
                            │               │               │
                            ▼               ▼               ▼
                     [Account 1: Pro] [Account 2: Pro] [Account 3: Pro]
                            │               │               │
                            └───────┬───────┴───────────────┘
                                    │ (All Exhausted Fallback)
                                    ▼
                     ┌─────────────────────────────────────────────┐
                     │   Intel Lunar Lake NPU 4000 (Port 8765)     │
                     │   47 TOPS INT8 Zero-Cloud Sovereign Compute │
                     └─────────────────────────────────────────────┘
```

---

## ✨ Key Capabilities

### 1. Windows 11 Modern Standby & Away Mode Persistence
- Uses Win32 `SetThreadExecutionState(0x80000041)` with `ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED`.
- **Allows your laptop display backlight to turn off or dim**, saving power and screen life, while CPU, RAM, networking, and NPU compute remain **100% active indefinitely**.

### 2. Multi-Account Quota Reservoir (1,080 RPM / 12M TPM)
- Pools across your logged-in **Google Pro accounts** in [`antigravity-tools`](https://github.com/lbjlaq/antigravity-tools) (`http://127.0.0.1:8045`).
- **The 85% Shift Rule**: Automatically shifts traffic to the next account before hitting rate limits.
- **Pacific Midnight Reset Synchronization**: Tracks daily quota limits resetting at `00:00 PST` (12:30 PM IST).

### 3. Millisecond Circuit Breaker
- Intercepts HTTP 429 (`RESOURCE_EXHAUSTED`) and trips from `CLOSED` to `OPEN` in **<5ms**.
- Employs **Full Jitter Exponential Backoff**:
  $$T = \min\left(1800\text{s},\, T_0 \cdot 2^{\text{failures}}\right) \pm \text{rand}$$
- Probes standby accounts via `HALF_OPEN` state transitions before full reintegration.

### 4. RTK Token Compression Proxy
- Intercepts outputs of commands like `git diff`, `pytest`, `cargo test`, and `npm test`.
- Strips ANSI escape sequences, deduplicates repetitive stack frames, and compresses diff headers to achieve **70% to 92% token reduction**.
- Your 3 Pro accounts feel like a **9-to-15 account cluster**.

### 5. Intel Lunar Lake NPU Local Co-Processor
- Offloads vector embeddings (**FastMiniLM @ 1.99 ms**) and vision inference (**MobileNetV3 @ 1,320+ FPS**) to local silicon.
- **Zero-Cloud Stall Guarantee**: If cloud accounts are cooling down, local NPU handles triage and embeddings without stalling the agent.
- **Rebootless Driver Recovery**: Level Zero context resets in **<350 ms** without restarting Windows.

### 6. Supervisor Watchdog & Deadlock Killer
- Silence timeout killer (default: 180s). If an agent hangs on an interactive CLI prompt, the watchdog auto-recovers from the last SQLite WAL checkpoint.
- Thermal throttle monitor protects hardware if temperatures exceed **80°C**.

### 7. Real-Time Observability HUD
- Glassmorphic dark-mode web dashboard served at `http://127.0.0.1:8765/` (or `/pulse`).
- Displays live quota gauges, active account states, silicon metrics, task progression, and audit logs.

---

## 🚀 2-Minute Quickstart

### Prerequisites
- Windows 11 (or Linux/macOS in simulated persistence mode)
- Python 3.10+
- (Optional) [`antigravity-tools`](https://github.com/lbjlaq/antigravity-tools) running on port `8045`

### 1. Installation
```powershell
# Clone the repository
git clone https://github.com/janmejai2002/antigravity-perpetual.git
cd antigravity-perpetual

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Run the Supervisor
```powershell
# Run the 2-minute zero-dependency bootstrap runner
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

Or via CLI:
```powershell
perpetual run
```

Open your browser to **`http://127.0.0.1:8765/`** to monitor the live supervisor HUD!

---

## 🛠️ CLI Reference

```powershell
# Start the supervisor and live HUD
perpetual run

# Check host persistence, thermals, bridge status, and NPU health
perpetual status

# View active account quotas and circuit breaker states
perpetual accounts

# Generate a default configuration file
perpetual init
```

---

## ⚙️ Configuration (`perpetual_config.yaml`)

```yaml
quota_pool:
  accounts:
    - id: "account_pro_1"
      name: "Google Pro - Alpha"
      rpm_limit: 360
      tpm_limit: 4000000
      rpd_limit: 30000
      priority: 1
    - id: "account_pro_2"
      name: "Google Pro - Beta"
      rpm_limit: 360
      tpm_limit: 4000000
      rpd_limit: 30000
      priority: 2
    - id: "account_pro_3"
      name: "Google Pro - Gamma"
      rpm_limit: 360
      tpm_limit: 4000000
      rpd_limit: 30000
      priority: 3
  circuit_breaker:
    failure_threshold: 3
    recovery_timeout_sec: 60.0
    backoff_factor: 2.0
    jitter_range: 0.2

antigravity_tools:
  enabled: true
  gateway_url: "http://127.0.0.1:8045"
  timeout_sec: 30.0

host_persistence:
  execution_state: "0x80000041"
  silence_deadlock_timeout_sec: 180
  max_thermal_celsius: 80.0
  min_battery_percent: 15.0

npu_fallback:
  enabled: true
  npu_server_url: "http://127.0.0.1:8765"
  device: "NPU"

server:
  host: "127.0.0.1"
  port: 8765
  hud_enabled: true

db_path: "runtime_state.db"
```

---

## 🧪 Physical Silicon Benchmarks (Intel Core Ultra 7 256V)

| Metric | Target | Verified Hardware Result | Status |
| :--- | :--- | :--- | :--- |
| **FastMiniLM-L6 Embedding Latency** | < 3.0 ms | **1.99 ms** | ✅ PASS |
| **MobileNetV3 Direct3D 11 Stream** | > 857 FPS | **1,320.3 FPS** | ✅ PASS |
| **Whisper / Moonshine ASR Speed** | > 2,000x RTF | **3,354.7x RTF** | ✅ PASS |
| **Level Zero Rebootless Recovery** | < 1,000 ms | **348.67 ms** | ✅ PASS |
| **1,000-Cycle Memory Soak Delta** | < 5.0 MB | **+0.012 MB (Zero-Leak)** | ✅ PASS |
| **rtk CLI Token Compression** | > 70% | **84.2% Average** | ✅ PASS |

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).

```powershell
# Run the test suite
python -m pytest
```

---

## 📄 License

MIT License © 2026 [Janmejai Singh Minhas](https://github.com/janmejai2002).
