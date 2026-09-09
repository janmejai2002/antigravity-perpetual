"""
Tests for AlertNotifier and multi-channel telemetry notifications.
"""
import time
from unittest.mock import patch, MagicMock
from antigravity_perpetual.config import NotificationConfig
from antigravity_perpetual.quota.ledger import QuotaLedger
from antigravity_perpetual.supervisor.notifier import AlertNotifier, AlertCategory


def test_notifier_records_to_sqlite(tmp_path):
    db_file = str(tmp_path / "test_alerts.db")
    ledger = QuotaLedger(db_path=db_file)
    cfg = NotificationConfig(enabled=True, windows_toast_enabled=False, cooldown_sec=10.0)
    notifier = AlertNotifier(config=cfg, ledger=ledger)

    # 1. Send alert
    success = notifier.notify(
        category=AlertCategory.THERMAL_THROTTLE,
        severity="CRITICAL",
        title="Overheat Test",
        message="CPU temp 68.5°C",
        details={"temp": 68.5}
    )
    assert success is True

    # 2. Verify alert persisted in SQLite WAL ledger
    alerts = ledger.get_recent_alerts(limit=10)
    assert len(alerts) == 1
    assert alerts[0]["category"] == AlertCategory.THERMAL_THROTTLE
    assert alerts[0]["severity"] == "CRITICAL"
    assert "Overheat Test" in alerts[0]["message"]
    assert alerts[0]["details"]["temp"] == 68.5


def test_notifier_cooldown_suppression(tmp_path):
    db_file = str(tmp_path / "test_cooldown.db")
    ledger = QuotaLedger(db_path=db_file)
    cfg = NotificationConfig(enabled=True, windows_toast_enabled=False, cooldown_sec=60.0)
    notifier = AlertNotifier(config=cfg, ledger=ledger)

    # First notification goes through
    first = notifier.notify(
        category=AlertCategory.BATTERY_CRITICAL,
        severity="WARNING",
        title="Battery Low",
        message="18% remaining"
    )
    assert first is True

    # Immediate second notification is rate-limited
    second = notifier.notify(
        category=AlertCategory.BATTERY_CRITICAL,
        severity="WARNING",
        title="Battery Low",
        message="17% remaining"
    )
    assert second is False

    # Force bypass works
    forced = notifier.notify(
        category=AlertCategory.BATTERY_CRITICAL,
        severity="WARNING",
        title="Battery Low",
        message="15% remaining",
        force=True
    )
    assert forced is True
