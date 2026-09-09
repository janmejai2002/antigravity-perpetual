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

    def _accounts_path(self) -> Path:
        return Path.home() / ".antigravity_tools" / "accounts.json"

    def _google_accounts_path(self) -> Path:
        return Path.home() / ".gemini" / "google_accounts.json"

    def _headers(self, with_auth: bool = True) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AntigravityPerpetualSupervisor/1.0"
        }
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

    def get_accounts_state(self) -> Dict[str, Any]:
        """Fetch raw accounts and current_account_id from API with disk fallback."""
        online, _ = self.is_gateway_online()
        if online:
            try:
                res = requests.get(
                    f"{self.gateway_url}/api/accounts",
                    headers=self._headers(with_auth=True),
                    timeout=3.0
                )
                if res.status_code == 200:
                    return res.json()
            except Exception:
                pass

        # Fallback to reading disk
        acc_path = self._accounts_path()
        if acc_path.exists():
            try:
                with open(acc_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"accounts": [], "current_account_id": None}

    def get_current_account_id(self) -> Optional[str]:
        """Return the active account ID currently configured."""
        state = self.get_accounts_state()
        return state.get("current_account_id")

    def get_active_account_details(self) -> Optional[Dict[str, Any]]:
        """Return full details of the currently active account."""
        state = self.get_accounts_state()
        curr_id = state.get("current_account_id")
        for a in state.get("accounts", []):
            if a.get("id") == curr_id:
                return a
        return None

    def sync_accounts_into_ledger(self, ledger: Optional[Any] = None) -> int:
        """Sync discovered physical accounts from accounts.json into supervisor QuotaLedger."""
        target_ledger = ledger or (self.rotator.ledger if self.rotator else None)
        if not target_ledger:
            return 0
        state = self.get_accounts_state()
        accounts = state.get("accounts", [])
        if not accounts:
            return 0

        from antigravity_perpetual.quota.models import AccountQuota
        count = 0
        for idx, acc in enumerate(accounts, 1):
            acc_id = acc.get("id")
            email = acc.get("email", f"account_{idx}")
            name = f"{acc.get('name', 'Google Pro')} ({email})"
            target_ledger.register_account(AccountQuota(
                account_id=acc_id,
                account_name=name,
                rpm_limit=360,
                tpm_limit=4000000,
                rpd_limit=30000,
                priority=idx
            ))
            count += 1

        if count > 0:
            with target_ledger._get_connection() as conn:
                conn.execute("DELETE FROM accounts WHERE id LIKE 'account_pro_%';")

        return count

    def switch_active_account(self, identifier: str) -> Dict[str, Any]:
        """
        Switch active Google account across Antigravity Tools API, accounts.json, and .gemini state.
        Identifier can be account UUID or email address.
        """
        state = self.get_accounts_state()
        accounts = state.get("accounts", [])
        target = None

        for acc in accounts:
            if acc.get("id") == identifier or acc.get("email", "").lower() == identifier.lower():
                target = acc
                break

        if not target:
            return {
                "success": False,
                "error": f"Account not found for '{identifier}'",
                "available": [f"{a.get('email')} ({a.get('id')})" for a in accounts]
            }

        target_id = target["id"]
        target_email = target.get("email", "")

        # 1. Physical API switch against Antigravity Tools :8045
        api_switched = False
        online, _ = self.is_gateway_online()
        if online:
            try:
                res = requests.post(
                    f"{self.gateway_url}/api/accounts/switch",
                    json={"accountId": target_id},
                    headers=self._headers(with_auth=True),
                    timeout=5.0
                )
                api_switched = (res.status_code == 200)
            except Exception:
                api_switched = False

        # 2. Atomic disk persistence to ~/.antigravity_tools/accounts.json
        disk_switched = False
        acc_path = self._accounts_path()
        if acc_path.exists():
            try:
                with open(acc_path, "r", encoding="utf-8") as f:
                    disk_data = json.load(f)
                disk_data["current_account_id"] = target_id
                with open(acc_path, "w", encoding="utf-8") as f:
                    json.dump(disk_data, f, indent=2)
                disk_switched = True
            except Exception:
                disk_switched = False

        # 3. Synchronize ~/.gemini/google_accounts.json if applicable
        gemini_path = self._google_accounts_path()
        if gemini_path.exists() and target_email:
            try:
                with open(gemini_path, "r", encoding="utf-8") as f:
                    g_data = json.load(f)
                g_data["active"] = target_email
                with open(gemini_path, "w", encoding="utf-8") as f:
                    json.dump(g_data, f, indent=2)
            except Exception:
                pass

        # 4. If proxy is running and API switch wasn't confirmed, restart proxy to apply changes
        if not api_switched and self.is_proxy_running():
            try:
                requests.post(
                    f"{self.gateway_url}/api/proxy/stop",
                    headers=self._headers(with_auth=True),
                    timeout=3.0
                )
                time.sleep(0.5)
                requests.post(
                    f"{self.gateway_url}/api/proxy/start",
                    headers=self._headers(with_auth=True),
                    timeout=5.0
                )
            except Exception:
                pass

        return {
            "success": True,
            "switched_to": target_email,
            "account_id": target_id,
            "api_applied": api_switched,
            "disk_applied": disk_switched
        }

    def force_cycle(self) -> Dict[str, Any]:
        """Force-advance to the next available healthy Google account."""
        state = self.get_accounts_state()
        accounts = state.get("accounts", [])
        if not accounts:
            return {"success": False, "error": "No accounts configured in Antigravity Tools"}

        curr_id = state.get("current_account_id")
        available_ids = [a["id"] for a in accounts if not (a.get("disabled") or a.get("proxy_disabled"))]
        if not available_ids:
            return {"success": False, "error": "All accounts are disabled"}

        # Determine next account index
        if curr_id in available_ids:
            idx = available_ids.index(curr_id)
            next_id = available_ids[(idx + 1) % len(available_ids)]
        else:
            next_id = available_ids[0]

        return self.switch_active_account(next_id)

    def forward_chat_completion(
        self,
        payload: Dict[str, Any],
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Forward chat completion request with automatic physical rotation and 429 auto-retry.
        """
        # Auto-discover accounts into ledger if not yet synced
        if self.rotator:
            self.sync_accounts_into_ledger()

        selected_account = None
        if self.rotator:
            selected_account = self.rotator.select_account(estimated_tokens=payload.get("max_tokens", 1000))
            if selected_account and not account_id:
                account_id = selected_account.account_id

        # Physical Account Switch Verification
        curr_active_id = self.get_current_account_id()
        if account_id and account_id != curr_active_id:
            self.switch_active_account(account_id)

        headers = self._headers(with_auth=True)
        if account_id:
            headers["X-Antigravity-Account-Id"] = account_id

        t0 = time.time()
        endpoint = f"{self.gateway_url}/v1/chat/completions"
        try:
            res = requests.post(endpoint, json=payload, headers=headers, timeout=self.timeout_sec)
            latency_ms = (time.time() - t0) * 1000.0
            status_code = res.status_code

            # Handle 429 Quota Exhaustion with Transparent Auto-Failover
            if status_code == 429 and self.rotator:
                # 1. Record failure & trip circuit breaker for exhausted account
                self.rotator.record_completion(
                    account_id=account_id or curr_active_id,
                    status_code=429,
                    token_count=0,
                    latency_ms=latency_ms
                )
                # 2. Cycle to next account
                cycle_result = self.force_cycle()
                if cycle_result.get("success"):
                    next_account_id = cycle_result.get("account_id")
                    headers["X-Antigravity-Account-Id"] = next_account_id
                    t_retry = time.time()
                    retry_res = requests.post(endpoint, json=payload, headers=headers, timeout=self.timeout_sec)
                    retry_latency = (time.time() - t_retry) * 1000.0
                    status_code = retry_res.status_code
                    if status_code == 200:
                        body = retry_res.json()
                        tokens_used = body.get("usage", {}).get("total_tokens", payload.get("max_tokens", 500))
                        self.rotator.record_completion(
                            account_id=next_account_id,
                            status_code=200,
                            token_count=tokens_used,
                            latency_ms=retry_latency
                        )
                        return {
                            "status_code": 200,
                            "latency_ms": latency_ms + retry_latency,
                            "account_id": next_account_id,
                            "failover_triggered": True,
                            "data": body,
                            "error": None
                        }

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
