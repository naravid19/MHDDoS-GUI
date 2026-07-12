import logging, pytest
from src.core import engine

@pytest.fixture
def reset_ml_state(monkeypatch):
    # Store initial logger level
    initial_level = engine.logger.level
    
    # Enable debug logging for tests
    engine.logger.setLevel(logging.DEBUG)
    
    # Store initial stats to restore them since dictionaries mutate in place
    initial_stats = engine._ML_SWITCH_STATS.copy()
    initial_count = engine._ML_SWITCH_COUNT
    
    # Reset for tests
    monkeypatch.setattr(engine, '_ML_SWITCH_COUNT', 0)
    monkeypatch.setattr(engine, '_ML_SWITCH_STATS', {})
    
    yield
    
    # Restore state
    engine.logger.setLevel(initial_level)
    engine._ML_SWITCH_COUNT = initial_count
    engine._ML_SWITCH_STATS.clear()
    engine._ML_SWITCH_STATS.update(initial_stats)


def test_no_per_call_log(caplog, reset_ml_state, monkeypatch):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(engine, '_ML_LOG_INTERVAL', 200)
    
    for _ in range(20):
        engine._ml_switch_fingerprint("chrome_win_133", 10.0, 15.0)
        
    ml_logs = [r for r in caplog.records if "ML_ENGINE: Switching active fingerprint" in r.getMessage()]
    assert len(ml_logs) == 0, f"Expected 0 per-call logs, got {len(ml_logs)}"

def test_summary_logged_at_interval(caplog, reset_ml_state, monkeypatch):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(engine, '_ML_LOG_INTERVAL', 5)
    
    for _ in range(10):
        engine._ml_switch_fingerprint("safari_ios_18", 10.0, 15.0)
        
    summary = [r for r in caplog.records if "ML_ENGINE" in r.getMessage() and "switches" in r.getMessage()]
    assert len(summary) >= 1
