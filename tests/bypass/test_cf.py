import asyncio
import nodriver as uc
import sys
import random
import time

async def main():
    target_url = "https://google.com/"
    print(f"Testing direct connection to {target_url}...")
    
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox"
    ]
    
    browser = await uc.start(browser_args=browser_args)
    page = browser.main_tab
    await page.get(target_url)
    
    start_wait = time.time()
    while time.time() - start_wait < 20:
        title = await page.evaluate('document.title')
        print(f"[{time.time() - start_wait:.1f}s] Title: {title}")
        
        # Check for challenge
        try:
            iframes = await page.select_all('iframe')
            for iframe in iframes:
                src = iframe.attributes.get('src', '').lower()
                if any(k in src for k in ["cloudflare", "turnstile", "challenge"]):
                    print("Cloudflare iframe found! Taking screenshot...")
                    await page.save_screenshot("cf_stuck.png")
                    
                    print("Attempting to click...")
                    try:
                        rect = await iframe.get_position()
                        if rect:
                            x = rect.x + (rect.width / 2)
                            y = rect.y + (rect.height / 2)
                            await page.mouse_move(x, y)
                            await asyncio.sleep(0.5)
                            await page.mouse_click(x, y)
                            print(f"Clicked at {x}, {y}")
                    except Exception as e:
                        print(f"Click failed: {e}")
                    
                    await asyncio.sleep(5)
                    await page.save_screenshot("cf_after_click.png")
                    break
        except Exception as e:
            print(f"Iframe check failed: {e}")
                
        cookies = await browser.cookies.get_all()
        cookie_str = "; ".join([f"{c.name}={c.value}" for c in cookies])
        if "cf_clearance" in cookie_str:
            print("[SUCCESS] cf_clearance acquired!")
            break
            
        await asyncio.sleep(2)
        
    await page.save_screenshot("cf_final.png")
    browser.stop()

if __name__ == '__main__':
    if sys.platform == 'win32':
        import warnings
        from asyncio.proactor_events import _ProactorBasePipeTransport
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<.*pipe.*>")
        _original_repr = _ProactorBasePipeTransport.__repr__
        def _safe_repr(self):
            try: return _original_repr(self)
            except: return "<_ProactorBasePipeTransport closed=True>"
        _ProactorBasePipeTransport.__repr__ = _safe_repr
        from asyncio.base_subprocess import BaseSubprocessTransport
        _original_del = BaseSubprocessTransport.__del__
        def _safe_del(self):
            try: _original_del(self)
            except: pass
        BaseSubprocessTransport.__del__ = _safe_del
    asyncio.run(main())