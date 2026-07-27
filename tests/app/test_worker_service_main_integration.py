"""Unit tests verifying WorkerService multi-process dictionary attributes."""

from unittest.mock import MagicMock
import pytest

from src.worker.service import WorkerService


def test_worker_service_has_active_processes_dict_not_single_process() -> None:
    """Verify WorkerService uses multi-task dictionaries (_active_processes, _monitor_tasks)

    and does not have single-process attributes (_process, _monitor_task).
    """
    service = WorkerService()

    # Check WorkerService has _active_processes (dict) and _monitor_tasks (dict)
    assert hasattr(service, "_active_processes")
    assert isinstance(service._active_processes, dict)
    assert hasattr(service, "_monitor_tasks")
    assert isinstance(service._monitor_tasks, dict)

    # Check WorkerService does NOT have _process or _monitor_task
    assert not hasattr(service, "_process")
    assert not hasattr(service, "_monitor_task")


def test_worker_service_process_lookup() -> None:
    """Verify dictionary process lookup behavior for present and missing task IDs."""
    service = WorkerService()
    task_id = "task_test_123"

    # Check .get(task_id) returns None when task not present
    assert service._active_processes.get(task_id) is None

    # Store process object
    mock_process = MagicMock()
    service._active_processes[task_id] = mock_process

    # Check .get(task_id) returns stored process object when present
    assert service._active_processes.get(task_id) is mock_process


@pytest.mark.asyncio
async def test_main_task_lookup_helper() -> None:
    from src.worker.service import worker_service

    test_id = "eval_task_999"
    assert worker_service._active_processes.get(test_id) is None
    assert worker_service._monitor_tasks.get(test_id) is None

