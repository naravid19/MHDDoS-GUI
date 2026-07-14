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

class TestWaterfallTier2(unittest.TestCase):
    @patch('src.core.engine.BOTASAURUS_INSTALLED', False)
    @patch('src.core.engine.NODRIVER_INSTALLED', False)
    @patch('src.core.engine.DRISSION_INSTALLED', True)
    @patch('src.core.engine.ChromiumPage')
    @patch('src.core.engine.ChromiumOptions')
    def test_solve_tier2_fallback_to_drission(self, mock_options, mock_chromium_page):
        # We need to mock the import failure if we want to be thorough, 
        # but here we just want to see if the logic flows.
        # Since 'from DrissionPage import ...' is inside the method, 
        # we might need to mock the sys.modules or just patch the usage if possible.
        
        mock_page = MagicMock()
        mock_page.cookies.return_value = [{"name": "cf_clearance", "value": "token_456"}]
        mock_page.run_js.return_value = "test_ua"
        mock_chromium_page.return_value = mock_page
        
        # Mocking the import by putting it in sys.modules
        mock_drission = MagicMock()
        mock_drission.ChromiumPage = mock_chromium_page
        mock_drission.ChromiumOptions = mock_options

        with patch.dict('sys.modules', {'DrissionPage': mock_drission}):
            cookie, ua = BrowserEngine._solve_tier2_fast_cdp("https://test.com", None, "test_ua", 15)
        
        # Check if the result is correct
        self.assertIsNotNone(cookie)
        self.assertIn("cf_clearance=token_456", cookie)
        self.assertEqual(ua, "test_ua")
        self.assertTrue(mock_page.quit.called)

if __name__ == '__main__':
    unittest.main()
