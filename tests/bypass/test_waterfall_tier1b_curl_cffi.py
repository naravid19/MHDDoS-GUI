import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.core.engine import BrowserEngine

class TestWaterfallTier1bCurlCffi:
    """Test suite for Tier 1b (curl_cffi)."""

    @pytest.mark.asyncio
    async def test_tier1b_curl_cffi_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = {"cf_clearance": "token123"}

        mock_session_inst = AsyncMock()
        mock_session_inst.get.return_value = mock_resp

        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session_inst

        with patch("src.core.engine.CURL_CFFI_INSTALLED", True), \
             patch("curl_cffi.requests.AsyncSession", mock_session_cls):
            cookie, ua = await BrowserEngine._solve_tier1_lightweight("https://readtoon.com", None, "UA", 10)

            assert cookie == "cf_clearance=token123"
            assert ua == "UA"
            mock_session_inst.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_tier1b_curl_cffi_challenge_fast_fail(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        mock_session_inst = AsyncMock()
        mock_session_inst.get.return_value = mock_resp

        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session_inst

        with patch("src.core.engine.CURL_CFFI_INSTALLED", True), \
             patch("curl_cffi.requests.AsyncSession", mock_session_cls), \
             patch.object(BrowserEngine, "_cf_challenge_active", return_value=True):
            cookie, ua = await BrowserEngine._solve_tier1_lightweight("https://readtoon.com", None, "UA", 10)

            assert cookie is None
            assert ua is None

    @pytest.mark.asyncio
    async def test_tier1b_curl_cffi_exception(self):
        mock_session_inst = AsyncMock()
        mock_session_inst.get.side_effect = Exception("TLS Error")

        mock_session_cls = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session_inst

        with patch("src.core.engine.CURL_CFFI_INSTALLED", True), \
             patch("curl_cffi.requests.AsyncSession", mock_session_cls):
            cookie, ua = await BrowserEngine._solve_tier1_lightweight("https://readtoon.com", None, "UA", 10)

            assert cookie is None
            assert ua is None
