# tests/test_telemetry_pipeline.py
import re
import pytest
from unittest.mock import AsyncMock, patch
from src.app.main import _parse_numeric

RAW_LINE = "PPS: 1234, BPS: 567890, Latency: 42ms, Pool: 8/100 (Warm: 3)"


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


@pytest.mark.asyncio
async def test_telemetry_log_parsing_numeric_types():
    """Verify that handle_log_line extracts exact float/int fields required by TelemetryStore."""
    broadcast_mock = AsyncMock()
    with patch("src.app.main.broadcast_log", broadcast_mock):
        from src.app.main import _parse_numeric
        assert _parse_numeric("1.5k") == 1500.0
        assert _parse_numeric("2MB/s") == 2097152.0
        assert _parse_numeric("42.5ms") == 42.5
        assert _parse_numeric("0") == 0.0


def test_engine_line_buffering_reconfigure():
    """Verify engine.py forces line_buffering=True on sys.stdout and sys.stderr."""
    with open("src/core/engine.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "sys.stdout.reconfigure(line_buffering=True)" in content
    assert "sys.stderr.reconfigure(line_buffering=True)" in content


@pytest.mark.asyncio
async def test_handle_log_line_telemetry_payload():
    """Test handle_log_line in run_attack_subprocess broadcasts exact float and int values."""
    broadcast_mock = AsyncMock()
    start_attack_mock = AsyncMock()
    with patch("src.app.main.broadcast_log", broadcast_mock), \
         patch("src.app.main.worker_service.start_attack", start_attack_mock):
        from src.app.main import run_attack_subprocess, AttackParams
        params = AttackParams(target="http://example.com", duration=60, threads=10, method="GET")
        await run_attack_subprocess("task_123", params)
        
        assert start_attack_mock.called
        log_callback = start_attack_mock.call_args.kwargs["log_callback"]
        await log_callback("PPS: 1.5k, BPS: 2MB/s, Latency: 42.5ms, Pool: 8/100 (Warm: 3)")
        
        telemetry_calls = [
            c for c in broadcast_mock.call_args_list 
            if c.args and isinstance(c.args[0], dict) and c.args[0].get("type") == "telemetry"
        ]
        assert len(telemetry_calls) == 1
        payload = telemetry_calls[0].args[0]
        assert type(payload["rps"]) is float
        assert payload["rps"] == 1500.0
        assert type(payload["bps"]) is float
        assert payload["bps"] == 2097152.0
        assert type(payload["lat"]) is float
        assert payload["lat"] == 42.5
        assert type(payload["threads"]) is int
        assert payload["threads"] == 8
        assert type(payload["pool_total"]) is int
        assert payload["pool_total"] == 100
        assert type(payload["pool_warm"]) is int
        assert payload["pool_warm"] == 3


def simulate_handle_log_line(line: str, task_id: str = "t1") -> dict | None:
    from src.app.main import _parse_numeric
    if "PPS:" not in line or "BPS:" not in line:
        return None
    m_pps = re.search(r'PPS:\s*([^,]+)', line)
    m_bps = re.search(r'BPS:\s*([^,]+)', line)
    m_lat = re.search(r'Latency:\s*([^,]+)', line)
    m_pool = re.search(r'Pool:\s*(\d+)/(\d+)(?:\s*\(Warm:\s*(\d+)\))?', line)
    if not m_pps or not m_bps:
        return None
    lat_raw = m_lat.group(1).strip() if m_lat else "0"
    return {
        "task_id": task_id,
        "type": "telemetry",
        "level": "DEBUG",
        "rps": float(_parse_numeric(m_pps.group(1))),
        "bps": float(_parse_numeric(m_bps.group(1))),
        "lat": float(_parse_numeric(lat_raw.replace('ms', ''))),
        "threads": int(m_pool.group(1)) if m_pool else 0,
        "pool_total": int(m_pool.group(2)) if m_pool else 0,
        "pool_warm": int(m_pool.group(3)) if m_pool and m_pool.group(3) else 0,
    }


def test_telemetry_field_is_rps_not_pps():
    r = simulate_handle_log_line(RAW_LINE)
    assert "rps" in r and "pps" not in r


def test_telemetry_values_are_numeric():
    r = simulate_handle_log_line(RAW_LINE)
    assert type(r["rps"]) is float
    assert type(r["bps"]) is float
    assert type(r["lat"]) is float
    assert type(r["threads"]) is int
    assert type(r["pool_total"]) is int
    assert type(r["pool_warm"]) is int


def test_telemetry_threads_present():
    r = simulate_handle_log_line(RAW_LINE)
    assert r["threads"] == 8
    assert r["pool_total"] == 100
    assert r["pool_warm"] == 3


def test_telemetry_correct_values():
    r = simulate_handle_log_line(RAW_LINE)
    assert r["rps"] == 1234.0
    assert r["bps"] == 567890.0
    assert r["lat"] == 42.0

