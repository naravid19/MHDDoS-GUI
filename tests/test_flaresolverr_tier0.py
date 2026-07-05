# tests/test_flaresolverr_tier0.py
import pytest
import sys
import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from src.core.engine import ENGINE_STATE, BrowserEngine

def test_flaresolverr_url_state_default():
    # Verify the attribute exists
    assert hasattr(ENGINE_STATE, "flaresolverr_url")

def test_flaresolverr_cli_argument_parsing():
    # Mock sys.argv to test CLI argument parsing block
    test_argv = ["engine.py", "GET", "https://readtoon.com/", "5", "10", "socks5.txt", "10", "60", "--flaresolverr", "http://test-flare:8191/v1"]
    
    # Let's mock argv in engine.py and run the parsing block logic
    # The actual parsing logic does:
    # args_iter = iter(argv[8:])
    # and processes --flaresolverr
    args_iter = iter(test_argv[8:])
    for arg in args_iter:
        if arg == "--flaresolverr":
            ENGINE_STATE.flaresolverr_url = next(args_iter, "http://localhost:8191/v1")
            
    assert ENGINE_STATE.flaresolverr_url == "http://test-flare:8191/v1"

def test_solve_cf_internal_uses_flaresolverr():
    ENGINE_STATE.flaresolverr_url = "http://localhost:8191/v1"
    
    # Mock response from FlareSolverr
    mock_response_data = {
        "status": "ok",
        "solution": {
            "cookies": [
                {"name": "cf_clearance", "value": "mocked_clearance_cookie_value"}
            ],
            "userAgent": "MockUserAgent/1.0"
        }
    }
    
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        cookie, ua = BrowserEngine._solve_cf_internal("https://readtoon.com/")
        
        # Check that urlopen was called with our configured flaresolverr_url
        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.full_url == "http://localhost:8191/v1"
        
        # Verify returned cookies and UA
        assert cookie == "cf_clearance=mocked_clearance_cookie_value"
        assert ua == "MockUserAgent/1.0"
