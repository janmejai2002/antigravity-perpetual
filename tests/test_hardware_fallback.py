"""
Tests for NPUFallback local silicon offloading.
"""
from unittest.mock import patch, MagicMock
from antigravity_perpetual.hardware.npu_fallback import NPUFallback


def test_npu_fallback_health():
    npu = NPUFallback(npu_server_url="http://127.0.0.1:8765")

    mock_res = MagicMock()
    mock_res.status_code = 200
    with patch("requests.get", return_value=mock_res):
        assert npu.is_available() is True

    with patch("requests.get", side_effect=Exception("Timeout")):
        assert npu.is_available() is False


def test_npu_fallback_embedding():
    npu = NPUFallback(npu_server_url="http://127.0.0.1:8765")

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]
    }

    with patch("requests.post", return_value=mock_res):
        res = npu.embed_text("test input")
        assert res["status"] == "ok"
        assert res["dim"] == 4
        assert res["latency_ms"] >= 0.0
