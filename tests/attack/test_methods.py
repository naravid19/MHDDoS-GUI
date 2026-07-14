import asyncio
import sys
import logging
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger("test_methods")

# Add parent directory to path so we can import from start.py
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock globals needed by start.py
global REQUESTS_SENT, BYTES_SEND, SUCCESS_SENT, WAF_SENT, ERROR_SENT, TIMEOUT_SENT
from src.core import engine as start
start.REQUESTS_SENT = 0
start.BYTES_SEND = 0
start.SUCCESS_SENT = 0
start.WAF_SENT = 0
start.ERROR_SENT = 0
start.TIMEOUT_SENT = 0

from src.core.engine import HttpFlood, ProxyManager, ProxyType, argv
from yarl import URL

async def run_method_test(target_url, method_name, duration=30):
    logger.info(f"\n{bcolors.HEADER}======================================================{bcolors.RESET}")
    logger.info(f"{bcolors.HEADER}Starting Headless Diagnostic Test for Method: {method_name}{bcolors.RESET}")
    logger.info(f"{bcolors.HEADER}Target: {target_url}{bcolors.RESET}")
    logger.info(f"{bcolors.HEADER}Duration: {duration} seconds{bcolors.RESET}")
    logger.info(f"{bcolors.HEADER}======================================================{bcolors.RESET}\n")

    # Force debug to activate our telemetry
    if "--debug" not in start.argv:
        start.argv.append("--debug")

    target = URL(target_url)
    
    # Initialize HttpFlood worker
    flood = HttpFlood(
        thread_id=0,
        target=target,
        host=target.host,
        method=method_name,
        rpc=10, # low rpc for testing
        synevent=asyncio.Event(),
        proxy_pool=None # No proxies for simple diagnostic test
    )

    # Let the flood run in the background
    logger.info(f"{bcolors.OKBLUE}[*] Launching {method_name} task...{bcolors.RESET}")
    flood_task = asyncio.create_task(flood.methods[method_name]())

    # Wait for the test duration
    elapsed = 0
    while elapsed < duration:
        await asyncio.sleep(2)
        elapsed += 2
        logger.info(f"{bcolors.WARNING}[~] Status Update ({elapsed}s) | Success: {start.SUCCESS_SENT} | WAF Hits: {start.WAF_SENT} | Errors: {start.ERROR_SENT} | Timeouts: {start.TIMEOUT_SENT}{bcolors.RESET}")

    # Cancel task
    logger.info(f"{bcolors.OKBLUE}[*] Canceling task and cleaning up...{bcolors.RESET}")
    flood_task.cancel()
    
    # Let cancellation process
    await asyncio.sleep(1)
    
    logger.info(f"\n{bcolors.OKGREEN}Test for {method_name} concluded.{bcolors.RESET}")

async def main():
    target = "https://google.com/"
    browser_methods = {"BROWSER", "HYBRID"}
    
    # Check if a specific method was requested, otherwise run all sequentially
    all_methods = ["CFBUAM", "BEHAVIOR", "BROWSER", "HYBRID"]
    methods_to_test = all_methods if len(sys.argv) <= 1 else [sys.argv[1]]
    
    # Pre-warm: If we will test BROWSER or HYBRID (but not CFBUAM first),
    # run CFBUAM once to acquire a valid cf_clearance token so BROWSER/HYBRID
    # can use IMPERSONATE instead of spinning up a live browser.
    needs_prewarm = any(m in browser_methods for m in methods_to_test) and "CFBUAM" not in methods_to_test
    if needs_prewarm:
        logger.info(f"\n{bcolors.WARNING}[*] Pre-warming CFBUAM cookie before browser tests...{bcolors.RESET}")
        start.REQUESTS_SENT = start.BYTES_SEND = start.SUCCESS_SENT = start.WAF_SENT = start.ERROR_SENT = start.TIMEOUT_SENT = 0
        start.HttpFlood._cfbuam_cookie = ""
        await run_method_test(target, "CFBUAM", duration=45)
        await asyncio.sleep(3)
        cookie_status = start.HttpFlood._cfbuam_cookie
        if cookie_status and cookie_status != "_yummy=choco":
            logger.info(f"{bcolors.OKGREEN}[*] Cookie acquired! Token ready for BROWSER/HYBRID tests.{bcolors.RESET}")
        else:
            logger.info(f"{bcolors.WARNING}[!] Cookie NOT acquired. BROWSER/HYBRID tests may show WAF hits.{bcolors.RESET}")
        
    for method in methods_to_test:
        # Reset counters but preserve cookie for browser-mode tests
        start.REQUESTS_SENT = start.BYTES_SEND = start.SUCCESS_SENT = start.WAF_SENT = start.ERROR_SENT = start.TIMEOUT_SENT = 0
        if method not in browser_methods:
            start.HttpFlood._cfbuam_cookie = ""
        
        await run_method_test(target, method, duration=45)
        
        logger.info(f"{bcolors.OKBLUE}[*] Cooling down for 5 seconds...{bcolors.RESET}")
        await asyncio.sleep(5)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n[!] Test interrupted by user.")
