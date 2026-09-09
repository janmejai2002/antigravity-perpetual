"""
ACID Task DAG State Machine & SQLite WAL Checkpoint Journal.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class TaskNode:
    task_id: str
    run_epoch: str
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any] = None
    retry_count: int = 0
    max_retries: int = 3
    git_commit_hash: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}
        if self.created_at == 0.0:
            self.created_at = time.time()
            self.updated_at = self.created_at


class CheckpointManager:
    def __init__(self, db_path: str = "runtime_state.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS task_dag (
                    task_id TEXT PRIMARY KEY,
                    run_epoch TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    git_commit_hash TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS system_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    git_hash TEXT NOT NULL,
                    description TEXT,
                    metadata_json TEXT
                );
            """)

    def save_task(self, task: TaskNode):
        task.updated_at = time.time()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO task_dag (
                    task_id, run_epoch, status, payload_json, retry_count,
                    max_retries, git_commit_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    payload_json=excluded.payload_json,
                    retry_count=excluded.retry_count,
                    git_commit_hash=excluded.git_commit_hash,
                    updated_at=excluded.updated_at;
            """, (
                task.task_id, task.run_epoch, task.status.value,
                json.dumps(task.payload), task.retry_count, task.max_retries,
                task.git_commit_hash, task.created_at, task.updated_at
            ))

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM task_dag WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                return None
            return TaskNode(
                task_id=row["task_id"],
                run_epoch=row["run_epoch"],
                status=TaskStatus(row["status"]),
                payload=json.loads(row["payload_json"]),
                retry_count=row["retry_count"],
                max_retries=row["max_retries"],
                git_commit_hash=row["git_commit_hash"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    def get_tasks_by_epoch(self, epoch: str) -> List[TaskNode]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM task_dag WHERE run_epoch = ? ORDER BY created_at ASC", (epoch,)).fetchall()
            return [
                TaskNode(
                    task_id=r["task_id"],
                    run_epoch=r["run_epoch"],
                    status=TaskStatus(r["status"]),
                    payload=json.loads(r["payload_json"]),
                    retry_count=r["retry_count"],
                    max_retries=r["max_retries"],
                    git_commit_hash=r["git_commit_hash"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ) for r in rows
            ]
