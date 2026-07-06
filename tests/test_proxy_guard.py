import asyncio
import pytest
from src.core.proxy_guard import ProxyCircuitBreaker

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


@pytest.mark.asyncio
async def test_proxy_circuit_breaker_recovery_race_condition() -> None:
    breaker = ProxyCircuitBreaker(failure_threshold=2, recovery_timeout=0.2)
    proxy = "127.0.0.1:8080"

    # Trip the proxy the first time (t=0)
    await breaker.register_failure(proxy)
    await breaker.register_failure(proxy)
    assert breaker.is_available(proxy) is False

    # Wait 0.1s (t=0.1)
    await asyncio.sleep(0.1)

    # Register success (resets status and cancels task)
    await breaker.register_success(proxy)
    assert breaker.is_available(proxy) is True

    # Trip it a second time (t=0.1)
    await breaker.register_failure(proxy)
    await breaker.register_failure(proxy)
    assert breaker.is_available(proxy) is False

    # Wait 0.15s (t=0.25).
    # If the first task (scheduled at t=0 to run for 0.2s, i.e. finish at t=0.2) was not cancelled,
    # it would have run at t=0.2 and set is_evicted = False, making the proxy available.
    # If it was cancelled successfully, the second task (scheduled at t=0.1 to run for 0.2s,
    # i.e. finish at t=0.3) is the only one running, so at t=0.25 the proxy must still be evicted (False).
    await asyncio.sleep(0.15)
    assert breaker.is_available(proxy) is False

    # Wait another 0.1s (t=0.35), the second task should finish and recover it.
    await asyncio.sleep(0.1)
    assert breaker.is_available(proxy) is True
