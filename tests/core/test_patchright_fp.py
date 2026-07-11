def test_inject_sets_navigator_properties():
    from src.core.engine import _inject_cf_fingerprint
    from unittest.mock import MagicMock
    page = MagicMock()
    _inject_cf_fingerprint(page)
    assert page.add_init_script.called
    script = page.add_init_script.call_args[0][0]
    assert "hardwareConcurrency" in script
    assert "deviceMemory" in script
    assert "webdriver" in script

def test_inject_spoofs_webgl():
    from src.core.engine import _inject_cf_fingerprint
    from unittest.mock import MagicMock
    page = MagicMock()
    _inject_cf_fingerprint(page)
    script = page.add_init_script.call_args[0][0]
    assert "ANGLE" in script or "Intel" in script

def test_inject_called_before_goto():
    from unittest.mock import patch, MagicMock, call
    from src.core.engine import _run_patchright_bypass, _inject_cf_fingerprint
    page = MagicMock()
    page.title.return_value = "readtoon.com"
    page.cookies.return_value = [{"name": "cf_clearance", "value": "tok"}]
    ctx = MagicMock(); ctx.new_page.return_value = page; ctx.cookies.return_value = []
    browser = MagicMock(); browser.new_context.return_value = ctx
    with patch("src.core.engine._inject_cf_fingerprint") as mock_inj, \
         patch("patchright.sync_api.sync_playwright") as pw:
        pw.return_value.__enter__.return_value.chromium.launch.return_value = browser
        _run_patchright_bypass("https://readtoon.com")
    assert mock_inj.called
