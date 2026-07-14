import os
import pytest
from pathlib import Path
from src.core.engine import BrowserEngine

@pytest.fixture(autouse=True)
def clean_token_cache():
    """Automatically clear the token_cache.json file and BrowserEngine._cache between tests."""
    cache_path = Path(__file__).resolve().parent.parent / "data" / "assets" / "token_cache.json"
    if cache_path.exists():
        try:
            os.remove(cache_path)
        except Exception:
            pass
    if hasattr(BrowserEngine, "_cache") and isinstance(BrowserEngine._cache, dict):
        BrowserEngine._cache.clear()
    
    yield
    
    if cache_path.exists():
        try:
            os.remove(cache_path)
        except Exception:
            pass
    if hasattr(BrowserEngine, "_cache") and isinstance(BrowserEngine._cache, dict):
        BrowserEngine._cache.clear()
