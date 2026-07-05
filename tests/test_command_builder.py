import pytest
from src.app.main import build_attack_command, AttackParams


def test_build_attack_command_includes_debug() -> None:
    params = AttackParams(
        target="https://example.com",
        duration=60,
        threads=10,
        method="GET",
        rpc=100
    )
    command = build_attack_command(params)
    assert "--debug" in command, "build_attack_command must include '--debug' flag so engine emits verbose diagnostic logs for GUI terminal filtering"
