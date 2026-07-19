from unittest.mock import MagicMock, patch, AsyncMock
import sys
from pathlib import Path
import os

# Mock missing imports gracefully without overwriting globally installed libraries
def _mock_if_missing(mod_name):
    try:
        __import__(mod_name)
    except ImportError:
        sys.modules[mod_name] = MagicMock()

for _m in [
    "PyRoxy", "cloudscraper", "dns", "dns.resolver", "icmplib", "impacket",
    "impacket.ImpactPacket", "psutil", "yarl", "curl_cffi", "curl_cffi.requests",
    "playwright", "playwright.sync_api", "playwright_stealth", "nodriver"
]:
    _mock_if_missing(_m)

if isinstance(sys.modules.get("PyRoxy"), MagicMock):
    pyroxy_mock = sys.modules["PyRoxy"]
    tools_mock = MagicMock()
    tools_mock.Random.rand_ipv4.return_value = "1.1.1.1"
    pyroxy_mock.Tools = tools_mock

import asyncio
import pytest
import time

# Add project root to path to from src.core import engine as start.py
sys.path.append(str(Path(__file__).parent))

from src.core.engine import BrowserEngine, HttpFlood, URL



@pytest.fixture
def mock_solvers():
    """Fixture to mock all solver methods in BrowserEngine."""
    solvers = [
        '_solve_cf_internal_async'
    ]

    mocks = {}
    patches = []
    for s in solvers:
        try:
            # _solve_cf_internal_async might be sync or async. In start.py it seems sync if to_thread is used
            # Let's use MagicMock. If it returns a tuple directly, it's sync.
            p = patch.object(BrowserEngine, s, new_callable=AsyncMock)
            mocks[s] = p.start()
            mocks[s].return_value = (None, None)
            patches.append(p)
        except AttributeError:
            pass

    yield mocks
    for p in patches:
        p.stop()

@pytest.mark.asyncio
async def test_cfbuam_integration():
    """Test HttpFlood.CFBUAM correctly calls BrowserEngine."""
    target_url = MagicMock()
    target_url.human_repr.return_value = "https://target.com"
    target_url.host = "target.com"
    target_url.port = 443
    target_url.scheme = "https"
    target_url.path = "/"
    target_url.raw_path_qs = "/"
    target_url.authority = "target.com"
    target_url.raw_host = "target.com"
    target_url.query_string = ""

    flood = HttpFlood(0, target_url, "target.com")

    # Force initialize bytes attributes that might be MagicMocks due to heavy mocking
    flood._method_bytes = b"GET"
    flood._path_bytes = b"/"
    flood._host_bytes = b"target.com"
    flood._conn_type_bytes = b"keep-alive"
    flood._fp_headers_bytes = b"X-Test: 1\r\n"
    flood._referers = ["https://google.com/"]

    with patch.object(BrowserEngine, 'solve_cf', new_callable=AsyncMock) as m_solve:
        m_solve.return_value = ("cf_clearance=synced", "ua_synced")

        # Trigger solve in CFBUAM
        HttpFlood._cfbuam_cookie = None
        HttpFlood._cfbuam_expiry = 0

        with patch("src.core.engine.CURL_CFFI_INSTALLED", False):
            await flood.CFBUAM()

            assert HttpFlood._cfbuam_cookie == "cf_clearance=synced"
            assert HttpFlood._cfbuam_ua == "ua_synced"
            m_solve.assert_called_once()

@pytest.mark.parametrize("url,expected", [
    ("example.com", "example.com"),
    ("http://example.com", "http://example.com"),
    ("https://example.com", "https://example.com"),
])
@pytest.mark.asyncio
async def test_url_normalization(url, expected, mock_solvers):
    """Test URL normalization in BrowserEngine."""
    await BrowserEngine.solve_cf(url)
    # Check first solver called with normalized URL
    mock_solvers['_solve_cf_internal_async'].assert_called_with(expected, None, None, 45000)

@pytest.mark.asyncio
async def test_browser_method_integration():
    """Test HttpFlood.BROWSER correctly calls BrowserEngine."""
    target_url = MagicMock()
    target_url.human_repr.return_value = "https://target.com"
    target_url.__str__.return_value = "https://target.com"

    flood = HttpFlood(0, target_url, "target.com")

    with patch.object(BrowserEngine, 'solve_cf', new_callable=AsyncMock) as m_solve:
        m_solve.return_value = ("cf_clearance=browser_test", "ua_browser")
        
        HttpFlood._cfbuam_cookie = None
        HttpFlood._cfbuam_expiry = 0
        HttpFlood._last_solve_attempt = 0

        await flood.BROWSER()

        m_solve.assert_called_once()
        assert HttpFlood._cfbuam_cookie == "cf_clearance=browser_test"

@pytest.mark.asyncio
async def test_hybrid_method_integration():
    """Test HttpFlood.HYBRID logic."""
    target_url = MagicMock()
    target_url.human_repr.return_value = "https://target.com"

    flood = HttpFlood(0, target_url, "target.com")

    with patch.object(flood, 'BROWSER', new_callable=AsyncMock) as m_browser, \
         patch.object(flood, 'IMPERSONATE', new_callable=AsyncMock) as m_impersonate:

        # Override values dynamically on class since HYBRID reads HttpFlood._waf_blocks
        HttpFlood._waf_blocks = 100
        HttpFlood._sample_count = 100

        await flood.HYBRID()
        m_browser.assert_awaited_once()
        m_browser.reset_mock()
        HttpFlood._waf_blocks = 10
        HttpFlood._sample_count = 100

        await flood.HYBRID()
        m_impersonate.assert_awaited_once()
if __name__ == "__main__":
    # Manual run logic
    print("Running Advanced Bypass Engine Tests...")
    
    async def run_all():
        # Setup mocks manually for direct execution
        solvers = [
            '_solve_cloudscraper', '_solve_hrequests', '_solve_curl_cffi',
            '_solve_nodriver', '_solve_drissionpage', '_solve_playwright',
            '_solve_uc_selenium', '_solve_botasaurus', '_solve_patchright',
            '_solve_zendriver', '_solve_flaresolverr', '_solve_cfb_scraping',
            '_solve_cloakbrowser'
        ]
        mocks = {}
        patches = []
        for s in solvers:
            p = patch.object(BrowserEngine, s, new_callable=AsyncMock)
            mocks[s] = p.start()
            mocks[s].return_value = (None, None)
            patches.append(p)
            
        try:
            print("[*] Testing Adaptive Scoring...")
            await test_adaptive_scoring(mocks)
            print("[+] Adaptive Scoring: PASSED")
            
            print("[*] Testing URL Normalization...")
            await test_url_normalization("example.com", "https://example.com", mocks)
            print("[+] URL Normalization: PASSED")
            
            print("[*] Testing CFBUAM Integration...")
            await test_cfbuam_integration()
            print("[+] CFBUAM Integration: PASSED")
            
        finally:
            for p in patches: p.stop()

    asyncio.run(run_all())
    print("\nAll advanced logic tests passed!")
