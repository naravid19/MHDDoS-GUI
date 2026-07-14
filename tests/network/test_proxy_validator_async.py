# tests/test_proxy_validator_async.py
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from src.core.engine import TacticalProxy, ProxyType, _check_proxy_async

@pytest.mark.asyncio
async def test_check_proxy_async_timeout_handling():
    proxy = TacticalProxy("192.0.2.1:8080", 0.0, False, 0)
    proxy.type = ProxyType.HTTP
    
    # Simulate a hanging open_connection
    async def hanging_connect(*args, **kwargs):
        await asyncio.sleep(10.0)
        return AsyncMock(), AsyncMock()
        
    with patch("asyncio.open_connection", side_effect=hanging_connect):
        result = await _check_proxy_async("example.com", proxy, timeout=1.0)
        
    assert result.is_protocol_verified is False
    assert result.latency >= 5000.0
