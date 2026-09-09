"""
Win32 Power Management: Prevents system sleep and Modern Standby hibernation.
"""
from __future__ import annotations

import sys
import ctypes
from typing import Dict, Any

# Execution flags
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040
ES_CONTINUOUS = 0x80000000

# 0x80000041 = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
FLAG_PERPETUAL_AWAY = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED


class PowerManager:
    def __init__(self, allow_display_sleep: bool = True):
        self.allow_display_sleep = allow_display_sleep
        self.is_active = False
        self.is_windows = sys.platform == "win32"

    def enable_perpetual_mode(self) -> Dict[str, Any]:
        """Engage Win32 SetThreadExecutionState to keep CPU, RAM & NPU awake indefinitely."""
        if not self.is_windows:
            self.is_active = True
            return {"status": "ok", "platform": sys.platform, "flag": "non_windows_simulated"}

        flags = FLAG_PERPETUAL_AWAY
        if not self.allow_display_sleep:
            flags |= ES_DISPLAY_REQUIRED

        try:
            prev_state = ctypes.windll.kernel32.SetThreadExecutionState(flags)
            self.is_active = True
            return {
                "status": "ok",
                "platform": "windows",
                "flags_set": hex(flags),
                "away_mode_enabled": True,
                "display_sleep_allowed": self.allow_display_sleep,
                "previous_state": hex(prev_state)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def restore_normal_mode(self) -> Dict[str, Any]:
        """Restore default Windows power management."""
        if not self.is_windows:
            self.is_active = False
            return {"status": "restored", "platform": sys.platform}

        try:
            prev_state = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self.is_active = False
            return {
                "status": "restored",
                "flags_set": hex(ES_CONTINUOUS),
                "previous_state": hex(prev_state)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
