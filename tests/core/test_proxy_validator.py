import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_valid_proxy_returns_true():
    from src.core.proxy_validator import CurlProxyValidator
    v = CurlProxyValidator()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("src.core.proxy_validator.AsyncSession") as M:
        inst = AsyncMock()
        inst.get = AsyncMock(return_value=mock_resp)
        M.return_value.__aenter__ = AsyncMock(return_value=inst)
        M.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await v.validate_curl_socks5("socks5://1.2.3.4:1080", "https://example.com")
    assert result is True

@pytest.mark.asyncio
async def test_proxy_error_returns_false():
    from src.core.proxy_validator import CurlProxyValidator
    v = CurlProxyValidator()
    with patch("src.core.proxy_validator.AsyncSession") as M:
        inst = AsyncMock()
        inst.get = AsyncMock(side_effect=Exception("curl: (97) cannot complete SOCKS5"))
        M.return_value.__aenter__ = AsyncMock(return_value=inst)
        M.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await v.validate_curl_socks5("socks5://bad:9999", "https://example.com")
    assert result is False

@pytest.mark.asyncio
async def test_score_filters_bad_proxies():
    from src.core.proxy_validator import CurlProxyValidator, score_proxies_for_curl
    good = "socks5://1.1.1.1:1080"
    bad = "socks5://9.9.9.9:9999"

    async def fake_val(proxy, target_url, timeout=10):
        return proxy == good

    v = CurlProxyValidator()
    v.validate_curl_socks5 = fake_val
    result = await score_proxies_for_curl([good, bad], "https://example.com", validator=v)
    assert result == [good]


@pytest.mark.asyncio
async def test_validate_curl_socks5_fallback():
    from src.core.proxy_validator import CurlProxyValidator, _PROBE_URL
    v = CurlProxyValidator()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("src.core.proxy_validator.AsyncSession") as M:
        inst = AsyncMock()
        inst.get = AsyncMock(return_value=mock_resp)
        M.return_value.__aenter__ = AsyncMock(return_value=inst)
        M.return_value.__aexit__ = AsyncMock(return_value=False)
        
        # Test with empty target_url
        await v.validate_curl_socks5("socks5://1.2.3.4:1080", "")
        inst.get.assert_called_with(_PROBE_URL, proxy="socks5://1.2.3.4:1080", impersonate="chrome", timeout=10)
        
        # Test with None target_url
        await v.validate_curl_socks5("socks5://1.2.3.4:1080", None)
        inst.get.assert_called_with(_PROBE_URL, proxy="socks5://1.2.3.4:1080", impersonate="chrome", timeout=10)


@pytest.mark.asyncio
async def test_score_proxies_for_curl_fallback():
    from src.core.proxy_validator import score_proxies_for_curl, CurlProxyValidator, _PROBE_URL
    
    called_target_url = None
    async def fake_val(proxy, target_url, timeout=10):
        nonlocal called_target_url
        called_target_url = target_url
        return True

    v = CurlProxyValidator()
    v.validate_curl_socks5 = fake_val
    
    # Test with empty target
    await score_proxies_for_curl(["socks5://1.1.1.1:1080"], "", validator=v)
    assert called_target_url == _PROBE_URL
    
    # Test with None target
    await score_proxies_for_curl(["socks5://1.1.1.1:1080"], None, validator=v)
    assert called_target_url == _PROBE_URL

