import sys
from src.app.main import build_attack_command, AttackParams

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
