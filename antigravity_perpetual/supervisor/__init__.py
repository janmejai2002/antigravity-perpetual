"""Supervisor subsystem for host persistence, thermal safety, and watchdog monitoring."""
from antigravity_perpetual.supervisor.power import PowerManager
from antigravity_perpetual.supervisor.thermal import ThermalMonitor
from antigravity_perpetual.supervisor.watchdog import SupervisorWatchdog

__all__ = ["PowerManager", "ThermalMonitor", "SupervisorWatchdog"]
