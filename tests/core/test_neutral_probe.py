import asyncio
import pytest
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_score_proxies_uses_neutral_url_not_target():
    from src.core.proxy_validator import _PROBE_URL
    captured_targets = []
    class CapturingValidator:
        async def validate_curl_socks5(self, proxy, target_url=_PROBE_URL, timeout=8):
            captured_targets.append(target_url)
            return True
    from src.core.proxy_validator import score_proxies_for_curl
    await score_proxies_for_curl(
        proxies=["http://1.2.3.4:8080"],
        target="https://readtoon.com",
        validator=CapturingValidator(),
    )
    assert all(t == _PROBE_URL for t in captured_targets)

@pytest.mark.asyncio
async def test_validate_curl_socks5_sets_proxy_on_session_constructor():
    captured_kwargs = {}
    class FakeSession:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url, **kwargs):
            resp = MagicMock()
            resp.status_code = 204
            return resp
    with patch("src.core.proxy_validator.AsyncSession", FakeSession):
        from src.core.proxy_validator import CurlProxyValidator
        validator = CurlProxyValidator()
        result = await validator.validate_curl_socks5("socks5://1.2.3.4:1080")
    assert result is True
    assert "proxies" in captured_kwargs
    assert "socks5://1.2.3.4:1080" in captured_kwargs["proxies"].values()
