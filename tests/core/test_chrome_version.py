import sys, unittest
from unittest.mock import patch, MagicMock

class TestChromeVersionDetection(unittest.TestCase):
    def test_returns_int_greater_than_100(self):
        from src.core.engine import _get_installed_chrome_version
        v = _get_installed_chrome_version()
        self.assertIsInstance(v, int)
        self.assertGreater(v, 100)

    def test_uc_chrome_receives_version_main(self):
        import undetected_chromedriver as uc
        with patch("src.core.engine._get_installed_chrome_version", return_value=149), \
             patch.object(uc, "Chrome", return_value=MagicMock()) as mock_chrome:
            from src.core.engine import _launch_uc_chrome
            _launch_uc_chrome(headless=True)
            self.assertEqual(mock_chrome.call_args[1]["version_main"], 149)
