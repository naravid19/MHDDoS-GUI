import pytest
from src.core.engine import parse_global_flags, ENGINE_STATE, ML_ENGINE

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
    from src.core.engine import parse_global_flags, ENGINE_STATE, ML_ENGINE
    argv = ["python", "-m", "engine", "TCP", "http://example.com:80", "5", "100", "proxy.txt", "100", "3600", "--intensity", "35", "--adaptive", "false"]
    clean_pos, flags = parse_global_flags(argv)
    if flags["intensity"] is not None:
        ML_ENGINE.intensity = flags["intensity"]
    if flags["adaptive"] is not None:
        ENGINE_STATE.adaptive_mode = flags["adaptive"]
    assert ML_ENGINE.intensity == 35
    assert ENGINE_STATE.adaptive_mode is False

