import subprocess
import webbrowser
import time
import os
import sys

def main():
    print("[*] Starting MHDDoS Professional Web Server...")
    # Start the FastAPI server as a subprocess
    server_process = subprocess.Popen([sys.executable, "api.py"])
    
    # Wait a moment for the server to start
    time.sleep(1.5)
    
    # Open the default web browser to the server URL
    url = "http://127.0.0.1:8000"
    print(f"[*] Opening {url} in your web browser...")
    webbrowser.open(url)
    
    try:
        # Keep the main process alive while the server runs
        server_process.wait()
    except KeyboardInterrupt:
        print("\n[*] Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
