"""
Tests for CheckpointManager task DAG state machine in SQLite WAL.
"""
import os
import tempfile
import pytest

from antigravity_perpetual.state.checkpoint import CheckpointManager, TaskNode, TaskStatus


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


def test_checkpoint_task_lifecycle(temp_db):
    mgr = CheckpointManager(db_path=temp_db)

    task = TaskNode(
        task_id="task_build_01",
        run_epoch="epoch_42",
        status=TaskStatus.PENDING,
        payload={"action": "compile_module"}
    )
    mgr.save_task(task)

    retrieved = mgr.get_task("task_build_01")
    assert retrieved is not None
    assert retrieved.status == TaskStatus.PENDING
    assert retrieved.payload["action"] == "compile_module"

    # Update to COMPLETED
    retrieved.status = TaskStatus.COMPLETED
    retrieved.git_commit_hash = "abc1234"
    mgr.save_task(retrieved)

    updated = mgr.get_task("task_build_01")
    assert updated.status == TaskStatus.COMPLETED
    assert updated.git_commit_hash == "abc1234"
