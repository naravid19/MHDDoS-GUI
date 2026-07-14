import asyncio
import os
import sys
import time
from unittest.mock import MagicMock

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.engine import HttpFlood, ML_ENGINE, BrowserEngine

async def mock_engine_test(method_name):
    print(f"\n{'='*50}\nTesting L7 Method: {method_name}\n{'='*50}")
    url_str = "https://google.com/"
    
    target = MagicMock()
    target.human_repr.return_value = url_str
    target.__str__.return_value = url_str
    target.authority = "example-target.com"
    target.raw_host = "example-target.com"
    target.raw_path_qs = "/"
    target.query_string = ""
    
    # Initialize the HttpFlood object
    flood = HttpFlood(
        thread_id=0,
        target=target,
        host=target.authority,
        method=method_name,
        rpc=5,
        synevent=None,
        useragents=None,
        referers=None,
        proxy_pool=None
    )
    
    # Force real bytes for internal attributes
    flood._method_bytes = b"GET"
    flood._path_bytes = b"/"
    flood._host_bytes = b"example-target.com"
    flood._raw_host_bytes = b"example-target.com"
    flood._host_header = b"Host: example-target.com\r\n"
    
    # Run the method for a short duration
    print(f"Starting {method_name} test loop...")
    task = asyncio.create_task(getattr(flood, method_name)())
    
    try:
        await asyncio.wait_for(task, timeout=45)
    except asyncio.TimeoutError:
        print(f"{method_name} test loop completed successfully (Timeout reached).")
    except Exception as e:
        print(f"{method_name} crashed: {e}")
        
    print(f"Results for {method_name}:")
    print(f"  CFBUAM Cookie: {getattr(HttpFlood, '_cfbuam_cookie', 'None')}")
    print(f"  CFBUAM UA: {getattr(HttpFlood, '_cfbuam_ua', 'None')}")
    print(f"  Active Solver: {getattr(HttpFlood, '_active_solver', 'None')}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    async def run_tests():
        # First test CFBUAM (this triggers BrowserEngine and then uses the token)
        await mock_engine_test("CFBUAM")
        
        # Test BROWSER
        await mock_engine_test("BROWSER")
        
        # Test HYBRID
        await mock_engine_test("HYBRID")
        
    asyncio.run(run_tests())
