"""Integration: FlareSolverr startup → ENGINE_STATE → command build → cookie inject."""
from unittest.mock import patch
import pytest


def _params(**kw):
    from src.app.main import AttackParams
    d = dict(target="https://readtoon.com:443", method="CFB",
             threads=50, rpc=100, duration=60,
             proxy_list="none", proxy_type="SOCKS5", proxy_refresh=300,
             flaresolverr_url="http://localhost:8191/v1")
    d.update(kw)
    return AttackParams(**d)


def test_happy_path_fs_alive():
    """Port 8191 alive → url set in ENGINE_STATE → --flaresolverr in command."""
    import src.core.engine as eng
    eng.ENGINE_STATE.flaresolverr_url = None

    from src.gui.web_runner import start_flaresolverr_backend
    from src.app.main import build_attack_command

    with patch("src.gui.web_runner.is_port_listening", return_value=True):
        start_flaresolverr_backend()
        cmd = build_attack_command(_params())

    assert eng.ENGINE_STATE.flaresolverr_url == "http://localhost:8180/v1"
    assert "--flaresolverr" in cmd
    eng.ENGINE_STATE.flaresolverr_url = None


def test_sad_path_fs_dead():
    """Port 8191 dead → url stays None → --flaresolverr NOT in command."""
    import src.core.engine as eng
    eng.ENGINE_STATE.flaresolverr_url = None

    from src.gui.web_runner import start_flaresolverr_backend
    from src.app.main import build_attack_command

    with patch("src.gui.web_runner.is_port_listening", return_value=False), \
         patch("pathlib.Path.exists", return_value=False):
        start_flaresolverr_backend()
        cmd = build_attack_command(_params())

    assert eng.ENGINE_STATE.flaresolverr_url is None
    assert "--flaresolverr" not in cmd


def test_shared_cookie_injected_when_prefetch_succeeds():
    """C2.shared_cf_cookie set by Phase 0 → --shared-cookie in command."""
    from src.app.main import C2, build_attack_command

    C2.shared_cf_cookie = "cf_clearance=PREFETCHED; __cf_bm=x"
    C2.shared_cf_ua = "Mozilla/5.0 Test"

    with patch("src.gui.web_runner.is_port_listening", return_value=False):
        cmd = build_attack_command(_params())

    assert "--shared-cookie" in cmd
    idx = cmd.index("--shared-cookie")
    assert "cf_clearance" in cmd[idx + 1]

    C2.shared_cf_cookie = None
    C2.shared_cf_ua = None
