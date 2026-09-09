"""
SQLite WAL Quota Ledger with Sliding Window and Pacific Midnight Reset tracking.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from antigravity_perpetual.quota.models import AccountQuota, RequestRecord, CircuitState

PACIFIC_OFFSET = timedelta(hours=-7)  # PDT / UTC-7


class QuotaLedger:
    def __init__(self, db_path: str = "quota_ledger.db"):
        expanded = os.path.abspath(os.path.expanduser(db_path))
        Path(expanded).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = expanded
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

                CREATE TABLE IF NOT EXISTS system_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_requests_acc_ts ON request_ledger(account_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_alerts_ts ON system_alerts(timestamp);
            """)
            self._migrate_legacy_db_if_needed(conn)

    def _migrate_legacy_db_if_needed(self, conn: sqlite3.Connection):
        """Migrate existing account records from legacy runtime_state.db if brand new default db."""
        try:
            from antigravity_perpetual.config import DEFAULT_DB_PATH
            if os.path.abspath(self.db_path) != os.path.abspath(DEFAULT_DB_PATH):
                return
            row = conn.execute("SELECT COUNT(*) as cnt FROM accounts;").fetchone()
            if row and row["cnt"] == 0:
                legacy_path = Path("runtime_state.db")
                if legacy_path.exists() and str(legacy_path.resolve()) != str(Path(self.db_path).resolve()):
                    legacy_conn = sqlite3.connect(legacy_path)
                    legacy_conn.row_factory = sqlite3.Row
                    try:
                        accounts = legacy_conn.execute("SELECT * FROM accounts;").fetchall()
                        for a in accounts:
                            conn.execute("""
                                INSERT OR IGNORE INTO accounts (
                                    id, name, rpm_limit, tpm_limit, rpd_limit, priority,
                                    circuit_state, consecutive_failures, last_failure_timestamp,
                                    next_probe_timestamp, last_pacific_reset
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                a["id"], a["name"], a["rpm_limit"], a["tpm_limit"], a["rpd_limit"],
                                a["priority"], a["circuit_state"], a["consecutive_failures"],
                                a["last_failure_timestamp"], a["next_probe_timestamp"], a["last_pacific_reset"]
                            ))
                        conn.commit()
                    finally:
                        legacy_conn.close()
        except Exception:
            pass


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

    def record_alert(
        self,
        category: str,
        severity: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        now: Optional[float] = None
    ) -> int:
        ts = now if now is not None else time.time()
        details_str = json.dumps(details) if details else None
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO system_alerts (timestamp, category, severity, message, details_json)
                VALUES (?, ?, ?, ?, ?);
            """, (ts, category, severity, message, details_str))
            return cursor.lastrowid

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, timestamp, category, severity, message, details_json
                FROM system_alerts
                ORDER BY timestamp DESC
                LIMIT ?;
            """, (limit,)).fetchall()
            alerts = []
            for r in rows:
                details = None
                if r["details_json"]:
                    try:
                        details = json.loads(r["details_json"])
                    except Exception:
                        details = r["details_json"]
                alerts.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "category": r["category"],
                    "severity": r["severity"],
                    "message": r["message"],
                    "details": details
                })
            return alerts

