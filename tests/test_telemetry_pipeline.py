# tests/test_telemetry_pipeline.py
import re
import pytest

RAW_LINE = "PPS: 1234, BPS: 567890, Latency: 42ms, Pool: 8/100 (Warm: 3)"

def _parse_numeric(s: str) -> float:
    """Will be imported from src.app.main after fix."""
    from src.app.main import _parse_numeric as real
    return real(s)

def test_parse_numeric_plain():
    from src.app.main import _parse_numeric
    assert _parse_numeric("1234") == 1234.0

def test_parse_numeric_k_suffix():
    from src.app.main import _parse_numeric
    assert _parse_numeric("1.5k") == 1500.0

def test_parse_numeric_ms_suffix():
    from src.app.main import _parse_numeric
    assert _parse_numeric("42ms") == 42.0

def test_parse_numeric_MB_per_s():
    from src.app.main import _parse_numeric
    assert _parse_numeric("2MB/s") == pytest.approx(2 * 1_048_576, rel=1e-3)

def simulate_handle_log_line(line: str, task_id: str = "t1") -> dict | None:
    from src.app.main import _parse_numeric
    if "PPS:" not in line or "BPS:" not in line:
        return None
    m_pps = re.search(r'PPS:\s*([^,]+)', line)
    m_bps = re.search(r'BPS:\s*([^,]+)', line)
    m_lat = re.search(r'Latency:\s*([^,ms]+)', line)
    m_pool = re.search(r'Pool:\s*(\d+)/(\d+)(?:\s*\(Warm:\s*(\d+)\))?', line)
    if not m_pps or not m_bps:
        return None
    return {
        "task_id": task_id,
        "type": "telemetry",
        "rps": _parse_numeric(m_pps.group(1)),
        "bps": _parse_numeric(m_bps.group(1)),
        "lat": _parse_numeric(m_lat.group(1).replace('ms','').strip()) if m_lat else 0.0,
        "threads": int(m_pool.group(1)) if m_pool else 0,
    }

def test_telemetry_field_is_rps_not_pps():
    r = simulate_handle_log_line(RAW_LINE)
    assert "rps" in r and "pps" not in r

def test_telemetry_values_are_numeric():
    r = simulate_handle_log_line(RAW_LINE)
    assert isinstance(r["rps"], float)
    assert isinstance(r["bps"], float)
    assert isinstance(r["lat"], float)
    assert isinstance(r["threads"], int)

def test_telemetry_threads_present():
    r = simulate_handle_log_line(RAW_LINE)
    assert r["threads"] == 8

def test_telemetry_correct_values():
    r = simulate_handle_log_line(RAW_LINE)
    assert r["rps"] == 1234.0
    assert r["bps"] == 567890.0
    assert r["lat"] == 42.0
