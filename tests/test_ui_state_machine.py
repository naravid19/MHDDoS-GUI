import os
import pytest


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_css_tactical_glow_definitions() -> None:
    css_path = os.path.join(root_dir, "web", "design-pro-max.css")
    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".tactical-glow-primary" in content, "Missing .tactical-glow-primary class in design-pro-max.css"
    assert ".tactical-glow-error" in content, "Missing .tactical-glow-error class in design-pro-max.css"
    assert "tactical-breathing-glow" in content, "Missing keyframe animation tactical-breathing-glow"
    assert "transform: scale(" not in content.split("@keyframes tactical-breathing-glow")[1].split("}")[0] and "transform: scale(" not in content.split("@keyframes tactical-breathing-glow")[1].split("}")[1], "@keyframes tactical-breathing-glow must not animate transform: scale to avoid overriding button click micro-interactions"


def test_html_button_markup() -> None:
    html_path = os.path.join(root_dir, "web", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "tactical-glow-primary" in content, "deploy-hub-btn must use tactical-glow-primary instead of hardcoded shadow"
    assert 'id="deploy-hub-icon" class="material-symbols-outlined text-xl"' in content or 'class="material-symbols-outlined text-xl" id="deploy-hub-icon"' in content, "deploy-hub-icon must use text-xl for proper proportion"
    assert "design-pro-max.css" in content, "index.html must link design-pro-max.css"


def test_js_set_app_state_reconciliation() -> None:
    js_path = os.path.join(root_dir, "web", "js", "ui", "ui-pro-max.js")
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must explicitly remove animate-spin in running state or general cleanup
    assert "deployIcon.classList.remove('animate-spin')" in content, "setAppState must explicitly remove animate-spin"
    # Must explicitly restore disabled = false in running state
    assert "deployBtn.disabled = false" in content, "setAppState must explicitly restore disabled = false"
    # Must toggle tactical-glow-error and tactical-glow-primary
    assert "tactical-glow-error" in content, "setAppState must apply tactical-glow-error in running state"
    assert "tactical-glow-primary" in content, "setAppState must apply tactical-glow-primary in idle state"
    assert "if (!deployBtn || !deployIcon || !deployText) return;" in content, "setAppState must defensively check deployBtn, deployIcon, and deployText"
    assert "views.forEach(n =>" in content or "const navs =" in content, "switchView must not reference undefined navs variable"


def test_telemetry_js_reads_rps_not_pps() -> None:
    js_path = os.path.join(root_dir, "web", "js", "core", "telemetry.js")
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert 'm.rps' in content, "telemetry.js must read m.rps"
    assert 'm.pps' not in content, "telemetry.js must not read m.pps"


def test_telemetry_js_has_latency_in_aggregate() -> None:
    js_path = os.path.join(root_dir, "web", "js", "core", "telemetry.js")
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "'current-latency'" in content, "getAggregate must return current-latency"
    assert "'peak-latency'" in content, "getAggregate must return peak-latency"


def test_main_js_maps_latency_dom() -> None:
    js_path = os.path.join(root_dir, "web", "js", "main.js")
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert 'current-latency' in content, "main.js must update current-latency DOM"
    assert 'peak-latency' in content, "main.js must update peak-latency DOM"
