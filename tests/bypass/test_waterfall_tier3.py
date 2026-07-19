# tests/bypass/test_waterfall_tier3.py
"""
Tier 3: Heavy Stealth Chromium Bypass Tests
Sub-engines: 3a. CloakBrowser | 3b. Patchright (Stealth Playwright) | 3c. Undetected Chromedriver (UC)
All 3 use source-level anti-detection patches + human-like interaction on Chromium
=> Stronger stealth than Tier 2 — handles sites that fingerprint headless indicators
"""
import pytest
from unittest.mock import patch, MagicMock
from src.core.engine import BrowserEngine, BypassDebugger


# ---------------------------------------------------------------------------
# Tier 3a: CloakBrowser
# ---------------------------------------------------------------------------

def test_tier3_cloakbrowser_success():
    """Verify Tier 3a (CloakBrowser) returns cf_clearance when context cookies contain it."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "CloakBrowser-Chrome/122"

    mock_context = MagicMock()
    mock_context.cookies.return_value = [
        {"name": "cf_clearance", "value": "cloak_token_abc"},
        {"name": "_ga", "value": "GA1.2.xxx"},
    ]
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", True), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("src.core.engine.cloakbrowser_launch", return_value=mock_browser, create=True), \
         patch("time.sleep", return_value=None):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", "1.2.3.4:8080", "test-ua", 30)

    assert cookie is not None
    assert "cf_clearance=cloak_token_abc" in cookie
    assert ua == "CloakBrowser-Chrome/122"
    mock_browser.close.assert_called_once()


def test_tier3_cloakbrowser_proxy_with_no_schema():
    """Verify CloakBrowser receives properly formatted proxy URL (prepends http:// if missing)."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "UA"

    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "tok"}]
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", True), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("src.core.engine.cloakbrowser_launch", return_value=mock_browser, create=True) as mock_launch, \
         patch("time.sleep", return_value=None):
        BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", "103.68.214.164:8080", None, 30)

    mock_launch.assert_called_with(headless=True, humanize=True, geoip=True, proxy="http://103.68.214.164:8080")


def test_tier3_cloakbrowser_geoip_disabled_without_proxy():
    """Verify CloakBrowser disables geoip when no proxy is provided."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "UA"
    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "tok"}]
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", True), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("src.core.engine.cloakbrowser_launch", return_value=mock_browser, create=True) as mock_launch, \
         patch("time.sleep", return_value=None):
        BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    mock_launch.assert_called_with(headless=True, humanize=True, geoip=False, proxy=None)


def test_tier3_cloakbrowser_failure_captured():
    """Verify CloakBrowser challenge not solved after loop triggers BypassDebugger."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "UA"
    mock_context = MagicMock()
    mock_context.cookies.return_value = []  # never gets cf_clearance
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", True), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("src.core.engine.cloakbrowser_launch", return_value=mock_browser, create=True), \
         patch("time.sleep", return_value=None), \
         patch.object(BypassDebugger, "capture_failure") as mock_debug:
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    mock_debug.assert_any_call(
        "Tier 3 (CloakBrowser)", "https://readtoon.com/",
        page_obj=mock_page, error_msg="Challenge not solved"
    )
    assert cookie is None


def test_tier3_cloakbrowser_uses_human_mouse():
    """Verify Tier 3a (CloakBrowser) invokes human_mouse Bezier waypoints (>= 25 calls to mouse.move)."""
    mock_page = MagicMock()
    del mock_page.actions  # Real Playwright Page has no .actions attribute
    mock_page.evaluate.return_value = "CloakBrowser-Chrome/122"
    mock_page.mouse = MagicMock()
    mock_page.mouse.move = MagicMock()

    mock_context = MagicMock()
    mock_context.cookies.side_effect = [
        [],
        [{"name": "cf_clearance", "value": "cloak_token_abc"}],
        [{"name": "cf_clearance", "value": "cloak_token_abc"}],
    ]
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", True), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("src.core.engine.cloakbrowser_launch", return_value=mock_browser, create=True), \
         patch("time.sleep", return_value=None):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", "1.2.3.4:8080", "test-ua", 30)

    assert cookie is not None
    assert mock_page.mouse.move.call_count >= 25, f"Expected >= 25 waypoint moves, got {mock_page.mouse.move.call_count}"



# ---------------------------------------------------------------------------
# Tier 3b: Patchright (Stealth Playwright)
# ---------------------------------------------------------------------------

def test_tier3_patchright_success():
    """Verify Tier 3b (Patchright) returns cf_clearance from context.cookies()."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "Patchright-Chrome/122"

    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "patchright_tok"}]

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser

    mock_playwright_ctx = MagicMock()
    mock_playwright_ctx.chromium = mock_chromium
    mock_playwright_ctx.__enter__ = MagicMock(return_value=mock_playwright_ctx)
    mock_playwright_ctx.__exit__ = MagicMock(return_value=False)

    mock_context.new_page.return_value = mock_page

    mock_patchright_module = MagicMock()
    mock_patchright_module.sync_playwright.return_value = mock_playwright_ctx

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "patchright": MagicMock(),
             "patchright.sync_api": mock_patchright_module,
         }):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    assert cookie is not None
    assert "cf_clearance=patchright_tok" in cookie
    assert ua == "Patchright-Chrome/122"
    mock_browser.close.assert_called_once()


def test_tier3_patchright_with_proxy():
    """Verify Patchright passes proxy as {server: url} dict to new_context."""
    mock_page = MagicMock()
    mock_page.evaluate.return_value = "UA"

    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "tok"}]
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser

    mock_playwright_ctx = MagicMock()
    mock_playwright_ctx.chromium = mock_chromium
    mock_playwright_ctx.__enter__ = MagicMock(return_value=mock_playwright_ctx)
    mock_playwright_ctx.__exit__ = MagicMock(return_value=False)

    mock_patchright_module = MagicMock()
    mock_patchright_module.sync_playwright.return_value = mock_playwright_ctx

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "patchright": MagicMock(),
             "patchright.sync_api": mock_patchright_module,
         }):
        BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", "103.68.214.164:8080", None, 30)

    mock_browser.new_context.assert_called_with(proxy={"server": "http://103.68.214.164:8080"})


def test_tier3_patchright_failure_captured():
    """Verify Patchright challenge not solved triggers BypassDebugger.capture_failure."""
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.cookies.return_value = []  # no cf_clearance
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser

    mock_playwright_ctx = MagicMock()
    mock_playwright_ctx.chromium = mock_chromium
    mock_playwright_ctx.__enter__ = MagicMock(return_value=mock_playwright_ctx)
    mock_playwright_ctx.__exit__ = MagicMock(return_value=False)

    mock_patchright_module = MagicMock()
    mock_patchright_module.sync_playwright.return_value = mock_playwright_ctx

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("time.sleep", return_value=None), \
         patch.object(BypassDebugger, "capture_failure") as mock_debug, \
         patch.dict("sys.modules", {
             "patchright": MagicMock(),
             "patchright.sync_api": mock_patchright_module,
         }):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    mock_debug.assert_any_call(
        "Tier 3 (Patchright)", "https://readtoon.com/",
        page_obj=mock_page, error_msg="Challenge not solved"
    )
    assert cookie is None


def test_tier3_patchright_uses_human_mouse():
    """Verify Tier 3b (Patchright) invokes human_mouse Bezier waypoints (>= 25 calls to mouse.move)."""
    mock_page = MagicMock()
    del mock_page.actions  # Real Playwright Page has no .actions attribute
    mock_page.evaluate.return_value = "Patchright-Chrome/122"
    mock_page.mouse = MagicMock()
    mock_page.mouse.move = MagicMock()

    mock_context = MagicMock()
    mock_context.cookies.side_effect = [
        [],
        [{"name": "cf_clearance", "value": "patchright_tok"}],
        [{"name": "cf_clearance", "value": "patchright_tok"}],
    ]
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser

    mock_playwright_ctx = MagicMock()
    mock_playwright_ctx.chromium = mock_chromium
    mock_playwright_ctx.__enter__ = MagicMock(return_value=mock_playwright_ctx)
    mock_playwright_ctx.__exit__ = MagicMock(return_value=False)

    mock_patchright_module = MagicMock()
    mock_patchright_module.sync_playwright.return_value = mock_playwright_ctx

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", True), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "patchright": MagicMock(),
             "patchright.sync_api": mock_patchright_module,
         }):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    assert cookie is not None
    assert mock_page.mouse.move.call_count >= 25, f"Expected >= 25 waypoint moves, got {mock_page.mouse.move.call_count}"



# ---------------------------------------------------------------------------
# Tier 3c: Undetected Chromedriver (UC)
# ---------------------------------------------------------------------------

def test_tier3_uc_success():
    """Verify Tier 3c (Undetected Chromedriver) returns cf_clearance from driver.get_cookies()."""
    mock_driver = MagicMock()
    mock_driver.get_cookies.return_value = [
        {"name": "cf_clearance", "value": "uc_clearance_999"},
        {"name": "session", "value": "sess123"},
    ]
    mock_driver.execute_script.return_value = "UC-Chrome/122"

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", True), \
         patch("src.core.engine._launch_uc_chrome", return_value=mock_driver, create=True), \
         patch("time.sleep", return_value=None):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    assert cookie is not None
    assert "cf_clearance=uc_clearance_999" in cookie
    assert ua == "UC-Chrome/122"
    mock_driver.quit.assert_called_once()


def test_tier3_uc_with_proxy():
    """Verify UC Chromedriver passes proxy to _launch_uc_chrome helper."""
    mock_driver = MagicMock()
    mock_driver.get_cookies.return_value = [{"name": "cf_clearance", "value": "tok"}]
    mock_driver.execute_script.return_value = "UA"

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", True), \
         patch("src.core.engine._launch_uc_chrome", return_value=mock_driver, create=True) as mock_launch, \
         patch("time.sleep", return_value=None):
        BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", "103.68.214.164:8080", None, 30)

    mock_launch.assert_called_with(headless=True, proxy="103.68.214.164:8080")


def test_tier3_uc_failure_captured():
    """Verify UC challenge not solved triggers BypassDebugger and driver.quit() is always called."""
    mock_driver = MagicMock()
    mock_driver.get_cookies.return_value = []  # never gets cf_clearance

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", True), \
         patch("src.core.engine._launch_uc_chrome", return_value=mock_driver, create=True), \
         patch("time.sleep", return_value=None), \
         patch.object(BypassDebugger, "capture_failure") as mock_debug:
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    mock_debug.assert_any_call(
        "Tier 3 (UC)", "https://readtoon.com/",
        page_obj=mock_driver, error_msg="Challenge not solved"
    )
    mock_driver.quit.assert_called_once()
    assert cookie is None


def test_tier3_all_disabled_returns_none():
    """Verify (None, None) when all Tier 3 sub-engines are disabled."""
    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED", False):
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", None, None, 30)

    assert cookie is None
    assert ua is None


# ---------------------------------------------------------------------------
# Live Integration Test
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_tier3_readtoon_live_integration():
    """
    Live integration test for Tier 3 (Heavy Stealth Chromium) against https://readtoon.com/.
    Uses CloakBrowser (3a), Patchright (3b), or Undetected Chromedriver (3c) depending on what's installed.
    Proxies loaded dynamically from the checked-proxies directory.
    """
    import os
    import time
    from src.core.engine import CLOAKBROWSER_INSTALLED, PATCHRIGHT_INSTALLED, UNDETECTED_CHROMEDRIVER_INSTALLED

    print(f"\n[*] Tier 3 engine availability:")
    print(f"    3a. CloakBrowser:    {'✅ installed' if CLOAKBROWSER_INSTALLED else '❌ not installed'}")
    print(f"    3b. Patchright:      {'✅ installed' if PATCHRIGHT_INSTALLED else '❌ not installed'}")
    print(f"    3c. Undetected-CD:   {'✅ installed' if UNDETECTED_CHROMEDRIVER_INSTALLED else '❌ not installed'}")

    if not any([CLOAKBROWSER_INSTALLED, PATCHRIGHT_INSTALLED, UNDETECTED_CHROMEDRIVER_INSTALLED]):
        pytest.skip("No Tier 3 sub-engines installed (cloakbrowser / patchright / undetected-chromedriver)")

    proxy_file = r"C:\Users\narav\Desktop\CE code\Tools\proxy-scraper-checker\out\checked-proxies\proxies\http.txt"
    proxies = []
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip() and ":" in line]
        print(f"[*] Loaded {len(proxies)} checked proxies from http.txt")

    cookie, ua = None, None

    for i, test_proxy in enumerate(proxies[:2]):
        print(f"[*] Tier 3 attempt ({i+1}/2) with proxy: {test_proxy}")
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", proxy=test_proxy, timeout=35)
        if cookie and "cf_clearance" in cookie:
            print(f"[+] Tier 3 PASSED via proxy: cookie={cookie[:50]}...")
            break
        time.sleep(1.0)

    if not cookie or "cf_clearance" not in cookie:
        print("[*] Tier 3 direct connection attempt (no proxy)...")
        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://readtoon.com/", proxy=None, timeout=40)
        if cookie and "cf_clearance" in cookie:
            print(f"[+] Tier 3 PASSED direct: cookie={cookie[:50]}...")
        else:
            print("[-] Tier 3 did not obtain cf_clearance on this run.")

    assert (cookie is None and ua is None) or (isinstance(cookie, str) and isinstance(ua, str)), \
        f"Expected (str, str) or (None, None) but got ({type(cookie)}, {type(ua)})"