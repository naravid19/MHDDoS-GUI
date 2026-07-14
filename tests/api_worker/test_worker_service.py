# tests/test_worker_service.py
import asyncio
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.worker.service import WorkerService, worker_service
from src.core.state_manager import state_manager, AttackStatus


@pytest.mark.asyncio
async def test_worker_service_start_and_stop() -> None:
    service = WorkerService()
    
    # Mock asyncio.create_subprocess_exec
    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.wait.return_value = 0
    mock_proc.pid = 12345
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec, \
         patch.object(service, "_terminate_process_tree", new_callable=AsyncMock) as mock_kill:
        await service.start_attack(target="https://example.com", duration=60, threads=10)
        
        mock_exec.assert_called_once()
        state = await state_manager.get_state()
        assert state.status == AttackStatus.RUNNING
        assert state.target == "https://example.com"
        
        # Stop attack
        await service.stop_attack()
        state = await state_manager.get_state()
        assert state.status == AttackStatus.STOPPED
        mock_kill.assert_awaited_once_with(12345)


@pytest.mark.asyncio
async def test_worker_service_start_already_running() -> None:
    service = WorkerService()
    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.pid = 11111
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
         patch.object(service, "_terminate_process_tree", new_callable=AsyncMock):
        await service.start_attack(target="https://example.com", duration=30, threads=5)
        
        with pytest.raises(RuntimeError, match="An attack is already running."):
            await service.start_attack(target="https://example.com", duration=30, threads=5)
            
        await service.stop_attack()


@pytest.mark.asyncio
async def test_worker_service_start_spawn_error() -> None:
    service = WorkerService()
    
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("Command not found")):
        with pytest.raises(OSError, match="Command not found"):
            await service.start_attack(target="https://example.com", duration=30, threads=5)
            
        state = await state_manager.get_state()
        assert state.status == AttackStatus.ERROR
        assert "Command not found" in str(state.error_detail)


@pytest.mark.asyncio
async def test_worker_service_monitor_process_completion() -> None:
    service = WorkerService()
    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.wait.return_value = 0
    mock_proc.pid = 22222
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        await service.start_attack(target="https://example.com", duration=10, threads=2)
        assert service._monitor_task is not None
        
        # Wait for monitor task to complete
        await service._monitor_task
        
        state = await state_manager.get_state()
        assert state.status == AttackStatus.COMPLETED
        assert service._process is None


@pytest.mark.asyncio
async def test_worker_service_monitor_process_error() -> None:
    service = WorkerService()
    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.wait.return_value = 1
    mock_proc.pid = 33333
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        await service.start_attack(target="https://example.com", duration=10, threads=2)
        assert service._monitor_task is not None
        
        # Wait for monitor task to complete
        await service._monitor_task
        
        state = await state_manager.get_state()
        assert state.status == AttackStatus.ERROR
        assert "exited with code 1" in str(state.error_detail)
        assert service._process is None


@pytest.mark.asyncio
async def test_worker_service_stop_no_process() -> None:
    service = WorkerService()
    # Stopping when no process is running should not raise an error
    await service.stop_attack()


@pytest.mark.asyncio
async def test_worker_service_terminate_process_tree_win32() -> None:
    service = WorkerService()
    mock_kill_proc = AsyncMock()
    mock_kill_proc.wait.return_value = 0
    
    with patch("sys.platform", "win32"), \
         patch("asyncio.create_subprocess_exec", return_value=mock_kill_proc) as mock_exec:
        await service._terminate_process_tree(9999)
        mock_exec.assert_called_once_with(
            "taskkill", "/F", "/T", "/PID", "9999",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )


def test_worker_service_singleton() -> None:
    assert isinstance(worker_service, WorkerService)
