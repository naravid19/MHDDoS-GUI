import asyncio
import nodriver as uc
import sys
import random
import time

# Monkey patch
import nodriver.cdp.network as network
if hasattr(network, 'Cookie'):
    original_from_json = network.Cookie.from_json
    @classmethod
    def patched_from_json(cls, json_obj):
        if 'sameParty' not in json_obj:
            json_obj['sameParty'] = False
        if 'partitionKey' not in json_obj:
            json_obj['partitionKey'] = None
        if 'partitionKeyOpaque' not in json_obj:
            json_obj['partitionKeyOpaque'] = False
        return original_from_json.__func__(cls, json_obj)
    network.Cookie.from_json = patched_from_json

async def main():
    browser = await uc.start(browser_args=[
        "--disable-blink-features=AutomationControlled",
        "--window-position=-32000,-32000"
    ])
    page = browser.main_tab
    await page.get("https://google.com/")
    start_wait = time.time()
    
    while time.time() - start_wait < 45:
        try:
            title = await asyncio.wait_for(page.evaluate('document.title'), timeout=5)
            print(f"[{time.time() - start_wait:.1f}s] Title: {title}")
            
            cookies = await asyncio.wait_for(browser.cookies.get_all(), timeout=5)
            cookie_str = "; ".join([f"{c.name}={c.value}" for c in cookies])
            
            if "cf_clearance" in cookie_str:
                print(f"Bypass Successful! Found cf_clearance.")
                break
                
            if time.time() - start_wait > 5:
                print("Attempting interaction pulse...")
                await page.mouse_move(random.randint(100, 800), random.randint(100, 800))
                try:
                    iframe = await asyncio.wait_for(page.select('iframe', timeout=1), timeout=2)
                    if iframe:
                        print("Found iframe, moving mouse to it.")
                        await asyncio.wait_for(iframe.mouse_move(), timeout=2)
                        await asyncio.sleep(0.5)
                        await asyncio.wait_for(iframe.mouse_click(), timeout=2)
                except:
                    pass
                    
        except asyncio.TimeoutError:
            print("Timeout in loop iteration")
        except BaseException as e:
            print(f"Error in loop: {type(e)} {e}")
            
        await asyncio.sleep(2.0)
        
    try:
        res = browser.stop()
        if asyncio.iscoroutine(res):
            await res
    except Exception:
        pass

asyncio.run(main())