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

class TestWaterfallTier1(unittest.TestCase):
    @patch('cloudscraper.create_scraper')
    def test_solve_tier1_cloudscraper_success(self, mock_create_scraper):
        mock_scraper = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.cookies = {"cf_clearance": "token_123"}
        mock_resp.request.headers = {"User-Agent": "test_ua"}
        mock_scraper.get.return_value = mock_resp
        mock_create_scraper.return_value = mock_scraper

        cookie, ua = BrowserEngine._solve_tier1_lightweight("https://test.com", None, "test_ua", 10)
        
        # Check if the result is correct
        self.assertIsNotNone(cookie)
        self.assertIn("cf_clearance=token_123", cookie)
        self.assertEqual(ua, "test_ua")

if __name__ == '__main__':
    unittest.main()
