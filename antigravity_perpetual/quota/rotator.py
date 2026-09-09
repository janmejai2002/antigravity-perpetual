"""
Dynamic Multi-Account Quota Rotator and Load Balancer.
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

from antigravity_perpetual.quota.models import AccountQuota, RequestRecord, CircuitState
from antigravity_perpetual.quota.ledger import QuotaLedger
from antigravity_perpetual.quota.circuit_breaker import CircuitBreaker


class QuotaRotator:
    def __init__(self, ledger: QuotaLedger, circuit_breaker: CircuitBreaker):
        self.ledger = ledger
        self.circuit_breaker = circuit_breaker
        self._round_robin_idx = 0

    def select_account(self, estimated_tokens: int = 1000, now: Optional[float] = None) -> Optional[AccountQuota]:
        if now is None:
            now = time.time()

        accounts = self.ledger.get_account_quotas()
        if not accounts:
            return None

        # Sort by priority
        accounts.sort(key=lambda a: a.priority)

        # 1. Filter candidates where circuit breaker allows dispatch
        healthy_candidates = []
        for a in accounts:
            if not self.circuit_breaker.can_dispatch(a, now):
                continue

            # Check capacity safety margins (85% buffer rule)
            if a.current_rpm >= int(a.rpm_limit * 0.85):
                continue
            if a.current_tpm + estimated_tokens > int(a.tpm_limit * 0.90):
                continue
            if a.current_rpd >= a.rpd_limit:
                continue

            healthy_candidates.append(a)

        if healthy_candidates:
            # Pick using priority + round-robin within equal priority
            min_prio = healthy_candidates[0].priority
            top_tier = [c for c in healthy_candidates if c.priority == min_prio]
            selected = top_tier[self._round_robin_idx % len(top_tier)]
            self._round_robin_idx += 1
            return selected

        # 2. Secondary fallback: check any CLOSED account with remaining daily capacity
        for a in accounts:
            if a.circuit_state == CircuitState.CLOSED and a.current_rpd < a.rpd_limit:
                if a.current_rpm < a.rpm_limit:
                    return a

        # 3. Tertiary fallback: check if any HALF_OPEN probe can be sent
        for a in accounts:
            if a.circuit_state == CircuitState.HALF_OPEN:
                return a

        return None

    def record_completion(
        self,
        account_id: str,
        status_code: int,
        token_count: int,
        latency_ms: float,
        now: Optional[float] = None
    ):
        if now is None:
            now = time.time()

        is_failure = (status_code >= 400)
        record = RequestRecord(
            account_id=account_id,
            timestamp=now,
            token_count=token_count,
            status_code=status_code,
            latency_ms=latency_ms,
            is_failure=is_failure
        )
        self.ledger.record_request(record)

        if status_code in (200, 201):
            self.circuit_breaker.record_success(account_id)
        elif status_code in (429, 503, 504, 500):
            self.circuit_breaker.record_failure(account_id, status_code, now)
