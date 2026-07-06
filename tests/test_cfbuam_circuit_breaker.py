# tests/test_cfbuam_circuit_breaker.py
from __future__ import annotations

from typing import Any
from unittest.mock import patch
import pytest
from yarl import URL
from PyRoxy import Proxy, ProxyType

from src.core.engine import HttpFlood, TacticalProxyPool, TacticalProxy
from src.core.proxy_guard import ProxyCircuitBreaker


@pytest.mark.asyncio
async def test_cfbuam_evicts_dead_proxy_on_failure() -> None:
    """Verify that a dead proxy gets evicted on registration of failure."""
    # Ensure HttpFlood._circuit_breaker exists as class attribute
    HttpFlood._circuit_breaker = ProxyCircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    dead_proxy = "http://10.0.0.1:8080"
    
    assert HttpFlood._circuit_breaker.is_available(dead_proxy) is True
    await HttpFlood._circuit_breaker.register_failure(dead_proxy)
    assert HttpFlood._circuit_breaker.is_available(dead_proxy) is False


@pytest.mark.asyncio
async def test_cfbuam_circuit_breaker_integration() -> None:
    """Assert end-to-end integration: filtering, failure/success registration."""
    # Set up custom breaker on HttpFlood
    HttpFlood._circuit_breaker = ProxyCircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
    
    # Create two proxies
    p1 = Proxy("1.1.1.1", 80, ProxyType.HTTP)
    p2 = Proxy("2.2.2.2", 80, ProxyType.HTTP)
    
    tp1 = TacticalProxy(p1, 100.0, True, 200)
    tp2 = TacticalProxy(p2, 100.0, True, 200)
    
    pool = TacticalProxyPool([tp1, tp2])
    
    target_url = URL("https://example.com")
    flood = HttpFlood(
        thread_id=1,
        target=target_url,
        host="example.com",
        proxy_pool=pool
    )
    
    # Reset cfbuam states
    HttpFlood._cfbuam_cookie = None
    HttpFlood._cfbuam_proxy = None
    HttpFlood._last_solve_attempt = 0
    
    p1_str = str(p1)
    p2_str = str(p2)
    
    solve_calls: list[str | None] = []
    
    def mock_solve_cf(
        url: Any,
        proxy: str | None = None,
        user_agent: str | None = None,
        timeout: int = 45000
    ) -> tuple[str | None, str | None]:
        """Mock solve_cf implementation."""
        solve_calls.append(proxy)
        if proxy == p1_str:
            return None, None
        elif proxy == p2_str:
            return "cf_clearance=ok", "mock_ua"
        return None, None

    with patch("src.core.engine.BrowserEngine.solve_cf", side_effect=mock_solve_cf):
        # We mock get_proxy to return p1 first, then p2.
        pool_proxies = [p1, p2, p2, p2]
        
        def mock_get_proxy() -> Proxy:
            """Mock get_proxy implementation."""
            return pool_proxies.pop(0) if pool_proxies else p2
            
        with patch.object(pool, "get_proxy", side_effect=mock_get_proxy):
            # First run: will pick p1, fails, registers failure, retries without proxy
            await flood.CFBUAM()
            
            assert HttpFlood._circuit_breaker.is_available(p1_str) is False
            assert HttpFlood._circuit_breaker.is_available(p2_str) is True
            
            # Reset solve attempt cooldown/cookies for second run
            HttpFlood._cfbuam_cookie = None
            HttpFlood._last_solve_attempt = 0
            
            # Second run:
            # Loop picks p1 from mock, detects it is evicted, skips it, gets next (p2).
            # p2 is available, succeeds.
            await flood.CFBUAM()
            
            assert HttpFlood._cfbuam_cookie == "cf_clearance=ok"
            assert HttpFlood._cfbuam_proxy == p2_str
            assert HttpFlood._circuit_breaker.is_available(p2_str) is True
