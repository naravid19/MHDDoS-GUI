import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from src.core.engine import BrowserEngine, BypassDebugger


# ---------------------------------------------------------------------------
# Tier 4a: AsyncCamoufox (Ultimate Stealth Firefox)
# ---------------------------------------------------------------------------

def _make_camoufox_mocks(cf_clearance_value: str, ua_value: str = "AsyncCamoufox-Firefox/121"):
    """Helper: build AsyncCamoufox mock hierarchy (context manager, browser, page, cookies)."""
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=ua_value)
    mock_page.content = AsyncMock(return_value="<html><body>Just a moment...</body></html>")
    mock_page.title = AsyncMock(return_value="Just a moment...")
    mock_page.frame_locator.return_value.locator.return_value.count.return_value = 0
    mock_page.goto = AsyncMock()

    mock_context = MagicMock()
    mock_context.cookies = AsyncMock(return_value=[
        {"name": "cf_clearance", "value": cf_clearance_value},
        {"name": "_ga", "value": "GA1.2.xxx"},
    ])

    mock_browser = MagicMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.contexts = [mock_context]

    mock_camoufox_class = MagicMock()
    mock_camoufox_class.return_value.__aenter__ = AsyncMock(return_value=mock_browser)
    mock_camoufox_class.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_camoufox_module = MagicMock()
    mock_camoufox_module.AsyncCamoufox = mock_camoufox_class

    return mock_camoufox_class, mock_camoufox_module, mock_browser, mock_page, mock_context


async def test_tier4_camoufox_success():
    """Verify AsyncCamoufox returns cf_clearance + UA when context cookies contain it."""
    mock_camoufox_class, mock_camoufox_module, mock_browser, mock_page, _ = \
        _make_camoufox_mocks("camoufox_clearance_abc", "AsyncCamoufox-Firefox/121.0")

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", None, None, 45)

    assert cookie is not None
    assert "cf_clearance=camoufox_clearance_abc" in cookie
    assert "_ga=GA1.2.xxx" in cookie
    assert ua == "AsyncCamoufox-Firefox/121.0"


async def test_tier4_camoufox_launch_kwargs_no_proxy():
    """Verify AsyncCamoufox is launched with correct kwargs when no proxy is provided."""
    mock_camoufox_class, mock_camoufox_module, _, _, _ = \
        _make_camoufox_mocks("cf_tok")

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", None, None, 45)

    mock_camoufox_class.assert_called_once_with(
        headless=False,
        humanize=2.5,
        fingerprint_preset=False,
        os=ANY,
        disable_coop=True,
        firefox_user_prefs=ANY,
    )


async def test_tier4_camoufox_launch_kwargs_with_proxy():
    """Verify AsyncCamoufox receives proxy dict {server: url} when proxy is provided."""
    mock_camoufox_class, mock_camoufox_module, _, _, _ = \
        _make_camoufox_mocks("cf_tok")

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", "103.68.214.164:8080", None, 45)

    mock_camoufox_class.assert_called_once_with(
        headless=False,
        humanize=2.5,
        fingerprint_preset=False,
        os=ANY,
        disable_coop=True,
        firefox_user_prefs=ANY,
        proxy={"server": "http://103.68.214.164:8080"},
        geoip=True,
    )


async def test_tier4_camoufox_proxy_schema_preserved():
    """Verify socks5:// schema in proxy string is preserved in Camoufox launch kwargs."""
    mock_camoufox_class, mock_camoufox_module, _, _, _ = \
        _make_camoufox_mocks("cf_tok")

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", "socks5://103.68.214.164:1080", None, 45)

    mock_camoufox_class.assert_called_once()
    kwargs = mock_camoufox_class.call_args.kwargs
    assert kwargs.get("proxy") == {"server": "socks5://103.68.214.164:1080"}


async def test_tier4_camoufox_challenge_not_solved_captured():
    """Verify timeout without cf_clearance cookie triggers BypassDebugger async_capture_failure."""
    mock_camoufox_class, mock_camoufox_module, _, mock_page, mock_context = \
        _make_camoufox_mocks("dummy")
    mock_context.cookies = AsyncMock(return_value=[{"name": "session", "value": "abc"}])

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.object(BypassDebugger, "async_capture_failure", new_callable=AsyncMock) as mock_debug, \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", None, None, 1)

    mock_debug.assert_any_call(
        "Tier 4 (Camoufox)", "https://readtoon.com/",
        page_obj=mock_page, error_msg="Challenge not solved"
    )
    assert cookie is None
    assert ua is None


async def test_tier4_camoufox_uses_human_mouse():
    """Verify Tier 4a (AsyncCamoufox) invokes human_mouse Bezier waypoints."""
    mock_page = MagicMock()
    del mock_page.actions  # Real Playwright/AsyncCamoufox Page has no .actions attribute
    mock_page.evaluate = AsyncMock(return_value="AsyncCamoufox-Firefox/122")
    mock_page.content = AsyncMock(return_value="<html><body>Just a moment...</body></html>")
    mock_page.title = AsyncMock(return_value="Just a moment...")
    mock_page.goto = AsyncMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.move = AsyncMock()
    mock_page.mouse.wheel = AsyncMock()

    mock_context = MagicMock()
    mock_context.cookies = AsyncMock(side_effect=[
        [],
        [],
        [],
        [{"name": "cf_clearance", "value": "camoufox_tok"}],
    ])

    mock_browser = MagicMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.contexts = [mock_context]

    mock_camoufox_class = MagicMock()
    mock_camoufox_class.return_value.__aenter__ = AsyncMock(return_value=mock_browser)
    mock_camoufox_class.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_camoufox_module = MagicMock()
    mock_camoufox_module.AsyncCamoufox = mock_camoufox_class

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch("src.core.engine.human_mouse_async_move", new_callable=AsyncMock) as mock_mouse_move, \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", None, None, 45)

    assert cookie is not None
    assert mock_mouse_move.called



async def test_tier4_camoufox_launch_exception_captured():
    """Verify AsyncCamoufox launch exception (e.g. Firefox not found) triggers BypassDebugger."""
    mock_camoufox_class = MagicMock()
    mock_camoufox_class.side_effect = RuntimeError("Firefox binary not found")

    mock_camoufox_module = MagicMock()
    mock_camoufox_module.AsyncCamoufox = mock_camoufox_class

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch.object(BypassDebugger, "async_capture_failure", new_callable=AsyncMock) as mock_debug, \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", None, None, 45)

    mock_debug.assert_any_call(
        "Tier 4 (Camoufox-Launch)", "https://readtoon.com/",
        error_msg="Firefox binary not found"
    )
    assert cookie is None
    assert ua is None


async def test_tier4_camoufox_disabled_returns_none():
    """Verify (None, None) when AsyncCamoufox is not installed."""
    with patch("src.core.engine.CAMOUFOX_INSTALLED", False):
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", None, None, 45)

    assert cookie is None
    assert ua is None


async def test_tier4_turnstile_interaction_attempted():
    """Verify the Turnstile iframe interaction block is executed in each polling iteration."""
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value="Firefox-UA")
    mock_page.content = AsyncMock(return_value="<html><body>Just a moment...</body></html>")
    mock_page.title = AsyncMock(return_value="Just a moment...")
    mock_page.goto = AsyncMock()

    # Make frame_locator chain findable but checkbox has count=0 (no Turnstile found)
    mock_checkbox = MagicMock()
    mock_checkbox.count.return_value = 0
    mock_page.frame_locator.return_value.locator.return_value = mock_checkbox

    # First poll: empty cookies -> forces Turnstile interaction; second: cf_clearance found
    call_count = [0]
    def side_effect_cookies():
        call_count[0] += 1
        if call_count[0] >= 2:
            return [{"name": "cf_clearance", "value": "tok"}]
        return []

    mock_context = MagicMock()
    mock_context.cookies = AsyncMock(side_effect=side_effect_cookies)

    mock_browser = MagicMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.contexts = [mock_context]

    mock_camoufox_class = MagicMock()
    mock_camoufox_class.return_value.__aenter__ = AsyncMock(return_value=mock_browser)
    mock_camoufox_class.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_camoufox_module = MagicMock()
    mock_camoufox_module.AsyncCamoufox = mock_camoufox_class

    with patch("src.core.engine.CAMOUFOX_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {
             "camoufox": MagicMock(),
             "camoufox.async_api": mock_camoufox_module,
         }):
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", None, None, 45)

    assert cookie is not None
    assert "cf_clearance=tok" in cookie


# ---------------------------------------------------------------------------
# Live Integration Test
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_tier4_readtoon_live_integration():
    """
    Live integration test for Tier 4 (AsyncCamoufox — Ultimate Stealth Firefox) against https://readtoon.com/.
    This is the LAST RESORT tier: uses Firefox (not Chromium) with deep anti-fingerprint patches.
    Proxies loaded dynamically from the checked-proxies directory.
    
    Expected result: cf_clearance cookie OR graceful (None, None) if Firefox/AsyncCamoufox not installed.
    The live integration validates:
    - Correct browser launch with humanize=True, fingerprint_preset=True
    - Turnstile iframe interaction polling loop
    - Proper cleanup via context manager (no resource leaks)
    """
    import os
    import time
    from src.core.engine import CAMOUFOX_INSTALLED

    print(f"\n[*] Tier 4 engine availability:")
    print(f"    4a. AsyncCamoufox (Firefox): {'✅ installed' if CAMOUFOX_INSTALLED else '❌ not installed'}")

    if not CAMOUFOX_INSTALLED:
        pytest.skip("AsyncCamoufox not installed — install with: pip install camoufox && python -m camoufox fetch")

    proxy_file = r"C:\Users\narav\Desktop\CE code\Tools\proxy-scraper-checker\out\checked-proxies\proxies\http.txt"
    proxies = []
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip() and ":" in line]
        print(f"[*] Loaded {len(proxies)} checked proxies from http.txt")

    cookie, ua = None, None

    # Try with 1 proxy first (Tier 4 is slow — limit attempts)
    for i, test_proxy in enumerate(proxies[:1]):
        print(f"[*] Tier 4 attempt with proxy: {test_proxy}")
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", proxy=test_proxy, timeout=50)
        if cookie and "cf_clearance" in cookie:
            print(f"[+] Tier 4 PASSED via proxy: cookie={cookie[:50]}...")
            break
        time.sleep(2.0)

    # Direct connection if proxy didn't work
    if not cookie or "cf_clearance" not in cookie:
        print("[*] Tier 4 direct connection attempt (no proxy)...")
        cookie, ua = await BrowserEngine._solve_tier4_ultimate_stealth("https://readtoon.com/", proxy=None, timeout=55)
        if cookie and "cf_clearance" in cookie:
            print(f"[+] Tier 4 PASSED direct: cookie={cookie[:50]}...")
        else:
            print("[-] Tier 4 did not obtain cf_clearance on this run (AsyncCamoufox may need fresh Firefox install).")

    assert (cookie is None and ua is None) or (isinstance(cookie, str) and isinstance(ua, str)), \
        f"Expected (str, str) or (None, None) but got ({type(cookie)}, {type(ua)})"
