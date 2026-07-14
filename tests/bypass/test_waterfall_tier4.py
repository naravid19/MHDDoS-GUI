import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.append('.')
from src.core.engine import BrowserEngine

class TestWaterfallTier4(unittest.TestCase):
    @patch('src.core.engine.CAMOUFOX_INSTALLED', True)
    def test_solve_tier4_camoufox_advanced(self):
        # We need to mock the import failure if we want to be thorough, 
        # but here we just want to see if the logic flows.
        import sys
        mock_camoufox_module = MagicMock()
        mock_camoufox_class = MagicMock()
        mock_camoufox_module.Camoufox = mock_camoufox_class

        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_context.cookies.return_value = [{"name": "cf_clearance", "value": "token_camoufox"}]
        mock_page.evaluate.return_value = "ua_camoufox"
        mock_browser.contexts = [mock_context]
        mock_browser.new_page.return_value = mock_page
        
        # Mock context manager
        mock_camoufox_class.return_value.__enter__.return_value = mock_browser

        with patch.dict('sys.modules', {
            'camoufox': MagicMock(),
            'camoufox.sync_api': mock_camoufox_module
        }):
            cookie, ua = BrowserEngine._solve_tier4_ultimate_stealth("https://test.com", "1.1.1.1:80", "ua_test", 45)
        
        self.assertIsNotNone(cookie)
        self.assertIn("cf_clearance=token_camoufox", cookie)
        self.assertEqual(ua, "ua_camoufox")
        
        # Verify launch arguments
        mock_camoufox_class.assert_called_with(
            headless=True, 
            humanize=True, 
            fingerprint_preset=True,
            os="windows",
            proxy={"server": "http://1.1.1.1:80"}
        )

if __name__ == '__main__':
    unittest.main()
