import pytest
from src.core import engine

def test_new_bypass_flags_exist():
    assert hasattr(engine, 'BOTASAURUS_INSTALLED')
    assert hasattr(engine, 'PATCHRIGHT_INSTALLED')
    assert hasattr(engine, 'UNDETECTED_CHROMEDRIVER_INSTALLED')
    assert hasattr(engine, 'CAMOUFOX_INSTALLED')
