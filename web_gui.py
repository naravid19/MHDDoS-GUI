import subprocess
import webbrowser
import time
import os
import sys
from typing import Optional

def main() -> None:
    print("[*] Starting MHDDoS Professional Web Server v1.0.1...")
    # Start the FastAPI server as a subprocess
    server_process: Optional[subprocess.Popen] = None
    try:
        server_process = subprocess.Popen([sys.executable, "api.py"])
        
        # Wait a moment for the server to start
        time.sleep(1.5)
        
        # Open the default web browser to the server URL
        url: str = "http://127.0.0.1:8000"
        print(f"[*] Opening {url} in your web browser...")
        webbrowser.open(url)
        
        # Keep the main process alive while the server runs
        server_process.wait()
    except KeyboardInterrupt:
        print("\n[*] Stopping server...")
        if server_process:
            server_process.terminate()
            server_process.wait()
    except Exception as e:
        print(f"[!] Critical Error: {e}")
        if server_process:
            server_process.terminate()

if __name__ == "__main__":
    main()
