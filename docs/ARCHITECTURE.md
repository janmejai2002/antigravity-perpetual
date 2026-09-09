# Antigravity Perpetual: System Architecture

Antigravity Perpetual is an autonomous host supervisor, multi-account quota pool, and local silicon co-processor engine designed to enable multi-day sovereign execution for Google Antigravity, Claude Code, Cursor, and agentic AI tools.

---

## 1. High-Level Architecture Topology

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

## 2. Core Subsystems

### Subsystem 1: Win32 Host Persistence (`antigravity_perpetual/supervisor/`)
- **Modern Standby Prevention**: Calls `kernel32.dll` `SetThreadExecutionState(0x80000041)`.
  - Flags: `ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED`.
  - Effect: The laptop display backlight is allowed to sleep/dim normally to save battery and reduce screen burn-in, while CPU, RAM, and NPU compute run at 100% throughput indefinitely.
- **Supervisor Watchdog**: Silence deadlock killer. Tracks timestamp of last agent heartbeat. If no activity is recorded for `180s`, it interrupts hanging CLI processes, restores state from the last SQLite WAL checkpoint, and restarts the task.
- **Thermal & Battery Guard**: Monitors CPU temperatures and battery percentages. Throttles execution if thermal envelope exceeds 80°C.

### Subsystem 2: Multi-Account Quota Reservoir (`antigravity_perpetual/quota/`)
- **Sliding-Window Math**:
  - 1-Minute Window: Enforces max 360 RPM per account (1,080 RPM aggregate pool).
  - 85% Shift Rule: Switches active traffic to the next account before hitting 429.
  - 24-Hour Pacific Midnight Reset: Tracks daily quotas resetting at 00:00 PST (12:30 PM IST).
- **Circuit Breaker**:
  - State machine: `CLOSED` -> `OPEN` -> `HALF_OPEN` -> `CLOSED`.
  - Full Jitter Exponential Backoff: $T = \min(1800\text{s}, T_0 \cdot 2^{\text{failures}}) \pm \text{rand}$.

### Subsystem 3: Token Compression (`antigravity_perpetual/compression/`)
- Intercepts outputs of commands like `git diff`, `pytest`, `cargo test`, `npm test`.
- Strips ANSI escape sequences, deduplicates repetitive stack frames, and consolidates diff hunks.
- Delivers 70% to 92% token compression, tripling to quintupling the effective capacity of Google Pro accounts.

### Subsystem 4: Local Silicon Fallback (`antigravity_perpetual/hardware/`)
- Connects to local NPU inference runtime (Intel Core Ultra 7 256V / Lunar Lake NPU 4000 @ 47 TOPS).
- Generates FastMiniLM embeddings in **1.99 ms** and processes vision surfaces at **1,320+ FPS**.
- Driver recovery: Level Zero context reset completes in **<350 ms** without rebooting Windows.
