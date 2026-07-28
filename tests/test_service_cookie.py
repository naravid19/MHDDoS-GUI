"""Tests: Phase 0 pre-fetch + __SYNC_BYPASS__ parsing in AttackService."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch


def make_svc():
    from src.worker.service import WorkerService
    return WorkerService()


# ── Phase 0 Pre-fetch ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prefetch_returns_cookie_on_success():
    svc = make_svc()
    fake_cookie = "cf_clearance=abc; __cf_bm=x"
    fake_ua = "Mozilla/5.0 (Windows NT 10.0)"

    with patch("src.core.engine.BrowserEngine.solve_cf", new_callable=AsyncMock) as mock_solve:
        mock_solve.return_value = (fake_cookie, fake_ua)
        cookie, ua = await svc._prefetch_cf_cookie("https://readtoon.com", "CFB")

    assert cookie == fake_cookie
    assert ua == fake_ua


@pytest.mark.asyncio
async def test_prefetch_skips_non_cf_methods():
    svc = make_svc()
    cookie, ua = await svc._prefetch_cf_cookie("https://target.com", "GET")
    assert cookie is None and ua is None


@pytest.mark.asyncio
async def test_prefetch_returns_none_on_timeout():
    svc = make_svc()
    with patch("src.core.engine.BrowserEngine.solve_cf", new_callable=AsyncMock) as mock_solve:
        mock_solve.side_effect = asyncio.TimeoutError
        cookie, ua = await svc._prefetch_cf_cookie("https://readtoon.com", "CFB")
    assert cookie is None and ua is None


@pytest.mark.asyncio
async def test_prefetch_ignores_cookie_without_clearance():
    svc = make_svc()
    with patch("src.core.engine.BrowserEngine.solve_cf", new_callable=AsyncMock) as mock_solve:
        mock_solve.return_value = ("__cfduid=bad", "UA")
        cookie, ua = await svc._prefetch_cf_cookie("https://readtoon.com", "CFB")
    assert cookie is None


# ── __SYNC_BYPASS__ Parsing ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_bypass_updates_c2():
    from src.app.main import C2
    C2.shared_cf_cookie = None
    C2.shared_cf_ua = None

    svc = make_svc()
    payload = json.dumps({"cookie": "cf_clearance=tok; __cf_bm=x", "ua": "TestUA"})
    await svc._handle_sync_bypass_line(f"__SYNC_BYPASS__||{payload}")

    assert C2.shared_cf_cookie == "cf_clearance=tok; __cf_bm=x"
    assert C2.shared_cf_ua == "TestUA"
    C2.shared_cf_cookie = None


@pytest.mark.asyncio
async def test_sync_bypass_ignores_no_clearance():
    from src.app.main import C2
    C2.shared_cf_cookie = None

    svc = make_svc()
    payload = json.dumps({"cookie": "__cfduid=junk", "ua": "UA"})
    await svc._handle_sync_bypass_line(f"__SYNC_BYPASS__||{payload}")

    assert C2.shared_cf_cookie is None


@pytest.mark.asyncio
async def test_sync_bypass_ignores_unrelated_line():
    from src.app.main import C2
    C2.shared_cf_cookie = None

    svc = make_svc()
    await svc._handle_sync_bypass_line("[INFO] Normal log line")
    assert C2.shared_cf_cookie is None
