import asyncio, pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_worker_blocks_until_event_set():
    from src.core import state_manager
    state_manager.bypass_ready_event = asyncio.Event()  # not set
    request_sent = asyncio.Event()

    async def spy(*a, **kw):
        request_sent.set()
        return MagicMock(status=200)

    with patch("src.core.engine._cfb_send_request", side_effect=spy):
        from src.core.engine import _cfb_worker_task
        stop = asyncio.Event()
        task = asyncio.create_task(_cfb_worker_task(target="example.com", stop_event=stop))
        await asyncio.sleep(0.15)
        assert not request_sent.is_set(), "Worker must NOT fire before gate is set"
        state_manager.bypass_ready_event.set()
        await asyncio.sleep(0.15)
        assert request_sent.is_set(), "Worker MUST fire after gate is set"
        stop.set(); task.cancel()

@pytest.mark.asyncio
async def test_re_solve_clears_then_re_sets_event():
    from src.core import state_manager
    state_manager.bypass_ready_event = asyncio.Event()
    state_manager.bypass_ready_event.set()

    with patch("src.core.engine._run_waterfall_bypass", new_callable=AsyncMock, return_value="tok"):
        from src.core.engine import _trigger_bypass_re_solve
        await _trigger_bypass_re_solve("https://example.com")
        assert state_manager.bypass_ready_event.is_set()
