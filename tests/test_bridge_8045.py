"""
Tests for AntigravityToolsBridge adapter.
"""
import pytest
from unittest.mock import patch, MagicMock

from antigravity_perpetual.quota.bridge_8045 import AntigravityToolsBridge


def test_bridge_gateway_health_check():
    bridge = AntigravityToolsBridge(gateway_url="http://127.0.0.1:8045")

    # Mock 200 health response
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"status": "ok", "version": "4.6.9"}

    with patch("requests.get", return_value=mock_res):
        online, ver = bridge.is_gateway_online()
        assert online is True
        assert ver == "4.6.9"

    # Mock connection failure
    with patch("requests.get", side_effect=Exception("Connection refused")):
        online, err = bridge.is_gateway_online()
        assert online is False
        assert "refused" in err


def test_bridge_forward_chat_completion():
    bridge = AntigravityToolsBridge(gateway_url="http://127.0.0.1:8045")

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
        "usage": {"total_tokens": 42}
    }

    with patch("requests.post", return_value=mock_res):
        res = bridge.forward_chat_completion({"messages": [{"role": "user", "content": "Hi"}]})
        assert res["status_code"] == 200
        assert res["data"]["choices"][0]["message"]["content"] == "Hello!"
        assert res["latency_ms"] >= 0.0
