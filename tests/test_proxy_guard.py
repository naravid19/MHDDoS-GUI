import asyncio
import pytest
from src.core.proxy_guard import ProxyCircuitBreaker, ProxyNode

@pytest.mark.asyncio
async def test_proxy_circuit_breaker_eviction_and_recovery() -> None:
    breaker = ProxyCircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
    proxy = "127.0.0.1:8080"

    assert breaker.is_available(proxy) is True

    await breaker.register_failure(proxy)
    assert breaker.is_available(proxy) is True

    await breaker.register_failure(proxy)
    assert breaker.is_available(proxy) is False

    healthy = breaker.get_healthy_proxies([proxy, "127.0.0.1:9090"])
    assert healthy == ["127.0.0.1:9090"]

    await asyncio.sleep(0.3)
    assert breaker.is_available(proxy) is True

@pytest.mark.asyncio
async def test_proxy_circuit_breaker_success_reset() -> None:
    breaker = ProxyCircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
    proxy = "127.0.0.1:8080"

    assert breaker.is_available(proxy) is True

    await breaker.register_failure(proxy)
    assert breaker.is_available(proxy) is True

    await breaker.register_success(proxy)
    await breaker.register_failure(proxy)
    assert breaker.is_available(proxy) is True
