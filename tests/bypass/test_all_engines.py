"""
Comprehensive Dedicated Test Suite for All MHDDoS-GUI Bypass Engines (Tier 0 to Tier 4)
========================================================================================
This test suite specifically validates every anti-bot and Cloudflare bypass engine
integrated into BrowserEngine:
  - Tier 0: FlareSolverr API
  - Tier 1a: Cloudscraper
  - Tier 1b: curl_cffi
  - Tier 2a: Botasaurus
  - Tier 2b: Nodriver (async Chromium)
  - Tier 2c: DrissionPage (ChromiumPage)
  - Tier 3a: CloakBrowser
  - Tier 3b: Patchright (Stealth Playwright)
  - Tier 3c: Undetected Chromedriver (UC)
  - Tier 4a: Camoufox (Ultimate Stealth Firefox Anti-Detect)

It includes both:
  1. Unit & behavioral verification of engine orchestration and proxy/cookie extraction.
  2. Installation & version integrity checks (confirming Playwright pinned to 1.59.0).
  3. Live network/driver verification (enabled when TEST_LIVE_ENGINES=1 or via pytest markers).
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.engine import (
    BOTASAURUS_INSTALLED,
    CAMOUFOX_INSTALLED,
    CLOAKBROWSER_INSTALLED,
    CURL_CFFI_INSTALLED,
    DRISSION_INSTALLED,
    NODRIVER_INSTALLED,
    PATCHRIGHT_INSTALLED,
    PLAYWRIGHT_INSTALLED,
    UNDETECTED_CHROMEDRIVER_INSTALLED,
    BrowserEngine,
    HttpFlood,
)

# Windows event loop stability for async browser drivers
if sys.platform == "win32":
    import warnings
    from asyncio.proactor_events import _ProactorBasePipeTransport
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<.*pipe.*>")
    _original_repr = _ProactorBasePipeTransport.__repr__
    def _safe_repr(self):
        try:
            return _original_repr(self)
        except Exception:
            return "<_ProactorBasePipeTransport closed=True>"
    _ProactorBasePipeTransport.__repr__ = _safe_repr


# ==============================================================================
# SECTION 1: Installation & Version Integrity Checks
# ==============================================================================

def test_engine_library_installation_flags():
    """Verify that core bypass engine packages are detected and installed."""
    assert CURL_CFFI_INSTALLED is True, "curl_cffi must be installed for Tier 1b"
    assert NODRIVER_INSTALLED is True, "nodriver must be installed for Tier 2b"
    assert DRISSION_INSTALLED is True, "DrissionPage must be installed for Tier 2c"
    assert PATCHRIGHT_INSTALLED is True, "patchright must be installed for Tier 3b"
    assert UNDETECTED_CHROMEDRIVER_INSTALLED is True, "undetected-chromedriver must be installed for Tier 3c"
    assert CAMOUFOX_INSTALLED is True, "camoufox must be installed for Tier 4a"
    assert BOTASAURUS_INSTALLED is True, "botasaurus must be installed for Tier 2a"
    assert PLAYWRIGHT_INSTALLED is True, "playwright must be installed for browser bridges"


def test_playwright_version_pinned_for_camoufox():
    """Ensure Playwright is specifically pinned to 1.59.0 to prevent Juggler protocol crashes."""
    try:
        import importlib.metadata
        version = importlib.metadata.version("playwright")
        assert version == "1.59.0", (
            f"Playwright version {version} detected! Must be exactly 1.59.0 to maintain "
            f"compatibility with Camoufox/Firefox Juggler."
        )
    except importlib.metadata.PackageNotFoundError:
        pytest.fail("playwright package could not be found in installed distribution metadata")


# ==============================================================================
# SECTION 2: Unit & Behavioral Verification of Individual Tiers & Engines
# ==============================================================================



def test_tier0_flaresolverr_api_success():
    """Test Tier 0 (FlareSolverr API) successful clearance acquisition."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"status": "ok", "solution": {"cookies": [{"name": "cf_clearance", "value": "flaresolverr_token_123"}], "userAgent": "Mozilla/5.0 FlareSolverr UA"}}'
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
        # Enable FlareSolverr in ENGINE_STATE
        with patch("src.core.engine.ENGINE_STATE") as mock_state, \
             patch("src.core.engine.BrowserEngine._solve_tier1_lightweight", return_value=(None, None)), \
             patch("src.core.engine.BrowserEngine._solve_tier2_fast_cdp", return_value=(None, None)), \
             patch("src.core.engine.BrowserEngine._solve_tier3_heavy_stealth", return_value=(None, None)), \
             patch("src.core.engine.BrowserEngine._solve_tier4_ultimate_stealth", return_value=(None, None)):
            mock_state.flaresolverr_url = "http://localhost:8191/v1"
            mock_state.flaresolverr_tabs = None
            cookie, ua = BrowserEngine.solve_cf("https://protected.com", timeout=10)

            assert cookie == "cf_clearance=flaresolverr_token_123"
            assert ua == "Mozilla/5.0 FlareSolverr UA"
            assert HttpFlood._active_solver == "Tier 0 (FlareSolverr)"
            mock_url.assert_called_once()


def test_tier1a_cloudscraper_success():
    """Test Tier 1a (Cloudscraper) solver method handling headers and clearance cookies."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.cookies = {"cf_clearance": "cloudscraper_clearance_abc", "sessionid": "xyz"}
    mock_resp.request.headers = {"User-Agent": "CloudScraper/1.2 UA"}

    mock_scraper = MagicMock()
    mock_scraper.get.return_value = mock_resp

    with patch("cloudscraper.create_scraper", return_value=mock_scraper):
        cookie, ua = BrowserEngine._solve_tier1_lightweight("https://target.com", proxy="127.0.0.1:8080")

        assert "cf_clearance=cloudscraper_clearance_abc" in cookie
        assert ua == "CloudScraper/1.2 UA"
        mock_scraper.get.assert_called_once()
        assert mock_scraper.proxies == {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}


def test_tier1b_curl_cffi_success():
    """Test Tier 1b (curl_cffi) solver fallback inside Tier 1."""
    # Force cloudscraper to fail or return 403
    mock_cs_resp = MagicMock()
    mock_cs_resp.status_code = 403
    mock_cs_scraper = MagicMock()
    mock_cs_scraper.get.return_value = mock_cs_resp

    mock_curl_resp = MagicMock()
    mock_curl_resp.status_code = 200
    mock_curl_resp.cookies = {"cf_clearance": "curl_cffi_clearance_789"}

    mock_curl_session = MagicMock()
    mock_curl_session.__enter__.return_value = mock_curl_session
    mock_curl_session.__exit__.return_value = None
    mock_curl_session.get.return_value = mock_curl_resp

    with patch("cloudscraper.create_scraper", return_value=mock_cs_scraper), \
         patch("src.core.engine.CURL_CFFI_INSTALLED", True), \
         patch("curl_cffi.requests.Session", return_value=mock_curl_session):

        cookie, ua = BrowserEngine._solve_tier1_lightweight("https://target.com", user_agent="Custom-UA/1.0")

        assert "cf_clearance=curl_cffi_clearance_789" in cookie
        assert ua == "Custom-UA/1.0"
        mock_curl_session.get.assert_called_once()


def test_tier2a_botasaurus_success():
    """Test Tier 2a (Botasaurus) browser wrapper verification."""
    if not BOTASAURUS_INSTALLED:
        pytest.skip("botasaurus not installed")

    # Mock bot_solve return value from inner decorated function
    with patch("src.core.engine.BOTASAURUS_INSTALLED", True):
        # We mock botasaurus.browser.browser to return our dummy solver
        def fake_browser(*args, **kwargs):
            def decorator(func):
                def wrapper(data_list):
                    return [("cf_clearance=botasaurus_cookie_111", "Botasaurus/4.0 UA")]
                return wrapper
            return decorator

        with patch("botasaurus.browser.browser", side_effect=fake_browser):
            cookie, ua = BrowserEngine._solve_tier2_fast_cdp("https://target.com")
            assert cookie == "cf_clearance=botasaurus_cookie_111"
            assert ua == "Botasaurus/4.0 UA"


def test_tier2b_nodriver_success():
    """Test Tier 2b (Nodriver) async CDP verification and iframe challenge click logic."""
    if not NODRIVER_INSTALLED:
        pytest.skip("nodriver not installed")

    mock_cookie = MagicMock()
    mock_cookie.name = "cf_clearance"
    mock_cookie.value = "nodriver_cookie_222"

    mock_browser = AsyncMock()
    mock_browser.cookies.get_all.return_value = [mock_cookie]
    mock_page = AsyncMock()
    mock_page.evaluate.return_value = "Nodriver/0.48 UA"
    mock_browser.get.return_value = mock_page

    with patch("nodriver.start", return_value=mock_browser), \
         patch("src.core.engine.BOTASAURUS_INSTALLED", False):  # Skip Botasaurus first

        cookie, ua = BrowserEngine._solve_tier2_fast_cdp("https://target.com", timeout=5)
        assert cookie == "cf_clearance=nodriver_cookie_222"
        assert ua == "Nodriver/0.48 UA"
        mock_browser.stop.assert_called_once()


def test_tier2c_drissionpage_success():
    """Test Tier 2c (DrissionPage) solver logic."""
    if not DRISSION_INSTALLED:
        pytest.skip("DrissionPage not installed")

    mock_page = MagicMock()
    mock_page.cookies.return_value = [{"name": "cf_clearance", "value": "drission_cookie_333"}]
    mock_page.run_js.return_value = "DrissionPage Chromium UA"

    with patch("src.core.engine.BOTASAURUS_INSTALLED", False), \
         patch("src.core.engine.NODRIVER_INSTALLED", False), \
         patch("DrissionPage.ChromiumPage", return_value=mock_page), \
         patch("DrissionPage.ChromiumOptions"):

        cookie, ua = BrowserEngine._solve_tier2_fast_cdp("https://target.com", timeout=5)
        assert cookie == "cf_clearance=drission_cookie_333"
        assert ua == "DrissionPage Chromium UA"
        mock_page.quit.assert_called_once()


def test_tier3b_patchright_success():
    """Test Tier 3b (Patchright) stealth Playwright logic."""
    if not PATCHRIGHT_INSTALLED:
        pytest.skip("patchright not installed")

    mock_page = MagicMock()
    mock_page.evaluate.return_value = "Patchright/1.49 UA"
    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "patchright_cookie_444"}]
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_playwright_context = MagicMock()
    mock_playwright_context.chromium.launch.return_value = mock_browser
    mock_sync_p = MagicMock()
    mock_sync_p.__enter__.return_value = mock_playwright_context
    mock_sync_p.__exit__.return_value = None

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("patchright.sync_api.sync_playwright", return_value=mock_sync_p):

        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://target.com", timeout=5)
        assert cookie == "cf_clearance=patchright_cookie_444"
        assert ua == "Patchright/1.49 UA"
        mock_browser.close.assert_called_once()


def test_tier3c_undetected_chromedriver_success():
    """Test Tier 3c (Undetected Chromedriver) solver verification."""
    if not UNDETECTED_CHROMEDRIVER_INSTALLED:
        pytest.skip("undetected_chromedriver not installed")

    mock_driver = MagicMock()
    mock_driver.get_cookies.return_value = [{"name": "cf_clearance", "value": "uc_cookie_555"}]
    mock_driver.execute_script.return_value = "Undetected-Chromedriver UA"

    with patch("src.core.engine.CLOAKBROWSER_INSTALLED", False), \
         patch("src.core.engine.PATCHRIGHT_INSTALLED", False), \
         patch("src.core.engine._launch_uc_chrome", return_value=mock_driver):

        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://target.com", timeout=5)
        assert cookie == "cf_clearance=uc_cookie_555"
        assert ua == "Undetected-Chromedriver UA"
        mock_driver.quit.assert_called_once()


def test_tier4a_camoufox_success():
    """Test Tier 4a (Camoufox Ultimate Stealth Firefox Anti-Detect) solver."""
    if not CAMOUFOX_INSTALLED:
        pytest.skip("camoufox not installed")

    mock_page = MagicMock()
    mock_page.evaluate.return_value = "Camoufox Firefox/133.0 UA"
    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "camoufox_cookie_999"}]
    mock_browser = MagicMock()
    mock_browser.contexts = [mock_context]
    mock_browser.new_page.return_value = mock_page
    mock_browser.__enter__.return_value = mock_browser
    mock_browser.__exit__.return_value = None

    with patch("camoufox.sync_api.Camoufox", return_value=mock_browser):
        cookie, ua = BrowserEngine._solve_tier4_ultimate_stealth("https://target.com", proxy="1.2.3.4:8080", timeout=5)
        assert cookie == "cf_clearance=camoufox_cookie_999"
        assert ua == "Camoufox Firefox/133.0 UA"
        mock_page.goto.assert_called_once()


# ==============================================================================
# SECTION 3: Cascade Fallback Progression & Orchestration
# ==============================================================================

def test_full_cascade_fallback_progression():
    """Verify that BrowserEngine.solve_cf cascades smoothly from Tier 1 -> Tier 2 -> Tier 3 -> Tier 4 upon failures."""
    with patch("src.core.engine.ENGINE_STATE") as mock_state, \
         patch.object(BrowserEngine, "_solve_tier1_lightweight", return_value=(None, None)) as m_tier1, \
         patch.object(BrowserEngine, "_solve_tier2_fast_cdp", return_value=(None, None)) as m_tier2, \
         patch.object(BrowserEngine, "_solve_tier3_heavy_stealth", return_value=(None, None)) as m_tier3, \
         patch.object(BrowserEngine, "_solve_tier4_ultimate_stealth", return_value=("cf_clearance=final_tier4", "UA-Tier4")) as m_tier4:

        mock_state.flaresolverr_url = None  # No Tier 0 configured

        cookie, ua = BrowserEngine.solve_cf("https://target-cascade.com", timeout=30)

        assert cookie == "cf_clearance=final_tier4"
        assert ua == "UA-Tier4"
        assert HttpFlood._active_solver == "Tier 4"

        m_tier1.assert_called_once()
        m_tier2.assert_called_once()
        m_tier3.assert_called_once()
        m_tier4.assert_called_once()


# ==============================================================================
# SECTION 4: Live Functional Verification (Enabled via TEST_LIVE_ENGINES=1)
# ==============================================================================

@pytest.mark.skipif(
    os.environ.get("TEST_LIVE_ENGINES") != "1",
    reason="Live browser engine tests disabled by default. Run with TEST_LIVE_ENGINES=1 to execute against live targets."
)
def test_live_engine_basic_connectivity():
    """Test actual live engine connectivity against example.com to confirm binary and protocol integrity."""
    test_url = "http://example.com"
    print(f"\n[LIVE TEST] Executing live engine checks against {test_url}...")

    # 1. Cloudscraper
    if CURL_CFFI_INSTALLED:
        cookie, ua = BrowserEngine._solve_tier1_lightweight(test_url, timeout=10)
        print(f"  -> Tier 1 Result: Cookie={'yes' if cookie else 'no'}, UA={ua[:30] if ua else 'none'}...")

    # 2. Fast CDP / DrissionPage / Nodriver
    cookie, ua = BrowserEngine._solve_tier2_fast_cdp(test_url, timeout=15)
    print(f"  -> Tier 2 Result: Cookie={'yes' if cookie else 'no'}, UA={ua[:30] if ua else 'none'}...")

    # 3. Patchright / UC
    cookie, ua = BrowserEngine._solve_tier3_heavy_stealth(test_url, timeout=20)
    print(f"  -> Tier 3 Result: Cookie={'yes' if cookie else 'no'}, UA={ua[:30] if ua else 'none'}...")

    # 4. Camoufox
    if CAMOUFOX_INSTALLED:
        cookie, ua = BrowserEngine._solve_tier4_ultimate_stealth(test_url, timeout=25)
        print(f"  -> Tier 4 Result: Cookie={'yes' if cookie else 'no'}, UA={ua[:30] if ua else 'none'}...")
