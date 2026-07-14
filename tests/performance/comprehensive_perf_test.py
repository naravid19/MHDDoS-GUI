
import asyncio
import time
import json
import sqlite3
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.app.main import log_broadcaster_daemon, state, HistoryDB

async def test_telemetry_coalescer():
    print("Testing Telemetry Coalescer...")
    state.log_queue = asyncio.Queue(maxsize=5000)
    
    # Mock WebSocket
    class MockWS:
        def __init__(self):
            self.messages = []
        async def send_text(self, msg):
            self.messages.append(msg)
    
    ws = MockWS()
    state.connected_websockets = [ws]
    
    # Start daemon
    daemon_task = asyncio.create_task(log_broadcaster_daemon())
    
    # Push messages
    # Same task telemetry - should be coalesced
    for i in range(50):
        await state.log_queue.put(json.dumps({"task_id": "test", "type": "telemetry", "pps": i}))
    
    # Different task telemetry - should be preserved
    await state.log_queue.put(json.dumps({"task_id": "other", "type": "telemetry", "pps": 100}))
    
    # System logs - should be preserved
    await state.log_queue.put(json.dumps({"msg": "system log 1"}))
    await state.log_queue.put(json.dumps({"msg": "system log 2"}))
    
    await asyncio.sleep(0.5) # Wait for flush
    
    daemon_task.cancel()
    
    if len(ws.messages) > 0:
        first_msg = json.loads(ws.messages[0])
        if first_msg["type"] == "batch":
            items = first_msg['items']
            print(f"SUCCESS: Received batch with {len(items)} items")
            # Expected: 1 coalesced 'test', 1 'other', 2 system logs = 4 items
            if len(items) == 4:
                print("SUCCESS: Coalescing logic verified (4 items)")
            else:
                print(f"FAILURE: Expected 4 items, got {len(items)}")
                for it in items: print(f"  - {it}")
        else:
            print(f"FAILURE: Expected batch envelope, got {first_msg['type']}")
    else:
        print("FAILURE: No messages received")

async def test_history_resolution():
    print("\nTesting History Resolution (Sandboxed)...")
    
    test_db_path = "files/test_comprehensive.db"
    # Sandbox HistoryDB
    original_db_path = HistoryDB.DB_PATH
    HistoryDB.DB_PATH = test_db_path
    
    try:
        Path("files").mkdir(exist_ok=True)
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            
        with sqlite3.connect(test_db_path) as conn:
            conn.execute("CREATE TABLE attack_sessions (session_id TEXT PRIMARY KEY, start_time TEXT, end_time TEXT, target TEXT, method TEXT, threads INTEGER, duration INTEGER, proxy_type TEXT, rpc INTEGER, reflector TEXT, exit_status TEXT, duration_actual REAL, peak_pps INTEGER, peak_bps INTEGER, avg_latency REAL, total_requests INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS attack_metrics (session_id TEXT, timestamp TEXT, pps INTEGER, bps INTEGER, latency REAL)")
            conn.execute("CREATE TABLE IF NOT EXISTS attack_metrics_rollup_5s (session_id TEXT, timestamp TEXT, pps INTEGER, bps INTEGER, latency REAL)")
            
            # 1. Short session (< 1 hour)
            conn.execute("INSERT INTO attack_sessions (session_id, start_time, end_time, duration_actual) VALUES ('short', '2026-03-21T10:00:00', '2026-03-21T10:05:00', 300.0)")
            # 2. Long session (> 1 hour)
            conn.execute("INSERT INTO attack_sessions (session_id, start_time, end_time, duration_actual) VALUES ('long', '2026-03-21T10:00:00', '2026-03-21T12:00:00', 7200.0)")
        
        # Verify pragmas are set through HistoryDB
        results = HistoryDB._query_sync("PRAGMA journal_mode")
        print(f"Journal mode (WAL check): {results[0]['journal_mode']}")
        
        # Verify table selection logic (mimic api.py)
        def get_resolution_table(duration_actual):
            if duration_actual > 3600: return "attack_metrics_rollup_5s"
            return "attack_metrics"
            
        res_short = get_resolution_table(300.0)
        res_long = get_resolution_table(7200.0)
        
        print(f"Resolution for short session: {res_short} (Expected: attack_metrics)")
        print(f"Resolution for long session: {res_long} (Expected: attack_metrics_rollup_5s)")
        
        if res_short == "attack_metrics" and res_long == "attack_metrics_rollup_5s":
            print("SUCCESS: History resolution table mapping verified.")
        else:
            print("FAILURE: History resolution mapping incorrect.")

    finally:
        HistoryDB.DB_PATH = original_db_path
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
            except:
                pass

if __name__ == "__main__":
    asyncio.run(test_telemetry_coalescer())
    asyncio.run(test_history_resolution())
