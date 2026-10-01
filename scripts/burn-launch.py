#!/usr/bin/env python3
"""
Unified Launcher for AI Subscription Trackers:
- OmniBurn (Built by AGY) on port 8787
- Burn Ledger (Built by Codex) on port 8795

Supports:
  burn-launch [all|omniburn|ledger] [--open] [--no-open]
  burn-launch status
  burn-launch stop [all|omniburn|ledger]
  burn-launch restart [all|omniburn|ledger]
  burn-launch logs [omniburn|ledger]
"""

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OMNIBURN_DIR = os.path.abspath(os.environ.get("OMNIBURN_DIR", os.path.join(SCRIPT_DIR, "..")))
OMNIBURN_PORT = 8787
OMNIBURN_URL = f"http://localhost:{OMNIBURN_PORT}"
OMNIBURN_LOG = os.path.join(OMNIBURN_DIR, "omniburn.log")
OMNIBURN_PID_FILE = "/tmp/omniburn_8787.pid"

LEDGER_DIR = os.path.abspath(os.environ["BURN_LEDGER_DIR"]) if os.environ.get("BURN_LEDGER_DIR") else ""
LEDGER_PORT = 8795
LEDGER_URL = f"http://localhost:{LEDGER_PORT}"
LEDGER_LOG = os.path.join(LEDGER_DIR, "burn-ledger.log") if LEDGER_DIR else ""
LEDGER_PID_FILE = "/tmp/burn_ledger_8795.pid"
LEDGER_VENV_UVICORN = os.path.join(LEDGER_DIR, ".venv/bin/uvicorn") if LEDGER_DIR else ""


def is_port_open(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex(("127.0.0.1", port)) == 0


def check_http_health(url: str, timeout: float = 1.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BurnLauncher/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 302, 307)
    except Exception:
        return False


def get_pid_from_file(pid_file: str) -> int | None:
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            pass
    return None


def find_pid_by_port(port: int) -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-t", "-i", f":{port}", "-sTCP:LISTEN"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if out:
            return int(out.split()[0])
    except Exception:
        pass
    return None


def stop_process(name: str, port: int, pid_file: str) -> bool:
    pid = get_pid_from_file(pid_file) or find_pid_by_port(port)
    if not pid:
        print(f"  • {name} (port {port}) is not running.")
        return False

    print(f"  • Stopping {name} (PID {pid})...", end="", flush=True)
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(25):
            time.sleep(0.1)
            if not is_port_open(port):
                break
        if is_port_open(port):
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.2)
        print(" [STOPPED]")
    except ProcessLookupError:
        print(" [ALREADY TERMINATED]")
    except Exception as e:
        print(f" [ERROR: {e}]")

    if os.path.exists(pid_file):
        try:
            os.remove(pid_file)
        except OSError:
            pass
    return True


def start_omniburn() -> bool:
    if is_port_open(OMNIBURN_PORT) and check_http_health(OMNIBURN_URL):
        pid = find_pid_by_port(OMNIBURN_PORT)
        print(f"  ✓ OmniBurn [Built by AGY] is already running on port {OMNIBURN_PORT} (PID {pid or 'active'})")
        return True

    if is_port_open(OMNIBURN_PORT):
        stale_pid = find_pid_by_port(OMNIBURN_PORT)
        if stale_pid:
            try:
                os.kill(stale_pid, signal.SIGTERM)
                time.sleep(0.5)
            except OSError:
                pass

    print(f"  🚀 Launching OmniBurn [Built by AGY] on {OMNIBURN_URL}...", end="", flush=True)
    log_f = open(OMNIBURN_LOG, "a")
    proc = subprocess.Popen(
        ["python3", "serve.py", "--port", str(OMNIBURN_PORT)],
        cwd=OMNIBURN_DIR,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    with open(OMNIBURN_PID_FILE, "w") as f:
        f.write(str(proc.pid))

    for _ in range(40):
        time.sleep(0.1)
        if check_http_health(OMNIBURN_URL):
            print(f" [READY · PID {proc.pid}]")
            return True

    print(" [FAILED TO RESPOND]")
    return False


def start_burn_ledger() -> bool:
    if not LEDGER_DIR:
        print("  • Burn Ledger is unavailable; set BURN_LEDGER_DIR to enable the paired launcher.")
        return False
    health_url = f"{LEDGER_URL}/api/health"
    if is_port_open(LEDGER_PORT) and check_http_health(health_url):
        pid = find_pid_by_port(LEDGER_PORT)
        print(f"  ✓ Burn Ledger [Built by Codex] is already running on port {LEDGER_PORT} (PID {pid or 'active'})")
        return True

    if is_port_open(LEDGER_PORT):
        stale_pid = find_pid_by_port(LEDGER_PORT)
        if stale_pid:
            try:
                os.kill(stale_pid, signal.SIGTERM)
                time.sleep(0.5)
            except OSError:
                pass

    print(f"  🚀 Launching Burn Ledger [Built by Codex] on {LEDGER_URL}...", end="", flush=True)
    log_f = open(LEDGER_LOG, "a")
    proc = subprocess.Popen(
        [LEDGER_VENV_UVICORN, "app.main:app", "--host", "127.0.0.1", "--port", str(LEDGER_PORT)],
        cwd=LEDGER_DIR,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    with open(LEDGER_PID_FILE, "w") as f:
        f.write(str(proc.pid))

    for _ in range(40):
        time.sleep(0.1)
        if check_http_health(health_url):
            print(f" [READY · PID {proc.pid}]")
            return True

    print(" [FAILED TO RESPOND]")
    return False


def open_browser(url: str):
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception:
        pass


def cmd_status():
    print("\n==========================================================================")
    print("           AI SUBSCRIPTION BURN TRACKER SUITE STATUS                     ")
    print("==========================================================================")
    
    # 1. OmniBurn
    omni_port_open = is_port_open(OMNIBURN_PORT)
    omni_health = check_http_health(OMNIBURN_URL) if omni_port_open else False
    omni_pid = find_pid_by_port(OMNIBURN_PORT) or get_pid_from_file(OMNIBURN_PID_FILE)
    omni_status = "ONLINE (Healthy)" if omni_health else "LISTENING" if omni_port_open else "OFFLINE"
    
    print("1. OmniBurn [Built by AGY]")
    print(f"   Status:   {omni_status}")
    print(f"   URL:      {OMNIBURN_URL}")
    print(f"   PID:      {omni_pid or 'None'}")
    print(f"   Log:      {OMNIBURN_LOG}")
    print("--------------------------------------------------------------------------")

    # 2. Burn Ledger
    ledger_port_open = bool(LEDGER_DIR) and is_port_open(LEDGER_PORT)
    ledger_health = check_http_health(f"{LEDGER_URL}/api/health") if ledger_port_open else False
    ledger_pid = find_pid_by_port(LEDGER_PORT) or get_pid_from_file(LEDGER_PID_FILE)
    ledger_status = "ONLINE (Healthy)" if ledger_health else "LISTENING" if ledger_port_open else "OFFLINE"

    print("2. Burn Ledger [Built by Codex]")
    print(f"   Status:   {ledger_status}")
    print(f"   URL:      {LEDGER_URL}")
    print(f"   PID:      {ledger_pid or 'None'}")
    print(f"   Log:      {LEDGER_LOG}")
    print("==========================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Launcher for AI Burn Rate Tracker Applications")
    subparsers = parser.add_subparsers(dest="command")

    # default / start
    start_parser = subparsers.add_parser("start", help="Start applications (default)")
    start_parser.add_argument("target", nargs="?", default="all", choices=["all", "omniburn", "ledger", "both"], help="Target application(s)")
    start_parser.add_argument("--open", action="store_true", default=None, help="Open in default web browser")
    start_parser.add_argument("--no-open", action="store_true", help="Do not open browser")

    # status
    subparsers.add_parser("status", help="Check status of both applications")

    # stop
    stop_parser = subparsers.add_parser("stop", help="Stop applications")
    stop_parser.add_argument("target", nargs="?", default="all", choices=["all", "omniburn", "ledger", "both"], help="Target application(s) to stop")

    # restart
    restart_parser = subparsers.add_parser("restart", help="Restart applications")
    restart_parser.add_argument("target", nargs="?", default="all", choices=["all", "omniburn", "ledger", "both"], help="Target application(s) to restart")
    restart_parser.add_argument("--open", action="store_true", default=None, help="Open in web browser after restart")
    restart_parser.add_argument("--no-open", action="store_true", help="Do not open browser")

    # logs
    log_parser = subparsers.add_parser("logs", help="Tail application logs")
    log_parser.add_argument("target", choices=["omniburn", "ledger"], help="Application log to view")

    # Determine command if invoked via aliases
    prog = os.path.basename(sys.argv[0])
    argv = sys.argv[1:]
    
    if "omniburn" in prog:
        argv = ["start", "omniburn"] + argv
    elif "ledger" in prog:
        argv = ["start", "ledger"] + argv
    elif argv and argv[0] in ("all", "omniburn", "ledger", "both"):
        argv.insert(0, "start")
    elif not argv or argv[0] not in ("start", "status", "stop", "restart", "logs", "-h", "--help"):
        argv.insert(0, "start")

    args = parser.parse_args(argv)

    if args.command == "status":
        cmd_status()
        return

    if args.command == "logs":
        log_file = OMNIBURN_LOG if args.target == "omniburn" else LEDGER_LOG
        if os.path.exists(log_file):
            os.execvp("tail", ["tail", "-f", "-n", "50", log_file])
        else:
            print(f"Log file not found: {log_file}")
        return

    if args.command == "stop":
        print("\nStopping AI Burn Tracker applications...")
        target = args.target
        if target in ("all", "both", "omniburn"):
            stop_process("OmniBurn", OMNIBURN_PORT, OMNIBURN_PID_FILE)
        if target in ("all", "both", "ledger"):
            stop_process("Burn Ledger", LEDGER_PORT, LEDGER_PID_FILE)
        print("Done.\n")
        return

    if args.command == "restart":
        target = args.target
        print(f"\nRestarting {target}...")
        if target in ("all", "both", "omniburn"):
            stop_process("OmniBurn", OMNIBURN_PORT, OMNIBURN_PID_FILE)
            start_omniburn()
        if target in ("all", "both", "ledger"):
            stop_process("Burn Ledger", LEDGER_PORT, LEDGER_PID_FILE)
            start_burn_ledger()
        if args.open:
            if target in ("all", "both", "omniburn"):
                open_browser(OMNIBURN_URL)
            if target in ("all", "both", "ledger"):
                open_browser(LEDGER_URL)
        print("Done.\n")
        return

    # Default: start
    target = getattr(args, "target", "all")
    print(f"\n==========================================================================")
    print(f"          STARTING AI BURN RATE TRACKER SUITE ({target.upper()})         ")
    print(f"==========================================================================")

    should_open = False
    if getattr(args, "no_open", False):
        should_open = False
    elif getattr(args, "open", False):
        should_open = True
    elif sys.stdout.isatty() and os.environ.get("DISPLAY"):
        should_open = True

    if target in ("all", "both", "omniburn"):
        ok = start_omniburn()
        if ok and should_open:
            open_browser(OMNIBURN_URL)

    if target in ("all", "both", "ledger"):
        ok = start_burn_ledger()
        if ok and should_open:
            open_browser(LEDGER_URL)

    print("==========================================================================")
    if target in ("all", "both", "omniburn"):
        print(f"  • OmniBurn [Built by AGY]:      {OMNIBURN_URL}")
    if target in ("all", "both", "ledger"):
        print(f"  • Burn Ledger [Built by Codex]: {LEDGER_URL}")
    print("==========================================================================\n")


if __name__ == "__main__":
    main()
