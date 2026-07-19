import sys
import pytest
from unittest.mock import AsyncMock, patch

sys.path.append('.')

try:
    from src.core.engine import BrowserEngine
except ImportError as e:
    print(f"Failed to import BrowserEngine: {e}")
    sys.exit(1)

@pytest.mark.asyncio
@patch.object(BrowserEngine, '_solve_tier1_lightweight', new_callable=AsyncMock, return_value=(None, None))
@patch.object(BrowserEngine, '_solve_tier2_fast_cdp', new_callable=AsyncMock, return_value=("cf_clearance=abc", "ua_test"))
async def test_solve_cf_internal_async_waterfall(mock_tier2, mock_tier1):
    cookie, ua = await BrowserEngine._solve_cf_internal_async("https://test.com", None, "ua_test", 30)
    assert mock_tier1.called
    assert mock_tier2.called
    assert cookie == "cf_clearance=abc"
    assert ua == "ua_test"
