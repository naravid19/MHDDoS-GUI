import asyncio
import pytest
from src.core.state_manager import StateManager, AttackStatus, state_manager


@pytest.mark.asyncio
async def test_state_manager_concurrency_and_transitions() -> None:
    sm = StateManager()
    
    # Check initial state
    initial = await sm.get_state()
    assert initial.status == AttackStatus.IDLE
    assert initial.attack_id is None
    
    # Subscribe queue
    queue = sm.subscribe()
    
    # Transition to starting then running
    await sm.transition(AttackStatus.STARTING, attack_id="test-123", target="example.com", method="UDP")
    running_state = await sm.transition(AttackStatus.RUNNING)
    
    assert running_state.status == AttackStatus.RUNNING
    assert running_state.attack_id == "test-123"
    assert running_state.start_time is not None
    
    # Verify subscriber received snapshots
    assert not queue.empty()
    msg1 = await queue.get()
    assert msg1.status == AttackStatus.STARTING
    msg2 = await queue.get()
    assert msg2.status == AttackStatus.RUNNING
    
    sm.unsubscribe(queue)


@pytest.mark.asyncio
async def test_state_manager_error_and_completed_transitions() -> None:
    sm = StateManager()
    await sm.transition(AttackStatus.RUNNING, attack_id="atk-1", target="example.com", method="TCP")
    
    # Transition to ERROR
    error_state = await sm.transition(AttackStatus.ERROR, error_detail="Connection timeout")
    assert error_state.status == AttackStatus.ERROR
    assert error_state.error_detail == "Connection timeout"
    assert error_state.start_time is None
    assert error_state.elapsed_seconds == 0.0
    
    # Transition to COMPLETED
    comp_state = await sm.transition(AttackStatus.COMPLETED)
    assert comp_state.status == AttackStatus.COMPLETED
    assert comp_state.start_time is None
    assert comp_state.elapsed_seconds == 0.0


@pytest.mark.asyncio
async def test_state_manager_stats_update_and_elapsed_time() -> None:
    sm = StateManager()
    await sm.transition(AttackStatus.RUNNING, attack_id="atk-2")
    
    # Simulate time passing
    await asyncio.sleep(0.1)
    
    stats_data = {"pps": 15000, "mbps": 120.5}
    running_state = await sm.transition(AttackStatus.RUNNING, stats=stats_data)
    
    assert running_state.stats == stats_data
    assert running_state.elapsed_seconds >= 0.09
    
    # Verify stats persist if not overridden in next transition
    next_state = await sm.transition(AttackStatus.STOPPING)
    assert next_state.stats == stats_data
    assert next_state.status == AttackStatus.STOPPING


@pytest.mark.asyncio
async def test_state_manager_unsubscribe_and_queue_full() -> None:
    sm = StateManager()
    queue = sm.subscribe()
    
    # Unsubscribe immediately and verify no messages received
    sm.unsubscribe(queue)
    await sm.transition(AttackStatus.STARTING)
    assert queue.empty()
    
    # Subscribe again and fill queue beyond maxsize (50)
    queue2 = sm.subscribe()
    for i in range(60):
        await sm.transition(AttackStatus.RUNNING, stats={"iteration": i})
    
    # Queue size should be capped at maxsize (50) and should not have raised QueueFull
    assert queue2.qsize() == 50
    sm.unsubscribe(queue2)


@pytest.mark.asyncio
async def test_state_manager_concurrent_access() -> None:
    sm = StateManager()
    
    async def worker(worker_id: int) -> None:
        for i in range(10):
            await sm.transition(AttackStatus.RUNNING, stats={"worker": worker_id, "iter": i})
            await sm.get_state()
            await asyncio.sleep(0.001)
            
    # Run multiple concurrent workers modifying state
    await asyncio.gather(*(worker(w) for w in range(5)))
    
    final_state = await sm.get_state()
    assert final_state.status == AttackStatus.RUNNING
    assert "worker" in final_state.stats


def test_state_manager_singleton() -> None:
    assert isinstance(state_manager, StateManager)
