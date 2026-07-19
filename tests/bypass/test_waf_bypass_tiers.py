# tests/test_waf_bypass_tiers.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from src.core.engine import BrowserEngine

@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep", return_value=None):
        yield

@pytest.mark.asyncio
async def test_patchright_receives_proxy_config():
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "test_token"}]

    mock_patchright_module = AsyncMock()
    mock_patchright_module.async_playwright = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_playwright)))

    modules_mock = {
        "patchright": AsyncMock(),
        "patchright.async_api": mock_patchright_module
    }

    with patch.dict("sys.modules", modules_mock), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.CURL_CFFI_INSTALLED", False), \
         patch("src.core.engine.CLOAKBROWSER_INSTALLED", False):
        cookie, ua = await BrowserEngine._solve_tier3_heavy_stealth("https://example.com", proxy="192.0.2.1:8080", timeout=10)

    # Ensure proxy was passed to new_context as required by resource/patchright docs
    mock_browser.new_context.assert_called_once()
    kwargs = mock_browser.new_context.call_args.kwargs
    assert kwargs.get("proxy") == {"server": "http://192.0.2.1:8080"}


@pytest.mark.asyncio
async def test_patchright_automates_turnstile():
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_iframe = AsyncMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    # Return empty list for 3 calls so loop_idx reaches 3 and triggers click, then token on 4th call
    mock_context.cookies.side_effect = [[], [], [], [{"name": "cf_clearance", "value": "test_token"}]]

    mock_page.frames = [mock_iframe]
    mock_iframe.url = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/"
    mock_iframe.evaluate.return_value = {"found": True, "checked": False, "x": 10, "y": 10}
    mock_iframe.frame_element.return_value.bounding_box.return_value = {"x": 100, "y": 100, "width": 50, "height": 50}
    mock_page.mouse.move = AsyncMock()

    mock_patchright_module = AsyncMock()
    mock_patchright_module.async_playwright = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_playwright)))

    modules_mock = {
        "patchright": AsyncMock(),
        "patchright.async_api": mock_patchright_module
    }

    with patch.dict("sys.modules", modules_mock), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.CURL_CFFI_INSTALLED", False), \
         patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.BrowserEngine._click_turnstile_checkbox_precision_async") as mock_click:
        cookie, ua = await BrowserEngine._solve_tier3_heavy_stealth("https://example.com", timeout=10)

    assert mock_click.called


@pytest.mark.asyncio
async def test_camoufox_automates_turnstile():
    mock_camoufox_module = AsyncMock()
    mock_camoufox_class = MagicMock()
    mock_camoufox_module.AsyncCamoufox = mock_camoufox_class

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_iframe = AsyncMock()

    # Return empty list for 3 calls so loop_idx reaches 3 and triggers click, then token on 4th call
    mock_context.cookies.side_effect = [[], [], [], [{"name": "cf_clearance", "value": "test_token"}]]

    mock_page.evaluate.return_value = "ua_camoufox"
    mock_browser.contexts = [mock_context]
    mock_browser.new_page.return_value = mock_page
    mock_camoufox_class.return_value.__aenter__.return_value = mock_browser

    mock_page.frames = [mock_iframe]
    mock_iframe.url = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/"
    mock_iframe.evaluate.return_value = {"found": True, "checked": False, "x": 10, "y": 10}
    mock_iframe.frame_element.return_value.bounding_box.return_value = {"x": 100, "y": 100, "width": 50, "height": 50}
    mock_page.mouse.move = AsyncMock()

    modules_mock = {
        "camoufox": AsyncMock(),
        "camoufox.async_api": mock_camoufox_module
    }

    with patch.dict("sys.modules", modules_mock), \
         patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("src.core.engine.CURL_CFFI_INSTALLED", False), \
         patch("src.core.engine.BrowserEngine._click_turnstile_checkbox_precision_async") as mock_click:
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://example.com", timeout=10)

    assert mock_click.called
