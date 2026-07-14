# tests/test_tier0_preflight.py
import pytest
from unittest.mock import patch, AsyncMock
from src.worker.service import WorkerService
from src.core.state_manager import AttackStatus


@pytest.mark.asyncio
async def test_preflight_check_fails_when_flaresolverr_offline():
    """Verify that starting a CFB attack continues with fallback when port 8191 is closed (non-fatal)."""
    service = WorkerService()
    
    async def mock_offline(*args, **kwargs):
        return False

    mock_process = AsyncMock()
    mock_process.returncode = None

    with patch.object(service, "_check_tier0_readiness", side_effect=mock_offline) as mock_check, \
         patch("src.worker.service.state_manager.update_status", AsyncMock()) as mock_status, \
         patch.object(service, "_broadcast_state", AsyncMock()), \
         patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_spawn:
        
        await service.start_attack(
            target="https://example.com",
            duration=60,
            threads=10,
            method="CFB",
            rpc=100
        )
        
        mock_check.assert_called_once_with("CFB")
        mock_spawn.assert_called_once()
        # Verify it didn't update status to ERROR
        for call in mock_status.call_args_list:
            assert call[0][0] != AttackStatus.ERROR


@pytest.mark.asyncio
async def test_check_tier0_readiness_non_tls_methods_return_true():
    """Verify that non-CFB/BYPASS methods bypass the TCP readiness check immediately."""
    service = WorkerService()
    for method in ("GET", "SYN", "UDP", "HTTP", "POST"):
        assert await service._check_tier0_readiness(method) is True


@pytest.mark.asyncio
async def test_check_tier0_readiness_offline_returns_false():
    """Verify that _check_tier0_readiness returns False when connection fails or times out."""
    service = WorkerService()
    
    with patch("asyncio.open_connection", side_effect=ConnectionRefusedError()):
        assert await service._check_tier0_readiness("CFB") is False
    
    with patch("asyncio.open_connection", side_effect=TimeoutError()):
        assert await service._check_tier0_readiness("BYPASS") is False


@pytest.mark.asyncio
async def test_check_tier0_readiness_online_returns_true():
    """Verify that _check_tier0_readiness returns True and cleanly closes the writer when connection succeeds."""
    service = WorkerService()
    
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    
    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        assert await service._check_tier0_readiness("CFB") is True
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_awaited_once()

