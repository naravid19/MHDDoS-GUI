# tests/test_proxy_guard.py
import asyncio
import pytest
from src.core.proxy_guard import ProxyPoolSilo, ProxyCircuitBreaker

@pytest.mark.asyncio
async def test_proxy_silo_and_circuit_breaker():
    silo = ProxyPoolSilo()
    silo.add_proxies(["http://1.1.1.1:80", "socks5://2.2.2.2:1080", "socks4://3.3.3.3:1080"])
    
    assert silo.get_proxy("http") == "http://1.1.1.1:80"
    assert silo.get_proxy("socks5") == "socks5://2.2.2.2:1080"
    
    # Test Circuit Breaker eviction after 2 failures (e.g., curl error 97 or 0x01)
    silo.report_failure("socks5://2.2.2.2:1080", "CURLE_COULDNT_CONNECT")
    silo.report_failure("socks5://2.2.2.2:1080", "CURLE_COULDNT_CONNECT")
    
    assert silo.is_quarantined("socks5://2.2.2.2:1080") is True
    assert silo.get_proxy("socks5") is None


@pytest.mark.asyncio
async def test_proxy_circuit_breaker_compatibility():
    # Instantiated with recovery_timeout to check fallback
    cb = ProxyCircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    proxy = "http://5.5.5.5:80"
    
    assert cb.is_available(proxy) is True
    
    await cb.register_failure(proxy)
    await cb.register_failure(proxy)
    assert cb.is_available(proxy) is True
    
    await cb.register_failure(proxy)
    assert cb.is_available(proxy) is False
    assert cb.get_healthy_proxies([proxy, "http://6.6.6.6:80"]) == ["http://6.6.6.6:80"]
    
    await cb.register_success(proxy)
    assert cb.is_available(proxy) is True
    
    # Test quarantine expiry
    await cb.register_failure(proxy)
    await cb.register_failure(proxy)
    await cb.register_failure(proxy)
    assert cb.is_available(proxy) is False
    
    await asyncio.sleep(0.15)
    assert cb.is_available(proxy) is True


def test_proxy_rotation():
    silo = ProxyPoolSilo()
    silo.add_proxies(["http://1.1.1.1:80", "http://2.2.2.2:80", "http://3.3.3.3:80"])
    
    p1 = silo.get_proxy("http")
    p2 = silo.get_proxy("http")
    p3 = silo.get_proxy("http")
    p4 = silo.get_proxy("http")
    
    assert p1 == "http://1.1.1.1:80"
    assert p2 == "http://2.2.2.2:80"
    assert p3 == "http://3.3.3.3:80"
    assert p4 == "http://1.1.1.1:80"


def test_https_mapping():
    silo = ProxyPoolSilo()
    silo.add_proxies(["http://1.1.1.1:80"])
    assert silo.get_proxy("https") == "http://1.1.1.1:80"


def test_exact_error_code_matching():
    silo = ProxyPoolSilo()
    silo.add_proxies(["http://1.1.1.1:80"])
    
    # "135" contains "35", but should not trigger circuit breaker because it's a substring, not exact match
    silo.report_failure("http://1.1.1.1:80", "135")
    silo.report_failure("http://1.1.1.1:80", "135")
    assert silo.is_quarantined("http://1.1.1.1:80") is False
    
    # Exact match "35" should trigger circuit breaker
    silo.report_failure("http://1.1.1.1:80", "35")
    silo.report_failure("http://1.1.1.1:80", "35")
    assert silo.is_quarantined("http://1.1.1.1:80") is True


def test_url_sanitization():
    silo = ProxyPoolSilo()
    silo.add_proxies(["  http://1.1.1.1:80  ", "\tsocks5://2.2.2.2:1080\n"])
    assert "http://1.1.1.1:80" in silo.silos["http"]
    assert "socks5://2.2.2.2:1080" in silo.silos["socks5"]


@pytest.mark.asyncio
async def test_quarantine_cleanup_memory_growth():
    cb = ProxyCircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
    proxy1 = "http://1.1.1.1:80"
    proxy2 = "http://2.2.2.2:80"
    
    cb.record_failure(proxy1)
    cb.record_failure(proxy2)
    assert proxy1 in cb.quarantined_until
    assert proxy2 in cb.quarantined_until
    
    await asyncio.sleep(0.08)
    
    # We check proxy1. In the current codebase, checking proxy1 will NOT clean up proxy2 from quarantined_until.
    assert cb.is_quarantined(proxy1) is False
    
    # Under current code, proxy2 is still in quarantined_until, but under the new cleanup it should be removed.
    assert proxy2 not in cb.quarantined_until


def test_proxy_silo_timeout_eviction():
    """Verify that timeout (28) and winerror 10061 trigger circuit breaker failure counts."""
    silo = ProxyPoolSilo()
    silo.add_proxies(["socks5://1.2.3.4:1080"])
    
    silo.report_failure("socks5://1.2.3.4:1080", "28")
    silo.report_failure("socks5://1.2.3.4:1080", "10061")
    
    assert silo.is_quarantined("socks5://1.2.3.4:1080")


