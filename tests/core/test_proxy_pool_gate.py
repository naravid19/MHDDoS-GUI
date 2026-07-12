import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

def _make_tactical_proxy(ip="1.2.3.4", port=1080, latency=500.0):
    from src.core.engine import TacticalProxy
    base = MagicMock()
    base.__str__ = lambda self: f"{ip}:{port}"
    tp = MagicMock()
    tp.is_protocol_verified = True
    tp.latency = latency
    tp.base = base
    return tp

@pytest.mark.asyncio
async def test_empty_curl_ok_does_not_zero_tactical_proxies():
    surviving_tactical = [_make_tactical_proxy()]
    with patch("src.core.proxy_validator.score_proxies_for_curl", new_callable=AsyncMock, return_value=[]):
        from src.core.proxy_validator import score_proxies_for_curl
        curl_ok = await score_proxies_for_curl(["socks5://1.2.3.4:1080"], "https://example.com")
    from src.core.engine import _apply_curl_gate
    result_proxies, result_tactical = _apply_curl_gate(
        curl_ok=[],
        proxy_urls=["socks5://1.2.3.4:1080"],
        proxy_to_url={"socks5://1.2.3.4:1080": MagicMock()},
        proxies=[MagicMock()],
        tactical_proxies=surviving_tactical,
    )
    assert len(result_tactical) == 1
    assert len(result_proxies) == 1

@pytest.mark.asyncio
async def test_nonempty_curl_ok_filters_to_passing_proxies():
    from src.core.engine import _apply_curl_gate
    base_pass = MagicMock()
    base_pass.__str__ = lambda self: "1.2.3.4:1080"
    base_fail = MagicMock()
    base_fail.__str__ = lambda self: "9.9.9.9:9090"
    tp_pass = MagicMock()
    tp_pass.is_protocol_verified = True
    tp_pass.base = base_pass
    tp_fail = MagicMock()
    tp_fail.is_protocol_verified = True
    tp_fail.base = base_fail
    proxy_pass = base_pass
    proxy_fail = base_fail
    result_proxies, result_tactical = _apply_curl_gate(
        curl_ok=["socks5://1.2.3.4:1080"],
        proxy_urls=["socks5://1.2.3.4:1080", "socks5://9.9.9.9:9090"],
        proxy_to_url={
            "socks5://1.2.3.4:1080": proxy_pass,
            "socks5://9.9.9.9:9090": proxy_fail,
        },
        proxies=[proxy_pass, proxy_fail],
        tactical_proxies=[tp_pass, tp_fail],
    )
    assert proxy_pass in result_proxies
    assert proxy_fail not in result_proxies
    assert tp_pass in result_tactical
    assert tp_fail not in result_tactical
