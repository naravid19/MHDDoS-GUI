import asyncio
import sys
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("MethodTester")

# Mock missing imports gracefully without overwriting globally installed libraries
def _mock_if_missing(mod_name):
    # Unconditionally mock packages that trigger network checks or setup operations on import
    if mod_name in {"hrequests", "zendriver", "cloudflare_bypass_for_scraping"}:
        sys.modules[mod_name] = MagicMock()
        return
    try:
        __import__(mod_name)
    except ImportError:
        sys.modules[mod_name] = MagicMock()

for _m in [
    "PyRoxy", "certifi", "cloudscraper", "dns", "dns.resolver", "icmplib", "impacket",
    "impacket.ImpactPacket", "psutil", "yarl", "curl_cffi", "curl_cffi.requests",
    "playwright", "playwright.sync_api", "playwright_stealth", "nodriver",
    "undetected_chromedriver", "botasaurus", "patchright", "DrissionPage",
    "zendriver", "hrequests", "cloudflare_bypass_for_scraping", "httpx"
]:
    _mock_if_missing(_m)

if isinstance(sys.modules.get("PyRoxy"), MagicMock):
    pyroxy_mock = sys.modules["PyRoxy"]
    tools_mock = MagicMock()
    tools_mock.Random.rand_ipv4.return_value = "1.1.1.1"
    pyroxy_mock.Tools = tools_mock

import ssl
if not hasattr(ssl, "create_default_context") or isinstance(ssl.create_default_context, MagicMock):
    ssl.create_default_context = MagicMock()

sys.path.append(str(Path(__file__).parent))
from src.core.engine import HttpFlood, BrowserEngine

async def test_new_methods():
    target_url = "https://google.com/"
    domain = "example-target.com"
    mock_url = MagicMock()
    mock_url.human_repr.return_value = target_url
    mock_url.__str__.return_value = target_url
    
    mock_proxy_pool = MagicMock()
    flood = HttpFlood(0, mock_url, domain, proxy_pool=mock_proxy_pool)
    
    with patch.object(BrowserEngine, 'solve_cf', new_callable=AsyncMock) as m_solve:
        m_solve.return_value = ("cf_clearance=success", "ua_test")
        
        logger.info("Testing BROWSER method...")
        await asyncio.wait_for(flood.BROWSER(), timeout=10)
        logger.info("[+] BROWSER: SUCCESS")
        
        logger.info("Testing HYBRID method...")
        # Force BROWSER path
        with patch("random.random", return_value=0.1):
            await asyncio.wait_for(flood.HYBRID(), timeout=10)
            logger.info("[+] HYBRID (Browser Path): SUCCESS")
            
        # Force IMPERSONATE path (mocking curl_cffi presence)
        with patch("random.random", return_value=0.9), \
             patch("src.core.engine.CURL_CFFI_INSTALLED", True), \
             patch.object(flood, 'IMPERSONATE', new_callable=AsyncMock) as m_imp:
            await asyncio.wait_for(flood.HYBRID(), timeout=10)
            m_imp.assert_awaited_once()
            logger.info("[+] HYBRID (Impersonate Path): SUCCESS")

if __name__ == "__main__":
    asyncio.run(test_new_methods())
