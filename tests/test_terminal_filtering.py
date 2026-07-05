import os
import pytest

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_terminal_js_non_destructive_filtering() -> None:
    js_path = os.path.join(root_dir, "web", "js", "ui", "terminal.js")
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must NOT discard logs early before DOM creation
    assert "if (numericLevel < threshold) return;" not in content, "TerminalUI.append must not permanently discard logs below threshold; it must use non-destructive hiding"
    
    # Must store dataset.numericLevel on created entries
    assert "entry.dataset.numericLevel = numericLevel;" in content or "entry.dataset.numericLevel = String(numericLevel);" in content, "TerminalUI.append must assign dataset.numericLevel to DOM entry"
    
    # Must toggle 'hidden' class in append
    assert "classList.add('hidden')" in content and "classList.remove('hidden')" in content, "TerminalUI must use Tailwind 'hidden' class for filtering entries"
    
    # setLevel must iterate over existing terminal entries and re-filter them
    assert "querySelectorAll('.terminal-entry')" in content, "setLevel must re-evaluate existing .terminal-entry elements when filter level changes"
