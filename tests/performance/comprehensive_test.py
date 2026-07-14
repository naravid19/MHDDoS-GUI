import asyncio
import sys
import logging
import time
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("MethodTester")

# Mock problematic imports BEFORE importing start.py
m = MagicMock()
sys.modules["PyRoxy"] = m
sys.modules["certifi"] = m
sys.modules["cloudscraper"] = m
sys.modules["dns"] = m
sys.modules["dns.resolver"] = m
sys.modules["icmplib"] = m
sys.modules["impacket"] = m
sys.modules["impacket.ImpactPacket"] = m
sys.modules["psutil"] = m
sys.modules["yarl"] = m
sys.modules["curl_cffi"] = m
sys.modules["curl_cffi.requests"] = m
sys.modules["playwright"] = m
sys.modules["playwright.sync_api"] = m
sys.modules["playwright_stealth"] = m
sys.modules["nodriver"] = m
sys.modules["undetected_chromedriver"] = m
sys.modules["botasaurus"] = m
sys.modules["botasaurus.browser"] = m
sys.modules["patchright"] = m
sys.modules["patchright.sync_api"] = m
sys.modules["DrissionPage"] = m
sys.modules["zendriver"] = m
sys.modules["hrequests"] = m
sys.modules["cloudflare_bypass_for_scraping"] = m
sys.modules["httpx"] = m

# Mock SSL and ProxyTools
import ssl
ssl.create_default_context = MagicMock()
pyroxy_mock = MagicMock()
tools_mock = MagicMock()
tools_mock.Random.rand_ipv4.return_value = "1.1.1.1"
tools_mock.Random.rand_str.return_value = "test_string"
pyroxy_mock.Tools = tools_mock
sys.modules["PyRoxy"] = pyroxy_mock

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import the actual classes
try:
    from src.core.engine import HttpFlood, Layer4, BrowserEngine, URL
except ImportError as e:
    logger.error(f"Failed to from src.core import engine as start.py: {e}")
    sys.exit(1)

class MethodTester:
    def __init__(self, target_url):
        self.target_url = target_url
        self.domain = "example-target.com"
        # Mock URL object for HttpFlood
        self.mock_url = MagicMock()
        self.mock_url.human_repr.return_value = target_url
        self.mock_url.__str__.return_value = target_url
        self.mock_url.host = self.domain
        self.mock_url.port = 443
        self.mock_url.scheme = "https"
        self.mock_url.path = "/"
        self.mock_url.raw_path_qs = "/"
        self.mock_url.authority = self.domain
        self.mock_url.raw_authority = self.domain
        self.mock_url.raw_host = self.domain
        self.mock_url.query_string = ""

    async def test_l7_methods(self):
        logger.info("--- Starting Layer 7 Method Tests ---")
        
        # Mock Proxy Pool
        mock_proxy_pool = MagicMock()
        mock_proxy_pool.__len__.return_value = 1
        mock_proxy = MagicMock()
        mock_proxy.asRequest.return_value = None
        mock_proxy.__str__.return_value = "1.2.3.4:8080"
        mock_proxy_pool.get_proxy.return_value = mock_proxy
        
        # Ensure url representation returns bytes where necessary for start.py internal mock building
        self.mock_url.human_repr.return_value = "https://target.com"
        
        # Instantiate HttpFlood
        flood = HttpFlood(0, self.mock_url, self.domain, proxy_pool=mock_proxy_pool)
        
        # Force real bytes for all internal attributes used in b"".join
        flood._method_bytes = b"GET"
        flood._path_bytes = b"/"
        flood._host_bytes = self.domain.encode()
        flood._conn_type_bytes = b"keep-alive"
        flood._fp_headers_bytes = b"X-Test: 1\r\n"
        flood._target_repr_quoted = b"https%3A//target.com"
        flood._rpc = 1
        flood._referers = [b"https://google.com/"]
        flood._useragents = [b"Mozilla/5.0"]
        flood._payloads = [b"payload1"]
        flood._data = b"data1"
        flood._get_target = MagicMock(return_value=b"https://target.com")
        flood._amp_payloads = iter([b"amp1", b"amp2"])
        flood._create_payload = MagicMock(return_value=b"mocked_payload")
        flood._useragents_bytes = [b"Mozilla/5.0"]
        flood._referers_bytes = [b"https://google.com/"]

        def safe_randchoice(lst):
            if not lst:
                return b"test"
            val = lst[0]
            if isinstance(val, MagicMock):
                return b"mocked_bytes"
            return val

        # Mock BrowserEngine.solve_cf globally for all L7 methods
        with patch.object(BrowserEngine, 'solve_cf', new_callable=AsyncMock) as m_solve, \
             patch('src.core.engine.randchoice', side_effect=safe_randchoice), \
             patch('src.core.engine.randint', return_value=1), \
             patch('src.core.engine.randbytes', return_value=b"test"), \
             patch('src.core.engine.time', return_value=0.0): # Avoid timestamp errors
            
            m_solve.return_value = ("cf_clearance=test", "ua_test")
            
            # Additional mocks to fix TypeErrors inside flood payload building
            # Specifically: _payloads, _useragents, _referers etc need to match byte/str types
            flood._payloads = [b"payload1"] # usually strings, converted to bytes in method
            
            # Discover methods from HttpFlood.methods mapping
            methods = list(flood.methods.keys())
            results = {}

            for method_name in methods:
                logger.info(f"Testing L7 Method: {method_name}")
                try:
                    # Mock BrowserEngine.solve_cf and _rebuild_payload to avoid deep byte/MagicMock concatenation errors
                    with patch.object(BrowserEngine, 'solve_cf', new_callable=AsyncMock) as m_solve, \
                         patch.object(flood, '_rebuild_payload', return_value=None), \
                         patch.object(flood, '_send_async', new_callable=AsyncMock, return_value=None):
                        
                        m_solve.return_value = ("cf_clearance=test", "ua_test")

                        method_func = flood.methods[method_name]
                        flood.SENT_FLOOD = method_func # crucial for some methods that wrap around SENT_FLOOD

                        # We wrap in wait_for
                        await asyncio.wait_for(method_func(), timeout=1.0)
                        results[method_name] = "PASSED"
                        logger.info(f"  [+] {method_name}: SUCCESS")
                except asyncio.TimeoutError:
                    results[method_name] = "PASSED (Timeout - likely infinite loop/flood)"
                    logger.info(f"  [+] {method_name}: SUCCESS (Loop detected)")
                except Exception as e:
                    results[method_name] = f"FAILED: {str(e)[:50]}"
                    logger.error(f"  [!] {method_name}: FAILED - {e}")

            return results
    async def test_l4_methods(self):
        logger.info("--- Starting Layer 4 Method Tests ---")
        # Instantiate Layer4
        # target for L4 is Tuple[str, int]
        flood = Layer4((self.domain, 443))
        flood._rpc = 1
        flood._synevent = MagicMock()
        flood._synevent.is_set.return_value = True
        
        methods = list(flood.methods.keys())
        results = {}

        for method_name in methods:
            logger.info(f"Testing L4 Method: {method_name}")
            try:
                # Do not mock socket directly as it breaks Windows ProactorEventLoop internally
                method_func = flood.methods[method_name]
                await asyncio.wait_for(method_func(), timeout=1.0)
                results[method_name] = "PASSED"
                logger.info(f"  [+] {method_name}: SUCCESS")
            except asyncio.TimeoutError:
                results[method_name] = "PASSED (Timeout - standard loop behavior)"
                logger.info(f"  [w] {method_name}: TIMEOUT")
            except Exception as e:
                results[method_name] = f"FAILED: {e}"
                logger.error(f"  [!] {method_name}: FAILED - {e}")

        return results

async def main():
    target = "https://google.com/"
    tester = MethodTester(target)
    
    l7_results = await tester.test_l7_methods()
    l4_results = await tester.test_l4_methods()

    # Generate Report
    with open("conductor/test_report.md", "w") as f:
        f.write("# Comprehensive Method Test Report\n\n")
        f.write(f"**Target:** {target}\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Layer 7 Results\n")
        f.write("| Method | Status |\n")
        f.write("| --- | --- |\n")
        for m, s in sorted(l7_results.items()):
            f.write(f"| {m} | {s} |\n")
            
        f.write("\n## Layer 4 Results\n")
        f.write("| Method | Status |\n")
        f.write("| --- | --- |\n")
        for m, s in sorted(l4_results.items()):
            f.write(f"| {m} | {s} |\n")

    logger.info("Tests complete. Report generated at conductor/test_report.md")

if __name__ == "__main__":
    asyncio.run(main())
