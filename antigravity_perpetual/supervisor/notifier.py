"""
Remote Telemetry & Multi-Channel Alert Notifier for Perpetual Supervisor.
Supports Native Windows Toast, Discord Webhooks, and Telegram Bot alerts with debounce.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests

from antigravity_perpetual.config import NotificationConfig


class AlertCategory:
    THERMAL_THROTTLE = "THERMAL_THROTTLE"
    BATTERY_CRITICAL = "BATTERY_CRITICAL"
    QUOTA_EXHAUSTED_429 = "QUOTA_EXHAUSTED_429"
    DEADLOCK_SILENCE = "DEADLOCK_SILENCE"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class AlertNotifier:
    def __init__(
        self,
        config: Optional[NotificationConfig] = None,
        ledger: Any = None
    ):
        self.config = config or NotificationConfig()
        self.ledger = ledger
        self._last_alert_timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _is_rate_limited(self, category: str, now: float) -> bool:
        with self._lock:
            last = self._last_alert_timestamps.get(category, 0.0)
            if now - last < self.config.cooldown_sec:
                return True
            self._last_alert_timestamps[category] = now
            return False

    def notify(
        self,
        category: str,
        severity: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """Dispatch notification across configured channels with rate limiting."""
        if not self.config.enabled:
            return False

        now = time.time()
        if not force and self._is_rate_limited(category, now):
            return False

        # 1. Record in persistent WAL ledger if available
        if self.ledger and hasattr(self.ledger, "record_alert"):
            try:
                self.ledger.record_alert(
                    category=category,
                    severity=severity,
                    message=f"{title}: {message}",
                    details=details,
                    now=now
                )
            except Exception:
                pass

        # 2. Dispatch asynchronously so supervisor loop never blocks
        threading.Thread(
            target=self._dispatch_channels,
            args=(category, severity, title, message, details),
            daemon=True
        ).start()
        return True

    def _dispatch_channels(
        self,
        category: str,
        severity: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]]
    ):
        # Native Windows Toast
        if self.config.windows_toast_enabled and sys.platform == "win32":
            self._send_windows_toast(title, message, severity)

        # Discord Webhook
        if self.config.discord_webhook_url:
            self._send_discord(title, message, severity, details)

        # Telegram Bot
        if self.config.telegram_bot_token and self.config.telegram_chat_id:
            self._send_telegram(title, message, severity)

    def _send_windows_toast(self, title: str, message: str, severity: str):
        """Display native Windows 10/11 Toast via PowerShell WinRT."""
        clean_title = title.replace('"', '`"').replace("'", "''")
        clean_msg = message.replace('"', '`"').replace("'", "''")
        prefix = "🚨 " if severity == "CRITICAL" else "⚠️ " if severity == "WARNING" else "⚡ "
        full_title = f"{prefix}{clean_title}"

        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $xml = [xml]$template.GetXml()
        $xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{full_title}')) > $null
        $xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{clean_msg}')) > $null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Antigravity Perpetual').Show($toast)
        """
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=5.0
            )
        except Exception:
            pass

    def _send_discord(self, title: str, message: str, severity: str, details: Optional[Dict[str, Any]]):
        """Dispatch embed notification to Discord Webhook."""
        color_map = {
            "CRITICAL": 0xEF4444,  # Red
            "WARNING": 0xF59E0B,   # Ochre / Amber
            "INFO": 0x38BDF8       # Water / Cyan
        }
        color = color_map.get(severity, 0x818CF8)

        fields = []
        if details:
            for k, v in details.items():
                fields.append({"name": str(k), "value": str(v), "inline": True})

        payload = {
            "username": "Antigravity Supervisor",
            "embeds": [{
                "title": f"[{severity}] {title}",
                "description": message,
                "color": color,
                "fields": fields[:10],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "Antigravity Perpetual Sentinel"}
            }]
        }
        try:
            requests.post(self.config.discord_webhook_url, json=payload, timeout=5.0)
        except Exception:
            pass

    def _send_telegram(self, title: str, message: str, severity: str):
        """Dispatch notification to Telegram Bot."""
        prefix = "🚨 *CRITICAL*" if severity == "CRITICAL" else "⚠️ *WARNING*" if severity == "WARNING" else "ℹ️ *INFO*"
        text = f"{prefix}\n*{title}*\n{message}"
        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5.0)
        except Exception:
            pass
