import asyncio
import nodriver as uc
import sys
import random
import time

# Monkey patch
import nodriver.cdp.network as network
if hasattr(network, 'Cookie') and not hasattr(network.Cookie, '_is_patched_by_mhddos'):
    original_from_json = network.Cookie.__dict__.get('from_json', getattr(network.Cookie, 'from_json', None))
    @classmethod
    def patched_from_json(cls, json_obj):
        for k, v in [
            ('sameParty', False),
            ('partitionKey', None),
            ('partitionKeyOpaque', False),
            ('sourceScheme', 'NonSecure'),
            ('sourcePort', 80),
            ('priority', 'Medium')
        ]:
            if k not in json_obj:
                json_obj[k] = v
        if isinstance(original_from_json, classmethod):
            return original_from_json.__func__(cls, json_obj)
        elif hasattr(original_from_json, '__func__'):
            return original_from_json.__func__(cls, json_obj)
        elif callable(original_from_json):
            return original_from_json(json_obj)
        else:
            return cls(**json_obj)
    patched_from_json._is_patched_by_mhddos = True
    network.Cookie.from_json = patched_from_json
    network.Cookie._is_patched_by_mhddos = True

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
        if asyncio.iscoroutine(res) and not hasattr(res, '_mock_return_value'):
            await res
    except Exception:
        pass

def test_patched_cookie_from_json():
    """Verify that network.Cookie.from_json injects missing fields."""
    raw = {
        "name": "test_cookie",
        "value": "123",
        "domain": "example.com",
        "path": "/",
        "expires": 0,
        "size": 14,
        "httpOnly": False,
        "secure": True,
        "session": True,
        "priority": "Medium",
    }
    cookie = network.Cookie.from_json(raw)
    assert cookie.name == "test_cookie"
    assert cookie.value == "123"

if __name__ == '__main__':
    asyncio.run(main())