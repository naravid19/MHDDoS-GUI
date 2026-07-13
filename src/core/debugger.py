import os
import time
from datetime import datetime

class BypassDebugger:
    DEBUG_DIR = r"C:\Users\narav\Desktop\CE code\Tools\MHDDoS-GUI\debug"
    
    @classmethod
    def capture_failure(cls, tier_name, url, browser_obj=None, page_obj=None, error_msg="", response_obj=None):
        error_lower = str(error_msg).lower()
        network_keywords = [
            "connectionpool", "proxyerror", "connecttimeout", "network unreachable",
            "failed to establish a new connection", "sockshttpsconnection", "sockshttpconnection",
            "max retries exceeded", "connection refused", "timeout exceeded while waiting for event"
        ]
        if any(kw in error_lower for kw in network_keywords):
            try:
                os.makedirs(cls.DEBUG_DIR, exist_ok=True)
                log_path = os.path.join(cls.DEBUG_DIR, "proxy_network_errors.log")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{tier_name}] URL: {url} | Error: {error_msg}\n")
            except Exception:
                pass
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(cls.DEBUG_DIR, f"{timestamp}_{tier_name}")
        os.makedirs(folder, exist_ok=True)
        
        # 1. Save error metadata
        try:
            with open(os.path.join(folder, "error.log"), "w", encoding="utf-8") as f:
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"URL: {url}\n")
                f.write(f"Tier: {tier_name}\n")
                f.write(f"Error Message: {error_msg}\n")
                if response_obj:
                    f.write(f"HTTP Status: {getattr(response_obj, 'status_code', 'N/A')}\n")
        except: pass
            
        # 2. Capture Browser State (Screenshots and DOM)
        if page_obj:
            try:
                # Screenshot logic
                screenshot_path = os.path.join(folder, "screenshot.png")
                
                # Check for nodriver (async)
                if str(type(page_obj)).find('nodriver') != -1:
                    import asyncio
                    try:
                        # Since we are likely in a context where an event loop is running,
                        # we try to run this coroutine.
                        async def _async_snap():
                            await page_obj.save_screenshot(screenshot_path)
                            with open(os.path.join(folder, "dom.html"), "w", encoding="utf-8") as f:
                                f.write(await page_obj.get_content())
                        
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # This is tricky if already running, but capture_failure 
                            # is usually called from an async-managed thread or block
                            pass 
                    except: pass
                
                # Check for DrissionPage
                elif hasattr(page_obj, 'get_screenshot'):
                    page_obj.get_screenshot(path=screenshot_path, full_page=True)
                    with open(os.path.join(folder, "dom.html"), "w", encoding="utf-8") as f:
                        f.write(page_obj.html)
                
                # Standard Playwright / Patchright / CloakBrowser
                elif hasattr(page_obj, 'screenshot'):
                    page_obj.screenshot(path=screenshot_path, full_page=True)
                    with open(os.path.join(folder, "dom.html"), "w", encoding="utf-8") as f:
                        f.write(page_obj.content())
                
                # Selenium / UC / Botasaurus
                elif hasattr(page_obj, 'save_screenshot'):
                    page_obj.save_screenshot(screenshot_path)
                    with open(os.path.join(folder, "dom.html"), "w", encoding="utf-8") as f:
                        f.write(getattr(page_obj, 'page_source', getattr(page_obj, 'page_html', '')))
                        
                # Browser Console Logs (if supported)
                if hasattr(page_obj, 'evaluate'):
                    logs = page_obj.evaluate("() => { return window._logs || 'No logs captured'; }")
                    with open(os.path.join(folder, "console.log"), "w", encoding="utf-8") as f:
                        f.write(str(logs))
            except Exception as e:
                with open(os.path.join(folder, "debugger_error.log"), "w") as f:
                    f.write(f"Debugger failed to capture browser state: {str(e)}")

        # 3. Capture HTTP Response (for Tier 1)
        if response_obj and not page_obj:
            try:
                with open(os.path.join(folder, "response.html"), "w", encoding="utf-8") as f:
                    f.write(response_obj.text)
            except: pass

        print(f"[*] Superpower Debugger: Artifacts saved to {folder}")
        return folder
