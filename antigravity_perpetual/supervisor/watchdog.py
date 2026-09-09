"""
Supervisor Watchdog: Detects deadlocks, enforces silence timeouts, and triggers self-healing.
"""
from __future__ import annotations

import time
import subprocess
import threading
from typing import Optional, Callable, Dict, Any

from antigravity_perpetual.supervisor.power import PowerManager
from antigravity_perpetual.supervisor.thermal import ThermalMonitor


class SupervisorWatchdog:
    def __init__(
        self,
        silence_timeout_sec: int = 180,
        thermal_monitor: Optional[ThermalMonitor] = None,
        power_manager: Optional[PowerManager] = None,
        on_deadlock_callback: Optional[Callable[[], None]] = None
    ):
        self.silence_timeout_sec = silence_timeout_sec
        self.thermal_monitor = thermal_monitor or ThermalMonitor()
        self.power_manager = power_manager or PowerManager()
        self.on_deadlock_callback = on_deadlock_callback

        self.last_heartbeat = time.time()
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def heartbeat(self):
        """Record an activity pulse from the agent."""
        self.last_heartbeat = time.time()

    def check_health(self) -> Dict[str, Any]:
        now = time.time()
        silence_duration = now - self.last_heartbeat
        is_deadlocked = silence_duration > self.silence_timeout_sec

        hw_health = self.thermal_monitor.get_hardware_health()

        return {
            "is_alive": not is_deadlocked,
            "silence_duration_sec": round(silence_duration, 1),
            "silence_timeout_sec": self.silence_timeout_sec,
            "is_deadlocked": is_deadlocked,
            "hardware": {
                "cpu_percent": hw_health.cpu_percent,
                "memory_percent": hw_health.memory_percent,
                "battery_percent": hw_health.battery_percent,
                "power_plugged": hw_health.power_plugged,
                "thermal_celsius": hw_health.thermal_celsius,
                "thermal_throttling": hw_health.thermal_throttling_required,
                "battery_warning": hw_health.battery_warning
            }
        }

    def start(self):
        """Start background watchdog monitor."""
        self.is_running = True
        self.power_manager.enable_perpetual_mode()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
        self.power_manager.restore_normal_mode()

    def _monitor_loop(self):
        while self.is_running:
            health = self.check_health()
            if health["is_deadlocked"]:
                if self.on_deadlock_callback:
                    try:
                        self.on_deadlock_callback()
                    except Exception:
                        pass
                # Reset heartbeat to prevent rapid callback loops
                self.last_heartbeat = time.time()

            time.sleep(5.0)
