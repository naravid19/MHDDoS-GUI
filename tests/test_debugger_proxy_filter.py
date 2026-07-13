# C:\Users\narav\Desktop\CE code\Tools\MHDDoS-GUI\tests\test_debugger_proxy_filter.py
import os
import shutil
import tempfile
from src.core.debugger import BypassDebugger

def test_capture_failure_filters_proxy_network_errors(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    try:
        monkeypatch.setattr(BypassDebugger, "DEBUG_DIR", temp_dir)
        
        # 1. Trigger with SOCKS proxy connection error
        proxy_err = "SOCKSHTTPSConnectionPool(host='readtoon.com', port=443): Max retries exceeded with url: / (Caused by NewConnectionError('<urllib3.contrib.socks.SOCKSHTTPSConnection object>: Failed to establish a new connection: 0x03: Network unreachable'))"
        res1 = BypassDebugger.capture_failure("Tier 1 (Cloudscraper)", "https://readtoon.com", error_msg=proxy_err)
        
        # 2. Verify no timestamped folder was created for the proxy error
        assert res1 is None, f"Expected None for proxy network error, got {res1}"
        folders = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
        assert len(folders) == 0, f"No debug folder should be created for proxy errors, found: {folders}"
        
        # 3. Verify proxy_network_errors.log exists and contains the log entry
        log_file = os.path.join(temp_dir, "proxy_network_errors.log")
        assert os.path.exists(log_file), "proxy_network_errors.log should be created"
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Tier 1 (Cloudscraper)" in content
            assert "0x03: Network unreachable" in content
            
        # 4. Trigger with a real challenge failure (should still create folder)
        res2 = BypassDebugger.capture_failure("Tier 1 (Cloudscraper)", "https://readtoon.com", error_msg="HTTP 403 Challenge detected")
        assert res2 is not None and os.path.isdir(res2), "Real challenge failures must create artifact folder"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
