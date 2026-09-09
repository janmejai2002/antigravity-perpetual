"""
Tests for QuotaLedger and QuotaRotator.
"""
import os
import tempfile
import pytest

from antigravity_perpetual.quota.models import AccountQuota, CircuitState
from antigravity_perpetual.quota.ledger import QuotaLedger
from antigravity_perpetual.quota.circuit_breaker import CircuitBreaker
from antigravity_perpetual.quota.rotator import QuotaRotator


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


def test_rotator_account_selection_and_priority(temp_db):
    ledger = QuotaLedger(db_path=temp_db)
    cb = CircuitBreaker(ledger=ledger)
    rotator = QuotaRotator(ledger=ledger, circuit_breaker=cb)

    acc1 = AccountQuota(account_id="pro_1", account_name="Pro Alpha", rpm_limit=360, priority=1)
    acc2 = AccountQuota(account_id="pro_2", account_name="Pro Beta", rpm_limit=360, priority=2)
    acc3 = AccountQuota(account_id="pro_3", account_name="Pro Gamma", rpm_limit=360, priority=3)

    ledger.register_account(acc1)
    ledger.register_account(acc2)
    ledger.register_account(acc3)

    # Initial selection must choose Priority 1 (pro_1)
    selected = rotator.select_account(estimated_tokens=500)
    assert selected is not None
    assert selected.account_id == "pro_1"


def test_rotator_85_percent_safety_buffer(temp_db):
    ledger = QuotaLedger(db_path=temp_db)
    cb = CircuitBreaker(ledger=ledger)
    rotator = QuotaRotator(ledger=ledger, circuit_breaker=cb)

    acc1 = AccountQuota(account_id="pro_1", account_name="Pro Alpha", rpm_limit=10, priority=1)
    acc2 = AccountQuota(account_id="pro_2", account_name="Pro Beta", rpm_limit=10, priority=2)

    ledger.register_account(acc1)
    ledger.register_account(acc2)

    # Record 9 requests for acc1 (90% capacity, exceeding 85% safety threshold)
    for _ in range(9):
        rotator.record_completion("pro_1", status_code=200, token_count=100, latency_ms=50.0)

    # Rotator must automatically shift to acc2 to prevent hitting 429
    selected = rotator.select_account(estimated_tokens=100)
    assert selected is not None
    assert selected.account_id == "pro_2"
