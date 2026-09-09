"""
Tests for ~/.antigravity_perpetual/state.db path expansion and WAL ledger schema.
"""
import os
import sqlite3
from pathlib import Path
from antigravity_perpetual.config import load_config, DEFAULT_DB_PATH
from antigravity_perpetual.quota.ledger import QuotaLedger
from antigravity_perpetual.state.checkpoint import CheckpointManager, TaskNode, TaskStatus


def test_default_db_path_resolution():
    cfg = load_config()
    expected = str(Path.home() / ".antigravity_perpetual" / "state.db")
    assert cfg.db_path == expected
    assert len(cfg.accounts) == 4


def test_state_db_wal_mode_and_tables(tmp_path):
    db_file = str(tmp_path / "custom_state.db")
    ledger = QuotaLedger(db_path=db_file)
    ckpt = CheckpointManager(db_path=db_file)

    # Verify WAL mode
    with ledger._get_connection() as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert mode.lower() == "wal"

        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        assert "accounts" in tables
        assert "request_ledger" in tables
        assert "system_alerts" in tables
        assert "task_dag" in tables
        assert "system_checkpoints" in tables

    # Save and verify task DAG node
    node = TaskNode(task_id="task_audit_01", run_epoch="epoch_1", status=TaskStatus.IN_PROGRESS, payload={"model": "gemini-pro"})
    ckpt.save_task(node)
    loaded = ckpt.get_task("task_audit_01")
    assert loaded is not None
    assert loaded.status == TaskStatus.IN_PROGRESS
    assert loaded.payload["model"] == "gemini-pro"
