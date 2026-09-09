"""
Atomic Git Hygiene: Automated checkpoint commits, dirty-tree stashing, and instant rollback.
"""
from __future__ import annotations

import subprocess
import time
from typing import Optional, Dict, Any


class GitManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def _run_git(self, *args) -> Tuple[int, str]:
        try:
            res = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=15.0
            )
            return res.returncode, res.stdout.strip()
        except Exception as e:
            return 1, str(e)

    def get_current_head(self) -> Optional[str]:
        code, out = self._run_git("rev-parse", "HEAD")
        return out if code == 0 else None

    def commit_checkpoint(self, message: str) -> Optional[str]:
        """Stage all changes and create an atomic checkpoint commit."""
        self._run_git("add", "-A")
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        full_msg = f"[AUTOPILOT_CHECKPOINT] {message} ({ts})"
        code, _ = self._run_git("commit", "-m", full_msg)
        if code == 0:
            return self.get_current_head()
        return None

    def rollback_to_commit(self, commit_hash: str) -> bool:
        """Instant rollback to previous stable checkpoint."""
        code, _ = self._run_git("reset", "--hard", commit_hash)
        self._run_git("clean", "-fd")
        return code == 0

    def stash_dirty_tree(self) -> bool:
        code, _ = self._run_git("stash", "save", "--include-untracked", f"perpetual_stash_{int(time.time())}")
        return code == 0
