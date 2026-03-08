import os
import subprocess
import sys
import time
import webbrowser
from socket import AF_INET, SOCK_STREAM, socket
from typing import Optional

import requests

API_URL = "http://127.0.0.1:8000"
HEALTH_ENDPOINT = f"{API_URL}/api/health"

def is_api_running() -> bool:
    """Checks if something is already listening on port 8000."""
    with socket(AF_INET, SOCK_STREAM) as s:
        # If connect_ex returns 0, the port is open (busy)
        if s.connect_ex(('127.0.0.1', 8000)) == 0:
            # It's busy. Try to verify if it's OUR API
            try:
                response = requests.get(HEALTH_ENDPOINT, timeout=1)
                if response.status_code == 200:
                    return True  # It is our API (v1.0.8+)
            except requests.RequestException:
                pass
            return True  # It's busy, likely an old version or another app
    return False

def wait_for_api(timeout: float = 10.0) -> bool:
    """Blocks until the API is ready or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_api_running():
            return True
        time.sleep(0.5)
    return False

def main() -> None:
    print("[*] Initializing MHDDoS Professional Web Launcher v1.1.2...")
    
    # 1. Check if server is already active
    if is_api_running():
        print("[*] Tactical API Server already active. Redirecting to existing instance...")
        webbrowser.open(API_URL)
        return

    # 2. Prepare paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_path = os.path.join(base_dir, "api.py")
    
    # 3. Launch server process
    server_process: Optional[subprocess.Popen[bytes]] = None
    try:
        print("[*] Starting background API engine...")
        server_process = subprocess.Popen(
            [sys.executable, api_path], 
            cwd=base_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 4. Wait for readiness via health check
        print("[*] Synchronizing with tactical engine...", end="", flush=True)
        if wait_for_api():
            print(" SUCCESS.")
            print(f"[*] Opening {API_URL} in your web browser...")
            webbrowser.open(API_URL)
            # Keep the main process alive
            server_process.wait()
        else:
            print(" FAILED.")
            print("[!] Critical Error: Tactical API server failed to start within timeout.")
            print("[!] Possible cause: Port 8000 might be occupied by another application.")
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
