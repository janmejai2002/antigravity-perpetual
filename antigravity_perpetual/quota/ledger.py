"""
SQLite WAL Quota Ledger with Sliding Window and Pacific Midnight Reset tracking.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any

from antigravity_perpetual.quota.models import AccountQuota, RequestRecord, CircuitState

PACIFIC_OFFSET = timedelta(hours=-7)  # PDT / UTC-7


class QuotaLedger:
    def __init__(self, db_path: str = "quota_ledger.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    rpm_limit INTEGER NOT NULL,
                    tpm_limit INTEGER NOT NULL,
                    rpd_limit INTEGER NOT NULL,
                    priority INTEGER NOT NULL,
                    circuit_state TEXT NOT NULL DEFAULT 'CLOSED',
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    last_failure_timestamp REAL,
                    next_probe_timestamp REAL,
                    last_pacific_reset TEXT
                );

                CREATE TABLE IF NOT EXISTS request_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    token_count INTEGER NOT NULL,
                    status_code INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    is_failure INTEGER NOT NULL,
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                );

                CREATE INDEX IF NOT EXISTS idx_requests_acc_ts ON request_ledger(account_id, timestamp);
            """)

    @staticmethod
    def get_current_pacific_day() -> str:
        now_utc = datetime.now(timezone.utc)
        pacific_dt = now_utc + PACIFIC_OFFSET
        return pacific_dt.strftime("%Y-%m-%d")

    def register_account(self, account: AccountQuota):
        today_pac = self.get_current_pacific_day()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO accounts (
                    id, name, rpm_limit, tpm_limit, rpd_limit, priority,
                    circuit_state, consecutive_failures, last_failure_timestamp,
                    next_probe_timestamp, last_pacific_reset
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    rpm_limit=excluded.rpm_limit,
                    tpm_limit=excluded.tpm_limit,
                    rpd_limit=excluded.rpd_limit,
                    priority=excluded.priority;
            """, (
                account.account_id, account.account_name, account.rpm_limit,
                account.tpm_limit, account.rpd_limit, account.priority,
                account.circuit_state.value, account.consecutive_failures,
                account.last_failure_timestamp, account.next_probe_timestamp,
                today_pac
            ))

    def check_and_apply_pacific_reset(self, account_id: str):
        today_pac = self.get_current_pacific_day()
        with self._get_connection() as conn:
            row = conn.execute("SELECT last_pacific_reset FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if row and row["last_pacific_reset"] != today_pac:
                conn.execute("UPDATE accounts SET last_pacific_reset = ? WHERE id = ?", (today_pac, account_id))

    def record_request(self, record: RequestRecord):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO request_ledger (
                    account_id, timestamp, token_count, status_code, latency_ms, is_failure
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (
                record.account_id, record.timestamp, record.token_count,
                record.status_code, record.latency_ms, 1 if record.is_failure else 0
            ))

    def get_sliding_metrics(self, account_id: str, window_sec: float = 60.0) -> Tuple[int, int]:
        cutoff = time.time() - window_sec
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as req_count, COALESCE(SUM(token_count), 0) as total_tokens
                FROM request_ledger
                WHERE account_id = ? AND timestamp >= ?;
            """, (account_id, cutoff)).fetchone()
            return int(row["req_count"]), int(row["total_tokens"])

    def get_daily_requests(self, account_id: str) -> int:
        self.check_and_apply_pacific_reset(account_id)
        now_utc = datetime.now(timezone.utc)
        pacific_dt = now_utc + PACIFIC_OFFSET
        start_of_day_pac = pacific_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_day_utc = start_of_day_pac - PACIFIC_OFFSET
        ts_start = start_of_day_utc.timestamp()

        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as rpd
                FROM request_ledger
                WHERE account_id = ? AND timestamp >= ?;
            """, (account_id, ts_start)).fetchone()
            return int(row["rpd"])

    def update_circuit_state(
        self,
        account_id: str,
        state: CircuitState,
        consecutive_failures: int,
        last_failure_ts: Optional[float] = None,
        next_probe_ts: Optional[float] = None
    ):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE accounts SET
                    circuit_state = ?,
                    consecutive_failures = ?,
                    last_failure_timestamp = ?,
                    next_probe_timestamp = ?
                WHERE id = ?;
            """, (
                state.value, consecutive_failures, last_failure_ts, next_probe_ts, account_id
            ))

    def get_account_quotas(self) -> List[AccountQuota]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM accounts ORDER BY priority ASC;").fetchall()
            results = []
            for r in rows:
                rpm, tpm = self.get_sliding_metrics(r["id"], 60.0)
                rpd = self.get_daily_requests(r["id"])
                results.append(AccountQuota(
                    account_id=r["id"],
                    account_name=r["name"],
                    rpm_limit=r["rpm_limit"],
                    tpm_limit=r["tpm_limit"],
                    rpd_limit=r["rpd_limit"],
                    priority=r["priority"],
                    current_rpm=rpm,
                    current_tpm=tpm,
                    current_rpd=rpd,
                    circuit_state=CircuitState(r["circuit_state"]),
                    consecutive_failures=r["consecutive_failures"],
                    last_failure_timestamp=r["last_failure_timestamp"],
                    next_probe_timestamp=r["next_probe_timestamp"],
                    last_pacific_reset=r["last_pacific_reset"]
                ))
            return results
