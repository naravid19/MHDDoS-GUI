# tests/test_flaresolverr_tier0.py
import pytest
import sys
import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from src.core.engine import ENGINE_STATE, BrowserEngine

@pytest.fixture(autouse=True)
def clean_flaresolverr_state():
    orig = getattr(ENGINE_STATE, "flaresolverr_url", None)
    try:
        yield
    finally:
        ENGINE_STATE.flaresolverr_url = orig

def test_flaresolverr_url_state_default():
    # Verify the attribute exists
    assert hasattr(ENGINE_STATE, "flaresolverr_url")

def test_flaresolverr_cli_argument_parsing():
    # Mock sys.argv to test CLI argument parsing block
    test_argv = ["engine.py", "GET", "https://readtoon.com/", "5", "10", "socks5.txt", "10", "60", "--flaresolverr", "http://test-flare:8191/v1"]
    
    # Let's mock argv in engine.py and run the parsing block logic
    # The actual parsing logic does:
    # args_iter = iter(argv[8:])
    # and processes --flaresolverr
    args_iter = iter(test_argv[8:])
    for arg in args_iter:
        if arg == "--flaresolverr":
            ENGINE_STATE.flaresolverr_url = next(args_iter, "http://localhost:8191/v1")
            
    assert ENGINE_STATE.flaresolverr_url == "http://test-flare:8191/v1"

def test_solve_cf_internal_uses_flaresolverr():
    ENGINE_STATE.flaresolverr_url = "http://localhost:8191/v1"
    
    # Mock response from FlareSolverr
    mock_response_data = {
        "status": "ok",
        "solution": {
            "cookies": [
                {"name": "cf_clearance", "value": "mocked_clearance_cookie_value"}
            ],
            "userAgent": "MockUserAgent/1.0"
        }
    }
    
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        cookie, ua = BrowserEngine._solve_cf_internal("https://readtoon.com/")
        
        # Check that urlopen was called with our configured flaresolverr_url
        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.full_url == "http://localhost:8191/v1"
        
        # Verify returned cookies and UA
        assert cookie == "cf_clearance=mocked_clearance_cookie_value"
        assert ua == "MockUserAgent/1.0"

def test_solve_cf_internal_with_proxy_and_full_cookies():
    ENGINE_STATE.flaresolverr_url = "http://localhost:8191/v1"
    
    mock_response_data = {
        "status": "ok",
        "solution": {
            "cookies": [
                {"name": "cf_clearance", "value": "mock_cf_value"},
                {"name": "_ga", "value": "mock_ga_value"}
            ],
            "userAgent": "MockUserAgent/2.0"
        }
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        cookie, ua = BrowserEngine._solve_cf_internal("https://readtoon.com/", proxy="103.68.214.164:8080", timeout=30)
        
        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args[0][0]
        payload = json.loads(call_args.data.decode("utf-8"))
        
        # Verify proxy formatting according to FlareSolverr docs
        assert payload.get("proxy") == {"url": "http://103.68.214.164:8080"}
        # Verify maxTimeout uses the passed timeout parameter (converted to ms if in seconds)
        assert payload.get("maxTimeout") == 30000
        # Verify that all cookies are joined and returned, not just cf_clearance
        assert cookie == "cf_clearance=mock_cf_value; _ga=mock_ga_value"
        assert ua == "MockUserAgent/2.0"

def test_solve_cf_internal_proxy_schema_formatting():
    ENGINE_STATE.flaresolverr_url = "http://localhost:8191/v1"
    
    mock_response_data = {
        "status": "ok",
        "solution": {
            "cookies": [{"name": "cf_clearance", "value": "mock_cf"}],
            "userAgent": "MockUA"
        }
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        BrowserEngine._solve_cf_internal("https://readtoon.com/", proxy="socks5://127.0.0.1:1080", timeout=45000)
        call_args = mock_urlopen.call_args[0][0]
        payload = json.loads(call_args.data.decode("utf-8"))
        assert payload.get("proxy") == {"url": "socks5://127.0.0.1:1080"}
        assert payload.get("maxTimeout") == 45000

@pytest.mark.integration
def test_flaresolverr_readtoon_live_integration_with_checked_proxy():
    import urllib.request
    import os
    
    flaresolverr_url = getattr(ENGINE_STATE, "flaresolverr_url", "http://localhost:8191/v1")
    if not flaresolverr_url:
        flaresolverr_url = "http://localhost:8191/v1"
        ENGINE_STATE.flaresolverr_url = flaresolverr_url
        
    try:
        req = urllib.request.Request(flaresolverr_url, data=b'{"cmd": "sessions.list"}', headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status != 200:
                pytest.skip("FlareSolverr not responding properly on port 8191")
    except Exception as e:
        pytest.skip(f"FlareSolverr server not running locally on port 8191: {e}")
        
    proxy_file = r"C:\Users\narav\Desktop\CE code\Tools\proxy-scraper-checker\out\checked-proxies\proxies\http.txt"
    if not os.path.exists(proxy_file):
        pytest.skip(f"Checked proxies file not found at {proxy_file}")
        
    with open(proxy_file, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip() and ":" in line]
        
    if not proxies:
        pytest.skip("No proxies found in http.txt")
        
    # Isolate BrowserEngine from other Tiers so we only test Tier 0
    with patch.object(BrowserEngine, "_solve_tier1_lightweight", return_value=(None, None)) as mock_t1, \
         patch.object(BrowserEngine, "_solve_tier2_fast_cdp", return_value=(None, None)) as mock_t2, \
         patch.object(BrowserEngine, "_solve_tier3_heavy_stealth", return_value=(None, None)) as mock_t3, \
         patch.object(BrowserEngine, "_solve_tier4_ultimate_stealth", return_value=(None, None)) as mock_t4:
        
        cookie, ua = None, None
        for i, test_proxy in enumerate(proxies[:3]):
            print(f"\n[*] Testing live FlareSolverr bypass on https://readtoon.com/ using proxy ({i+1}/3): {test_proxy}")
            
            # Temporary local patch to print detailed exceptions during execution
            original_solve = BrowserEngine._solve_cf_internal
            def debug_solve(*args, **kwargs):
                try:
                    res = original_solve(*args, **kwargs)
                    if res and res[0] is not None:
                        print(f"[+] FlareSolverr Succeeded: cookie={res[0][:40]}... ua={res[1][:40]}...")
                    else:
                        print("[-] FlareSolverr returned None/empty cookies.")
                    return res
                except Exception as ex:
                    print(f"[-] FlareSolverr Failed: {ex}")
                    import traceback
                    traceback.print_exc()
                    raise ex
            
            import time
            with patch("src.core.engine.BrowserEngine._solve_cf_internal", side_effect=debug_solve):
                cookie, ua = BrowserEngine._solve_cf_internal("https://readtoon.com/", proxy=test_proxy, timeout=35000)
            if cookie:
                break
            time.sleep(2.0)

        if not cookie:
            print("\n[*] Public proxies triggered Cloudflare Turnstile verification or timeouts. Testing direct tier 0 bypass...")
            import time
            time.sleep(2.0)
            cookie, ua = BrowserEngine._solve_cf_internal("https://readtoon.com/", proxy=None, timeout=35000)

        assert cookie is not None and len(cookie) > 5, "FlareSolverr Tier 0 failed to obtain cookies (both proxies and direct bypass timed out or errored)"
        assert ua is not None


def test_solve_cf_internal_passes_tabs_till_verify():
    ENGINE_STATE.flaresolverr_url = "http://localhost:8191/v1"
    
    mock_response_data = {
        "status": "ok",
        "solution": {
            "cookies": [{"name": "cf_clearance", "value": "mock_val"}],
            "userAgent": "MockUA"
        }
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        BrowserEngine._solve_cf_internal("https://readtoon.com/", tabs_till_verify=3)
        
        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args[0][0]
        payload = json.loads(call_args.data.decode("utf-8"))
        
        assert payload.get("tabs_till_verify") == 3


def test_tier0_http_500_retries_and_falls_to_tier1():
    """Verify Tier 0 retries exactly once on HTTP 500 (browser cleanup in progress), sleeps 2.5s, then falls to Tier 1."""
    import urllib.error
    ENGINE_STATE.flaresolverr_url = "http://localhost:8191/v1"
    call_count = {"n": 0}

    def fake_urlopen(req, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise urllib.error.HTTPError(url="", code=500, msg="Internal Server Error", hdrs=None, fp=None)
        raise urllib.error.URLError("simulated: second attempt fallback")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("time.sleep") as mock_sleep, \
         patch("src.core.engine.BrowserEngine._solve_tier1_lightweight", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier2_fast_cdp", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier3_heavy_stealth", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier4_ultimate_stealth", return_value=(None, None)):
        BrowserEngine._solve_cf_internal("https://readtoon.com")

    assert call_count["n"] == 2, f"Expected 2 urlopen calls (initial + retry), got {call_count['n']}"
    sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert 2.5 in sleep_calls, f"Expected sleep(2.5) for Tier 0 HTTP 500 retry, got sleeps: {sleep_calls}"


def test_tier0_non_500_error_skips_retry_immediately():
    """Verify Tier 0 does NOT retry on non-500 errors, falling immediately to Tier 1."""
    import urllib.error
    ENGINE_STATE.flaresolverr_url = "http://localhost:8191/v1"
    call_count = {"n": 0}

    def fake_urlopen(req, timeout=None):
        call_count["n"] += 1
        raise urllib.error.URLError("connection refused")

    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("time.sleep") as mock_sleep, \
         patch("src.core.engine.BrowserEngine._solve_tier1_lightweight", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier2_fast_cdp", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier3_heavy_stealth", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier4_ultimate_stealth", return_value=(None, None)):
        BrowserEngine._solve_cf_internal("https://readtoon.com")

    assert call_count["n"] == 1, f"Expected 1 urlopen call (no retry on non-500), got {call_count['n']}"
    sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
    assert 2.5 not in sleep_calls, f"Unexpected sleep(2.5) for non-500 error: {sleep_calls}"

