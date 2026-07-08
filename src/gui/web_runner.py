import os
import subprocess
import sys
import time
import webbrowser
import argparse
import threading
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, socket
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def stream_output(pipe):
    """Reads from a pipe and prints to stdout line by line."""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                print(line.strip(), flush=True)
    except Exception:
        pass

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

def is_api_running_on_port(port: int) -> Tuple[bool, bool]:
    """
    Checks if something is already listening on the specified port.
    Returns (is_busy, is_our_api)
    """
    health_url = f"http://127.0.0.1:{port}/api/health"
    with socket(AF_INET, SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) == 0:
            try:
                response = requests.get(health_url, timeout=2)
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

def wait_for_api_on_port(port: int, timeout: float = 10.0) -> bool:
    """Blocks until the API is ready on specified port or timeout is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        busy, ours = is_api_running_on_port(port)
        if busy and ours:
            return True
        time.sleep(0.5)
    return False

def start_redis_backend():
    """Checks and starts the portable Redis server if not running."""
    try:
        # Check if already running
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq redis-server.exe" /NH', shell=True).decode()
        if "redis-server.exe" in output:
            print("[*] Redis Backend: ACTIVE")
            return

        # Attempt to start
        redis_path = Path(__file__).resolve().parent.parent.parent / "bin" / "redis" / "redis-server.exe"
        if redis_path.exists():
            print("[*] Redis Backend: STARTING...")
            # Use CREATE_NO_WINDOW (0x08000000) or just shell=False to run in background
            subprocess.Popen(
                [str(redis_path)],
                cwd=str(redis_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000 if sys.platform == "win32" else 0
            )
            time.sleep(1) # Let it bind to port 6379
        else:
            print("[!] Redis Backend: NOT FOUND (Falling back to In-Memory)")
    except Exception as e:
        print(f"[!] Redis Management Error: {e}")

def is_port_listening(port: int) -> bool:
    """Checks if a port is open and listening locally."""
    with socket(AF_INET, SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_flaresolverr_backend():
    """Checks and starts portable FlareSolverr backend if port 8191 is inactive."""
    try:
        if is_port_listening(8191):
            print("[*] FlareSolverr: ACTIVE (Listening on port 8191)")
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
            subprocess.Popen(
                [str(fs_path)],
                cwd=str(fs_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000 if sys.platform == "win32" else 0
            )
            time.sleep(1.5)  # Give it a moment to initialize
            if is_port_listening(8191):
                print("[*] FlareSolverr: ONLINE (Port 8191)")
            else:
                print("[!] FlareSolverr: FAILED TO BIND to port 8191")
        else:
            print("[*] FlareSolverr: NOT FOUND in bin/flaresolverr/ (Optional for bypass methods)")
    except Exception as e:
        print(f"[!] FlareSolverr Management Error: {e}")

def find_available_port(start_port: int, max_attempts: int = 100) -> int:
    """Finds the first available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket(AF_INET, SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts}")

def main() -> None:
    parser = argparse.ArgumentParser(description="MHDDoS Professional Web Launcher")
    parser.add_argument("--force", action="store_true", help="Force restart the API server by killing any process on port 8000")
    parser.add_argument("--port", type=int, help="Specify the port to run the API server on (default: auto-find starting from 8000)")
    args = parser.parse_args()

    print("[*] Initializing MHDDoS Professional Web Launcher v1.6.4...")
    
    # 0. System Dependencies
    start_redis_backend()
    start_flaresolverr_backend()
    
    # 1. Port Selection & Conflict Handling
    # Priority: 1. CLI --port, 2. .env MHDDoS_PORT, 3. Default 8000
    env_port = os.getenv("MHDDoS_PORT")
    target_port = args.port or (int(env_port) if env_port and env_port.isdigit() else 8000)
    actual_port = target_port
    
    busy, ours = is_api_running_on_port(target_port)
    
    if args.force and busy:
        pid, name = get_process_on_port(target_port)
        if pid:
            kill_process(pid)
            time.sleep(1)
            busy, ours = is_api_running_on_port(target_port)

    if busy:
        if ours:
            print(f"[*] Tactical API Server already active on port {target_port}. Redirecting...")
            webbrowser.open(f"http://127.0.0.1:{target_port}")
            return
        elif args.port:
            pid, name = get_process_on_port(target_port)
            print(f"[!] Port Conflict: Port {target_port} is occupied by '{name}' (PID: {pid}).")
            print("[!] Cannot proceed with manual port override.")
            return
        else:
            # Auto-find mode: Port is busy, look for next one
            print(f"[*] Port {target_port} is busy. Searching for available tactical port...")
            actual_port = find_available_port(target_port + 1)
            print(f"[*] Discovered available port: {actual_port}")

    api_url = f"http://127.0.0.1:{actual_port}"
    
    # 2. Prepare paths
    try:
        from src.core.paths import get_project_root
    except ImportError:
        from pathlib import Path
        sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
        from src.core.paths import get_project_root
        
    base_dir = get_project_root()
    
    # 3. Launch server process
    server_process: Optional[subprocess.Popen] = None
    try:
        print(f"[*] Starting background API engine on port {actual_port}...")
        # Pass port via environment variable
        env = os.environ.copy()
        env["MHDDoS_PORT"] = str(actual_port)
        
        server_process = subprocess.Popen(
            [sys.executable, "-u", "-m", "src.app.main"], 
            cwd=str(base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            errors='replace',
            env=env
        )
        
        # Start output streaming thread
        threading.Thread(target=stream_output, args=(server_process.stdout,), daemon=True).start()
        
        # 4. Wait for readiness via health check
        print("[*] Synchronizing with tactical engine...")
        if wait_for_api_on_port(actual_port, timeout=30.0):
            print("[*] Engine Synchronization: SUCCESS.")
            print(f"[*] Opening {api_url} in your web browser...")
            webbrowser.open(api_url)
            server_process.wait()
        else:
            print("[!] Engine Synchronization: FAILED.")
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
