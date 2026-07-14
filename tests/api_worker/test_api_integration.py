# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY
from api import app
from src.core.state_manager import state_manager, AttackStatus
from src.worker.service import worker_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_api_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "target" in data


@patch("src.worker.service.worker_service.start_attack", new_callable=AsyncMock)
def test_api_start_and_stop_attack(mock_start: AsyncMock, client: TestClient) -> None:
    response = client.post("/api/attack/start", json={
        "target": "https://example.com",
        "duration": 60,
        "threads": 10,
        "method": "GET",
        "rpc": 100
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_start.assert_awaited_once_with(target="https://example.com", duration=60, threads=10, method="GET", rpc=100, log_callback=ANY)
    
    with patch("src.worker.service.worker_service.stop_attack", new_callable=AsyncMock) as mock_stop:
        response = client.post("/api/attack/stop")
        assert response.status_code == 200
        mock_stop.assert_awaited_once()


def test_websocket_endpoint_reconcile(client: TestClient) -> None:
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "state_reconcile"
        assert "status" in data["payload"]


@patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
def test_websocket_reconnect_reconciliation(mock_exec: AsyncMock, client: TestClient) -> None:
    import asyncio
    mock_proc = mock_exec.return_value
    mock_proc.returncode = None
    mock_proc.pid = 54321
    
    killed = False
    wait_futures: list[asyncio.Future[int]] = []
    
    async def dummy_wait() -> int:
        loop = asyncio.get_running_loop()
        f = loop.create_future()
        if killed:
            f.set_result(0)
        else:
            wait_futures.append(f)
        return await f
        
    mock_proc.wait.side_effect = dummy_wait
    
    async def dummy_kill(*args: any, **kwargs: any) -> None:
        nonlocal killed
        killed = True
        for f in wait_futures:
            if not f.done():
                f.set_result(0)
    
    # First connection gets initial state
    with client.websocket_connect("/ws") as ws1:
        data1 = ws1.receive_json()
        assert data1["type"] == "state_reconcile"
        initial_status = data1["payload"]["status"]
        assert initial_status in ("idle", "stopped", "completed", "error")
        
    # Simulate state change while client was disconnected
    client.post("/api/attack/start", json={
        "target": "https://example.com",
        "duration": 60,
        "threads": 10,
        "method": "GET",
        "rpc": 100
    })
    
    # Second connection (reconnect) should immediately receive updated RUNNING state
    with client.websocket_connect("/ws") as ws2:
        data2 = ws2.receive_json()
        assert data2["type"] == "state_reconcile"
        assert data2["payload"]["status"] == "running"
        
    # Clean up
    with patch.object(worker_service, "_terminate_process_tree", side_effect=dummy_kill):
        client.post("/api/attack/stop")


@pytest.mark.asyncio
async def test_log_broadcaster_no_attribute_error():
    from src.app.main import state, log_broadcaster_daemon, ws_manager
    from unittest.mock import AsyncMock
    import asyncio
    
    # Put a log in state.log_queue
    if state.log_queue is None:
        state.log_queue = asyncio.Queue(maxsize=5000)
    await state.log_queue.put("Test log message")
    
    # Create a mock websocket
    mock_ws = AsyncMock()
    mock_ws.send_text = AsyncMock()
    
    # Add to ws_manager._clients
    ws_manager._clients.add(mock_ws)
    
    try:
        daemon_task = asyncio.create_task(log_broadcaster_daemon())
        await asyncio.sleep(0.3)
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            pass
            
        assert mock_ws.send_text.called
        call_args = mock_ws.send_text.call_args[0][0]
        assert "Test log message" in call_args
    finally:
        ws_manager._clients.discard(mock_ws)


def test_api_status_post_method(client: TestClient) -> None:
    response = client.post("/api/attack/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "active_tasks" in data


@patch("src.worker.service.worker_service.stop_attack", new_callable=AsyncMock)
def test_api_stop_attack_global_fallback(mock_stop: AsyncMock, client: TestClient) -> None:
    response = client.post("/api/attack/stop", json={})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_stop.assert_awaited_once()





