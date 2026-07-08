# tests/test_worker_termination.py
import asyncio
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.worker.service import WorkerService


@pytest.mark.asyncio
async def test_terminate_process_tree_windows_order():
    """Verify on win32 that taskkill /T runs BEFORE psutil parent kill to preserve OS tree graph."""
    service = WorkerService()
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    service._process = mock_proc

    call_order = []

    async def mock_exec(*args, **kwargs):
        call_order.append("taskkill")
        mock_subproc = AsyncMock()
        mock_subproc.wait.return_value = 0
        return mock_subproc

    def mock_psutil_process(pid):
        call_order.append("psutil_parent")
        parent = MagicMock()
        parent.children.return_value = []
        return parent

    with patch.object(sys, "platform", "win32"), \
         patch("asyncio.create_subprocess_exec", side_effect=mock_exec) as mock_sub, \
         patch("psutil.Process", side_effect=mock_psutil_process):
        await service._terminate_process_tree(12345)

    assert "taskkill" in call_order
    # On Windows, taskkill MUST execute before psutil_parent to avoid losing child process hierarchy
    assert call_order.index("taskkill") < call_order.index("psutil_parent")
