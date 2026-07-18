import pytest
import time
from unittest.mock import patch, MagicMock
from src.core.engine import parse_global_flags, ENGINE_STATE, ML_ENGINE, HttpFlood

@pytest.fixture(autouse=True)
def reset_engine_state():
    orig_adaptive = getattr(ENGINE_STATE, "adaptive_mode", None)
    orig_intensity = getattr(ML_ENGINE, "intensity", None)
    orig_fs_url = getattr(ENGINE_STATE, "flaresolverr_url", None)
    orig_fs_tabs = getattr(ENGINE_STATE, "flaresolverr_tabs", None)
    orig_engines = getattr(ENGINE_STATE, "engines", None)
    orig_cookie = getattr(HttpFlood, "_cfbuam_cookie", None)
    orig_ua = getattr(HttpFlood, "_cfbuam_ua", None)
    orig_expiry = getattr(HttpFlood, "_cfbuam_expiry", None)
    try:
        yield
    finally:
        ENGINE_STATE.adaptive_mode = orig_adaptive
        ML_ENGINE.intensity = orig_intensity
        ENGINE_STATE.flaresolverr_url = orig_fs_url
        ENGINE_STATE.flaresolverr_tabs = orig_fs_tabs
        ENGINE_STATE.engines = orig_engines
        HttpFlood._cfbuam_cookie = orig_cookie
        HttpFlood._cfbuam_ua = orig_ua
        HttpFlood._cfbuam_expiry = orig_expiry

def test_parse_global_flags_boolean_and_values():
    argv = [
        "python", "-m", "engine", "GET", "http://example.com", "5", "100", "proxy.txt", "100", "3600",
        "--smart", "--adaptive", "true", "--engines", "PY,GO", "--intensity", "25", "--flaresolverr", "http://localhost:8191/v1"
    ]
    clean_pos, flags = parse_global_flags(argv)
    assert clean_pos == ["python", "-m", "engine", "GET", "http://example.com", "5", "100", "proxy.txt", "100", "3600"]
    assert flags["smart"] is True
    assert flags["adaptive"] is True
    assert flags["engines"] == "PY,GO"
    assert flags["intensity"] == 25
    assert flags["flaresolverr"] == "http://localhost:8191/v1"

def test_parse_global_flags_adaptive_false():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--adaptive", "false"]
    clean_pos, flags = parse_global_flags(argv)
    assert flags["adaptive"] is False
    assert "--adaptive" not in clean_pos
    assert "false" not in clean_pos

def test_parse_global_flags_standalone_adaptive():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--adaptive"]
    clean_pos, flags = parse_global_flags(argv)
    assert flags["adaptive"] is True

def test_l4_flag_state_application():
    argv = ["python", "-m", "engine", "TCP", "http://example.com:80", "5", "100", "proxy.txt", "100", "3600", "--intensity", "35", "--adaptive", "false"]
    clean_pos, flags = parse_global_flags(argv)
    if flags["intensity"] is not None:
        ML_ENGINE.intensity = flags["intensity"]
    if flags["adaptive"] is not None:
        ENGINE_STATE.adaptive_mode = flags["adaptive"]
    assert ML_ENGINE.intensity == 35
    assert ENGINE_STATE.adaptive_mode is False

def test_parse_global_flags_flaresolverr_tabs_and_session():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--flaresolverr-tabs", "8", "--session-id", "task-xyz-123"]
    clean_pos, flags = parse_global_flags(argv)
    assert flags["flaresolverr_tabs"] == 8
    assert flags["session_id"] == "task-xyz-123"
    assert "--flaresolverr-tabs" not in clean_pos
    assert "--session-id" not in clean_pos

def test_parse_global_flags_shared_tokens():
    argv = ["python", "-m", "engine", "CFB", "http://example.com", "--shared-cookie", "cf_clearance=abc", "--shared-ua", "Mozilla/5.0 (Windows NT 10.0)"]
    clean_pos, flags = parse_global_flags(argv)
    assert flags["shared_cookie"] == "cf_clearance=abc"
    assert flags["shared_ua"] == "Mozilla/5.0 (Windows NT 10.0)"
    assert "--shared-cookie" not in clean_pos
    assert "--shared-ua" not in clean_pos

def test_parse_global_flags_intensity_clamping():
    argv_low = ["python", "-m", "engine", "GET", "http://example.com", "--intensity", "-15"]
    _, flags_low = parse_global_flags(argv_low)
    assert flags_low["intensity"] == 0

    argv_high = ["python", "-m", "engine", "GET", "http://example.com", "--intensity", "150"]
    _, flags_high = parse_global_flags(argv_high)
    assert flags_high["intensity"] == 50

def test_parse_global_flags_malformed_values():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--intensity", "not-a-number", "--flaresolverr-tabs", "invalid"]
    clean_pos, flags = parse_global_flags(argv)
    assert flags["intensity"] is None
    assert flags["flaresolverr_tabs"] is None

def test_parse_global_flags_unknown_passthrough():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--custom-flag", "custom_val"]
    clean_pos, flags = parse_global_flags(argv)
    assert "--custom-flag" in clean_pos
    assert "custom_val" in clean_pos

def test_parse_global_flags_go_and_evasion_booleans():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--go", "--evasion", "--autoscale"]
    clean_pos, flags = parse_global_flags(argv)
    assert flags["go"] is True
    assert flags["evasion"] is True
    assert flags["autoscale"] is True

def test_flag_application_flaresolverr_state():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--flaresolverr", "http://remote:8191/v1", "--flaresolverr-tabs", "4"]
    _, flags = parse_global_flags(argv)
    if flags["flaresolverr"] is not None:
        ENGINE_STATE.flaresolverr_url = flags["flaresolverr"]
    if flags["flaresolverr_tabs"] is not None:
        ENGINE_STATE.flaresolverr_tabs = flags["flaresolverr_tabs"]
    assert ENGINE_STATE.flaresolverr_url == "http://remote:8191/v1"
    assert ENGINE_STATE.flaresolverr_tabs == 4

def test_flag_application_shared_cookie_ua():
    argv = ["python", "-m", "engine", "CFB", "http://example.com", "--shared-cookie", "cookie_val=1", "--shared-ua", "CustomUA/1.0"]
    _, flags = parse_global_flags(argv)
    if flags["shared_cookie"]:
        HttpFlood._cfbuam_cookie = flags["shared_cookie"]
        HttpFlood._cfbuam_expiry = time.time() + 900
    if flags["shared_ua"]:
        HttpFlood._cfbuam_ua = flags["shared_ua"]
    assert HttpFlood._cfbuam_cookie == "cookie_val=1"
    assert HttpFlood._cfbuam_ua == "CustomUA/1.0"
    assert HttpFlood._cfbuam_expiry > time.time() + 890

def test_flag_application_autoscale():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--autoscale"]
    _, flags = parse_global_flags(argv)
    threads = 250
    if flags["autoscale"]:
        ENGINE_STATE.active_threads_target.value = threads
    assert ENGINE_STATE.active_threads_target.value == 250

def test_flag_application_engines_split():
    argv = ["python", "-m", "engine", "GET", "http://example.com", "--engines", " py , go , rust "]
    _, flags = parse_global_flags(argv)
    if flags["engines"]:
        ENGINE_STATE.engines = [e.strip().upper() for e in flags["engines"].split(",") if e.strip()]
    assert ENGINE_STATE.engines == ["PY", "GO", "RUST"]


