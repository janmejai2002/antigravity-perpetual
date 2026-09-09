"""
Quota data models and circuit breaker enums.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    CLOSED = "CLOSED"          # Normal operation, traffic flows
    OPEN = "OPEN"              # Tripped on 429/failures, traffic blocked
    HALF_OPEN = "HALF_OPEN"    # Probe request permitted to test recovery


@dataclass
class AccountQuota:
    account_id: str
    account_name: str
    rpm_limit: int = 360
    tpm_limit: int = 4000000
    rpd_limit: int = 30000
    priority: int = 1
    current_rpm: int = 0
    current_tpm: int = 0
    current_rpd: int = 0
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_timestamp: Optional[float] = None
    next_probe_timestamp: Optional[float] = None
    last_pacific_reset: Optional[str] = None


@dataclass
class RequestRecord:
    account_id: str
    timestamp: float
    token_count: int
    status_code: int
    latency_ms: float
    is_failure: bool = False
