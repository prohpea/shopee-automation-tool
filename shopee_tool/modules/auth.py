"""
Shopee Automation Tool - Authentication Module.
Handles interactive login, QR code scanning, session saving, and login state verification.
"""

import asyncio
from typing import Optional
from playwright.async_api import Page
from ..core.browser import BrowserManager
from ..core.config import settings
from ..core.session import SessionManager
from ..core.human import sleep_random
from ..utils.logger import logger
from ..utils.captcha import CaptchaDetector


class AuthManager:
    """Manages Shopee authentication, login sessions, and verification."""

    LOGGED_IN_SELECTORS = [
        ".navbar__username",
        "div.shopee-avatar",
        "a[href*='/user/account/profile']",
        "div:has-text('Tài khoản của tôi')",
        "div:has-text('My Account')",
    ]

    def __init__(self, session_name: Optional[str] = None):
        self.session_name = session_name or settings.default_session_name
        self.session_mgr = SessionManager(self.session_name)

    async def is_logged_in(self, page: Page) -> bool:
        """
        Checks whether the current page session is logged in.
        Verifies via DOM elements and presence of essential authentication cookies.
        """
        # First check DOM
        for selector in self.LOGGED_IN_SELECTORS:
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    return True
            except Exception:
                continue

        # Second check cookies for active SPC_EC or SPC_ST
        cookies = await page.context.cookies()
        auth_cookie_names = {"SPC_EC", "SPC_ST", "SPC_U", "SPC_R_T_ID"}
        found_auth_cookies = {c["name"] for c in cookies if c["name"] in auth_cookie_names and c.get("value")}
        
        return len(found_auth_cookies) >= 2

    async def interactive_login(self, timeout_seconds: int = 180) -> bool:
        """
        Opens a visible browser window to let the user log in (QR Code, SMS OTP, or username/password).
        Once logged in, saves the session state to disk for headless reuse.
        """
        logger.info(
            f"[bold cyan]Starting interactive login session '{self.session_name}'...[/bold cyan]"
        )
        logger.info("Opening browser window (headful mode)...")

        # Must run headfully for manual user login & QR scan
        mgr = BrowserManager(
            headless=False,
            session_name=self.session_name,
        )

        try:
            page = await mgr.start()
            login_url = settings.login_url
            logger.info(f"Navigating to login page: {login_url}")
            await page.goto(login_url, wait_until="domcontentloaded")

            detector = CaptchaDetector(page)

            logger.info(
                "[bold yellow]👉 Please scan the QR code or log in using your Shopee credentials in the browser.[/bold yellow]"
            )
            logger.info(
                f"Waiting up to {timeout_seconds} seconds for successful login..."
            )

            elapsed = 0
            check_interval = 2.0
            logged_in = False

            while elapsed < timeout_seconds:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                # Handle any captcha checkpoint
                if await detector.is_captcha_present() or await detector.is_otp_required():
                    await detector.wait_for_manual_solve(timeout_seconds=60)

                # Check if redirected to homepage or profile or logged in
                current_url = page.url
                if ("buyer/login" not in current_url) or (await self.is_logged_in(page)):
                    # Confirm login state
                    await sleep_random(2.0, 3.0)
                    if await self.is_logged_in(page):
                        logged_in = True
                        break

            if logged_in:
                logger.info("[bold green]🎉 Login successful![/bold green]")
                # Save session state
                saved_path = await mgr.session_mgr.save_session(mgr.context)
                logger.info(f"Session saved to: {saved_path}")
                await sleep_random(1.0, 2.0)
                return True
            else:
                logger.error("[bold red]❌ Login timed out or was not completed.[/bold red]")
                return False

        except Exception as e:
            logger.error(f"Error during interactive login: {e}")
            return False
        finally:
            await mgr.close()

    async def verify_session(self, cdp: Optional[str] = "9222") -> bool:
        """Verifies if the current Chrome CDP session or saved session is valid and authenticated."""
        from ..modules.fast_voucher_hunter import is_cdp_port_active, FastVoucherHunter

        if cdp and str(cdp).lower() != "none" and is_cdp_port_active(cdp):
            logger.info(f"Đang kiểm tra trạng thái đăng nhập trên Google Chrome (CDP {cdp})...")
            hunter = FastVoucherHunter(cdp=cdp)
            try:
                page = await hunter.connect()
                if "shopee" not in (page.url or "").lower():
                    await page.goto(settings.base_url, wait_until="domcontentloaded", timeout=25000)
                    await sleep_random(1.0, 2.0)
                await hunter.check_and_handle_verification()
                valid = await self.is_logged_in(page)
                if valid:
                    await hunter.save_session_state()
                    logger.info(f"[bold green]✓ Phiên đăng nhập '{self.session_name}' HỢP LỆ và đang hoạt động![/bold green]")
                    return True
            except Exception as e:
                logger.debug(f"CDP session check error: {e}")
            finally:
                await hunter.close()

        if not self.session_mgr.exists():
            logger.warning(
                f"No saved session found for '{self.session_name}' at {self.session_mgr.session_path}"
            )
            return False

        logger.info(f"Checking session validity for '{self.session_name}'...")
        mgr = BrowserManager(headless=True, session_name=self.session_name)
        try:
            page = await mgr.start()
            await page.goto(settings.base_url, wait_until="domcontentloaded")
            await sleep_random(1.5, 2.5)

            valid = await self.is_logged_in(page)
            if valid:
                logger.info(f"[green]✓ Session '{self.session_name}' is VALID and active.[/green]")
            else:
                logger.warning(
                    f"[yellow]⚠️ Session '{self.session_name}' is expired or not authenticated.[/yellow]"
                )
            return valid
        except Exception as e:
            logger.error(f"Failed to verify session: {e}")
            return False
        finally:
            await mgr.close()
