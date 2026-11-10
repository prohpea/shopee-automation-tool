"""
Shopee Automation Tool - Browser Lifecycle & Stealth Context Manager.
Handles Playwright Chromium launch, anti-bot flags, stealth scripts, and proxy injection.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Tuple, Union
from playwright.async_api import (
    Playwright,
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)
from .config import settings
from .stealth import apply_stealth
from .session import SessionManager
from ..utils.logger import logger

DEFAULT_WINDOWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-extensions",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--no-zygote",
    "--disable-gpu",
    "--window-size=1366,768",
]


class BrowserManager:
    """Manages Playwright browser lifecycle with anti-detection evasions and Chrome support."""

    def __init__(
        self,
        headless: Optional[bool] = None,
        session_name: Optional[str] = None,
        proxy_server: Optional[str] = None,
        stealth: Optional[bool] = None,
        use_persistent_profile: bool = False,
        channel: Optional[str] = None,
        cdp: Optional[Union[str, int]] = None,
    ):
        self.headless = settings.headless if headless is None else headless
        self.session_name = session_name or settings.default_session_name
        self.session_mgr = SessionManager(self.session_name)
        self.proxy_server = proxy_server or settings.proxy_server
        self.stealth = settings.stealth_mode if stealth is None else stealth
        self.use_persistent_profile = use_persistent_profile
        self.channel = channel
        self.cdp = cdp

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_cdp: bool = False

    async def start(self) -> Page:
        """Initializes Playwright, launches browser, configures context and returns a page."""
        self._playwright = await async_playwright().start()

        proxy_dict = None
        if self.proxy_server:
            proxy_dict = {"server": self.proxy_server}
            if settings.proxy_username:
                proxy_dict["username"] = settings.proxy_username
                proxy_dict["password"] = settings.proxy_password

        if self.cdp and str(self.cdp).lower() != "none":
            endpoint = f"http://127.0.0.1:{self.cdp}" if str(self.cdp).isdigit() else str(self.cdp)
            logger.info(f"Connecting to Chrome via CDP at {endpoint}...")
            self._browser = await self._playwright.chromium.connect_over_cdp(endpoint)
            self._is_cdp = True
            self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()

            target_page = None
            for p in self._context.pages:
                if "shopee" in (p.url or "").lower():
                    target_page = p
                    break
            if not target_page:
                for p in self._context.pages:
                    u = (p.url or "").lower()
                    if not u.startswith(("chrome://", "devtools://", "chrome-extension://")):
                        target_page = p
                        break

            self._page = target_page or await self._context.new_page()
            return self._page

        user_agent = settings.custom_user_agent or DEFAULT_WINDOWS_UA
        storage_state = self.session_mgr.get_storage_state_path()

        if self.use_persistent_profile:
            profile_dir = settings.get_profile_dir(self.session_name)
            logger.info(f"Launching persistent browser profile at: {profile_dir}")
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=self.headless,
                channel=self.channel,
                args=CHROMIUM_ARGS,
                user_agent=user_agent,
                locale="vi-VN",
                timezone_id="Asia/Ho_Chi_Minh",
                viewport={"width": 1366, "height": 768},
                proxy=proxy_dict,
            )
            pages = self._context.pages
            self._page = pages[0] if pages else await self._context.new_page()
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                channel=self.channel,
                args=CHROMIUM_ARGS,
            )

            context_kwargs = {
                "user_agent": user_agent,
                "locale": "vi-VN",
                "timezone_id": "Asia/Ho_Chi_Minh",
                "viewport": {"width": 1366, "height": 768},
                "device_scale_factor": 1.0,
                "is_mobile": False,
                "has_touch": False,
            }

            if storage_state:
                logger.info(f"Restoring session state from: {storage_state}")
                context_kwargs["storage_state"] = storage_state

            if proxy_dict:
                context_kwargs["proxy"] = proxy_dict

            self._context = await self._browser.new_context(**context_kwargs)
            self._page = await self._context.new_page()

        # Set default timeouts
        self._page.set_default_navigation_timeout(settings.nav_timeout_ms)
        self._page.set_default_timeout(settings.nav_timeout_ms)

        # Inject stealth scripts
        if self.stealth and self._context:
            await apply_stealth(self._context)

        return self._page

    async def save_session(self) -> None:
        """Saves current cookies and storage state."""
        if self._context:
            await self.session_mgr.save_session(self._context)

    async def close(self) -> None:
        """Gracefully closes page, context, and browser (preserves open Chrome tab when using CDP)."""
        try:
            if self._page and not self._is_cdp and not self._page.is_closed():
                await self._page.close()
        except Exception:
            pass

        try:
            if self._context and not self._is_cdp:
                await self._context.close()
        except Exception:
            pass

        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

    @property
    def page(self) -> Optional[Page]:
        return self._page

    @property
    def context(self) -> Optional[BrowserContext]:
        return self._context


@asynccontextmanager
async def get_browser(
    headless: Optional[bool] = None,
    session_name: Optional[str] = None,
    use_persistent_profile: bool = False,
) -> AsyncGenerator[Tuple[BrowserManager, Page], None]:
    """Context manager for clean lifecycle handling."""
    mgr = BrowserManager(
        headless=headless,
        session_name=session_name,
        use_persistent_profile=use_persistent_profile,
    )
    page = await mgr.start()
    try:
        yield mgr, page
    finally:
        await mgr.close()