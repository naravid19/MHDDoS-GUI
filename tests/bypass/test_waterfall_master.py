import sys
import unittest
from unittest.mock import patch, MagicMock

# Setup path
sys.path.append('.')

# Try to import after path setup
try:
    from src.core.engine import BrowserEngine
except ImportError as e:
    print(f"Failed to import BrowserEngine: {e}")
    sys.exit(1)

class TestWaterfallMaster(unittest.TestCase):
    @patch.object(BrowserEngine, '_solve_tier1_lightweight', return_value=(None, None))
    @patch.object(BrowserEngine, '_solve_tier2_fast_cdp', return_value=("cf_clearance=abc", "ua_test"))
    def test_solve_cf_internal_waterfall(self, mock_tier2, mock_tier1):
        cookie, ua = BrowserEngine._solve_cf_internal("https://test.com", None, "ua_test", 30)
        self.assertTrue(mock_tier1.called)
        self.assertTrue(mock_tier2.called)
        self.assertEqual(cookie, "cf_clearance=abc")
        self.assertEqual(ua, "ua_test")

if __name__ == '__main__':
    unittest.main()
