import sys
import pytest
from src.core.engine import get_max_ram_threshold, get_optimal_ram_threshold

def test_os_aware_ram_thresholds() -> None:
    # Max RAM thresholds
    assert get_max_ram_threshold("win32") == 94.0
    assert get_max_ram_threshold("linux") == 85.0
    
    # Optimal RAM thresholds
    assert get_optimal_ram_threshold("win32") == 75.0
    assert get_optimal_ram_threshold("linux") == 60.0
