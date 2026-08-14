import os
import subprocess
import sys
import time
import argparse
from socket import AF_INET, SOCK_STREAM, socket
from typing import Optional

import requests
import webview

from pathlib import Path

API_URL = "http://127.0.0.1:8000"
HEALTH_ENDPOINT = f"{API_URL}/api/health"

def is_port_listening(port: int) -> bool:
    """Checks if a port is open and listening locally."""
    with socket(AF_INET, SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_flaresolverr_backend():
    """Checks and starts portable FlareSolverr backend if target port is inactive."""
    try:
        target_port = int(os.getenv("FLARESOLVERR_PORT", os.getenv("PORT", "8180")))
        if is_port_listening(target_port):
            print(f"[*] FlareSolverr: ACTIVE (Listening on port {target_port})")
            return

        bin_dir = Path(__file__).resolve().parent.parent.parent / "bin"
        candidates = [
            bin_dir / "flaresolverr" / "flaresolverr.exe",
            bin_dir / "flaresolverr.exe",
            bin_dir / "flaresolverr" / "FlareSolverr.exe",
            bin_dir / "FlareSolverr.exe"
        ]

        fs_path = None
        for candidate in candidates:
            if candidate.exists():
                fs_path = candidate
                break

        if fs_path:
            print("[*] FlareSolverr: STARTING...")
            env = os.environ.copy()
            env["PORT"] = str(target_port)
            subprocess.Popen(
                [str(fs_path)],
                cwd=str(fs_path.parent),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000 if sys.platform == "win32" else 0
            )
            # Poll for up to 15s (FlareSolverr boots Chromium internally, takes 5-15s on Windows)
            max_wait = 15.0
            poll_interval = 0.5
            elapsed = 0.0
            while elapsed < max_wait:
                time.sleep(poll_interval)
                elapsed += poll_interval
                if is_port_listening(target_port):
                    print(f"[*] FlareSolverr: ONLINE (Port {target_port}) — ready in {elapsed:.1f}s")
                    return
            print(f"[!] FlareSolverr: FAILED TO BIND to port {target_port} after 15s — will use Tier 1-4 fallback")
        else:
            print("[*] FlareSolverr: NOT FOUND in bin/flaresolverr/ (Optional for bypass methods)")
    except Exception as e:
        print(f"[!] FlareSolverr Management Error: {e}")


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
    parser = argparse.ArgumentParser(description="MHDDoS Professional Desktop Launcher")
    parser.add_argument("--debug", action="store_true", help="Enable developer tools for UI debugging")
    args = parser.parse_args()

    print("[*] Initializing MHDDoS Professional Desktop Launcher v1.6.4...")
    
    # 1. Check if server is already active
    server_process: Optional[subprocess.Popen[bytes]] = None
    if not is_api_running():
        # Auto-start FlareSolverr backend if not already active
        start_flaresolverr_backend()
        
        # 2. Prepare paths
        try:
            from src.core.paths import get_project_root
        except ImportError:
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
            from src.core.paths import get_project_root
            
        base_dir = get_project_root()
        
        # 3. Launch server process
        try:
            print("[*] Starting background API engine...")
            server_process = subprocess.Popen(
                [sys.executable, "-m", "src.app.main"], 
                cwd=str(base_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # 4. Wait for readiness via health check
            print("[*] Synchronizing with tactical engine...", end="", flush=True)
            if not wait_for_api(timeout=30.0):
                print(" FAILED.")
                print("[!] Critical Error: Tactical API server failed to start within timeout.")
                if server_process:
                    server_process.terminate()
                return
            print(" SUCCESS.")
        except Exception as e:
            print(f"\n[!] Critical Launcher Error: {e}")
            return
    else:
        print("[*] Tactical API Server already active. Connecting to existing instance...")

    # 5. Launch UI
    try:
        print(f"[*] Launching Tactical Desktop Interface to {API_URL}...")
        
        # Create the pywebview window
        webview.create_window(
            title="MHDDoS PRO | Tactical Dashboard", 
            url=API_URL, 
            width=1366, 
            height=900, 
            resizable=True,
            background_color='#020617'
        )
        
        # Start the webview application.
        # debug=True allows Right Click -> Inspect Element
        webview.start(debug=args.debug, private_mode=True)
        
        # 6. Cleanup on exit
        if server_process:
            print("[*] Shutting down background server...")
            server_process.terminate()
            server_process.wait()
            
    except Exception as e:
        print(f"[!] UI Error: {e}")
        if server_process:
            server_process.terminate()

if __name__ == "__main__":
    main()
