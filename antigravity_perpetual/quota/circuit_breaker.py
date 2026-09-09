"""
Circuit Breaker with Full Jitter Exponential Backoff for Quota Management.
"""
from __future__ import annotations

import random
import time
from typing import Optional

from antigravity_perpetual.quota.models import CircuitState, AccountQuota
from antigravity_perpetual.quota.ledger import QuotaLedger


class CircuitBreaker:
    def __init__(
        self,
        ledger: QuotaLedger,
        failure_threshold: int = 3,
        recovery_timeout_sec: float = 60.0,
        backoff_factor: float = 2.0,
        jitter_range: float = 0.2,
        notifier: Optional[Any] = None
    ):
        self.ledger = ledger
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.backoff_factor = backoff_factor
        self.jitter_range = jitter_range
        self.notifier = notifier


    def calculate_backoff(self, consecutive_failures: int) -> float:
        """Full Jitter Exponential Backoff formula: T = min(T_max, T_0 * 2^failures) +/- rand."""
        base = self.recovery_timeout_sec * (self.backoff_factor ** max(0, consecutive_failures - 1))
        base = min(base, 1800.0)  # Max 30 minutes
        jitter = base * self.jitter_range * (2 * random.random() - 1)
        return max(5.0, base + jitter)

    def can_dispatch(self, account: AccountQuota, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()

        if account.circuit_state == CircuitState.CLOSED:
            return True

        if account.circuit_state == CircuitState.OPEN:
            if account.next_probe_timestamp and now >= account.next_probe_timestamp:
                self.ledger.update_circuit_state(
                    account.account_id,
                    CircuitState.HALF_OPEN,
                    account.consecutive_failures,
                    account.last_failure_timestamp,
                    account.next_probe_timestamp
                )
                account.circuit_state = CircuitState.HALF_OPEN
                return True
            return False

        if account.circuit_state == CircuitState.HALF_OPEN:
            return True

        return False

    def record_success(self, account_id: str):
        self.ledger.update_circuit_state(
            account_id,
            CircuitState.CLOSED,
            consecutive_failures=0,
            last_failure_ts=None,
            next_probe_ts=None
        )

    def record_failure(self, account_id: str, status_code: int, now: Optional[float] = None):
        if now is None:
            now = time.time()

        # Fetch latest state
        accounts = {a.account_id: a for a in self.ledger.get_account_quotas()}
        acc = accounts.get(account_id)
        if not acc:
            return

        failures = acc.consecutive_failures + 1
        is_429 = (status_code == 429)

        if is_429 or failures >= self.failure_threshold or acc.circuit_state == CircuitState.HALF_OPEN:
            backoff = self.calculate_backoff(failures)
            next_probe = now + backoff
            self.ledger.update_circuit_state(
                account_id,
                CircuitState.OPEN,
                consecutive_failures=failures,
                last_failure_ts=now,
                next_probe_ts=next_probe
            )
            if self.notifier:
                try:
                    from antigravity_perpetual.supervisor.notifier import AlertCategory
                    self.notifier.notify(
                        category=AlertCategory.QUOTA_EXHAUSTED_429,
                        severity="CRITICAL" if is_429 else "WARNING",
                        title="Quota Circuit Breaker Tripped",
                        message=f"Account '{account_id}' tripped to OPEN state (HTTP {status_code}). Backing off for {round(backoff, 1)}s.",
                        details={
                            "account_id": account_id,
                            "status_code": status_code,
                            "backoff_sec": round(backoff, 1),
                            "consecutive_failures": failures
                        }
                    )
                except Exception:
                    pass
        else:

            self.ledger.update_circuit_state(
                account_id,
                CircuitState.CLOSED,
                consecutive_failures=failures,
                last_failure_ts=now,
                next_probe_ts=None
            )
