import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

from antigravity_perpetual.quota.rotator import QuotaRotator


class AntigravityToolsBridge:
    def __init__(
        self,
        rotator: Optional[QuotaRotator] = None,
        gateway_url: str = "http://127.0.0.1:8045",
        api_key: Optional[str] = None,
        timeout_sec: float = 30.0
    ):
        self.rotator = rotator
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.api_key = api_key or self._discover_api_key()

    def _discover_api_key(self) -> Optional[str]:
        env_key = os.environ.get("ANTIGRAVITY_TOOLS_API_KEY")
        if env_key:
            return env_key
        config_path = Path.home() / ".antigravity_tools" / "gui_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("proxy", {}).get("api_key")
            except Exception:
                pass
        return None

    def _headers(self, with_auth: bool = True) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if with_auth and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def is_gateway_online(self) -> Tuple[bool, Optional[str]]:
        """Check if Antigravity Tools service is listening and responsive."""
        try:
            res = requests.get(f"{self.gateway_url}/health", timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                return True, data.get("version", "unknown")
            return False, f"HTTP {res.status_code}"
        except Exception as e:
            return False, str(e)

    def is_proxy_running(self) -> bool:
        """Check if the internal proxy is running."""
        try:
            res = requests.get(
                f"{self.gateway_url}/api/proxy/status",
                headers=self._headers(with_auth=True),
                timeout=3.0
            )
            if res.status_code == 200:
                return res.json().get("running", False)
            return False
        except Exception:
            return False

    def ensure_proxy_running(self) -> bool:
        """Ensure proxy is started, starting it via API if currently disabled."""
        if self.is_proxy_running():
            return True
        try:
            res = requests.post(
                f"{self.gateway_url}/api/proxy/start",
                headers=self._headers(with_auth=True),
                timeout=5.0
            )
            return res.status_code == 200
        except Exception:
            return False

    def forward_chat_completion(
        self,
        payload: Dict[str, Any],
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Forward chat completion request with automatic rotation tracking."""
        selected_account = None
        if self.rotator:
            selected_account = self.rotator.select_account(estimated_tokens=payload.get("max_tokens", 1000))
            if selected_account and not account_id:
                account_id = selected_account.account_id

        headers = self._headers(with_auth=True)
        if account_id:
            headers["X-Antigravity-Account-Id"] = account_id

        t0 = time.time()
        endpoint = f"{self.gateway_url}/v1/chat/completions"
        try:
            res = requests.post(endpoint, json=payload, headers=headers, timeout=self.timeout_sec)
            latency_ms = (time.time() - t0) * 1000.0
            status_code = res.status_code

            # Estimate token count
            tokens_used = 0
            if status_code == 200:
                body = res.json()
                usage = body.get("usage", {})
                tokens_used = usage.get("total_tokens", payload.get("max_tokens", 500))
            else:
                body = {"error": f"HTTP {status_code}", "text": res.text}

            if self.rotator and account_id:
                self.rotator.record_completion(
                    account_id=account_id,
                    status_code=status_code,
                    token_count=tokens_used,
                    latency_ms=latency_ms
                )

            return {
                "status_code": status_code,
                "latency_ms": latency_ms,
                "account_id": account_id,
                "data": body if status_code == 200 else None,
                "error": None if status_code == 200 else body
            }
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000.0
            if self.rotator and account_id:
                self.rotator.record_completion(
                    account_id=account_id,
                    status_code=500,
                    token_count=0,
                    latency_ms=latency_ms
                )
            return {
                "status_code": 500,
                "latency_ms": latency_ms,
                "account_id": account_id,
                "data": None,
                "error": str(e)
            }
