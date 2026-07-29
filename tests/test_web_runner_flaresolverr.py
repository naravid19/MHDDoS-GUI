import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.engine import ENGINE_STATE
from src.gui.web_runner import start_flaresolverr_backend


@pytest.fixture(autouse=True)
def reset_engine_state():
    ENGINE_STATE.flaresolverr_url = None
    yield
    ENGINE_STATE.flaresolverr_url = None


def test_flaresolverr_port_already_listening():
    with patch("src.gui.web_runner.is_port_listening", return_value=True):
        result = start_flaresolverr_backend()
        assert result is True
        assert ENGINE_STATE.flaresolverr_url == "http://localhost:8180/v1"


def test_flaresolverr_binary_not_found_port_dead():
    with patch("src.gui.web_runner.is_port_listening", return_value=False), \
         patch.object(Path, "exists", return_value=False):
        result = start_flaresolverr_backend()
        assert result is False
        assert ENGINE_STATE.flaresolverr_url is None


def test_flaresolverr_binary_found_and_port_comes_alive():
    # is_port_listening returns False on initial check, then True during polling
    listening_mock = MagicMock(side_effect=[False, True])

    with patch("src.gui.web_runner.is_port_listening", listening_mock), \
         patch.object(Path, "exists", return_value=True), \
         patch("subprocess.Popen") as mock_popen, \
         patch("time.sleep", return_value=None):
        result = start_flaresolverr_backend()
        assert result is True
        assert ENGINE_STATE.flaresolverr_url == "http://localhost:8180/v1"
        assert mock_popen.called
