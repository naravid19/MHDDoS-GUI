import inspect
from src.core import engine

def test_botasaurus_decorator_allows_css():
    """
    Verify that in _solve_tier2_fast_cdp, Botasaurus is decorated with block_images=True
    instead of block_images_and_css=True so Cloudflare shadow root elements retain height.
    """
    source = inspect.getsource(engine.BrowserEngine._solve_tier2_fast_cdp)
    
    # Ensure block_images_and_css=True is NOT present in Botasaurus configuration
    assert "block_images_and_css=True" not in source, (
        "Botasaurus must not use block_images_and_css=True when bypass_cloudflare=True "
        "because CSS is required for shadow root challenge elements to have non-zero height."
    )
    
    # Ensure block_images=True IS present to maintain bandwidth optimization without breaking layout
    assert "block_images=True" in source, "Expected block_images=True in @browser decorator"
