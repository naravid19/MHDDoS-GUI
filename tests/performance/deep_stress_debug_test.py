import sys
import os
import json
import unittest
import time
import random
from unittest.mock import patch, MagicMock

# Setup path
sys.path.append('.')

from src.core.engine import BrowserEngine, bcolors

class DeepStressDebugTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Load real proxies from the established path
        cls.proxy_path = r"C:\Users\narav\Desktop\CE code\Tools\proxy-scraper-checker\out\checked-proxies\proxies\all.txt"
        if os.path.exists(cls.proxy_path):
            with open(cls.proxy_path, 'r', encoding='utf-8') as f:
                cls.proxies = [line.strip() for line in f if line.strip()]
            print(f"[*] Stress Test: Loaded {len(cls.proxies)} real proxies.")
        else:
            print(f"[!] Warning: Proxy file not found at {cls.proxy_path}")
            cls.proxies = []

        cls.target_url = "https://nowsecure.nl" # Real Cloudflare target
        cls.debug_dir = r"C:\Users\narav\Desktop\CE code\Tools\MHDDoS-GUI\debug"

    def test_full_waterfall_with_debug_capture(self):
        print(f"\n{bcolors.BOLD}{'='*30} DEEP STRESS & DEBUG TEST {'='*30}{bcolors.RESET}")
        
        if not self.proxies:
            self.skipTest("No proxies available for stress test")

        # Pick 3 random proxies to simulate different network conditions
        test_proxies = random.sample(self.proxies, min(3, len(self.proxies)))
        
        for idx, proxy in enumerate(test_proxies):
            print(f"\n{bcolors.OKBLUE}[~] SCENARIO {idx+1}: Testing Waterfall escalation with proxy {proxy}{bcolors.RESET}")
            
            # We call the master internal method which executes the waterfall
            # We expect failures at early tiers for this specific target, which should trigger DEBUG captures
            cookie, ua = BrowserEngine._solve_cf_internal(self.target_url, proxy, timeout=30000)
            
            print(f"[*] Scenario {idx+1} Result: {'BYPASS SUCCESS' if cookie else 'BYPASS FAILED (Waterfall completed)'}")
            
            # Verify if debug folder has content
            debug_dirs = [os.path.join(self.debug_dir, d) for d in os.listdir(self.debug_dir) if os.path.isdir(os.path.join(self.debug_dir, d))]
            print(f"[*] Debug folder directories: {len(debug_dirs)}")
            
            if debug_dirs:
                latest_folder = sorted(debug_dirs, key=os.path.getmtime)[-1]
                print(f"[*] Latest debug artifact: {latest_folder}")
                files = os.listdir(latest_folder)
                print(f"[*] Artifact contents: {files}")
                
                # Check for essential forensic data
                has_log = "error.log" in files
                has_img = "screenshot.png" in files
                has_html = "dom.html" in files
                print(f"[*] Forensic Check: Log={has_log}, Screenshot={has_img}, DOM={has_html}")

if __name__ == '__main__':
    unittest.main()
