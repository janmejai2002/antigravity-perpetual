"""
Tests for CircuitBreaker state transitions and Full Jitter backoff.
"""
import os
import tempfile
import time
import pytest

from antigravity_perpetual.quota.models import AccountQuota, CircuitState
from antigravity_perpetual.quota.ledger import QuotaLedger
from antigravity_perpetual.quota.circuit_breaker import CircuitBreaker


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_circuit_breaker_429_trips_immediately(temp_db):
    ledger = QuotaLedger(db_path=temp_db)
    cb = CircuitBreaker(ledger=ledger, recovery_timeout_sec=10.0)

    acc = AccountQuota(account_id="pro_1", account_name="Pro Alpha", rpm_limit=360)
    ledger.register_account(acc)

    # 1. Initially CLOSED and ready
    quotas = ledger.get_account_quotas()
    assert quotas[0].circuit_state == CircuitState.CLOSED
    assert cb.can_dispatch(quotas[0]) is True

    # 2. Record HTTP 429 error
    now = time.time()
    cb.record_failure("pro_1", status_code=429, now=now)

    # 3. Circuit must immediately TRIP to OPEN
    quotas = ledger.get_account_quotas()
    assert quotas[0].circuit_state == CircuitState.OPEN
    assert cb.can_dispatch(quotas[0], now=now) is False

    # 4. Fast forward time beyond cooldown
    future = now + 15.0
    assert cb.can_dispatch(quotas[0], now=future) is True
    quotas = ledger.get_account_quotas()
    assert quotas[0].circuit_state == CircuitState.HALF_OPEN

    # 5. Successful probe restores CLOSED
    cb.record_success("pro_1")
    quotas = ledger.get_account_quotas()
    assert quotas[0].circuit_state == CircuitState.CLOSED
