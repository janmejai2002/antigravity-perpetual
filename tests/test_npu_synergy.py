"""
Tests for NPU Synergy, DFA regex command audits, and hyperspherical search.
"""
from unittest.mock import patch, MagicMock
from antigravity_perpetual.hardware.npu_fallback import NPUFallback


def test_npu_command_audit_local_dfa():
    npu = NPUFallback(npu_server_url="http://127.0.0.1:9999")  # Unreachable port to force local DFA

    # Safe commands
    safe_res = npu.audit_command("git status")
    assert safe_res["verdict"] == "ALLOWED"
    assert safe_res["hazard_probability"] == 0.0

    # Hazardous commands
    haz1 = npu.audit_command("rm -rf /")
    assert haz1["verdict"] == "BLOCKED"
    assert haz1["hazard_probability"] == 1.0

    haz2 = npu.audit_command("DROP DATABASE production;")
    assert haz2["verdict"] == "BLOCKED"

    haz3 = npu.audit_command("Remove-Item -Recurse C:\\Windows\\System32")
    assert haz3["verdict"] == "BLOCKED"


def test_npu_semantic_search():
    npu = NPUFallback(npu_server_url="http://127.0.0.1:8899")

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = [
        {"id": "doc_1", "text": "Perpetual agent memory", "score": 0.89}
    ]

    with patch("requests.get", return_value=mock_res):
        res = npu.semantic_search("agent memory", top_k=1)
        assert res["status"] == "ok"
        assert len(res["results"]) == 1
        assert res["results"][0]["id"] == "doc_1"
