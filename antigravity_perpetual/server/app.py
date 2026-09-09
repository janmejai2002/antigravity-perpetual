"""
FastAPI Server implementation providing the Live Supervisor HUD and Telemetry API.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from antigravity_perpetual.config import PerpetualConfig, load_config
from antigravity_perpetual.quota.ledger import QuotaLedger
from antigravity_perpetual.quota.circuit_breaker import CircuitBreaker
from antigravity_perpetual.quota.rotator import QuotaRotator
from antigravity_perpetual.quota.bridge_8045 import AntigravityToolsBridge
from antigravity_perpetual.supervisor.watchdog import SupervisorWatchdog
from antigravity_perpetual.supervisor.thermal import ThermalMonitor
from antigravity_perpetual.supervisor.power import PowerManager
from antigravity_perpetual.hardware.npu_fallback import NPUFallback


class HeartbeatRequest(BaseModel):
    caller: Optional[str] = "agent"
    task_id: Optional[str] = None


def create_app(config: Optional[PerpetualConfig] = None) -> FastAPI:
    if config is None:
        config = load_config()

    ledger = QuotaLedger(db_path=config.db_path)
    # Register configured accounts into ledger
    for acc in config.accounts:
        from antigravity_perpetual.quota.models import AccountQuota
        ledger.register_account(AccountQuota(
            account_id=acc.id,
            account_name=acc.name,
            rpm_limit=acc.rpm_limit,
            tpm_limit=acc.tpm_limit,
            rpd_limit=acc.rpd_limit,
            priority=acc.priority
        ))

    cb = CircuitBreaker(
        ledger=ledger,
        failure_threshold=config.circuit_breaker.failure_threshold,
        recovery_timeout_sec=config.circuit_breaker.recovery_timeout_sec,
        backoff_factor=config.circuit_breaker.backoff_factor,
        jitter_range=config.circuit_breaker.jitter_range
    )
    rotator = QuotaRotator(ledger=ledger, circuit_breaker=cb)
    bridge = AntigravityToolsBridge(
        rotator=rotator,
        gateway_url=config.antigravity_tools.gateway_url,
        timeout_sec=config.antigravity_tools.timeout_sec
    )
    power_mgr = PowerManager()
    thermal_mon = ThermalMonitor(
        max_thermal_celsius=config.host.max_thermal_celsius,
        min_battery_percent=config.host.min_battery_percent
    )
    watchdog = SupervisorWatchdog(
        silence_timeout_sec=config.host.silence_deadlock_timeout_sec,
        thermal_monitor=thermal_mon,
        power_manager=power_mgr
    )
    npu_fallback = NPUFallback(npu_server_url=config.npu.npu_server_url)

    app = FastAPI(
        title="Antigravity Perpetual Supervisor",
        description="Autonomous Multi-Day Agent Supervisor & 3-Account Quota Pool",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Cache UI path
    ui_path = Path(__file__).parent.parent / "ui" / "index.html"

    @app.get("/", response_class=HTMLResponse)
    @app.get("/hud", response_class=HTMLResponse)
    @app.get("/pulse", response_class=HTMLResponse)
    async def get_hud():
        if ui_path.exists():
            return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Antigravity Perpetual HUD Initializing...</h1>")

    @app.get("/api/health")
    async def get_health():
        return JSONResponse(content={"status": "ok", "version": "1.0.0"})

    @app.get("/api/telemetry")
    async def get_telemetry():
        hw = thermal_mon.get_hardware_health()
        watchdog_status = watchdog.check_health()
        gateway_ok, gateway_version = bridge.is_gateway_online()
        npu_ok = npu_fallback.is_available()
        accounts = ledger.get_account_quotas()

        return JSONResponse(content={
            "status": "online",
            "timestamp": time.time(),
            "execution_state": config.host.execution_state,
            "away_mode_enabled": power_mgr.is_active,
            "gateway_8045": {
                "online": gateway_ok,
                "version": gateway_version,
                "url": config.antigravity_tools.gateway_url
            },
            "npu_silicon": {
                "online": npu_ok,
                "url": config.npu.npu_server_url,
                "target_embedding_latency_ms": config.npu.target_embedding_latency_ms
            },
            "hardware": {
                "cpu_percent": hw.cpu_percent,
                "memory_percent": hw.memory_percent,
                "battery_percent": hw.battery_percent,
                "power_plugged": hw.power_plugged,
                "thermal_celsius": hw.thermal_celsius,
                "thermal_throttling_required": hw.thermal_throttling_required,
                "battery_warning": hw.battery_warning
            },
            "watchdog": {
                "silence_duration_sec": watchdog_status["silence_duration_sec"],
                "silence_timeout_sec": watchdog_status["silence_timeout_sec"],
                "is_deadlocked": watchdog_status["is_deadlocked"]
            },
            "accounts": [
                {
                    "id": a.account_id,
                    "name": a.account_name,
                    "current_rpm": a.current_rpm,
                    "rpm_limit": a.rpm_limit,
                    "current_tpm": a.current_tpm,
                    "tpm_limit": a.tpm_limit,
                    "current_rpd": a.current_rpd,
                    "rpd_limit": a.rpd_limit,
                    "circuit_state": a.circuit_state.value,
                    "consecutive_failures": a.consecutive_failures
                }
                for a in accounts
            ]
        })

    @app.get("/api/accounts")
    async def get_accounts():
        accounts = ledger.get_account_quotas()
        return JSONResponse(content=[
            {
                "id": a.account_id,
                "name": a.account_name,
                "rpm": f"{a.current_rpm}/{a.rpm_limit}",
                "tpm": f"{a.current_tpm}/{a.tpm_limit}",
                "rpd": f"{a.current_rpd}/{a.rpd_limit}",
                "circuit_state": a.circuit_state.value
            }
            for a in accounts
        ])

    @app.post("/api/heartbeat")
    async def post_heartbeat(req: HeartbeatRequest):
        watchdog.heartbeat()
        return JSONResponse(content={"status": "heartbeat_acknowledged", "timestamp": time.time()})

    @app.post("/api/forward")
    async def forward_request(req: Request):
        watchdog.heartbeat()
        body = await req.json()
        result = bridge.forward_chat_completion(body)
        return JSONResponse(content=result, status_code=result.get("status_code", 200))

    return app
