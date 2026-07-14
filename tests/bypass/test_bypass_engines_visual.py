import asyncio
import os
import sys
import time

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.engine import BrowserEngine, TacticalProxyPool, TacticalProxyValidator, ProxyManager
from PyRoxy import ProxyType

async def test_solvers():
    url = "https://google.com/"
    print(f"Testing Bypass Engines against {url} with visual tracing...")
    
    # We won't use proxies for this basic test to ensure connection isn't the issue
    proxy = None
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    
    os.makedirs("debug/trace", exist_ok=True)
    
    print("\n--- Testing DrissionPage ---")
    try:
        cookie, ua = await BrowserEngine._solve_drissionpage(url, proxy, user_agent, timeout=30)
        print(f"DrissionPage Result: Cookie={cookie[:30] if cookie else None}..., UA={ua}")
    except Exception as e:
        print(f"DrissionPage Failed: {e}")

    print("\n--- Testing Nodriver ---")
    try:
        cookie, ua = await BrowserEngine._solve_nodriver(url, proxy, user_agent, timeout=30)
        print(f"Nodriver Result: Cookie={cookie[:30] if cookie else None}..., UA={ua}")
    except Exception as e:
        print(f"Nodriver Failed: {e}")
        
    print("\n--- Testing Behavioral Specialized ---")
    try:
        cookie, ua = await BrowserEngine._solve_readtoon(url, proxy, user_agent, timeout=45)
        print(f"Behavioral Result: Cookie={cookie[:30] if cookie else None}..., UA={ua}")
    except Exception as e:
        print(f"Behavioral Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test_solvers())
