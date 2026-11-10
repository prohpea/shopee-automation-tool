"""
Unit tests for stealth script structure and properties.
"""

from shopee_tool.core.stealth import STEALTH_JS


def test_stealth_script_contents():
    # Verify key bot detection evasions are present
    assert "navigator.webdriver" in STEALTH_JS
    assert "window.chrome.runtime" in STEALTH_JS
    assert "fakePlugins" in STEALTH_JS
    assert "WebGLRenderingContext.prototype.getParameter" in STEALTH_JS
    assert "notifications" in STEALTH_JS
