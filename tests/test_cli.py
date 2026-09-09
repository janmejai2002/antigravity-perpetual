"""
Tests for CLI commands.
"""
import subprocess
import sys


def test_cli_help():
    res = subprocess.run(
        [sys.executable, "-m", "antigravity_perpetual", "--help"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "Autonomous Multi-Day Agent Supervisor" in res.stdout
    assert "accounts" in res.stdout
    assert "status" in res.stdout


def test_cli_status():
    res = subprocess.run(
        [sys.executable, "-m", "antigravity_perpetual", "status"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "ANTIGRAVITY PERPETUAL SUPERVISOR" in res.stdout
    assert "Execution State" in res.stdout


def test_cli_accounts():
    res = subprocess.run(
        [sys.executable, "-m", "antigravity_perpetual", "accounts"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "ACCOUNT ID" in res.stdout
    assert "Google Pro" in res.stdout
