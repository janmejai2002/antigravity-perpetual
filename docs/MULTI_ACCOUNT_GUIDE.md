# Multi-Account Quota Pooling & Setup Guide

This guide explains how to configure, balance, and maximize your usage across multiple Google Pro / Gemini / Claude accounts using **Antigravity Perpetual** and **Antigravity Tools**.

---

## 1. Prerequisites

1. **Antigravity Tools (lbjlaq)**:
   - Download or install `antigravity-tools` from [GitHub](https://github.com/lbjlaq/antigravity-tools).
   - Ensure the application is running on `http://127.0.0.1:8045`.
2. **Logged-In Accounts**:
   - Log into your 3 Google Pro accounts inside the Antigravity Tools GUI.

---

## 2. Configuration (`perpetual_config.yaml`)

Define your accounts in `perpetual_config.yaml`:

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
```

---

## 3. How Rotation Works

1. **Preventive Shift**: Traffic starts on Priority 1 (`account_pro_1`). When it reaches **85%** of its 1-minute RPM limit, traffic smoothly transitions to Priority 2 (`account_pro_2`) before Google triggers a 429.
2. **Circuit Breaking**: If an account unexpectedly throws `HTTP 429 RESOURCE_EXHAUSTED`, the circuit breaker trips it to `OPEN` in `<5ms`, redirects subsequent calls to the standby account, and initiates an exponential backoff cooldown with full jitter.
3. **Pacific Midnight Reset**: At `00:00 PST` (12:30 PM IST), all 3 daily counters automatically zero out in the SQLite ledger.
4. **Token Compression**: Command outputs are compressed via `rtk` (70–92% token reduction), effectively stretching 3 accounts to feel like a 9-to-15 account cluster.
