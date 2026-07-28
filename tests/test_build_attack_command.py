"""Tests: build_attack_command flaresolverr port-guard."""
from unittest.mock import patch
import pytest


def _params(**kwargs):
    from src.app.main import AttackParams
    d = dict(
        target="https://example.com", method="CFB",
        threads=100, rpc=100, duration=60,
        proxy_list="none", proxy_type="SOCKS5", proxy_refresh=300,
    )
    d.update(kwargs)
    return AttackParams(**d)


def test_flag_omitted_when_port_dead():
    """--flaresolverr must NOT appear when port 8191 unreachable."""
    from src.app.main import build_attack_command
    with patch("src.gui.web_runner.is_port_listening", return_value=False):
        cmd = build_attack_command(_params(flaresolverr_url="http://localhost:8191/v1"))
    assert "--flaresolverr" not in cmd


def test_flag_present_when_port_alive():
    """--flaresolverr must appear with correct URL when port 8191 reachable."""
    from src.app.main import build_attack_command
    with patch("src.gui.web_runner.is_port_listening", return_value=True):
        cmd = build_attack_command(_params(flaresolverr_url="http://localhost:8191/v1"))
    assert "--flaresolverr" in cmd
    assert cmd[cmd.index("--flaresolverr") + 1] == "http://localhost:8191/v1"
