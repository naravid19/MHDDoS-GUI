import sys
import pytest
from pydantic import ValidationError
from src.app.main import build_attack_command, AttackParams, C2

def test_l7_command_builder_parity():
    params = AttackParams(
        target="http://example.com",
        method="GET",
        proxy_type="SOCKS5",
        proxy_list="proxies.txt",
        threads=100,
        rpc=50,
        duration=300,
        proxy_refresh=15,
        smart_rpc=True,
        autoscale=True,
        evasion=True,
        behavioral_intensity=35,
        adaptive_learning=True,
        flaresolverr_url="http://localhost:8191/v1"
    )
    cmd = build_attack_command(params)
    
    # Check exact positional arguments sequence right after src.core.engine
    engine_idx = cmd.index("src.core.engine")
    pos_args = cmd[engine_idx + 1:engine_idx + 7]
    assert pos_args == ["GET", "http://example.com", "5", "100", "proxies.txt", "50"]
    assert cmd[engine_idx + 7] == "300"
    assert cmd[engine_idx + 8] == "15"
    
    # Check flags exist and have appropriate values
    assert "--smart" in cmd
    assert "--autoscale" in cmd
    assert "--evasion" in cmd
    assert "--intensity" in cmd
    assert cmd[cmd.index("--intensity") + 1] == "35"
    assert "--adaptive" in cmd
    assert cmd[cmd.index("--adaptive") + 1] == "true"
    assert "--flaresolverr" in cmd
    assert cmd[cmd.index("--flaresolverr") + 1] == "http://localhost:8191/v1"

def test_l4_command_builder_parity():
    params = AttackParams(
        target="1.2.3.4:80",
        method="TCP",
        threads=200,
        duration=60,
        proxy_type="SOCKS5",
        proxy_list="None",
        behavioral_intensity=25,
        adaptive_learning=False
    )
    cmd = build_attack_command(params)
    engine_idx = cmd.index("src.core.engine")
    pos_args = cmd[engine_idx + 1:engine_idx + 5]
    assert pos_args == ["TCP", "1.2.3.4:80", "200", "60"]
    assert "--intensity" in cmd
    assert cmd[cmd.index("--intensity") + 1] == "25"
    assert "--adaptive" in cmd
    assert cmd[cmd.index("--adaptive") + 1] == "false"

def test_l4_amp_command_builder_parity():
    params = AttackParams(
        target="1.2.3.4:53",
        method="DNS",
        threads=50,
        duration=120,
        reflector="dns_reflectors.txt"
    )
    cmd = build_attack_command(params)
    engine_idx = cmd.index("src.core.engine")
    pos_args = cmd[engine_idx + 1:engine_idx + 6]
    assert pos_args == ["DNS", "1.2.3.4:53", "50", "120", "dns_reflectors.txt"]

    params_default = AttackParams(
        target="1.2.3.4:123",
        method="NTP",
        threads=50,
        duration=120,
        reflector=""
    )
    cmd_default = build_attack_command(params_default)
    engine_idx = cmd_default.index("src.core.engine")
    assert cmd_default[engine_idx + 5] == "reflector.txt"

def test_command_builder_auto_harvest():
    params = AttackParams(
        target="http://example.com",
        method="GET",
        auto_harvest=True
    )
    cmd = build_attack_command(params)
    engine_idx = cmd.index("src.core.engine")
    assert cmd[engine_idx + 5] == "auto_harvest.txt"

    params_auto_str = AttackParams(
        target="http://example.com",
        method="GET",
        proxy_list="AUTO"
    )
    cmd2 = build_attack_command(params_auto_str)
    assert cmd2[engine_idx + 5] == "auto_harvest.txt"

def test_command_builder_all_proxy():
    params = AttackParams(
        target="http://example.com",
        method="GET",
        proxy_type="All Proxy",
        proxy_list="None"
    )
    cmd = build_attack_command(params)
    engine_idx = cmd.index("src.core.engine")
    assert cmd[engine_idx + 3] == "0"
    assert cmd[engine_idx + 5] == "all.txt"

def test_command_builder_engines_flag():
    params = AttackParams(
        target="http://example.com",
        method="GET",
        engine_sequence="PY,GO"
    )
    cmd = build_attack_command(params)
    assert "--engines" in cmd
    assert cmd[cmd.index("--engines") + 1] == "PY,GO"

def test_command_builder_c2_shared_cookie_ua():
    orig_cookie = getattr(C2, "shared_cf_cookie", None)
    orig_ua = getattr(C2, "shared_cf_ua", None)
    try:
        C2.shared_cf_cookie = "cf_clearance=test_cookie"
        C2.shared_cf_ua = "TestUA/2.0"
        params = AttackParams(target="http://example.com", method="CFB")
        cmd = build_attack_command(params)
        assert "--shared-cookie" in cmd
        assert cmd[cmd.index("--shared-cookie") + 1] == "cf_clearance=test_cookie"
        assert "--shared-ua" in cmd
        assert cmd[cmd.index("--shared-ua") + 1] == "TestUA/2.0"
    finally:
        C2.shared_cf_cookie = orig_cookie
        C2.shared_cf_ua = orig_ua

def test_command_builder_debug_flag_always_present():
    params = AttackParams(target="http://example.com", method="GET", debug_mode=False)
    cmd = build_attack_command(params)
    assert "--debug" in cmd

# --- Phase 5: Pydantic Validation Tests ---

def test_attack_params_validation_threads_duration_rpc():
    with pytest.raises(ValidationError):
        AttackParams(target="http://example.com", method="GET", threads=0)
    with pytest.raises(ValidationError):
        AttackParams(target="http://example.com", method="GET", threads=-5)
    with pytest.raises(ValidationError):
        AttackParams(target="http://example.com", method="GET", duration=0)
    with pytest.raises(ValidationError):
        AttackParams(target="http://example.com", method="GET", rpc=0)

def test_attack_params_validation_intensity_bounds():
    with pytest.raises(ValidationError):
        AttackParams(target="http://example.com", method="GET", behavioral_intensity=-1)
    with pytest.raises(ValidationError):
        AttackParams(target="http://example.com", method="GET", behavioral_intensity=51)

def test_attack_params_whitespace_stripping():
    params = AttackParams(target="  http://example.com  ", method="  GET  ")
    assert params.target == "http://example.com"
    assert params.method == "GET"

def test_attack_params_default_values():
    params = AttackParams(target="http://example.com", method="GET")
    assert params.threads == 100
    assert params.duration == 3600
    assert params.proxy_type == "SOCKS5"
    assert params.rpc == 100
    assert params.behavioral_intensity == 15
    assert params.adaptive_learning is True
    assert params.flaresolverr_url == "http://localhost:8191/v1"

