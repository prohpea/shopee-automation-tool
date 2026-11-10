"""
Unit tests for captcha detector selector configurations.
"""

from unittest.mock import AsyncMock, MagicMock
from shopee_tool.utils.captcha import CaptchaDetector


def test_captcha_detector_attributes():
    mock_page = MagicMock()
    detector = CaptchaDetector(mock_page)

    assert len(detector.CAPTCHA_SELECTORS) >= 5
    assert any("captcha" in s for s in detector.CAPTCHA_SELECTORS)
    assert any("puzzle" in s for s in detector.CAPTCHA_SELECTORS)
    assert len(detector.OTP_SELECTORS) >= 3


def test_is_captcha_present_positive():
    import asyncio
    mock_page = MagicMock()
    mock_element = MagicMock()
    mock_element.is_visible = AsyncMock(return_value=True)
    mock_page.query_selector = AsyncMock(return_value=mock_element)

    detector = CaptchaDetector(mock_page)
    result = asyncio.run(detector.is_captcha_present())
    assert result is True


def test_is_captcha_present_negative():
    import asyncio
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=None)

    detector = CaptchaDetector(mock_page)
    result = asyncio.run(detector.is_captcha_present())
    assert result is False
