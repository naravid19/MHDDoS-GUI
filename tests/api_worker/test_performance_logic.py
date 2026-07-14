import asyncio
import json
import time
import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.main import broadcast_log, log_broadcaster_daemon, state, history_session_metrics, HistoryDB
from src.core.paths import get_assets_path

@pytest.mark.asyncio
async def test_telemetry_coalescing():
    # Setup
    state.log_queue = asyncio.Queue(maxsize=5000)
    state.connected_websockets = [AsyncMock()]
    
    # 1. Send multiple telemetry messages for same task
    task_id = "test_task_1"
    msg1 = json.dumps({"task_id": task_id, "type": "telemetry", "pps": "100"})
    msg2 = json.dumps({"task_id": task_id, "type": "telemetry", "pps": "200"})
    msg3 = json.dumps({"task_id": task_id, "type": "system", "msg": "Important log"})
    
    await broadcast_log(msg1)
    await broadcast_log(msg2)
    await broadcast_log(msg3)
    
    # Run the daemon for a very short duration
    daemon_task = asyncio.create_task(log_broadcaster_daemon())
    await asyncio.sleep(0.3) # Wait for flush
    daemon_task.cancel()
    
    # Verify
    sent_payload = state.connected_websockets[0].send_text.call_args[0][0]
    data = json.loads(sent_payload)
    
    assert data["type"] == "batch"
    items = [json.loads(i) if isinstance(i, str) else i for i in data["items"]]
    
    # Should have 2 items: 1 system, 1 telemetry
    assert len(items) == 2
    types = [i["type"] for i in items]
    assert "system" in types
    assert "telemetry" in types
    
    # Telemetry should be the latest one (pps: 200)
    telemetry_item = next(i for i in items if i["type"] == "telemetry")
    assert telemetry_item["pps"] == "200"

@pytest.mark.asyncio
async def test_queue_saturation_dropping():
    # Setup tiny queue
    state.log_queue = asyncio.Queue(maxsize=2)
    state.dropped_low_priority = 0
    
    # 1. Fill queue with high priority (blocking)
    await broadcast_log("high1", priority="high")
    await broadcast_log("high2", priority="high")
    
    # 2. Try to send low priority (should drop)
    await broadcast_log("low1", priority="low")
    
    assert state.dropped_low_priority == 1
    assert state.log_queue.full()
    
    # Cleanup
    while not state.log_queue.empty():
        state.log_queue.get_nowait()

@pytest.mark.asyncio
async def test_history_resolution_switching():
    # Mock HistoryDB._query and _query_one
    HistoryDB._query = AsyncMock(return_value=[{"timestamp": "2026-03-21T12:00:00", "pps": 100}])
    HistoryDB._query_one = AsyncMock(return_value={"start_time": "2026-03-21T10:00:00", "end_time": "2026-03-21T11:00:00"})
    
    # 1. Test short session (raw)
    res = await history_session_metrics("short_id", resolution="auto")
    assert res["resolution"] == "raw"
    assert "attack_metrics" in res["table_source"]
    
    # 2. Test medium session (5s)
    HistoryDB._query_one.return_value = {"start_time": "2026-03-21T10:00:00", "end_time": "2026-03-21T15:00:00"}
    res = await history_session_metrics("medium_id", resolution="auto")
    assert res["resolution"] == "5s"
    assert "rollup_5s" in res["table_source"]
    
    # 3. Test long session (1m)
    HistoryDB._query_one.return_value = {"start_time": "2026-03-20T10:00:00", "end_time": "2026-03-21T15:00:00"}
    res = await history_session_metrics("long_id", resolution="auto")
    assert res["resolution"] == "1m"
    assert "rollup_1m" in res["table_source"]

if __name__ == "__main__":
    asyncio.run(test_telemetry_coalescing())
    asyncio.run(test_queue_saturation_dropping())
    asyncio.run(test_history_resolution_switching())
    print("Backend logic tests PASSED.")
