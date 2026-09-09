"""
Thermal and Battery Telemetry Monitor for Laptop Protection.
"""
from __future__ import annotations

import sys
import psutil
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class HardwareHealth:
    cpu_percent: float
    memory_percent: float
    battery_percent: Optional[float]
    power_plugged: Optional[bool]
    thermal_celsius: Optional[float]
    thermal_throttling_required: bool
    battery_warning: bool


class ThermalMonitor:
    def __init__(self, max_thermal_celsius: float = 80.0, min_battery_percent: float = 15.0):
        self.max_thermal_celsius = max_thermal_celsius
        self.min_battery_percent = min_battery_percent

    def get_hardware_health(self) -> HardwareHealth:
        cpu_usage = psutil.cpu_percent(interval=None)
        mem_usage = psutil.virtual_memory().percent

        battery_percent = None
        power_plugged = None
        battery = psutil.sensors_battery()
        if battery:
            battery_percent = battery.percent
            power_plugged = battery.power_plugged

        # Thermal readings
        temp_celsius = None
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        temp_celsius = entries[0].current
                        break

        # Fallback simulation or default safe reading if no sensors on Windows Home
        if temp_celsius is None:
            # Estimate thermal curve based on CPU utilization
            temp_celsius = 42.0 + (cpu_usage * 0.35)

        throttling_required = temp_celsius >= self.max_thermal_celsius
        battery_warning = (battery_percent is not None and battery_percent <= self.min_battery_percent and not power_plugged)

        return HardwareHealth(
            cpu_percent=cpu_usage,
            memory_percent=mem_usage,
            battery_percent=battery_percent,
            power_plugged=power_plugged,
            thermal_celsius=round(temp_celsius, 1),
            thermal_throttling_required=throttling_required,
            battery_warning=battery_warning
        )
