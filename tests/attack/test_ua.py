import asyncio
import nodriver as uc
import sys
import time

async def main():
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        '--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"'
    ]
    try:
        browser = await uc.start(browser_args=browser_args)
        page = browser.main_tab
        print("Navigating to https://google.com/ ...")
        await page.evaluate('window.location.href = "https://google.com/";')
        
        start_wait = time.time()
        while time.time() - start_wait < 15:
            try:
                title = await page.evaluate('document.title')
                print(f"[{time.time() - start_wait:.1f}s] Title: {title}")
                if "cf_clearance" in "; ".join([f"{c.name}={c.value}" for c in await browser.cookies.get_all()]):
                    print("Bypass Successful!")
                    break
            except Exception as e:
                pass
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"Global: {e}")
    finally:
        try:
            browser.stop()
        except:
            pass

if __name__ == '__main__':
    asyncio.run(main())