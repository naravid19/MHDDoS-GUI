import logging, pytest

def test_no_per_call_log(caplog):
    caplog.set_level(logging.DEBUG)
    from src.core import engine
    engine.logger.setLevel(logging.DEBUG)
    engine._ML_LOG_INTERVAL = 200  # higher than our call count
    engine._ML_SWITCH_COUNT = 0
    engine._ML_SWITCH_STATS = {}
    from src.core.engine import _ml_switch_fingerprint
    for _ in range(20):
        _ml_switch_fingerprint("chrome_win_133", 10.0, 15.0)
    ml_logs = [r for r in caplog.records if "ML_ENGINE: Switching active fingerprint" in r.getMessage()]
    assert len(ml_logs) == 0, f"Expected 0 per-call logs, got {len(ml_logs)}"

def test_summary_logged_at_interval(caplog):
    caplog.set_level(logging.DEBUG)
    from src.core import engine
    engine.logger.setLevel(logging.DEBUG)
    engine._ML_LOG_INTERVAL = 5
    engine._ML_SWITCH_COUNT = 0
    engine._ML_SWITCH_STATS = {}
    from src.core.engine import _ml_switch_fingerprint
    for _ in range(10):
        _ml_switch_fingerprint("safari_ios_18", 10.0, 15.0)
    summary = [r for r in caplog.records if "ML_ENGINE" in r.getMessage() and "switches" in r.getMessage()]
    assert len(summary) >= 1
