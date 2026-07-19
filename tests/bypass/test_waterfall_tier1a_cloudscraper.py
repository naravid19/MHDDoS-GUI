import pytest
from src.core.engine import BrowserEngine

@pytest.mark.asyncio
async def test_tier1a_cloudscraper_success(monkeypatch):
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.cookies = [
                type('Cookie', (), {'name': 'cf_clearance', 'value': '12345'})(),
                type('Cookie', (), {'name': 'other', 'value': 'test'})()
            ]
            self.headers = {"User-Agent": "cloudscraper_ua"}

    class MockScraper:
        def __init__(self, *args, **kwargs):
            self.proxies = {}
            self.headers = {"User-Agent": "default"}

        def get(self, url, timeout):
            self.cookies = [
                type('Cookie', (), {'name': 'cf_clearance', 'value': '12345'})(),
                type('Cookie', (), {'name': 'other', 'value': 'test'})()
            ]
            return MockResponse()

    def mock_create_scraper(**kwargs):
        return MockScraper()

    import cloudscraper
    monkeypatch.setattr(cloudscraper, "create_scraper", mock_create_scraper)

    cookie, ua = await BrowserEngine._solve_tier1a_cloudscraper("http://test.com", timeout=5)

    assert "cf_clearance=12345" in cookie
    assert "other=test" in cookie
    assert ua == "default"


@pytest.mark.asyncio
async def test_tier1a_cloudscraper_adaptive_mode(monkeypatch):
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"User-Agent": "cloudscraper_ua"}

    class MockScraper:
        def __init__(self, *args, **kwargs):
            self.proxies = {}
            self.headers = {"User-Agent": "cloudscraper_ua"}

        def get(self, url, timeout):
            self.cookies = [
                type('Cookie', (), {'name': 'session_id', 'value': '999'})()
            ]
            return MockResponse()

    def mock_create_scraper(**kwargs):
        return MockScraper()

    import cloudscraper
    monkeypatch.setattr(cloudscraper, "create_scraper", mock_create_scraper)

    import src.core.engine as engine_module
    original_adaptive = engine_module.ENGINE_STATE.adaptive_mode
    engine_module.ENGINE_STATE.adaptive_mode = True
    try:
        cookie, ua = await BrowserEngine._solve_tier1a_cloudscraper("http://test.com", timeout=5)
    finally:
        engine_module.ENGINE_STATE.adaptive_mode = original_adaptive

    assert cookie is not None, "Expected a cookie string in adaptive mode"
    assert "session_id=999" in cookie
    assert "cf_clearance" not in cookie
    assert ua == "cloudscraper_ua"


@pytest.mark.asyncio
async def test_tier1a_cloudscraper_failure(monkeypatch):
    class MockScraper:
        def __init__(self, *args, **kwargs):
            self.proxies = {}
            self.headers = {}

        def get(self, url, timeout):
            raise Exception("Connection timeout")

    def mock_create_scraper(**kwargs):
        return MockScraper()

    import cloudscraper
    monkeypatch.setattr(cloudscraper, "create_scraper", mock_create_scraper)

    cookie, ua = await BrowserEngine._solve_tier1a_cloudscraper("http://test.com", timeout=5)

    assert cookie is None
    assert ua is None
