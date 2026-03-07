import subprocess
import time
import os
import sys
import webview
from typing import Optional

def main() -> None:
    print("[*] Starting MHDDoS Professional API Server v1.0.1...")
    # Start the FastAPI server asynchronously relative to this script
    server_process: Optional[subprocess.Popen] = None
    try:
        server_process = subprocess.Popen([sys.executable, "api.py"])
        
        # Wait a moment for the server to bind to the port
        time.sleep(1.5)
        
        url: str = "http://127.0.0.1:8000"
        print(f"[*] Launching Desktop Interface to {url}...")
        
        # Create the pywebview window
        webview.create_window(
            title="MHDDoS-GUI v1.0.1", 
            url=url, 
            width=1200, 
            height=800, 
            resizable=True,
            background_color='#111827' # Tailwind gray-900 to match the dark theme
        )
        
        # Start the webview application. This blocks until the window is closed.
        webview.start(private_mode=False)
        
        # When the window is closed, terminate the background server
        print("[*] Shutting down server...")
        if server_process:
            server_process.terminate()
            server_process.wait()
            
    except Exception as e:
        print(f"[!] Critical Error: {e}")
        if server_process:
            server_process.terminate()

if __name__ == "__main__":
    main()
