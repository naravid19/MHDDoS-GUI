import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.core.engine import HttpFlood

@pytest.mark.asyncio
async def test_cfb_cascade_triggers_solver_when_no_cookie():
    # Reset HttpFlood state
    HttpFlood._cfbuam_cookie = None
    HttpFlood._solve_phase = "flooding"
    
    mock_target = MagicMock()
    mock_target.human_repr.return_value = "https://readtoon.com/"
    
    flood = HttpFlood(
        thread_id=1,
        target=mock_target,
        host="readtoon.com",
        method="CFB",
        rpc=1,
        useragents={"Mozilla/5.0"},
        referers={"https://google.com/"},
        proxy_pool=None
    )
    
    with patch("src.core.engine.HttpFlood.CFBUAM", new_callable=AsyncMock) as mock_cfbuam:
        await flood.CFB()
        # Should call CFBUAM to acquire cookie since _cfbuam_cookie is None
        mock_cfbuam.assert_called_once()
