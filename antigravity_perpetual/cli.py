"""
Command-Line Interface for Antigravity Perpetual.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
import uvicorn
import yaml

from antigravity_perpetual import __version__
from antigravity_perpetual.config import load_config, PerpetualConfig
from antigravity_perpetual.quota.ledger import QuotaLedger
from antigravity_perpetual.quota.circuit_breaker import CircuitBreaker
from antigravity_perpetual.quota.rotator import QuotaRotator
from antigravity_perpetual.quota.bridge_8045 import AntigravityToolsBridge
from antigravity_perpetual.supervisor.power import PowerManager
from antigravity_perpetual.supervisor.thermal import ThermalMonitor
from antigravity_perpetual.supervisor.watchdog import SupervisorWatchdog
from antigravity_perpetual.hardware.npu_fallback import NPUFallback
from antigravity_perpetual.server.app import create_app


def print_banner():
    print("=" * 72)
    print("  [+] ANTIGRAVITY PERPETUAL SUPERVISOR  v" + __version__)
    print("  Autonomous Multi-Day Agent Supervisor & 4-Account Quota Reservoir")
    print("=" * 72)


def cmd_status(args):
    print_banner()
    cfg = load_config(args.config)
    power_mgr = PowerManager()
    thermal_mon = ThermalMonitor(
        max_thermal_celsius=cfg.host.max_thermal_celsius,
        min_battery_percent=cfg.host.min_battery_percent
    )
    hw = thermal_mon.get_hardware_health()
    bridge = AntigravityToolsBridge(gateway_url=cfg.antigravity_tools.gateway_url)
    bridge_ok, bridge_ver = bridge.is_gateway_online()
    npu = NPUFallback(npu_server_url=cfg.npu.npu_server_url)
    npu_ok = npu.is_available()

    print(f" [Host Platform]        : {sys.platform.upper()} (Windows 11)")
    print(f" [Execution State]      : {cfg.host.execution_state} (Modern Standby Override)")
    print(f" [Thermal Telemetry]    : {hw.thermal_celsius}°C (Throttle limit: {cfg.host.max_thermal_celsius}°C)")
    batt_str = f"{hw.battery_percent}% ({'Plugged In' if hw.power_plugged else 'Battery'})" if hw.battery_percent is not None else "N/A"
    print(f" [Battery Status]       : {batt_str}")
    print(f" [Antigravity Tools]    : {'ONLINE (' + bridge_ver + ')' if bridge_ok else 'OFFLINE'} @ {cfg.antigravity_tools.gateway_url}")
    print(f" [Lunar Lake NPU]       : {'ONLINE (47 TOPS INT8)' if npu_ok else 'OFFLINE'} @ {cfg.npu.npu_server_url}")
    print(f" [State Database]       : {cfg.db_path}")
    print(f" [Watchdog Silence]     : Max {cfg.host.silence_deadlock_timeout_sec}s timeout")
    print("=" * 72)



def cmd_accounts(args):
    print_banner()
    cfg = load_config(args.config)
    ledger = QuotaLedger(db_path=cfg.db_path)
    accounts = ledger.get_account_quotas()
    if not accounts:
        # Register defaults from config if empty
        for a in cfg.accounts:
            from antigravity_perpetual.quota.models import AccountQuota
            ledger.register_account(AccountQuota(
                account_id=a.id,
                account_name=a.name,
                rpm_limit=a.rpm_limit,
                tpm_limit=a.tpm_limit,
                rpd_limit=a.rpd_limit,
                priority=a.priority
            ))
        accounts = ledger.get_account_quotas()

    print(f"{'ACCOUNT ID':<18} {'NAME':<22} {'RPM':<12} {'TPM':<16} {'RPD':<10} {'CIRCUIT':<10}")
    print("-" * 72)
    for a in accounts:
        rpm_disp = f"{a.current_rpm}/{a.rpm_limit}"
        tpm_disp = f"{a.current_tpm}/{a.tpm_limit}"
        rpd_disp = f"{a.current_rpd}/{a.rpd_limit}"
        print(f"{a.account_id:<18} {a.account_name:<22} {rpm_disp:<12} {tpm_disp:<16} {rpd_disp:<10} {a.circuit_state.value:<10}")
    print("=" * 72)


def cmd_init(args):
    out_file = Path("perpetual_config.yaml")
    if out_file.exists() and not args.force:
        print(f"[-] Config file already exists: {out_file.resolve()}. Use --force to overwrite.")
        return

    default_yaml = """# Antigravity Perpetual Configuration
quota_pool:
  accounts:
    - id: "account_pro_1"
      name: "Google Pro - Alpha"
      rpm_limit: 360
      tpm_limit: 4000000
      rpd_limit: 30000
      priority: 1
    - id: "account_pro_2"
      name: "Google Pro - Beta"
      rpm_limit: 360
      tpm_limit: 4000000
      rpd_limit: 30000
      priority: 2
    - id: "account_pro_3"
      name: "Google Pro - Gamma"
      rpm_limit: 360
      tpm_limit: 4000000
      rpd_limit: 30000
      priority: 3
  circuit_breaker:
    failure_threshold: 3
    recovery_timeout_sec: 60.0
    backoff_factor: 2.0
    jitter_range: 0.2

antigravity_tools:
  enabled: true
  gateway_url: "http://127.0.0.1:8045"
  timeout_sec: 30.0

host_persistence:
  execution_state: "0x80000041"
  silence_deadlock_timeout_sec: 180
  max_thermal_celsius: 80.0
  min_battery_percent: 15.0

npu_fallback:
  enabled: true
  npu_server_url: "http://127.0.0.1:8765"
  device: "NPU"

server:
  host: "127.0.0.1"
  port: 8765
  hud_enabled: true

db_path: "runtime_state.db"
"""
    out_file.write_text(default_yaml, encoding="utf-8")
    print(f"[+] Initialized declarative configuration: {out_file.resolve()}")


def find_available_port(host: str, target_port: int, max_attempts: int = 10) -> int:
    import socket
    for p in range(target_port, target_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    return target_port


def cmd_run(args):
    print_banner()
    cfg = load_config(args.config)
    requested_port = args.port or cfg.server.port
    host = args.host or cfg.server.host

    port = find_available_port(host, requested_port)
    if port != requested_port:
        print(f" [!] Port {requested_port} is busy. Automatically rebound to available port: {port}")

    # 1. Engage Win32 Persistence
    power_mgr = PowerManager(allow_display_sleep=True)
    res = power_mgr.enable_perpetual_mode()
    print(f" [+] Host Persistence Engaged  : {res.get('flags_set', 'ACTIVE')} (Away Mode Enabled)")

    # 2. Check Antigravity Tools :8045
    bridge = AntigravityToolsBridge(gateway_url=cfg.antigravity_tools.gateway_url)
    bridge_ok, bridge_ver = bridge.is_gateway_online()
    if bridge_ok:
        print(f" [+] Antigravity Tools Bridge   : Connected to {cfg.antigravity_tools.gateway_url} ({bridge_ver})")
    else:
        print(f" [!] Antigravity Tools Bridge   : Standalone mode ({bridge_ver})")

    # 3. Check NPU
    npu = NPUFallback(npu_server_url=cfg.npu.npu_server_url)
    if npu.is_available():
        print(f" [+] Lunar Lake NPU 4000       : Connected @ {cfg.npu.npu_server_url}")
    else:
        print(f" [!] Lunar Lake NPU 4000       : Standby/Fallback Mode")

    print(f" [+] Supervisor HUD & API      : http://{host}:{port}/")
    print(f" [+] Press Ctrl+C to terminate perpetual supervisor.")
    print("=" * 72)

    app = create_app(cfg, power_manager=power_mgr)
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    finally:
        print("\n [*] Restoring normal host power management...")
        power_mgr.restore_normal_mode()
        print(" [+] Host power mode restored.")


def cmd_service(args):
    import subprocess
    scripts_dir = Path(__file__).parent.parent / "scripts"
    task_name = "AntigravityPerpetualSupervisor"

    if args.service_action == "install":
        print(f"[*] Installing Windows Scheduled Task: {task_name}...")
        ps_script = scripts_dir / "register_autostart.ps1"
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)]
        if getattr(args, "start", False):
            cmd.append("-StartNow")
        res = subprocess.run(cmd, text=True, capture_output=True)
        print(res.stdout)
        if res.stderr:
            print(res.stderr)

    elif args.service_action == "uninstall":
        print(f"[*] Uninstalling Windows Scheduled Task: {task_name}...")
        ps_script = scripts_dir / "unregister_autostart.ps1"
        res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)], text=True, capture_output=True)
        print(res.stdout)
        if res.stderr:
            print(res.stderr)

    elif args.service_action == "status":
        print_banner()
        print(f" [Service Name]         : {task_name}")
        ps_cmd = f"Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue | Select-Object TaskName, State | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], text=True, capture_output=True)
        is_task_reg = False
        if res.returncode == 0 and res.stdout.strip():
            try:
                data = json.loads(res.stdout)
                state_str = {0: "Unknown", 1: "Disabled", 2: "Queued", 3: "Ready", 4: "Running"}.get(data.get("State"), str(data.get("State")))
                print(f" [Scheduled Task]       : REGISTERED (State: {state_str})")
                is_task_reg = True
            except Exception:
                print(f" [Scheduled Task]       : REGISTERED")
                is_task_reg = True
        else:
            print(f" [Scheduled Task]       : NOT_REGISTERED")

        reg_cmd = f"(Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -ErrorAction SilentlyContinue).{task_name}"
        res_reg = subprocess.run(["powershell", "-NoProfile", "-Command", reg_cmd], text=True, capture_output=True)
        if res_reg.returncode == 0 and res_reg.stdout.strip():
            print(f" [Registry Auto-Start]  : ACTIVE (HKCU Run on Logon)")
            print(f" [Target Command]       : {res_reg.stdout.strip()}")
        else:
            print(f" [Registry Auto-Start]  : INACTIVE")

        # Check if daemon is listening
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("127.0.0.1", 8765))
            s.close()
            print(f" [Live Daemon :8765]   : LISTENING (ONLINE)")
        except Exception:
            print(f" [Live Daemon :8765]   : NOT_LISTENING")
        print("=" * 72)



def main():
    parser = argparse.ArgumentParser(
        prog="perpetual",
        description="Autonomous Multi-Day Agent Supervisor & 4-Account Quota Reservoir"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-c", "--config", type=str, default=None, help="Path to perpetual_config.yaml")

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # run
    p_run = subparsers.add_parser("run", help="Start the perpetual supervisor and HUD")
    p_run.add_argument("--host", type=str, default=None, help="Host binding (default: 127.0.0.1)")
    p_run.add_argument("-p", "--port", type=int, default=None, help="Port binding (default: 8765)")

    # status
    subparsers.add_parser("status", help="Display host persistence, thermal, and bridge status")

    # accounts
    subparsers.add_parser("accounts", help="Display active accounts and quota reservoir meters")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a default perpetual_config.yaml")
    p_init.add_argument("-f", "--force", action="store_true", help="Overwrite existing config")

    # service
    p_service = subparsers.add_parser("service", help="Manage Windows Scheduled Task auto-start")
    p_service.add_argument("service_action", choices=["install", "uninstall", "status"], help="Action to perform")
    p_service.add_argument("--start", action="store_true", help="Start the task immediately upon installation")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "accounts":
        cmd_accounts(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "service":
        cmd_service(args)



if __name__ == "__main__":
    main()
