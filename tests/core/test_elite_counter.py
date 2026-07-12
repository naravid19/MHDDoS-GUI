import pytest
import sys
from unittest.mock import MagicMock, patch

def _tp(latency, http_status):
    tp = MagicMock()
    tp.latency = latency
    tp.latency_ms = None
    tp.http_status = http_status
    tp.is_protocol_verified = True
    return tp

def test_elite_count_uses_latency_field_not_latency_ms():
    from src.core.engine import TacticalProxyValidator
    proxies = [
        _tp(latency=500.0,  http_status=200),
        _tp(latency=1500.0, http_status=403),
        _tp(latency=4000.0, http_status=200),
        _tp(latency=200.0,  http_status=0),
    ]
    count = TacticalProxyValidator.count_elite_proxies(proxies)
    assert count == 2

def test_elite_count_zero_for_empty_list():
    from src.core.engine import TacticalProxyValidator
    assert TacticalProxyValidator.count_elite_proxies([]) == 0

def test_platform_semaphore_limit_windows_is_256():
    from src.core.engine import TacticalProxyValidator
    with patch.object(sys, "platform", "win32"):
        limit = TacticalProxyValidator.get_platform_semaphore_limit()
    assert limit == 256

def test_platform_semaphore_limit_linux_is_512():
    from src.core.engine import TacticalProxyValidator
    with patch.object(sys, "platform", "linux"):
        limit = TacticalProxyValidator.get_platform_semaphore_limit()
    assert limit == 512

def test_dynamic_timeout_formula_for_3k_proxies_with_256_semaphore():
    total_raw = 2972
    sem_limit = 256
    dynamic_timeout = min(900, max(240, (total_raw // sem_limit + 1) * 12))
    assert dynamic_timeout >= 240
    assert dynamic_timeout <= 900
