import os
import subprocess
import sys
import time
import webbrowser
import argparse
from socket import AF_INET, SOCK_STREAM, socket
from typing import Optional, Tuple

import requests

API_URL = "http://127.0.0.1:8000"
HEALTH_ENDPOINT = f"{API_URL}/api/health"

def get_process_on_port(port: int) -> Tuple[Optional[int], Optional[str]]:
    """Identifies the PID and Name of the process using the specified port on Windows."""
    try:
        # Get PID using netstat
        output = subprocess.check_output(f"netstat -ano | findstr LISTENING | findstr :{port}", shell=True).decode()
        for line in output.strip().split('\n'):
            parts = line.split()
            if parts and parts[1].endswith(f":{port}"):
                pid = int(parts[-1])
                # Get Process Name using tasklist
                task_output = subprocess.check_output(f"tasklist /FI \"PID eq {pid}\" /NH", shell=True).decode()
                name = task_output.split()[0] if task_output.strip() else "Unknown"
                return pid, name
    except Exception:
        pass
    return None, None

def is_api_running() -> Tuple[bool, bool]:
    """
    Checks if something is already listening on port 8000.
    Returns (is_busy, is_our_api)
    """
    with socket(AF_INET, SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', 8000)) == 0:
            try:
                response = requests.get(HEALTH_ENDPOINT, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "online" and "version" in data:
                        return True, True  # It is definitely our API
            except Exception:
                pass
            return True, False  # Port is busy but not by a responsive MHDDoS API
    return False, False

def kill_process(pid: int):
    """Kills a process and its children."""
    try:
        print(f"[*] Terminating conflicting process (PID: {pid})...")
        subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[!] Failed to kill process: {e}")

def wait_for_api(timeout: float = 10.0) -> bool:
    """Blocks until the API is ready or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        busy, ours = is_api_running()
        if busy and ours:
            return True
        time.sleep(0.5)
    return False

def main() -> None:
    parser = argparse.ArgumentParser(description="MHDDoS Professional Web Launcher")
    parser.add_argument("--force", action="store_true", help="Force restart the API server by killing any process on port 8000")
    args = parser.parse_args()

    print("[*] Initializing MHDDoS Professional Web Launcher v1.2.1...")
    
    # 1. Handle Conflict
    busy, ours = is_api_running()
    
    if args.force and busy:
        pid, name = get_process_on_port(8000)
        if pid:
            kill_process(pid)
            time.sleep(1)
            busy, ours = is_api_running()

    if busy:
        if ours:
            print("[*] Tactical API Server already active. Redirecting to existing instance...")
            webbrowser.open(API_URL)
            return
        else:
            pid, name = get_process_on_port(8000)
            print(f"[!] Port Conflict: Port 8000 is occupied by '{name}' (PID: {pid}).")
            print("[!] Please close that application or run with --force to terminate it.")
            return

    # 2. Prepare paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_path = os.path.join(base_dir, "api.py")
    
    # 3. Launch server process
    server_process: Optional[subprocess.Popen[bytes]] = None
    try:
        print("[*] Starting background API engine...")
        # Use CREATE_NEW_PROCESS_GROUP to ensure we can manage it
        server_process = subprocess.Popen(
            [sys.executable, api_path], 
            cwd=base_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 4. Wait for readiness via health check
        print("[*] Synchronizing with tactical engine...", end="", flush=True)
        if wait_for_api(timeout=30.0):
            print(" SUCCESS.")
            print(f"[*] Opening {API_URL} in your web browser...")
            webbrowser.open(API_URL)
            # Keep the main process alive
            server_process.wait()
        else:
            print(" FAILED.")
            print("[!] Critical Error: Tactical API server failed to start within timeout.")
            if server_process:
                server_process.terminate()

    except KeyboardInterrupt:
        print("\n[*] Stopping launcher...")
        if server_process:
            server_process.terminate()
            server_process.wait()
    except Exception as e:
        print(f"\n[!] Critical Launcher Error: {e}")
        if server_process:
            server_process.terminate()

if __name__ == "__main__":
    main()
