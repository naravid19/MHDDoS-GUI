import pytest
import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.engine import BrowserEngine

@pytest.mark.asyncio
async def test_solver_proxy_compatibility_gating():
    # Test that SOCKS proxies skip incompatible engines like DrissionPage and Behavioral
    url = "https://example.com"
    socks_proxy = "socks5://127.0.0.1:9050"
    
    mock_drission = AsyncMock(return_value=("cookie", "ua"))
    
    with patch("src.core.engine.BrowserEngine._solve_drissionpage", mock_drission, create=True), \
         patch("src.core.engine.BrowserEngine._solve_tier1_lightweight", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier2_fast_cdp", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier3_heavy_stealth", return_value=(None, None)), \
         patch("src.core.engine.BrowserEngine._solve_tier4_ultimate_stealth", return_value=(None, None)):
        engine = BrowserEngine()
        engine._solver_scores = {url: {"DrissionPage": 100}}
        engine.preferred_engines = ["DrissionPage"]
        
        # When passing a socks proxy, DrissionPage should be skipped 
        # (returning None, None)
        cookie, ua = engine.solve_cf(url, proxy=socks_proxy, timeout=5)
        
        assert cookie is None
        assert ua is None

def test_nodriver_teardown_suppresses_pending_tasks():
    # Simulate a crash in nodriver start to verify it doesn't leak exceptions or hang
    # Since nodriver is imported locally, we mock sys.modules to simulate it
    mock_nodriver = MagicMock()
    mock_nodriver.start = AsyncMock(side_effect=Exception("Simulated Nodriver Crash"))
    
    with patch.dict('sys.modules', {'nodriver': mock_nodriver}), \
         patch('src.core.engine.BOTASAURUS_INSTALLED', False), \
         patch('src.core.engine.NODRIVER_INSTALLED', True), \
         patch('src.core.engine.DRISSION_INSTALLED', False):
        engine = BrowserEngine()
        # Ensure it doesn't crash the thread or leak tasks when _solve_tier2_fast_cdp runs
        try:
            cookie, ua = engine._solve_tier2_fast_cdp("https://example.com", None, None, 1)
            # It should gracefully fail and return None, None
            assert cookie is None
            assert ua is None
        except Exception as e:
            pytest.fail(f"Exception escaped nodriver wrapper: {e}")

if __name__ == "__main__":
    asyncio.run(test_solver_proxy_compatibility_gating())
    test_nodriver_teardown_suppresses_pending_tasks()
    print("Runtime stability tests PASSED.")