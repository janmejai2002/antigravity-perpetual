"""
Declarative Configuration Loader for Antigravity Perpetual Runtime.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml


@dataclass
class AccountConfig:
    id: str
    name: str
    rpm_limit: int = 360
    tpm_limit: int = 4000000
    rpd_limit: int = 30000
    priority: int = 1
    api_key_env: Optional[str] = None
    endpoint_override: Optional[str] = None


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout_sec: float = 60.0
    backoff_factor: float = 2.0
    jitter_range: float = 0.2


@dataclass
class AntigravityToolsConfig:
    enabled: bool = True
    gateway_url: str = "http://127.0.0.1:8045"
    timeout_sec: float = 30.0
    health_endpoint: str = "/health"
    accounts_endpoint: str = "/api/accounts"


@dataclass
class HostPersistenceConfig:
    execution_state: str = "0x80000041"  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
    silence_deadlock_timeout_sec: int = 180
    max_thermal_celsius: float = 65.0
    min_battery_percent: float = 20.0


@dataclass
class NPUFallbackConfig:
    enabled: bool = True
    npu_server_url: str = "http://127.0.0.1:8899"
    device: str = "NPU"
    target_embedding_latency_ms: float = 3.0
    target_vision_fps: float = 857.0


@dataclass
class NotificationConfig:
    enabled: bool = True
    windows_toast_enabled: bool = True
    discord_webhook_url: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    thermal_alert_celsius: float = 65.0
    battery_alert_percent: float = 20.0
    cooldown_sec: float = 120.0


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    hud_enabled: bool = True


DEFAULT_DB_PATH = str(Path.home() / ".antigravity_perpetual" / "state.db")


@dataclass
class PerpetualConfig:
    accounts: List[AccountConfig] = field(default_factory=lambda: [
        AccountConfig(id="account_pro_1", name="Google Pro - Alpha", priority=1),
        AccountConfig(id="account_pro_2", name="Google Pro - Beta", priority=2),
        AccountConfig(id="account_pro_3", name="Google Pro - Gamma", priority=3),
        AccountConfig(id="account_pro_4", name="Google Pro - Delta", priority=4),
    ])
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    antigravity_tools: AntigravityToolsConfig = field(default_factory=AntigravityToolsConfig)
    host: HostPersistenceConfig = field(default_factory=HostPersistenceConfig)
    npu: NPUFallbackConfig = field(default_factory=NPUFallbackConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    db_path: str = DEFAULT_DB_PATH


def load_config(config_path: Optional[str | Path] = None) -> PerpetualConfig:
    """Load configuration from YAML file or return defaults."""
    if config_path is None:
        candidates = [
            Path("perpetual_config.yaml"),
            Path("perpetual_config.yml"),
            Path(__file__).parent.parent / "perpetual_config.yaml"
        ]
        for c in candidates:
            if c.exists():
                config_path = c
                break

    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # Parse accounts
        accounts_data = raw.get("quota_pool", {}).get("accounts", [])
        accounts = []
        for a in accounts_data:
            accounts.append(AccountConfig(
                id=a.get("id", "acc"),
                name=a.get("name", "Google Pro"),
                rpm_limit=a.get("rpm_limit", 360),
                tpm_limit=a.get("tpm_limit", 4000000),
                rpd_limit=a.get("rpd_limit", 30000),
                priority=a.get("priority", 1),
                api_key_env=a.get("api_key_env"),
                endpoint_override=a.get("endpoint_override")
            ))
        if not accounts:
            accounts = [
                AccountConfig(id="account_pro_1", name="Google Pro - Alpha", priority=1),
                AccountConfig(id="account_pro_2", name="Google Pro - Beta", priority=2),
                AccountConfig(id="account_pro_3", name="Google Pro - Gamma", priority=3),
                AccountConfig(id="account_pro_4", name="Google Pro - Delta", priority=4),
            ]

        cb_data = raw.get("quota_pool", {}).get("circuit_breaker", {})
        cb = CircuitBreakerConfig(
            failure_threshold=cb_data.get("failure_threshold", 3),
            recovery_timeout_sec=cb_data.get("recovery_timeout_sec", 60.0),
            backoff_factor=cb_data.get("backoff_factor", 2.0),
            jitter_range=cb_data.get("jitter_range", 0.2)
        )

        ag_tools_data = raw.get("antigravity_tools", {})
        ag_tools = AntigravityToolsConfig(
            enabled=ag_tools_data.get("enabled", True),
            gateway_url=ag_tools_data.get("gateway_url", "http://127.0.0.1:8045"),
            timeout_sec=ag_tools_data.get("timeout_sec", 30.0)
        )

        host_data = raw.get("host_persistence", {})
        host_cfg = HostPersistenceConfig(
            execution_state=host_data.get("execution_state", "0x80000041"),
            silence_deadlock_timeout_sec=host_data.get("silence_deadlock_timeout_sec", 180),
            max_thermal_celsius=host_data.get("max_thermal_celsius", 65.0),
            min_battery_percent=host_data.get("min_battery_percent", 20.0)
        )

        npu_data = raw.get("npu_fallback", {})
        npu_cfg = NPUFallbackConfig(
            enabled=npu_data.get("enabled", True),
            npu_server_url=npu_data.get("npu_server_url", "http://127.0.0.1:8899")
        )

        notif_data = raw.get("notifications", {})
        notif_cfg = NotificationConfig(
            enabled=notif_data.get("enabled", True),
            windows_toast_enabled=notif_data.get("windows_toast_enabled", True),
            discord_webhook_url=notif_data.get("discord_webhook_url"),
            telegram_bot_token=notif_data.get("telegram_bot_token"),
            telegram_chat_id=notif_data.get("telegram_chat_id"),
            thermal_alert_celsius=notif_data.get("thermal_alert_celsius", 65.0),
            battery_alert_percent=notif_data.get("battery_alert_percent", 20.0),
            cooldown_sec=notif_data.get("cooldown_sec", 120.0)
        )

        srv_data = raw.get("server", {})
        srv_cfg = ServerConfig(
            host=srv_data.get("host", "127.0.0.1"),
            port=srv_data.get("port", 8765),
            hud_enabled=srv_data.get("hud_enabled", True)
        )

        raw_db_path = raw.get("db_path", DEFAULT_DB_PATH)
        if raw_db_path.startswith("~"):
            resolved_db = str(Path.home() / raw_db_path[2:].lstrip("\\/"))
        else:
            resolved_db = raw_db_path

        return PerpetualConfig(
            accounts=accounts,
            circuit_breaker=cb,
            antigravity_tools=ag_tools,
            host=host_cfg,
            npu=npu_cfg,
            notifications=notif_cfg,
            server=srv_cfg,
            db_path=resolved_db
        )

    return PerpetualConfig()
