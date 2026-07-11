import pytest
from unittest.mock import patch, MagicMock

def _make_proc(total_cpu, children):
    p = MagicMock()
    p.cpu_percent.return_value = total_cpu
    p.children.return_value = children
    return p

def _make_child(name, cpu):
    c = MagicMock(); c.name.return_value = name; c.cpu_percent.return_value = cpu
    return c

def test_excludes_chrome_children():
    from unittest.mock import patch
    proc = _make_proc(80.0, [_make_child("chrome.exe", 70.0), _make_child("python.exe", 5.0)])
    with patch("psutil.Process", return_value=proc):
        from src.core.engine import _get_attack_cpu_percent
        assert _get_attack_cpu_percent() == pytest.approx(10.0, abs=1.0)

def test_result_never_negative():
    proc = _make_proc(20.0, [_make_child("chromium", 90.0)])
    with patch("psutil.Process", return_value=proc):
        from src.core.engine import _get_attack_cpu_percent
        assert _get_attack_cpu_percent() >= 0.0
