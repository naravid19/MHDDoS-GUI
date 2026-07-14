# tests/test_engine_latency.py
import asyncio
from unittest.mock import patch
import pytest
from src.core.engine import CURRENT_LATENCY

class MockResponse:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class MockSession:
    def __init__(self, response):
        self.response = response

    def get(self, url, timeout=None):
        return self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.mark.asyncio
async def test_latency_checker_detects_waf_challenge():
    # Reset latency
    CURRENT_LATENCY.value = 0.0
    
    mock_response = MockResponse(
        status=503,
        text="<html><title>Just a moment...</title><body>Cloudflare Turnstile Check</body></html>"
    )
    mock_session = MockSession(mock_response)
    
    with patch("src.core.engine.aiohttp.ClientSession", return_value=mock_session):
        # We import and run the check logic in isolation
        from src.core.engine import _check_target_latency_once
        await _check_target_latency_once("https", "readtoon.com", 443, 5)
        
    assert CURRENT_LATENCY.value == -1.0, f"Expected -1.0 for WAF challenge, got {CURRENT_LATENCY.value}"


@pytest.mark.asyncio
async def test_latency_checker_records_positive_latency_on_success():
    # Reset latency
    CURRENT_LATENCY.value = -1.0
    
    mock_response = MockResponse(
        status=200,
        text="<html><body>OK</body></html>"
    )
    mock_session = MockSession(mock_response)
    
    with patch("src.core.engine.aiohttp.ClientSession", return_value=mock_session):
        from src.core.engine import _check_target_latency_once
        await _check_target_latency_once("https", "readtoon.com", 443, 5)
        
    assert CURRENT_LATENCY.value > 0.0, f"Expected positive latency, got {CURRENT_LATENCY.value}"


@pytest.mark.asyncio
async def test_latency_checker_records_negative_one_on_exception():
    # Reset latency
    CURRENT_LATENCY.value = 100.0
    
    # Mock ClientSession to raise an exception on creation
    with patch("src.core.engine.aiohttp.ClientSession", side_effect=Exception("Connection failed")):
        from src.core.engine import _check_target_latency_once
        await _check_target_latency_once("https", "readtoon.com", 443, 5)
        
    assert CURRENT_LATENCY.value == -1.0, f"Expected -1.0 on Exception, got {CURRENT_LATENCY.value}"


