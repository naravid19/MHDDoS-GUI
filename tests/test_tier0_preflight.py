# tests/test_tier0_preflight.py
import pytest
from unittest.mock import patch, AsyncMock
from src.worker.service import WorkerService
from src.core.state_manager import AttackStatus


@pytest.mark.asyncio
async def test_preflight_check_fails_when_flaresolverr_offline():
    """Verify that starting a CFB attack fails fast when port 8191 is closed without launching subprocess."""
    service = WorkerService()
    
    async def mock_offline(*args, **kwargs):
        return False

    with patch.object(service, "_check_tier0_readiness", side_effect=mock_offline), \
         patch("src.worker.service.state_manager.update_status", AsyncMock()) as mock_status, \
         patch.object(service, "_broadcast_state", AsyncMock()):
        with pytest.raises(RuntimeError, match="Tier 0 FlareSolverr unreachable on localhost:8191."):
            await service.start_attack(
                target="https://example.com",
                duration=60,
                threads=10,
                method="CFB",
                rpc=100
            )
        mock_status.assert_called_with(AttackStatus.ERROR, "Tier 0 FlareSolverr unreachable on localhost:8191.")
