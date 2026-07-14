import asyncio
import nodriver as uc
import sys
import time

async def main():
    browser_args = ['--proxy-server=127.0.0.1:9999'] # dead proxy
    browser = await uc.start(browser_args=browser_args)
    page = browser.main_tab
    await page.evaluate('window.location.href = "http://example.com";')
    start_time = time.time()
    while time.time() - start_time < 5:
        try:
            title = await page.evaluate('document.title')
            content = await page.evaluate('document.body.innerText')
            print(f"Title: {title}")
            print(f"Content: {content[:50]}...")
        except Exception as e:
            print(f"Eval Error: {e}")
        await asyncio.sleep(1)
    try: browser.stop()
    except: pass

if __name__ == '__main__':
    asyncio.run(main())