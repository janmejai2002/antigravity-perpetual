"""
Tests for PowerManager host persistence execution flags.
"""
from antigravity_perpetual.supervisor.power import PowerManager, FLAG_PERPETUAL_AWAY


def test_power_manager_flags():
    pm = PowerManager(allow_display_sleep=True)
    res = pm.enable_perpetual_mode()
    assert res["status"] == "ok"
    assert pm.is_active is True

    restore_res = pm.restore_normal_mode()
    assert restore_res["status"] == "restored"
    assert pm.is_active is False
