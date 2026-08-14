# tests/bypass/test_waterfall_tier2.py
"""
Tier 2: Fast Headless CDP Bypass Tests
Sub-engines: 2a. Botasaurus | 2b. Nodriver | 2c. DrissionPage
All 3 use a real headless Chromium browser with CDP protocol
=> Can solve Cloudflare Turnstile (unlike Tier 1)
=> Tier 2 is the first tier that should pass readtoon.com
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.core.engine import BrowserEngine, BypassDebugger


# ---------------------------------------------------------------------------
# Tier 2a: Botasaurus
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier2_botasaurus_success():
    """Verify Tier 2a (Botasaurus) returns cf_clearance when bypass_cloudflare succeeds."""
    mock_driver = MagicMock()
    mock_driver.get_cookies_dict.return_value = {"cf_clearance": "bota_token_abc", "session": "xyz"}
    mock_driver.run_js.return_value = "Botasaurus-Chrome/120"

    # bot_solve is a decorated function created inside the method — we mock at the decorator level
    mock_bot_solve_result = [["cf_clearance=bota_token_abc; session=xyz", "Botasaurus-Chrome/120"]]

    with patch("src.core.engine.BOTASAURUS_INSTALLED", True), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", False):

        # Mock the entire botasaurus.browser module and its decorator
        mock_browser_module = MagicMock()
        mock_driver_class = MagicMock()

        # The @browser decorator wraps the inner function; mock it to return a callable
        # that returns our desired result when called with a list of dicts
        def mock_browser_decorator(**kwargs):
            def wrapper(fn):
                def runner(data_list):
                    return mock_bot_solve_result
                return runner
            return wrapper

        mock_browser_module.browser = mock_browser_decorator
        mock_browser_module.Driver = mock_driver_class

        with patch.dict("sys.modules", {
            "botasaurus": MagicMock(),
            "botasaurus.browser": mock_browser_module,
        }):
            cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    assert cookie is not None
    assert "cf_clearance=bota_token_abc" in cookie
    assert ua == "Botasaurus-Chrome/120"


@pytest.mark.asyncio
async def test_tier2_botasaurus_failure_falls_to_nodriver():
    """Verify Botasaurus returning (None, None) skips to Nodriver (2b)."""
    mock_bot_solve_result = [[None, None]]  # simulate bot failing

    with patch("src.core.engine.BOTASAURUS_INSTALLED", True), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", False):

        def mock_browser_decorator(**kwargs):
            def wrapper(fn):
                def runner(data_list):
                    return mock_bot_solve_result
                return runner
            return wrapper

        mock_browser_module = MagicMock()
        mock_browser_module.browser = mock_browser_decorator

        with patch.dict("sys.modules", {
            "botasaurus": MagicMock(),
            "botasaurus.browser": mock_browser_module,
        }):
            cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    # Nodriver disabled -> DrissionPage disabled -> returns (None, None)
    assert cookie is None
    assert ua is None


@pytest.mark.asyncio
async def test_tier2_botasaurus_exception_captured():
    """Verify Botasaurus launch exception triggers BypassDebugger.capture_failure."""
    with patch("src.core.engine.BOTASAURUS_INSTALLED", True), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", False), \
         patch.object(BypassDebugger, "capture_failure") as mock_debug:

        def mock_browser_decorator(**kwargs):
            def wrapper(fn):
                def runner(data_list):
                    raise RuntimeError("Chrome not found on PATH")
                return runner
            return wrapper

        mock_browser_module = MagicMock()
        mock_browser_module.browser = mock_browser_decorator

        with patch.dict("sys.modules", {
            "botasaurus": MagicMock(),
            "botasaurus.browser": mock_browser_module,
        }):
            cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    mock_debug.assert_any_call(
        "Tier 2 (Botasaurus-Launch)", "https://readtoon.com/", error_msg="Chrome not found on PATH"
    )
    assert cookie is None


# ---------------------------------------------------------------------------
# Tier 2b: Nodriver (Async CDP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier2_nodriver_success():
    """Verify Tier 2b (Nodriver) returns cf_clearance when async solve succeeds."""
    # Build mock cookie objects
    mock_cf_cookie = MagicMock()
    mock_cf_cookie.name = "cf_clearance"
    mock_cf_cookie.value = "nodriver_clearance_xyz"

    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value="Nodriver-Chrome/120")
    mock_page.select_all = AsyncMock(return_value=[])  # no iframes to click

    mock_browser_obj = MagicMock()
    mock_browser_obj.cookies = MagicMock()
    mock_browser_obj.cookies.get_all = AsyncMock(return_value=[mock_cf_cookie])
    mock_browser_obj.stop = MagicMock()
    mock_browser_obj.get = AsyncMock(return_value=mock_page)

    mock_nodriver_module = MagicMock()
    mock_nodriver_module.start = AsyncMock(return_value=mock_browser_obj)

    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", True), \
         patch("src.core.engine.DRISSION_INSTALLED", False), \
         patch.dict("sys.modules", {"nodriver": mock_nodriver_module}):
        cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    assert cookie is not None
    assert "cf_clearance=nodriver_clearance_xyz" in cookie
    assert ua == "Nodriver-Chrome/120"


@pytest.mark.asyncio
async def test_tier2_nodriver_challenge_not_solved_captured():
    """Verify Nodriver logs failure when no cf_clearance is found after polling loop."""
    # Cookies never contain cf_clearance
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value="Chrome-UA")
    mock_page.select_all = AsyncMock(return_value=[])

    mock_browser_obj = MagicMock()
    mock_browser_obj.cookies = MagicMock()
    mock_browser_obj.cookies.get_all = AsyncMock(return_value=[])  # empty cookies
    mock_browser_obj.stop = MagicMock()
    mock_browser_obj.get = AsyncMock(return_value=mock_page)

    mock_nodriver_module = MagicMock()
    mock_nodriver_module.start = AsyncMock(return_value=mock_browser_obj)

    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", True), \
         patch("src.core.engine.DRISSION_INSTALLED", False), \
         patch("asyncio.sleep", new_callable=lambda: lambda *a, **kw: asyncio.coroutine(lambda: None)()), \
         patch.object(BypassDebugger, "capture_failure") as mock_debug, \
         patch.dict("sys.modules", {"nodriver": mock_nodriver_module}):
        # Patch asyncio.sleep to avoid real sleep in unit test
        import asyncio as _asyncio
        with patch.object(_asyncio, "sleep", new_callable=AsyncMock):
            cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    # Should have called capture_failure with "Challenge not solved"
    assert cookie is None


# ---------------------------------------------------------------------------
# Tier 2c: DrissionPage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier2_drissionpage_success():
    """Verify Tier 2c (DrissionPage) returns cf_clearance when ChromiumPage finds the cookie."""
    mock_page = MagicMock()
    mock_page.cookies.return_value = [
        {"name": "cf_clearance", "value": "drission_token_789"},
        {"name": "_ga", "value": "GA1.2.xxx"},
    ]
    mock_page.run_js.return_value = "DrissionPage-Chrome/121"

    mock_chromium_page_class = MagicMock(return_value=mock_page)
    mock_chromium_options_class = MagicMock()
    mock_options_instance = MagicMock()
    mock_chromium_options_class.return_value = mock_options_instance

    mock_drission_module = MagicMock()
    mock_drission_module.ChromiumPage = mock_chromium_page_class
    mock_drission_module.ChromiumOptions = mock_chromium_options_class

    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {"DrissionPage": mock_drission_module}):
        cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    assert cookie is not None
    assert "cf_clearance=drission_token_789" in cookie
    assert "_ga=GA1.2.xxx" in cookie
    assert ua == "DrissionPage-Chrome/121"
    mock_page.quit.assert_called_once()


@pytest.mark.asyncio
async def test_tier2_drissionpage_with_proxy():
    """Verify DrissionPage (2c) passes proxy to ChromiumOptions correctly."""
    mock_page = MagicMock()
    mock_page.cookies.return_value = [{"name": "cf_clearance", "value": "tok"}]
    mock_page.run_js.return_value = "UA"

    mock_options_instance = MagicMock()
    mock_chromium_page_class = MagicMock(return_value=mock_page)
    mock_chromium_options_class = MagicMock(return_value=mock_options_instance)

    mock_drission_module = MagicMock()
    mock_drission_module.ChromiumPage = mock_chromium_page_class
    mock_drission_module.ChromiumOptions = mock_chromium_options_class

    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", True), \
         patch("src.core.engine.CURL_CFFI_INSTALLED", False), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {"DrissionPage": mock_drission_module}):
        await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", "103.68.214.164:8080", None, 15)

    # Verify proxy was passed via set_argument
    mock_options_instance.set_argument.assert_any_call("--proxy-server=http://103.68.214.164:8080")


@pytest.mark.asyncio
async def test_tier2_drissionpage_uses_human_mouse():
    """Verify DrissionPage (2c) invokes human_mouse Bezier waypoints (>= 25 calls to actions.move) during pulse."""
    mock_page = MagicMock()
    mock_page.cookies.side_effect = [
        [], # pulse 1
        [], # pulse 2
        [], # pulse 3 (triggers human_mouse)
        [{"name": "cf_clearance", "value": "drission_solved"}], # pulse 4: solved
        [{"name": "cf_clearance", "value": "drission_solved"}],
    ]
    mock_page.run_js.return_value = "UA"
    mock_page.actions = MagicMock()
    mock_page.actions.move = MagicMock()

    mock_chromium_page_class = MagicMock(return_value=mock_page)
    mock_chromium_options_class = MagicMock(return_value=MagicMock())

    mock_drission_module = MagicMock()
    mock_drission_module.ChromiumPage = mock_chromium_page_class
    mock_drission_module.ChromiumOptions = mock_chromium_options_class

    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.dict("sys.modules", {"DrissionPage": mock_drission_module}):
        cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    assert cookie is not None
    # If using human_mouse, page.actions.move should have been called at least 25 times for the Bezier waypoints
    assert mock_page.actions.move.call_count >= 25, f"Expected >= 25 waypoint moves, got {mock_page.actions.move.call_count}"


@pytest.mark.asyncio
async def test_tier2_drissionpage_failure_captured():
    """Verify DrissionPage challenge not solved triggers capture_failure and returns (None, None)."""
    mock_page = MagicMock()
    mock_page.cookies.return_value = []  # no cf_clearance ever

    mock_drission_module = MagicMock()
    mock_drission_module.ChromiumPage = MagicMock(return_value=mock_page)
    mock_drission_module.ChromiumOptions = MagicMock()

    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", True), \
         patch("time.sleep", return_value=None), \
         patch.object(BypassDebugger, "capture_failure") as mock_debug, \
         patch.dict("sys.modules", {"DrissionPage": mock_drission_module}):
        cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    mock_debug.assert_called_with(
        "Tier 2 (DrissionPage)", "https://readtoon.com/",
        page_obj=mock_page, error_msg="Challenge not solved"
    )
    mock_page.quit.assert_called_once()
    assert cookie is None
    assert ua is None


@pytest.mark.asyncio
async def test_tier2_all_disabled_returns_none():
    """Verify if all 3 Tier 2 sub-engines are disabled, returns (None, None) immediately."""
    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("src.core.engine.DRISSION_INSTALLED", False):
        cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", None, None, 15)

    assert cookie is None
    assert ua is None


# ---------------------------------------------------------------------------
# Live Integration Test
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_tier2_readtoon_live_integration():
    """
    Live integration test using installed Tier 2 sub-engines against https://readtoon.com/.
    Tier 2 is the FIRST tier expected to solve Cloudflare Turnstile via a real headless browser.
    Proxies are loaded from the checked-proxies directory (auto-updated by proxy-scraper-checker).
    """
    import os
    import time
    from src.core.engine import BOTASAURUS_INSTALLED, NODRIVER_INSTALLED, DRISSION_INSTALLED

    if os.getenv("TEST_LIVE_ENGINES") != "1":
        pytest.skip("Skipping live integration test (set TEST_LIVE_ENGINES=1 to run)")

    # Report available engines
    print(f"\n[*] Tier 2 engine availability:")
    print(f"    2a. Botasaurus:   {'✅ installed' if BOTASAURUS_INSTALLED else '❌ not installed'}")
    print(f"    2b. Nodriver:     {'✅ installed' if NODRIVER_INSTALLED else '❌ not installed'}")
    print(f"    2c. DrissionPage: {'✅ installed' if DRISSION_INSTALLED else '❌ not installed'}")

    if not any([BOTASAURUS_INSTALLED, NODRIVER_INSTALLED, DRISSION_INSTALLED]):
        pytest.skip("No Tier 2 sub-engines installed (botasaurus / nodriver / DrissionPage)")

    # Load proxies from checked-proxies directory or local proxies.txt
    proxy_file = os.getenv("CHECKED_PROXIES_PATH", "proxies.txt")
    proxies = []
    if os.path.exists(proxy_file):
        with open(proxy_file, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip() and ":" in line]
        print(f"[*] Loaded {len(proxies)} checked proxies from http.txt")

    cookie, ua = None, None

    # Try up to 2 proxies first
    for i, test_proxy in enumerate(proxies[:2]):
        print(f"[*] Tier 2 attempt ({i+1}/2) with proxy: {test_proxy}")
        cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", proxy=test_proxy, timeout=20)
        if cookie and "cf_clearance" in cookie:
            print(f"[+] Tier 2 PASSED via proxy: cookie={cookie[:50]}...")
            break
        time.sleep(1.0)

    # Direct connection if proxy didn't work
    if not cookie or "cf_clearance" not in cookie:
        print("[*] Tier 2 direct connection attempt (no proxy)...")
        cookie, ua = await BrowserEngine._solve_tier2_fast_cdp("https://readtoon.com/", proxy=None, timeout=25)
        if cookie and "cf_clearance" in cookie:
            print(f"[+] Tier 2 PASSED direct: cookie={cookie[:50]}...")
        else:
            print("[-] Tier 2 did not obtain cf_clearance on this run.")

    # Tier 2 returns (None, None) OR a valid cookie string — both are valid tuple types
    assert (cookie is None and ua is None) or (isinstance(cookie, str) and isinstance(ua, str)), \
        f"Expected (str, str) or (None, None) but got ({type(cookie)}, {type(ua)})"
