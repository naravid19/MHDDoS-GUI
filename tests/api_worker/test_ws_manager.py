# tests/test_ws_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.api.ws_manager import ConnectionManager, WSMessage, ws_manager
from src.core.state_manager import AttackStateSnapshot, AttackStatus


@pytest.mark.asyncio
async def test_ws_manager_connect_and_broadcast() -> None:
    manager = ConnectionManager()
    
    mock_ws = AsyncMock()
    await manager.connect(mock_ws)
    
    # Verify accept was called and initial state reconcile message was sent
    mock_ws.accept.assert_awaited_once()
    mock_ws.send_json.assert_awaited_once()
    
    # Verify payload structure of initial message
    call_arg = mock_ws.send_json.call_args[0][0]
    assert call_arg["type"] == "state_reconcile"
    
    # Broadcast a test message
    msg = WSMessage(type="test_event", payload={"foo": "bar"})
    await manager.broadcast(msg)
    
    # Verify send_json called again for broadcast
    assert mock_ws.send_json.await_count == 2
    
    await manager.disconnect(mock_ws)
    assert len(manager._clients) == 0


@pytest.mark.asyncio
async def test_ws_manager_send_personal_message_failure() -> None:
    manager = ConnectionManager()
    
    mock_ws = AsyncMock()
    await manager.connect(mock_ws)
    assert len(manager._clients) == 1
    
    # Simulate send_json raising an exception on subsequent send
    mock_ws.send_json.side_effect = Exception("Connection closed by client")
    
    msg = WSMessage(type="test_event", payload={"data": 123})
    await manager.send_personal_message(msg, mock_ws)
    
    # Should catch exception and automatically disconnect the client
    assert len(manager._clients) == 0


@pytest.mark.asyncio
async def test_ws_manager_broadcast_dead_client_removal() -> None:
    manager = ConnectionManager()
    
    good_client = AsyncMock()
    dead_client = AsyncMock()
    
    await manager.connect(good_client)
    await manager.connect(dead_client)
    assert len(manager._clients) == 2
    
    # Make dead_client fail on send_json
    dead_client.send_json.side_effect = Exception("Broken pipe")
    
    msg = WSMessage(type="broadcast_event", payload={"status": "running"})
    await manager.broadcast(msg)
    
    # Good client should still receive broadcast, dead client should be removed
    assert len(manager._clients) == 1
    assert good_client in manager._clients
    assert dead_client not in manager._clients


@pytest.mark.asyncio
async def test_ws_manager_broadcast_empty() -> None:
    manager = ConnectionManager()
    msg = WSMessage(type="test_event", payload={})
    # Should not raise any exception when broadcasting to zero clients
    await manager.broadcast(msg)
    assert len(manager._clients) == 0


def test_ws_manager_singleton() -> None:
    assert isinstance(ws_manager, ConnectionManager)
