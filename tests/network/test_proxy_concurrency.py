# tests/test_proxy_concurrency.py
import sys
import pytest
from src.core.engine import TacticalProxyValidator

def test_get_platform_semaphore_limit():
    limit = TacticalProxyValidator.get_platform_semaphore_limit()
    expected = 256 if sys.platform == "win32" else 512
    assert limit == expected
