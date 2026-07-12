import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_tcp_fallback_called_when_curl_http_probe_fails():
    from src.core.engine import TacticalProxy

    tcp_result = MagicMock(spec=TacticalProxy)
    tcp_result.is_protocol_verified = True
    tcp_result.latency = 800.0
    tcp_result.http_status = 200
    tcp_result.score = 100
    tcp_result.fail_count = 0

    try:
        from PyRoxy import ProxyType
        proxy = MagicMock()
        proxy.type = ProxyType.SOCKS5
    except ImportError:
        proxy = MagicMock()
    proxy.__str__ = lambda self: "1.2.3.4:1080"
    proxy.host = "1.2.3.4"
    proxy.port = 1080

    with (
        patch("src.core.engine.CURL_CFFI_INSTALLED", True),
        patch("src.core.engine._check_proxy_async", new_callable=AsyncMock, return_value=tcp_result) as mock_tcp,
        patch("src.core.engine.INTEL_DB.get_bulk_proxy_intel", return_value={}),
    ):
        from curl_cffi.requests import AsyncSession
        with patch.object(AsyncSession, "__aenter__", side_effect=Exception("1.1.1.1 unreachable")):
            from src.core.engine import TacticalProxyValidator
            result = await TacticalProxyValidator.validate_and_score(
                {proxy}, target_url="https://example.com", is_layer7=True
            )

    mock_tcp.assert_called()
    verified = [r for r in result if r.is_protocol_verified]
    assert len(verified) >= 1


@pytest.mark.asyncio
async def test_proxy_dead_when_both_curl_and_tcp_fail():
    from src.core.engine import TacticalProxy

    dead_result = MagicMock(spec=TacticalProxy)
    dead_result.is_protocol_verified = False
    dead_result.latency = 5000.0
    dead_result.http_status = 0

    try:
        from PyRoxy import ProxyType
        proxy = MagicMock()
        proxy.type = ProxyType.SOCKS5
    except ImportError:
        proxy = MagicMock()
    proxy.__str__ = lambda self: "9.9.9.9:9090"
    proxy.host = "9.9.9.9"
    proxy.port = 9090

    with (
        patch("src.core.engine.CURL_CFFI_INSTALLED", True),
        patch("src.core.engine._check_proxy_async", new_callable=AsyncMock, return_value=dead_result),
        patch("src.core.engine.INTEL_DB.get_bulk_proxy_intel", return_value={}),
    ):
        from curl_cffi.requests import AsyncSession
        with patch.object(AsyncSession, "__aenter__", side_effect=Exception("Timeout")):
            from src.core.engine import TacticalProxyValidator
            result = await TacticalProxyValidator.validate_and_score(
                {proxy}, target_url="https://example.com", is_layer7=True
            )

    verified = [r for r in result if r.is_protocol_verified]
    assert len(verified) == 0
