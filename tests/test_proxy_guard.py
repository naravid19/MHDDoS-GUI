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
