"""
Antigravity Perpetual: Autonomous Multi-Day Agent Supervisor,
3-Account Quota Reservoir & Zero-Sleep Runtime for Google Antigravity & AI Coding Agents.
"""

__version__ = "1.0.0"
__author__ = "Janmejai Singh Minhas"
__license__ = "MIT"

from antigravity_perpetual.config import PerpetualConfig, load_config
from antigravity_perpetual.quota.rotator import QuotaRotator
from antigravity_perpetual.quota.circuit_breaker import CircuitBreaker
from antigravity_perpetual.quota.bridge_8045 import AntigravityToolsBridge
from antigravity_perpetual.compression.rtk_proxy import RtkCompressor
from antigravity_perpetual.supervisor.power import PowerManager
from antigravity_perpetual.supervisor.watchdog import SupervisorWatchdog
from antigravity_perpetual.state.checkpoint import CheckpointManager
from antigravity_perpetual.hardware.npu_fallback import NPUFallback

__all__ = [
    "PerpetualConfig",
    "load_config",
    "QuotaRotator",
    "CircuitBreaker",
    "AntigravityToolsBridge",
    "RtkCompressor",
    "PowerManager",
    "SupervisorWatchdog",
    "CheckpointManager",
    "NPUFallback",
]
