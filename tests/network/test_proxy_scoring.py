# tests/test_proxy_scoring.py
import pytest
from unittest.mock import MagicMock
from src.core.engine import TacticalProxyValidator

def test_cloudflare_proxy_scoring_elite_count():
    # p1 and p2 should be counted as elite as status codes 403 and 503 are valid for Cloudflare checks
    p1 = MagicMock(latency=500, http_status=403)
    p2 = MagicMock(latency=1200, http_status=503)
    p3 = MagicMock(latency=4000, http_status=200) # lat too high -> not elite
    
    assert TacticalProxyValidator.count_elite_proxies([p1, p2, p3]) == 2
