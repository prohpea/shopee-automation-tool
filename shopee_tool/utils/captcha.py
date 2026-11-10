"""
Shopee Automation Tool - Captcha and Verification Detector.
Detects Shopee puzzles, slide captchas, SMS OTP requests, and anti-bot verification screens.
"""

from typing import Optional, Callable
from playwright.async_api import Page
from .logger import logger


class CaptchaDetector:
    """Detects and alerts on Shopee security challenges (captchas, OTPs, verification)."""

    CAPTCHA_SELECTORS = [
        "iframe[src*='captcha']",
        "div[class*='shopee-puzzle-drag']",
        "div[class*='captcha']",
        ".shopee-slider-captcha",
        "div.geetest_radar_tip",
        "div.geetest_popup_wrap",
        "#captcha_container",
        "div:has-text('Vui lòng hoàn thành xác minh')",
        "div:has-text('Please complete verification')",
    ]

    OTP_SELECTORS = [
        "input[type='tel']",
        "input[placeholder*='OTP']",
        "input[placeholder*='mã xác nhận']",
        "input[placeholder*='verification code']",
        "div:has-text('Nhập mã xác nhận')",
        "div:has-text('Enter Verification Code')",
    ]

    def __init__(self, page: Page):
        self.page = page

    async def is_captcha_present(self) -> bool:
        """Checks if any captcha or puzzle verification element is visible."""
        for selector in self.CAPTCHA_SELECTORS:
            try:
                el = await self.page.query_selector(selector)
                if el and await el.is_visible():
                    return True
            except Exception:
                continue
        return False

    async def is_otp_required(self) -> bool:
        """Checks if an OTP / verification code input is currently presented."""
        for selector in self.OTP_SELECTORS:
            try:
                el = await self.page.query_selector(selector)
                if el and await el.is_visible():
                    return True
            except Exception:
                continue
        return False

    async def wait_for_manual_solve(
        self,
        timeout_seconds: int = 120,
        check_interval: float = 2.0,
        callback: Optional[Callable[[], None]] = None,
    ) -> bool:
        """
        Pauses and waits for the user to manually solve the captcha/OTP in the browser window.
        Returns True if resolved before timeout, False otherwise.
        """
        is_captcha = await self.is_captcha_present()
        is_otp = await self.is_otp_required()

        if not (is_captcha or is_otp):
            return True

        challenge_type = "Captcha / Puzzle" if is_captcha else "SMS / Email OTP"
        logger.warning(
            f"[bold yellow]⚠️ {challenge_type} detected! Please solve it in the browser window.[/bold yellow]"
        )
        logger.info(f"Waiting up to {timeout_seconds} seconds for manual resolution...")

        if callback:
            callback()

        elapsed = 0.0
        while elapsed < timeout_seconds:
            await self.page.wait_for_timeout(int(check_interval * 1000))
            elapsed += check_interval

            captcha_still_here = await self.is_captcha_present()
            otp_still_here = await self.is_otp_required()

            if not (captcha_still_here or otp_still_here):
                logger.info(
                    "[bold green]✓ Challenge solved successfully! Continuing...[/bold green]"
                )
                # Extra small delay for page state to settle
                await self.page.wait_for_timeout(1500)
                return True

        logger.error(
            f"[bold red]✗ Timed out waiting for {challenge_type} resolution.[/bold red]"
        )
        return False
