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


from antigravity_perpetual.supervisor.notifier import AlertNotifier, AlertCategory
from antigravity_perpetual.state.analytics import AnalyticsEngine


class HeartbeatRequest(BaseModel):
    caller: Optional[str] = "agent"
    task_id: Optional[str] = None


class SwitchAccountRequest(BaseModel):
    identifier: str


class NPUEmbedRequest(BaseModel):
    text: str


class NPUAuditRequest(BaseModel):
    command: str


class TestNotificationRequest(BaseModel):
    title: Optional[str] = "Test Sentinel Alert"
    message: Optional[str] = "Autonomous perpetual sentinel alert pipeline verified."
    severity: Optional[str] = "INFO"


def create_app(
    config: Optional[PerpetualConfig] = None,
    power_manager: Optional[PowerManager] = None
) -> FastAPI:
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

    notifier = AlertNotifier(config=config.notifications, ledger=ledger)

    cb = CircuitBreaker(
        ledger=ledger,
        failure_threshold=config.circuit_breaker.failure_threshold,
        recovery_timeout_sec=config.circuit_breaker.recovery_timeout_sec,
        backoff_factor=config.circuit_breaker.backoff_factor,
        jitter_range=config.circuit_breaker.jitter_range,
        notifier=notifier
    )
    rotator = QuotaRotator(ledger=ledger, circuit_breaker=cb)
    bridge = AntigravityToolsBridge(
        rotator=rotator,
        gateway_url=config.antigravity_tools.gateway_url,
        timeout_sec=config.antigravity_tools.timeout_sec
    )
    bridge.sync_accounts_into_ledger()
    analytics = AnalyticsEngine(db_path=config.db_path)

    power_mgr = power_manager or PowerManager()
    if not power_mgr.is_active:
        power_mgr.enable_perpetual_mode()

    thermal_mon = ThermalMonitor(
        max_thermal_celsius=config.host.max_thermal_celsius,
        min_battery_percent=config.host.min_battery_percent,
        notifier=notifier
    )
    watchdog = SupervisorWatchdog(
        silence_timeout_sec=config.host.silence_deadlock_timeout_sec,
        thermal_monitor=thermal_mon,
        power_manager=power_mgr,
        notifier=notifier
    )
    npu_fallback = NPUFallback(npu_server_url=config.npu.npu_server_url)

    app = FastAPI(
        title="Antigravity Perpetual Supervisor",
        description="Autonomous Multi-Day Agent Supervisor & 4-Account Quota Pool",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    @app.on_event("startup")
    async def on_startup():
        watchdog.start()

    @app.on_event("shutdown")
    async def on_shutdown():
        watchdog.stop()

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
        curr_active_id = bridge.get_current_account_id()
        active_details = bridge.get_active_account_details()

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
            "active_account": active_details,
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
                    "is_active": (a.account_id == curr_active_id),
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
        curr_active_id = bridge.get_current_account_id()
        return JSONResponse(content=[
            {
                "id": a.account_id,
                "name": a.account_name,
                "is_active": (a.account_id == curr_active_id),
                "rpm": f"{a.current_rpm}/{a.rpm_limit}",
                "tpm": f"{a.current_tpm}/{a.tpm_limit}",
                "rpd": f"{a.current_rpd}/{a.rpd_limit}",
                "circuit_state": a.circuit_state.value
            }
            for a in accounts
        ])

    @app.get("/api/accounts/active")
    async def get_active_account():
        details = bridge.get_active_account_details()
        return JSONResponse(content=details or {"current_account_id": None})

    @app.post("/api/accounts/cycle")
    async def post_cycle_account():
        res = bridge.force_cycle()
        return JSONResponse(content=res)

    @app.post("/api/accounts/switch")
    async def post_switch_account(req: Optional[SwitchAccountRequest] = None, account_id: Optional[str] = None):
        target = (req.identifier if req else None) or account_id
        if not target:
            raise HTTPException(status_code=400, detail="Must provide identifier or account_id")
        res = bridge.switch_active_account(target)
        return JSONResponse(content=res)

    @app.get("/api/analytics/summary")
    async def get_analytics_summary(hours: float = 24.0):
        data = analytics.get_summary_metrics(window_hours=hours)
        return JSONResponse(content=data)

    @app.get("/api/analytics/review")
    async def get_analytics_review():
        report = analytics.generate_v2_review_report()
        return JSONResponse(content=report)

    @app.get("/api/alerts")
    async def get_alerts(limit: int = 50):
        alerts = ledger.get_recent_alerts(limit=limit)
        return JSONResponse(content=alerts)

    @app.post("/api/notify/test")
    async def post_test_alert(req: TestNotificationRequest):
        sent = notifier.notify(
            category=AlertCategory.SYSTEM_EVENT,
            severity=req.severity or "INFO",
            title=req.title or "Test Sentinel Alert",
            message=req.message or "Autonomous perpetual sentinel alert verified.",
            force=True
        )
        return JSONResponse(content={"status": "dispatched" if sent else "suppressed"})

    @app.get("/api/npu/status")
    async def get_npu_status():
        status = npu_fallback.get_device_status()
        return JSONResponse(content=status)

    @app.post("/api/npu/embed")
    async def post_npu_embed(req: NPUEmbedRequest):
        res = npu_fallback.embed_text(req.text)
        return JSONResponse(content=res)

    @app.get("/api/npu/search")
    async def get_npu_search(q: str, top_k: int = 3):
        res = npu_fallback.semantic_search(q, top_k=top_k)
        return JSONResponse(content=res)

    @app.get("/api/npu/audit")
    @app.post("/api/npu/audit")
    async def audit_npu_command(cmd: Optional[str] = None, req: Optional[NPUAuditRequest] = None):
        target_cmd = cmd or (req.command if req else "")
        res = npu_fallback.audit_command(target_cmd)
        return JSONResponse(content=res)

    @app.post("/api/heartbeat")
    async def post_heartbeat(req: HeartbeatRequest):
        watchdog.heartbeat()
        return JSONResponse(content={"status": "heartbeat_acknowledged", "timestamp": time.time()})

    @app.post("/api/circuit_breaker/trip")
    async def post_trip_circuit(account_id: Optional[str] = None):
        accs = ledger.get_account_quotas()
        target = account_id or (accs[0].account_id if accs else "account_pro_1")
        cb.record_failure(target, status_code=429)
        return JSONResponse(content={"status": "tripped", "account_id": target})

    @app.post("/api/circuit_breaker/reset")
    async def post_reset_circuits():
        accs = ledger.get_account_quotas()
        for a in accs:
            cb.record_success(a.account_id)
        return JSONResponse(content={"status": "all_circuits_reset_closed", "count": len(accs)})

    @app.post("/api/forward")
    async def forward_request(req: Request):
        watchdog.heartbeat()
        body = await req.json()
        result = bridge.forward_chat_completion(body)
        return JSONResponse(content=result, status_code=result.get("status_code", 200))

    return app


