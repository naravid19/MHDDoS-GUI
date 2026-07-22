import pytest
import warnings
from unittest.mock import AsyncMock, MagicMock
from src.core.debugger import BypassDebugger

def test_capture_failure_handles_async_get_screenshot(tmp_path, monkeypatch):
    monkeypatch.setattr(BypassDebugger, "DEBUG_DIR", str(tmp_path))
    
    # Create mock page where get_screenshot is an AsyncMock returning a coroutine
    mock_page = MagicMock(spec=["get_screenshot", "html"])
    mock_page.get_screenshot = AsyncMock()
    mock_page.html = "<html><body>test</body></html>"

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        BypassDebugger.capture_failure("test_tier", "http://example.com", page_obj=mock_page)

    runtime_warnings = [w for w in record if issubclass(w.category, RuntimeWarning)]
    assert len(runtime_warnings) == 0, f"Expected 0 RuntimeWarnings, got: {runtime_warnings}"
