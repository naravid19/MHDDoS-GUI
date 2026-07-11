import asyncio, pytest

@pytest.mark.asyncio
async def test_get_token_blocks_until_set():
    from src.core.token_manager import TokenManager
    tm = TokenManager()
    result = []
    async def getter():
        result.append(await tm.get_token())
    task = asyncio.create_task(getter())
    await asyncio.sleep(0.05)
    assert len(result) == 0
    await tm.set_token("abc")
    await asyncio.sleep(0.05)
    assert result == ["abc"]
    task.cancel()

@pytest.mark.asyncio
async def test_concurrent_invalidations_trigger_one_solve():
    from src.core.token_manager import TokenManager
    count = 0
    async def fake_wf(url):
        nonlocal count; count += 1
        await asyncio.sleep(0.05); return "tok"
    tm = TokenManager(waterfall_fn=fake_wf)
    await tm.set_token("old")
    await asyncio.gather(*[tm.invalidate_and_resolve("https://x.com") for _ in range(10)])
    assert count == 1

@pytest.mark.asyncio
async def test_is_stale_response():
    from src.core.token_manager import TokenManager
    tm = TokenManager()
    assert tm.is_stale_response(403, "Just a moment...") is True
    assert tm.is_stale_response(200, "readtoon.com") is False

@pytest.mark.asyncio
async def test_gate_cleared_during_solve():
    from src.core.token_manager import TokenManager
    events = []
    async def slow_wf(url):
        events.append("solving"); await asyncio.sleep(0.1); return "tok"
    tm = TokenManager(waterfall_fn=slow_wf)
    await tm.set_token("old")
    task = asyncio.create_task(tm.invalidate_and_resolve("https://x.com"))
    await asyncio.sleep(0.02)
    assert not tm.gate.is_set()
    await task
    assert tm.gate.is_set()
