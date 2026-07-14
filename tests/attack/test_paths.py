import os
from src.core.paths import get_project_root, get_bin_path, get_data_path

def test_project_root():
    root = get_project_root()
    # Verify by checking for a known file in root
    assert (root / "requirements.txt").exists()

def test_bin_path():
    bin_dir = get_bin_path()
    assert bin_dir.name == "bin"
    assert bin_dir.is_dir()

def test_data_path():
    data_dir = get_data_path()
    assert data_dir.name == "data"
    assert data_dir.is_dir()
