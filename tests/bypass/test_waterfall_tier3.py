import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.append('.')
from src.core.engine import BrowserEngine

class TestWaterfallTier3(unittest.TestCase):
    @patch('src.core.engine.PATCHRIGHT_INSTALLED', False)
    @patch('src.core.engine.UNDETECTED_CHROMEDRIVER_INSTALLED', False)
    @patch('src.core.engine.CLOAKBROWSER_INSTALLED', True)
    @patch('src.core.engine.cloakbrowser_launch', create=True)
    def test_solve_tier3_cloakbrowser_humanized(self, mock_launch):
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.evaluate.return_value = "ua_test"
        
        # Mocking context cookies
        mock_context = MagicMock()
        mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "token_cloak"}]
        mock_context.new_page.return_value = mock_page
        
        mock_browser.new_context.return_value = mock_context
        mock_launch.return_value = mock_browser

        cookie, ua = BrowserEngine._solve_tier3_heavy_stealth("https://test.com", "1.1.1.1:80", "ua_test", 30)
        
        self.assertIsNotNone(cookie)
        self.assertIn("cf_clearance=token_cloak", cookie)
        self.assertEqual(ua, "ua_test")
        self.assertTrue(mock_browser.close.called)
        
        # Verify launch arguments
        mock_launch.assert_called_with(headless=True, humanize=True, geoip=True, proxy="http://1.1.1.1:80")

if __name__ == '__main__':
    unittest.main()