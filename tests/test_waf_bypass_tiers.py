# tests/test_waf_bypass_tiers.py
from unittest.mock import MagicMock, patch
import pytest
import sys
from src.core.engine import BrowserEngine

@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep", return_value=None):
        yield

def test_patchright_receives_proxy_config():
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "test_token"}]
    
    mock_patchright_module = MagicMock()
    mock_patchright_module.sync_playwright = MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=mock_playwright)))
    
    # Use patch.dict for sys.modules mutation cleanup
    modules_mock = {
        "patchright": MagicMock(),
        "patchright.sync_api": mock_patchright_module
    }
    
    with patch.dict("sys.modules", modules_mock), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.CLOAKBROWSER_INSTALLED", False):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://example.com", proxy="192.0.2.1:8080", timeout=10)
        
    # Ensure proxy was passed to new_context as required by resource/patchright docs
    mock_browser.new_context.assert_called_once()
    kwargs = mock_browser.new_context.call_args.kwargs
    assert kwargs.get("proxy") == {"server": "http://192.0.2.1:8080"}

def test_patchright_automates_turnstile():
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_iframe = MagicMock()
    mock_checkbox = MagicMock()
    
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    # Return empty list on first call to allow loop to execute, then token on second call
    mock_context.cookies.side_effect = [[], [{"name": "cf_clearance", "value": "test_token"}]]
    
    mock_page.frame_locator.return_value = mock_iframe
    mock_iframe.locator.return_value = mock_checkbox
    mock_checkbox.count.return_value = 1
    
    mock_patchright_module = MagicMock()
    mock_patchright_module.sync_playwright = MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=mock_playwright)))
    
    # Use patch.dict for sys.modules mutation cleanup
    modules_mock = {
        "patchright": MagicMock(),
        "patchright.sync_api": mock_patchright_module
    }
    
    with patch.dict("sys.modules", modules_mock), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.CLOAKBROWSER_INSTALLED", False):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://example.com", timeout=10)
        
    mock_page.frame_locator.assert_called()
    mock_iframe.locator.assert_called()
    mock_checkbox.first.click.assert_called_with(timeout=1000)

def test_camoufox_automates_turnstile():
    mock_camoufox_module = MagicMock()
    mock_camoufox_class = MagicMock()
    mock_camoufox_module.Camoufox = mock_camoufox_class
    
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_iframe = MagicMock()
    mock_checkbox = MagicMock()
    
    # Return empty list on first call to allow loop to execute, then token on second call
    mock_context.cookies.side_effect = [[], [{"name": "cf_clearance", "value": "test_token"}]]
    
    mock_page.evaluate.return_value = "ua_camoufox"
    mock_browser.contexts = [mock_context]
    mock_browser.new_page.return_value = mock_page
    mock_camoufox_class.return_value.__enter__.return_value = mock_browser
    
    mock_page.frame_locator.return_value = mock_iframe
    mock_iframe.locator.return_value = mock_checkbox
    mock_checkbox.count.return_value = 1
    
    # Use patch.dict for sys.modules mutation cleanup
    modules_mock = {
        "camoufox": MagicMock(),
        "camoufox.sync_api": mock_camoufox_module
    }
    
    with patch.dict("sys.modules", modules_mock), \
         patch("src.core.engine.CAMOUFOX_INSTALLED", True):
        cookie, ua = BrowserEngine._solve_tier4_ultimate_stealth("https://example.com", timeout=10)
        
    mock_page.frame_locator.assert_called()
    mock_iframe.locator.assert_called()
    mock_checkbox.first.click.assert_called_with(timeout=1000)
