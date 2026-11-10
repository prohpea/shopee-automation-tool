"""
Shopee Automation Tool - Fast Voucher Hunter Module.
Specialized high-speed voucher collector interacting directly with Google Chrome (via CDP or persistent session).
Uses direct DOM JavaScript evaluation to claim vouchers in milliseconds.
"""

import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Union
import urllib.parse
import urllib.request
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..core.config import settings
from ..utils.logger import console, logger


def find_chrome_executable() -> Optional[str]:
    """Locates the Google Chrome executable path on Windows."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
        )
        val, _ = winreg.QueryValueEx(key, "")
        if os.path.exists(val):
            return val
    except Exception:
        pass
    return None


def _cdp_http(port: Union[int, str], path: str, timeout: float = 2.0) -> Optional[str]:
    """Calls a passive Chrome DevTools HTTP endpoint (/json/...). Does not attach a debugger to any page."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{int(port)}{path}",
            headers={"User-Agent": "ShopeeToolCDPCheck"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def is_cdp_port_active(port: Union[int, str] = 9222) -> bool:
    """Checks if Google Chrome CDP remote debugging port is open and responding."""
    return _cdp_http(port, "/json/version", timeout=1.0) is not None


def _cdp_list_page_tabs(port: Union[int, str]) -> List[Dict[str, Any]]:
    """Returns open page tabs from Chrome's passive /json endpoint."""
    raw = _cdp_http(port, "/json")
    if not raw:
        return []
    try:
        return [t for t in json.loads(raw) if t.get("type") == "page"]
    except Exception:
        return []


def _is_mock(obj: Any) -> bool:
    """True for unit-test doubles, which skip real browser waits."""
    return "mock" in type(obj).__name__.lower()


def get_default_chrome_user_data_dir() -> str:
    """
    Returns a directory junction pointing directly to the user's real Desktop Google Chrome
    User Data directory (%LOCALAPPDATA%\\Google\\Chrome\\User Data).
    This allows Chrome to open with the exact Desktop profile, cookies, history, and verification
    state while bypassing Chrome's default-path restriction on --remote-debugging-port.
    """
    real_chrome_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    junction_path = settings.profiles_dir / "desktop_chrome"
    settings.profiles_dir.mkdir(parents=True, exist_ok=True)

    if os.path.exists(real_chrome_data):
        if not junction_path.exists():
            try:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(junction_path), real_chrome_data],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass
        if junction_path.exists():
            return str(junction_path)

    profile_path = settings.get_profile_dir("chrome_debug")
    profile_path.mkdir(parents=True, exist_ok=True)
    return str(profile_path)


def auto_launch_chrome_cdp(
    port: Union[int, str] = 9222, profile_dir: Optional[str] = None, start_url: Optional[str] = None
) -> Optional[Any]:
    """
    Automatically launches the user's Desktop Google Chrome with remote debugging port enabled.
    If Chrome is already running without the debugging port, gracefully restarts it with
    --restore-last-session so open tabs and login state are preserved.
    """
    if is_cdp_port_active(port):
        logger.info(f"[bold green]✓ Cổng Google Chrome CDP ({port}) đang sẵn sàng![/bold green]")
        return None

    chrome_exe = find_chrome_executable()
    if not chrome_exe:
        logger.warning("Không tìm thấy chrome.exe trên máy tính để tự động mở Chrome.")
        return None

    if not profile_dir:
        profile_dir = get_default_chrome_user_data_dir()

    # If Chrome is already running without CDP port, close it so the profile lock is released
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            if "chrome.exe" in (res.stdout or "").lower():
                logger.info(
                    "Đang chuyển đổi cửa sổ Chrome hiện tại trên Desktop sang chế độ kết nối tự động (giữ nguyên các tab đang mở)..."
                )
                subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                time.sleep(1.5)
        except Exception:
            pass

    logger.info(
        f"Đang khởi chạy Google Chrome chính trên Desktop với cổng kết nối [bold cyan]{port}[/bold cyan]..."
    )
    cmd = [
        chrome_exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--restore-last-session",
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
        start_url or settings.vouchers_url,
    ]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    proc = subprocess.Popen(cmd, creationflags=flags)

    # Wait up to 10 seconds for CDP port to open
    for _ in range(20):
        time.sleep(0.5)
        if is_cdp_port_active(port):
            logger.info(
                f"[bold green]✓ Google Chrome đã mở cổng CDP {port}! Đang đợi trang Shopee tải hoàn tất (4.5s)...[/bold green]"
            )
            # Crucial: Let Chrome load the Shopee voucher page natively BEFORE Playwright attaches CDP
            # so Shopee's dfp-exp page-load anti-bot check passes with zero CDP debugger attached.
            time.sleep(4.5)
            return proc

    logger.warning("Chrome đã được gọi nhưng chưa phản hồi trên cổng CDP trong 10 giây.")
    return proc


# High-speed JavaScript: scans, prioritizes "Voucher Khủng", and clicks every claimable
# voucher instantly. Kept in claim_vouchers.js so it stays real, lintable JavaScript.
JS_CLAIM_VOUCHERS = (Path(__file__).parent / "claim_vouchers.js").read_text(encoding="utf-8").strip()

JS_RESET_CLICKED_VOUCHERS = """
() => {
    window._shopeeClickedVouchers = new WeakSet();
    return true;
}
"""

JS_SCROLL_TO_TOP = """
() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
    if (document.documentElement) document.documentElement.scrollTop = 0;
    if (document.body) document.body.scrollTop = 0;
    return true;
}
"""

JS_FAST_SCROLL = """
(offset) => {
    window.scrollBy({ top: offset, behavior: 'instant' });
    if (document.documentElement) {
        document.documentElement.scrollTop += offset;
    }
    if (document.body) {
        document.body.scrollTop += offset;
    }
    return {
        scrollY: window.scrollY || (document.documentElement ? document.documentElement.scrollTop : 0),
        scrollHeight: Math.max(
            document.body ? document.body.scrollHeight : 0,
            document.documentElement ? document.documentElement.scrollHeight : 0
        ),
        innerHeight: window.innerHeight
    };
}
"""


class FastVoucherHunter:
    """
    High-speed Shopee Voucher Hunter (24/7 Golden Hour & Flash Drop Auto-Sniper).
    Connects to Google Chrome via Chrome DevTools Protocol (CDP) or persistent session,
    navigates to voucher hubs, and executes ultra-fast JS evaluation to claim vouchers.
    """

    # Major Shopee Golden Hours (Khung Giờ Vàng Chính tung mã khủng toàn sàn)
    GOLDEN_HOURS_MAJOR = {
        (0, 0): "🔥 SIÊU GIỜ VÀNG NỬA ĐÊM (00:00 - Mã Khủng Nhất Ngày)",
        (6, 0): "⚡ KHUNG GIỜ VÀNG SÁNG SỚM (06:00 - Khởi Động Săn Sale)",
        (9, 0): "🔥 KHUNG GIỜ VÀNG BUỔI SÁNG (09:00 - Mở Màn Săn Sale)",
        (11, 0): "⚡ KHUNG GIỜ VÀNG TRƯA SỚM (11:00 - Bật Mí Voucher Hot)",
        (12, 0): "🔥 SIÊU GIỜ VÀNG GIỮA TRƯA (12:00 - Đại Tiệc Mã Giảm Giá)",
        (15, 0): "🔥 KHUNG GIỜ VÀNG BUỔI CHIỀU (15:00 - Tung Thêm Lượt Mã Hot)",
        (18, 0): "🔥 KHUNG GIỜ VÀNG BUỔI TỐI (18:00 - Giờ Cao Điểm Mua Sắm)",
        (20, 0): "🔥 KHUNG GIỜ VÀNG LIVESTREAM & VIDEO (20:00 - Mã Giảm 50%)",
        (21, 0): "🔥 SIÊU GIỜ VÀNG ĐÊM KHUYA (21:00 - Đợt Tung Mã Cuối Ngày)",
        (22, 0): "🔥 KHUNG GIỜ VÀNG CHỐT ĐƠN ĐÊM (22:00 - Xả Kho Voucher)",
        (23, 0): "⚡ KHUNG GIỜ VÀNG 1 GIỜ CUỐI (23:00 - Chốt Hạ Sale Sập Sàn)",
    }

    # Secondary hourly drop slots (Khung Giờ Cao Điểm - mỗi giờ tròn, nghỉ 03h-05h).
    # Kept deliberately sparse: every page load is an anti-bot exposure on Shopee.
    PEAK_DROP_SLOTS = [(h, 0) for h in range(24) if h not in (3, 4, 5)]

    def __init__(
        self,
        cdp: Optional[Union[str, int]] = 9222,
        url: Optional[str] = None,
        all_hubs: bool = False,
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        max_claims: int = 50,
    ):
        self.cdp = cdp
        self.url = url or settings.vouchers_url
        self.all_hubs = all_hubs
        self.headless = headless
        self.user_data_dir = user_data_dir or get_default_chrome_user_data_dir()
        self.max_claims = max_claims

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_cdp = False
        self._chrome_proc = None

    def _normalize_cdp_url(self, cdp_val: Union[str, int]) -> str:
        s = str(cdp_val).strip()
        if s.startswith("http://") or s.startswith("https://") or s.startswith("ws://"):
            return s
        if s.isdigit():
            return f"http://127.0.0.1:{s}"
        return f"http://{s}"

    def _cdp_port(self) -> int:
        """CDP port as int, defaulting to 9222 for non-numeric CDP values."""
        return int(self.cdp) if str(self.cdp).isdigit() else 9222

    async def _launch_persistent_chrome(self) -> Page:
        """Launches the real Google Chrome with the user's profile (no CDP attach)."""
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            viewport={"width": 1366, "height": 768},
        )
        self._page = (
            self._context.pages[0]
            if self._context.pages
            else await self._context.new_page()
        )
        return self._page

    @staticmethod
    def _is_blocked_tab(url: str) -> bool:
        """True for verification/anti-bot pages and non-web Chrome tabs."""
        u = url.lower()
        return (
            u.startswith(("chrome://", "devtools://", "chrome-extension://"))
            or "verify" in u
            or "anti_bot" in u
        )

    def _pick_existing_tab(self) -> Optional[Page]:
        """
        Picks the best existing tab to reuse, in preference order:
        1. A clean target-hub tab, 2. any clean Shopee tab, 3. any clean tab,
        4. any tab at all. Never closes the user's browser.
        """
        pages = self._context.pages if self._context else []
        target_base = self.url.rstrip("/").lower()
        for page in pages:
            if target_base in (page.url or "").lower() and not self._is_blocked_tab(page.url or ""):
                return page
        for page in pages:
            if "shopee" in (page.url or "").lower() and not self._is_blocked_tab(page.url or ""):
                return page
        for page in pages:
            if not self._is_blocked_tab(page.url or ""):
                return page
        return pages[0] if pages else None

    async def connect(self) -> Page:
        """
        Connects to Chrome browser. Prefers CDP (port 9222 or custom).
        Automatically launches Google Chrome if port is not yet active,
        or seamlessly falls back to persistent Chrome session.
        """
        self._playwright = await async_playwright().start()

        if not self.cdp or str(self.cdp).lower() == "none":
            return await self._launch_persistent_chrome()

        port = self._cdp_port()
        target_base = self.url.rstrip("/")

        if not is_cdp_port_active(port):
            # Auto-launch Chrome on the default port only; other ports must be user-managed.
            if port == 9222:
                self._chrome_proc = auto_launch_chrome_cdp(
                    port=port, profile_dir=self.user_data_dir, start_url=target_base
                )
        else:
            # Chrome loads the hub natively (no debugger attached) so its page-load
            # anti-bot handshake passes before Playwright attaches.
            has_clean_hub = any(
                target_base in (t.get("url") or "")
                and "verify" not in (t.get("url") or "").lower()
                for t in _cdp_list_page_tabs(port)
            )
            chrome_exe = None if has_clean_hub else find_chrome_executable()
            if chrome_exe:
                logger.info(
                    f"Đang mở trang voucher tự nhiên trên Chrome trước khi kết nối CDP: [cyan]{target_base}[/cyan]..."
                )
                subprocess.Popen(
                    [chrome_exe, f"--user-data-dir={self.user_data_dir}", target_base]
                )
                time.sleep(4.5)

        endpoint = self._normalize_cdp_url(self.cdp)
        logger.info(f"Connecting to Google Chrome via CDP at [bold cyan]{endpoint}[/bold cyan]...")
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                endpoint, timeout=5000
            )
        except Exception as e:
            if port != 9222:
                await self.close()
                raise ConnectionError(f"CDP connection failed: {e}")
            logger.warning(
                f"CDP connection could not attach ({e}). Falling back to direct Chrome persistent launch..."
            )
            return await self._launch_persistent_chrome()

        self._is_cdp = True
        logger.info("[bold green]✓ Successfully connected to Google Chrome via CDP![/bold green]")

        self._context = (
            self._browser.contexts[0]
            if self._browser.contexts
            else await self._browser.new_context()
        )

        target_page = self._pick_existing_tab()
        if target_page:
            self._page = target_page
            if not self._is_blocked_tab(target_page.url or ""):
                logger.info(f"Reusing existing tab: {target_page.url}")
            try:
                await self._page.bring_to_front()
            except Exception:
                pass
        else:
            try:
                self._page = await self._context.new_page()
            except Exception:
                # Fallback via passive CDP HTTP /json/new
                _cdp_http(port, f"/json/new?{urllib.parse.quote(target_base)}")
                await asyncio.sleep(1.0)
                if not self._context.pages:
                    raise RuntimeError("Cannot open or find any tab in Google Chrome.")
                self._page = self._context.pages[-1]

        # Drop stale verification tabs, but never leave Chrome without a window.
        pages = self._context.pages
        if len(pages) > 1:
            for p in pages:
                if p != self._page and self._is_blocked_tab(p.url or ""):
                    try:
                        await p.close()
                    except Exception:
                        pass

        # Note: Do NOT inject STEALTH_JS when using real Google Chrome (--disable-blink-features=AutomationControlled),
        # because real Chrome already has authentic native PluginArray, WebGL, and chrome.runtime objects.
        # Overriding them with JS mocks breaks Function.prototype.toString() native checks in Shopee's dfp-exp.
        return self._page

    async def restore_session_cookies_if_needed(self) -> bool:
        """
        Attempts to restore saved Shopee cookies from disk (default.json / shopee_session.json)
        into the active browser context if the browser does not currently hold an active session.
        """
        if not self._context or not self._page or _is_mock(self._page):
            return False

        # Secondary file kept for backward compatibility with v1.0 sessions.
        candidate_files = [
            settings.get_session_path(),
            settings.sessions_dir / "shopee_session.json",
        ]
        for s_file in candidate_files:
            if s_file.exists() and s_file.stat().st_size > 0:
                try:
                    with open(s_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cookies = data.get("cookies", [])
                    has_spc_u = any(
                        c.get("name") == "SPC_U" and c.get("value") not in (None, "", "-")
                        for c in cookies
                    )
                    if cookies and has_spc_u:
                        logger.info(
                            f"Đang tự động khôi phục phiên đăng nhập đã lưu từ: [cyan]{s_file.name}[/cyan]..."
                        )
                        await self._context.add_cookies(cookies)
                        try:
                            await self._page.reload(wait_until="domcontentloaded", timeout=20000)
                            await asyncio.sleep(1.0)
                        except Exception:
                            pass
                        return True
                except Exception as e:
                    logger.debug(f"Could not restore cookies from {s_file}: {e}")
        return False

    async def save_session_state(self) -> None:
        """Saves current cookies and storage state to project session files for reuse."""
        if not self._context or _is_mock(self._context):
            return
        try:
            session_path = settings.get_session_path()
            session_path.parent.mkdir(parents=True, exist_ok=True)
            await self._context.storage_state(path=str(session_path))

            # Also copy to shopee_session.json for backward compatibility
            alt_path = session_path.parent / "shopee_session.json"
            await self._context.storage_state(path=str(alt_path))
            logger.info(f"[bold green]✓ Đã tự động lưu phiên đăng nhập vào: {session_path}[/bold green]")
        except Exception as e:
            logger.debug(f"Không thể lưu session state: {e}")

    async def check_and_handle_verification(self) -> bool:
        """
        Checks if the page was blocked by a Shopee anti-bot / verification challenge
        ('verify/captcha', 'verify/traffic', ...). If so it clicks 'Try Again' when
        available, then waits up to 180s for the user to solve it in the Chrome window.

        Returns True when the challenge is gone, False on timeout. The caller decides
        whether to retry the page load; recovery navigation is not attempted here.
        """
        if not self._page:
            return False

        current_url = (self._page.url or "").lower()
        is_verify_url = (
            "verify/captcha" in current_url
            or "verify/traffic" in current_url
            or "/verify" in current_url
            or "anti_bot" in current_url
        )

        if not is_verify_url:
            return False

        logger.warning(
            "[bold yellow]⚠️ Phát hiện màn hình xác thực Shopee (/verify/captcha). Đang tự động xử lý và phục hồi phiên...[/bold yellow]"
        )

        # 1. Try clicking 'Try Again' / 'Thử lại' button
        try:
            btn = await self._page.query_selector(
                "button:has-text('Try Again'), button:has-text('Thử lại'), .shopee-button"
            )
            if btn and await btn.is_visible():
                logger.info("Đang bấm nút 'Try Again' / 'Thử lại' trên màn hình xác thực...")
                await btn.click()
                await asyncio.sleep(2.0)
                if "verify" not in (self._page.url or "").lower():
                    logger.info("[bold green]✓ Phục hồi sau xác thực thành công![/bold green]")
                    return True
        except Exception as e:
            logger.debug(f"Could not click Try Again: {e}")

        # If running in mock/test environment, complete immediately
        if _is_mock(self._page):
            return True

        # 2. Interactive Manual Verification Pause:
        # Prompt the user clearly to solve captcha/verification on Chrome window
        console.print("\n" + "=" * 70)
        console.print("[bold red]⚠️ PHÁT HIỆN MÀN HÌNH XÁC THỰC SHOPEE (CAPTCHA / TRƯỢT MÃ / OTP)![/bold red]")
        console.print("[bold yellow]👉 Vui lòng chuyển sang cửa sổ Google Chrome và kéo thanh trượt / giải mã xác minh.[/bold yellow]")
        console.print("[bold cyan]⏳ Tool đang tạm dừng chờ bạn (tối đa 180s, tự động nhận diện ngay khi bạn hoàn tất)...[/bold cyan]")
        console.print("=" * 70 + "\n")

        # Bring window to front so the user notices the challenge immediately
        try:
            await self._page.bring_to_front()
        except Exception:
            pass

        start_time = time.time()
        last_logged = 0
        wait_timeout = 180
        while time.time() - start_time < wait_timeout:
            await asyncio.sleep(1.0)
            elapsed = int(time.time() - start_time)
            if elapsed - last_logged >= 15:
                last_logged = elapsed
                console.print(f"[yellow]⏳ Đang chờ bạn giải xác minh trên Chrome... ({elapsed}s/{wait_timeout}s)[/yellow]")

            try:
                curr_url = (self._page.url or "").lower()
                if "verify" not in curr_url and "anti_bot" not in curr_url:
                    console.print("\n[bold green]=======================================================[/bold green]")
                    console.print("[bold green]✓ BẠN ĐÃ XÁC MINH THÀNH CÔNG TRÊN GOOGLE CHROME![/bold green]")
                    console.print("[bold green]✓ Đang lưu phiên đăng nhập sạch để không bao giờ bị hỏi lại...[/bold green]")
                    console.print("[bold green]=======================================================\n[/bold green]")
                    await self.save_session_state()
                    await asyncio.sleep(2.0)
                    return True
            except Exception:
                pass

        logger.warning(
            f"[bold red]✗ Đã quá thời gian chờ ({wait_timeout}s). Vui lòng thử lại sau.[/bold red]"
        )
        return False

    async def _native_reload_hub(self, hub_url: Optional[str] = None, load_wait: float = 4.5) -> None:
        """
        Reloads the voucher hub WITHOUT a CDP debugger attached during page load:
        1. Disconnects Playwright (the user's Chrome and tabs stay open).
        2. Asks Chrome itself to open a fresh hub tab, then closes stale hub/verify tabs.
        3. Waits for Shopee's page-load anti-bot handshake to finish natively.
        4. Re-attaches over CDP and waits for voucher cards to hydrate.
        """
        hub = (hub_url or self.url).rstrip("/")
        port = self._cdp_port()

        await self.close()

        chrome_exe = find_chrome_executable()
        if not (chrome_exe and is_cdp_port_active(port)):
            # No native reload possible (standalone/headless): just re-attach.
            self._page = await self.connect()
            await self._wait_for_voucher_dom_ready()
            return

        old_tab_ids = [
            t.get("id")
            for t in _cdp_list_page_tabs(port)
            if settings.base_url.split("//")[-1] in (t.get("url") or "")
            and (hub in (t.get("url") or "") or "verify" in (t.get("url") or "").lower())
        ]

        subprocess.Popen([chrome_exe, f"--user-data-dir={self.user_data_dir}", hub])
        await asyncio.sleep(1.0)
        # Close stale tabs only after the new one exists so Chrome never runs out of windows
        for tab_id in old_tab_ids:
            _cdp_http(port, f"/json/close/{tab_id}")
        await asyncio.sleep(max(0.5, load_wait - 1.0))

        self._page = await self.connect()
        await self._wait_for_voucher_dom_ready()

    async def _is_shopee_logged_in(self) -> bool:
        """True when the page holds an authenticated Shopee session."""
        if not self._page:
            return False
        try:
            cookies = await self._page.context.cookies([f"{settings.base_url}/"])
        except Exception:
            cookies = []
        if any(
            c.get("name") == "SPC_U" and c.get("value") not in (None, "", "-")
            for c in cookies
        ):
            return True
        try:
            user_el = await self._page.query_selector(
                ".navbar__username, [class*='navbar__username'], [class*='shopee-avatar']"
            )
            return bool(user_el and await user_el.is_visible())
        except Exception:
            return False

    async def ensure_logged_in(self, timeout_sec: int = 120) -> bool:
        """
        Verifies if the user is logged into Shopee.
        If not, prompts the user to log in on the open Chrome window and waits.
        """
        if not self._page or timeout_sec <= 0 or self.headless or _is_mock(self._page):
            return True

        # Check and handle verification screen if currently blocking view
        await self.check_and_handle_verification()

        logger.info("Đang kiểm tra trạng thái đăng nhập Shopee...")
        if await self._is_shopee_logged_in():
            logger.info("[bold green]✓ Đã nhận diện tài khoản Shopee đã đăng nhập sẵn sàng![/bold green]")
            await self.save_session_state()
            return True

        # Attempt to auto-restore saved cookies from disk before prompting user
        if await self.restore_session_cookies_if_needed() and await self._is_shopee_logged_in():
            logger.info("[bold green]✓ Đã khôi phục phiên đăng nhập tự động thành công![/bold green]")
            return True

        # If not logged in, prompt user clearly
        console.print(
            "\n[bold yellow]════════════════════════════════════════════════════════════════════════════════════════[/bold yellow]\n"
            "[bold red][CHÚ Ý] TÀI KHOẢN SHOPEE CHƯA ĐĂNG NHẬP TRÊN CỬA SỔ GOOGLE CHROME[/bold red]\n"
            "Vui lòng thao tác trên cửa sổ Chrome vừa mở:\n"
            "  1. Quét mã QR bằng App Shopee trên điện thoại (Cách nhanh nhất)\n"
            "  2. Hoặc đăng nhập bằng Số điện thoại & Mật khẩu\n\n"
            "[bold cyan]Tool đang tự động chờ bạn đăng nhập xong...[/bold cyan]\n"
            "(Lưu ý: Chỉ cần đăng nhập 1 lần, các lần chạy sau tool sẽ tự nhớ vĩnh viễn!)\n"
            "[bold yellow]════════════════════════════════════════════════════════════════════════════════════════[/bold yellow]\n"
        )

        start_wait = time.time()
        while time.time() - start_wait < timeout_sec:
            await asyncio.sleep(2.0)
            if await self._is_shopee_logged_in():
                console.print("[bold green]✓ Đăng nhập thành công! Bắt đầu săn voucher...[/bold green]\n")
                await self.save_session_state()
                return True

        logger.warning("Đã hết thời gian chờ đăng nhập. Tiếp tục quét mã ở chế độ hiện tại...")
        return False

    async def navigate_to_hub(self, hub_url: str) -> None:
        """Navigates to the voucher hub URL if not already there."""
        if not self._page:
            raise RuntimeError("Browser not connected.")

        await self.check_and_handle_verification()

        current_url = self._page.url or ""
        base_current = current_url.split("?")[0].rstrip("/")
        # If already on the same hub and not on a verification screen, ensure DOM is hydrated
        if "verify" not in current_url.lower() and hub_url.rstrip("/") in base_current:
            logger.info(f"Already on target voucher hub: {hub_url}")
            if not _is_mock(self._page):
                await self._wait_for_voucher_dom_ready()
            return

        logger.info(f"Navigating to voucher hub: [bold cyan]{hub_url}[/bold cyan]...")
        await self._page.goto(
            hub_url,
            referer=f"{settings.base_url}/",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        # Wait for React voucher cards hydration
        if _is_mock(self._page):
            await asyncio.sleep(0.1)
        else:
            await self._wait_for_voucher_dom_ready()
        await self.check_and_handle_verification()

    async def _wait_for_voucher_dom_ready(self, max_wait: float = 6.0) -> None:
        """Waits up to max_wait seconds for Shopee React voucher components to render in DOM."""
        if not self._page or _is_mock(self._page):
            return
        start = time.time()
        while time.time() - start < max_wait:
            try:
                ready = await self._page.evaluate("""() => {
                    const txt = (document.body ? document.body.innerText : '').toLowerCase();
                    return (
                        txt.includes('lưu') ||
                        txt.includes('claim') ||
                        txt.includes('voucher') ||
                        txt.includes('mã giảm giá') ||
                        txt.includes('fully redeemed') ||
                        txt.includes('hết lượt')
                    ) && txt.length > 400;
                }""")
                if ready:
                    await asyncio.sleep(0.6)
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)

    async def claim_visible_vouchers(self) -> Dict[str, Any]:
        """
        Executes parallel JavaScript DOM evaluation to instantly claim all visible vouchers.
        Returns count and metadata of claimed vouchers.
        """
        if not self._page:
            return {"claimed_count": 0, "vouchers": []}

        start_t = time.perf_counter()
        try:
            res = await self._page.evaluate(JS_CLAIM_VOUCHERS)
            elapsed_ms = (time.perf_counter() - start_t) * 1000
            res["elapsed_ms"] = round(elapsed_ms, 2)
            return res
        except Exception as e:
            logger.debug(f"Error evaluating claim script: {e}")
            return {"claimed_count": 0, "vouchers": [], "error": str(e)}

    async def _burst_claim(
        self, duration: float, label: str = "BURST", cap: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Claims in a tight loop for `duration` seconds — the shared flash-drop burst.
        `cap` stops early once that many vouchers were claimed (None = no cap).
        """
        end = time.time() + duration
        res: Dict[str, Any] = {
            "claimed_count": 0,
            "vip_count": 0,
            "vouchers": [],
            "passes": 0,
        }
        while time.time() < end and (cap is None or res["claimed_count"] < cap):
            res["passes"] += 1
            for v in (await self.claim_visible_vouchers()).get("vouchers", []):
                if cap is not None and res["claimed_count"] >= cap:
                    break
                res["vouchers"].append(v)
                res["claimed_count"] += 1
                if v.get("is_vip"):
                    res["vip_count"] += 1
                tag = "🔥 [VOUCHER KHỦNG]" if v.get("is_vip") else "⚡"
                logger.info(
                    f"[bold green]{tag} [{label} #{res['passes']}] {v.get('info', '')}[/bold green]"
                )
            # Micro-delay between burst scans (25ms)
            await asyncio.sleep(0.025)
        return res

    @staticmethod
    def is_big_sale_day(dt: Optional[datetime] = None) -> bool:
        """
        Checks if the date is a Shopee Mega Sale day:
        - Double Day (1/1, 2/2, ..., 11/11, 12/12)
        - Mid-Month Sale (15th)
        - Payday Sale (25th)
        - Or Eve of Double Day (e.g. 10/11 at night)
        """
        d = dt or datetime.now()
        tomorrow = d + timedelta(days=1)
        return (
            d.day == d.month
            or d.day in (15, 25)
            or (tomorrow.day == tomorrow.month and d.hour >= 20)
        )

    def get_next_golden_drop(
        self, now: Optional[datetime] = None, major_only: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically determines the next Golden Hour or Peak Voucher Drop window
        without requiring the user to specify a time manually.
        Returns metadata with target_dt, time_str, label, is_major, and seconds_until.
        """
        curr = now or datetime.now()
        big_sale = self.is_big_sale_day(curr)

        if major_only:
            slots = sorted(self.GOLDEN_HOURS_MAJOR.keys())
        elif big_sale:
            # On Mega Sale days, add half-hour restock slots (still sparse enough to avoid anti-bot)
            slots_set = set(self.PEAK_DROP_SLOTS)
            for h in range(24):
                slots_set.add((h, 0))
                slots_set.add((h, 30))
            slots = sorted(slots_set)
        else:
            slots = sorted(set(self.PEAK_DROP_SLOTS))

        candidates: List[datetime] = []
        for day_offset in (0, 1):
            base_day = curr + timedelta(days=day_offset)
            for h, m in slots:
                cand = base_day.replace(hour=h, minute=m, second=0, microsecond=0)
                if cand > curr + timedelta(seconds=2):
                    candidates.append(cand)

        target_dt = min(candidates)
        hm = (target_dt.hour, target_dt.minute)
        is_major = hm in self.GOLDEN_HOURS_MAJOR
        if is_major:
            label = self.GOLDEN_HOURS_MAJOR[hm]
        elif hm[1] == 0:
            label = f"⚡ Khung Giờ Cao Điểm ({target_dt.hour:02d}:00 - Tung Thêm Lượt Mã)"
        else:
            label = f"⚡ Đợt Hồi Lượt Flash Voucher ({target_dt.hour:02d}:{target_dt.minute:02d})"

        if big_sale and not is_major:
            label = f"🎉 [NGÀY SIÊU SALE] {label}"

        return {
            "target_dt": target_dt,
            "time_str": target_dt.strftime("%H:%M:%S"),
            "label": label,
            "is_major": is_major,
            "is_big_sale": big_sale,
            "seconds_until": max(0.0, (target_dt - curr).total_seconds()),
        }

    async def _run_full_page_sweep(
        self,
        scroll_rounds: int = 6,
        scroll_delay: float = 0.7,
        reset_clicked: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes a full top-to-bottom multi-scroll sweep on the active voucher page,
        claiming all available vouchers and prioritizing 'Voucher Khủng'.
        """
        page = self._page
        if not page:
            return {"claimed_count": 0, "vip_count": 0, "vouchers": []}

        if reset_clicked and not _is_mock(page):
            try:
                await page.evaluate(JS_RESET_CLICKED_VOUCHERS)
                await page.evaluate(JS_SCROLL_TO_TOP)
                await asyncio.sleep(0.3)
            except Exception:
                pass

        sweep_claimed = 0
        vip_claimed = 0
        sweep_items: List[Dict[str, Any]] = []

        def _absorb(res: Dict[str, Any], label: str) -> None:
            """Records claimed vouchers up to max_claims and logs each one."""
            nonlocal sweep_claimed, vip_claimed
            for v in res.get("vouchers", []):
                if sweep_claimed >= self.max_claims:
                    break
                sweep_items.append(v)
                sweep_claimed += 1
                is_vip = v.get("is_vip", False)
                if is_vip:
                    vip_claimed += 1
                tag = "🔥 [VOUCHER KHỦNG]" if is_vip else "✓"
                logger.info(
                    f"[bold green]{tag} {label} Claimed voucher "
                    f"({res.get('elapsed_ms', 0)}ms): {v['info']}[/bold green]"
                )

        # Round 0: immediate instant claim
        _absorb(await self.claim_visible_vouchers(), "")

        # Fast scroll passes
        for s_round in range(1, scroll_rounds + 1):
            if sweep_claimed >= self.max_claims:
                break
            await page.evaluate(JS_FAST_SCROLL, 900)
            await asyncio.sleep(scroll_delay)
            _absorb(await self.claim_visible_vouchers(), f"[Scroll {s_round}]")

        # Final sweep at bottom only if quota remains
        if sweep_claimed < self.max_claims:
            _absorb(await self.claim_visible_vouchers(), "[Final pass]")

        return {
            "claimed_count": sweep_claimed,
            "vip_count": vip_claimed,
            "vouchers": sweep_items,
        }

    def resolve_hubs(self) -> List[str]:
        """
        Returns the list of voucher hubs to scan.

        In all-hubs mode the platform voucher hub and (for the 'vn' region, the only
        one with a known free-shipping slug) the free-shipping hub are scanned, plus
        any user-supplied --url, which is prepended rather than dropped.
        """
        if not self.all_hubs:
            return [self.url]

        hubs = [settings.vouchers_url]
        if settings.region == "vn":
            hubs.append(f"{settings.base_url}/m/mien-phi-van-chuyen")
        if self.url not in hubs:
            hubs.insert(0, self.url)
        return hubs

    async def hunt_vouchers(
        self,
        scroll_rounds: int = 10,
        scroll_delay: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Performs high-speed voucher hunting:
        1. Navigates to voucher hub(s).
        2. Ensures user is logged in.
        3. Claims all visible vouchers immediately (prioritizing Voucher Khủng).
        4. Fast scrolls through the page to render and claim newly loaded vouchers.
        """
        start_time = time.time()
        self._page = await self.connect()

        hubs = self.resolve_hubs()
        total_claimed = 0
        claimed_items: List[Dict[str, Any]] = []

        try:
            for idx, hub in enumerate(hubs):
                if total_claimed >= self.max_claims:
                    break

                if idx > 0:
                    # Polite pause between hub scans to prevent anti-bot rate limits
                    await asyncio.sleep(1.5)

                logger.info(f"[bold cyan]>>> Scanning Voucher Hub: {hub}[/bold cyan]")
                await self.navigate_to_hub(hub)

                # Ensure user login status
                await self.ensure_logged_in(timeout_sec=90)

                # Check login status (self._page may have been re-attached during verification recovery)
                try:
                    is_login_page = "buyer/login" in (self._page.url or "")
                    if is_login_page:
                        logger.warning("[bold yellow]Cảnh báo: Tab hiện tại đang ở trang đăng nhập. Vui lòng đăng nhập tài khoản Shopee trên Chrome![/bold yellow]")
                except Exception:
                    pass

                sweep_res = await self._run_full_page_sweep(
                    scroll_rounds=scroll_rounds,
                    scroll_delay=scroll_delay,
                    reset_clicked=False,
                )
                for v in sweep_res.get("vouchers", []):
                    if total_claimed >= self.max_claims:
                        break
                    claimed_items.append(v)
                    total_claimed += 1

            duration = round(time.time() - start_time, 2)
            msg = f"Đã hoàn thành quét voucher! Tổng cộng đã lưu thành công {total_claimed} mã trong {duration}s."
            logger.info(f"[bold green]=== {msg} ===[/bold green]")

            return {
                "success": True,
                "claimed_count": total_claimed,
                "vouchers": claimed_items,
                "duration_seconds": duration,
                "message": msg,
            }

        finally:
            await self.close()

    async def sniper_hunt(
        self,
        target_time_str: Optional[str] = None,
        refresh_interval: float = 0.5,
        burst_duration: float = 6.0,
    ) -> Dict[str, Any]:
        """
        Fast sniper mode for newly released flash vouchers:
        - If target_time_str == 'auto', automatically selects the next Golden Hour / Peak Drop.
        - If target_time_str (e.g. '12:00:00') is given, counts down to target time with millisecond precision,
          then fires burst claiming right at T=0.
        - If no target_time_str, runs continuous auto-refresh polling every refresh_interval seconds.
        """
        self._page = await self.connect()
        page = self._page
        await self.navigate_to_hub(self.url)
        await self.ensure_logged_in(timeout_sec=90)

        total_claimed = 0
        claimed_items: List[Dict[str, Any]] = []

        try:
            if target_time_str:
                if target_time_str.strip().lower() == "auto":
                    drop_info = self.get_next_golden_drop()
                    target_dt = drop_info["target_dt"]
                    display_time = f"{drop_info['time_str']} ({drop_info['label']})"
                else:
                    target_dt = self._parse_target_time(target_time_str)
                    display_time = target_time_str

                logger.info(f"[bold yellow]Sniper Target Time set to: {target_dt.strftime('%Y-%m-%d %H:%M:%S')} - {display_time}[/bold yellow]")

                # Pre-reload at ~T-18s so freshly released vouchers are already in the DOM
                await self._wait_until_preload(target_dt)

                if not _is_mock(page):
                    logger.info("Đang làm mới trang trước giờ G để nạp danh sách Flash Voucher mới nhất...")
                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=15000)
                        await self._wait_for_voucher_dom_ready(max_wait=5.0)
                        await page.evaluate(JS_RESET_CLICKED_VOUCHERS)
                    except Exception:
                        pass

                await self._countdown_to(target_dt)
                console.print("\n[bold green]>>> TARGET TIME REACHED! ĐANG GIẬT VOUCHER SIÊU TỐC <<<[/bold green]")

                # Burst phase: Claim rapidly for burst_duration seconds
                burst = await self._burst_claim(
                    burst_duration, "BURST", cap=self.max_claims - total_claimed
                )
                claimed_items.extend(burst["vouchers"])
                total_claimed += burst["claimed_count"]

                msg = f"Sniper kết thúc! Đã giật thành công {total_claimed} voucher trong đợt flash drop ({burst['passes']} lượt quét)."
                logger.info(f"[bold green]{msg}[/bold green]")
                return {
                    "success": True,
                    "claimed_count": total_claimed,
                    "vouchers": claimed_items,
                    "burst_passes": burst["passes"],
                    "message": msg,
                }

            else:
                # Auto-refresh loop mode
                logger.info(f"[bold cyan]Auto-Refresh Sniper Mode đang chạy (chu kỳ {refresh_interval}s). Nhấn Ctrl+C để dừng.[/bold cyan]")
                loop_count = 0
                while total_claimed < self.max_claims:
                    loop_count += 1
                    res = await self.claim_visible_vouchers()
                    for v in res.get("vouchers", []):
                        if total_claimed >= self.max_claims:
                            break
                        claimed_items.append(v)
                        total_claimed += 1
                        logger.info(f"[bold green]⚡ [Loop #{loop_count}] Lưu thành công: {v['info']}[/bold green]")

                    await asyncio.sleep(refresh_interval)
                    # Quick reload if no vouchers found
                    if not res.get("claimed_count") and loop_count % 5 == 0:
                        logger.info("Đang tải lại trang để cập nhật voucher mới...")
                        try:
                            await page.reload(wait_until="domcontentloaded", timeout=15000)
                            await self.check_and_handle_verification()
                        except Exception as reload_err:
                            logger.warning(f"Reload trang gặp lỗi (tiếp tục quét): {reload_err}")

                msg = f"Đã hoàn thành! Tổng cộng lưu được {total_claimed} voucher."
                return {
                    "success": True,
                    "claimed_count": total_claimed,
                    "vouchers": claimed_items,
                    "message": msg,
                }

        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Sniper mode đã được người dùng dừng lại.")
            return {
                "success": True,
                "claimed_count": total_claimed,
                "vouchers": claimed_items,
                "message": f"Dừng sniper bởi người dùng. Đã lưu {total_claimed} voucher.",
            }
        finally:
            await self.close()

    async def _countdown_to(self, target_dt: datetime) -> None:
        """
        Sleeps until `target_dt`, waking progressively earlier so the burst can fire
        on time. Brings the tab to the front once at the start of the last second so
        the CDP websocket is not clogged by a background tab at T=0.
        """
        brought_to_front = False
        while True:
            diff = (target_dt - datetime.now()).total_seconds()
            if diff <= 0:
                return
            if diff > 1.2:
                await asyncio.sleep(min(0.5, diff - 1.0))
            else:
                if not brought_to_front:
                    brought_to_front = True
                    if self._page:
                        try:
                            await self._page.bring_to_front()
                        except Exception:
                            pass
                await asyncio.sleep(0.02 if diff > 0.05 else 0.001)

    async def _wait_until_preload(self, target_dt: datetime) -> None:
        """Blocks until T-20s, showing a live countdown to the target time."""
        while True:
            diff = (target_dt - datetime.now()).total_seconds()
            if diff <= 20.0:
                return
            if diff > 25.0:
                console.print(
                    f"[cyan]Đang đếm ngược đến {target_dt.strftime('%H:%M:%S')}: còn {diff:.1f}s...[/cyan]",
                    end="\r",
                )
            await asyncio.sleep(min(1.0, diff - 20.0))

    async def _attached_sweep(self, scroll_rounds: int, label: str) -> Optional[Dict[str, Any]]:
        """
        Native-reloads the hub, attaches, sweeps all vouchers, then detaches.
        Returns None if Shopee is showing a verification page (caller should back off).
        """
        await self._native_reload_hub(self.url)
        if "verify" in (self._page.url or "").lower():
            await self.close()
            return None
        res = await self._run_full_page_sweep(
            scroll_rounds=scroll_rounds, scroll_delay=0.7, reset_clicked=True
        )
        if res["claimed_count"] > 0:
            logger.info(
                f"[bold green]🎉 [{label}] Lưu được {res['claimed_count']} mã "
                f"({res['vip_count']} 🔥 Voucher Khủng).[/bold green]"
            )
        else:
            logger.info(f"[{label}] Không có mã mới (các mã hiện có đã được lưu trước đó).")
        await self.save_session_state()
        await self.close()
        return res

    async def auto_247_hunt(
        self,
        patrol_interval: float = 900.0,
        scroll_rounds: int = 5,
        burst_duration: float = 8.0,
        max_cycles: Optional[int] = None,
        verify_backoff: float = 300.0,
    ) -> Dict[str, Any]:
        """
        24/7 Auto-Pilot: automatically hunts every Golden Hour without manual time input.

        Anti-bot design (learned from v1.0): Shopee flags pages that are loaded while a CDP
        debugger is attached. So between drops the tool stays fully DETACHED from Chrome, and
        every refresh is done natively by Chrome before re-attaching:
          1. Startup: full sweep of currently available vouchers.
          2. Idle: detached. Optional light patrol every `patrol_interval` seconds (default 15 min).
          3. T-25s: Chrome reloads the hub natively, tool attaches and arms the sniper.
          4. T=0: millisecond burst for `burst_duration` seconds (prioritizes Voucher Khủng).
          5. T+burst: native reload + full sweep to grab vouchers unlocked by the drop, then detach.
          6. Any error -> detach, wait, continue (self-healing). Verification page -> back off.
        """
        total_claimed = 0
        vip_claimed = 0
        claimed_items: List[Dict[str, Any]] = []
        cycle_count = 0

        def _record(res: Optional[Dict[str, Any]]) -> None:
            nonlocal total_claimed, vip_claimed
            if not res:
                return
            total_claimed += res.get("claimed_count", 0)
            vip_claimed += res.get("vip_count", 0)
            claimed_items.extend(res.get("vouchers", []))

        console.print(
            "\n[bold yellow]══════════════════════════════════════════════════════════════════[/bold yellow]\n"
            "[bold cyan]  🔥 AUTO-PILOT 24/7: TỰ ĐỘNG SĂN VOUCHER MỌI KHUNG GIỜ VÀNG[/bold cyan]\n"
            "[bold yellow]══════════════════════════════════════════════════════════════════[/bold yellow]\n"
            "  • Quét toàn bộ mã hiện có ngay khi khởi động\n"
            "  • Tự canh Giờ Vàng 00h, 09h, 12h, 15h, 18h, 20h, 21h, 22h + mỗi giờ tròn\n"
            "  • Chờ ở chế độ tách kết nối để không bị Shopee nhận diện bot\n"
            "  • [dim]Nhấn Ctrl+C để dừng. Vẫn có thể dùng Chrome bình thường trong lúc chờ.[/dim]\n"
        )

        try:
            # Step 1: Startup sweep (same proven flow as v1.0 fast mode)
            self._page = await self.connect()
            await self.navigate_to_hub(self.url)
            await self.ensure_logged_in(timeout_sec=90)
            logger.info("[bold cyan]🚀 [KHỞI ĐỘNG] Đang quét toàn bộ Kho Voucher...[/bold cyan]")
            init_res = await self._run_full_page_sweep(
                scroll_rounds=scroll_rounds, scroll_delay=0.7, reset_clicked=False
            )
            _record(init_res)
            logger.info(
                f"[bold green]✓ Quét khởi động xong: {init_res['claimed_count']} mã "
                f"({init_res['vip_count']} 🔥 Voucher Khủng).[/bold green]"
            )
            await self.save_session_state()
            await self.close()

            # Step 2: Continuous loop over golden hours
            while max_cycles is None or cycle_count < max_cycles:
                cycle_count += 1
                drop = self.get_next_golden_drop()
                target_dt: datetime = drop["target_dt"]
                hhmm = target_dt.strftime("%H:%M:%S")
                logger.info(
                    f"[bold magenta]🎯 [CA #{cycle_count}] Mốc tiếp theo: {hhmm} — {drop['label']} | "
                    f"Tổng đã săn: {total_claimed} mã ({vip_claimed} 🔥)[/bold magenta]"
                )

                try:
                    # --- Idle phase (detached), with sparse optional patrol ---
                    last_patrol = time.time()
                    while True:
                        diff = (target_dt - datetime.now()).total_seconds()
                        if diff <= 25.0:
                            break
                        if (
                            patrol_interval > 0
                            and time.time() - last_patrol >= patrol_interval
                            and diff > 180.0
                        ):
                            last_patrol = time.time()
                            res = await self._attached_sweep(max(2, scroll_rounds // 2), "TUẦN TRA")
                            if res is None:
                                logger.warning(
                                    f"Shopee đang yêu cầu xác thực — tạm nghỉ {int(verify_backoff)}s "
                                    "(có thể giải captcha thủ công trên Chrome)."
                                )
                                last_patrol = time.time() + verify_backoff
                            _record(res)
                            continue
                        console.print(
                            f"[cyan]⏳ Chờ {hhmm} | còn {int(diff // 60):02d}:{int(diff % 60):02d} | "
                            f"Đã săn: {total_claimed} mã ({vip_claimed} 🔥)[/cyan]   ",
                            end="\r",
                        )
                        await asyncio.sleep(min(5.0, max(0.5, diff - 25.0)))

                    # --- Arm phase: native reload at ~T-25s, then attach ---
                    console.print()
                    logger.info(f"[bold yellow]⚡ Chuẩn bị Giờ Vàng {hhmm}: tải lại Kho Voucher...[/bold yellow]")
                    await self._native_reload_hub(self.url)
                    if "verify" in (self._page.url or "").lower():
                        logger.warning(
                            "[bold yellow]Shopee yêu cầu xác thực trước giờ vàng. Vui lòng giải captcha trên "
                            "Chrome — tool vẫn sẽ thử giật mã khi đến giờ.[/bold yellow]"
                        )
                    try:
                        await self._page.evaluate(JS_RESET_CLICKED_VOUCHERS)
                        await self._page.evaluate(JS_SCROLL_TO_TOP)
                    except Exception:
                        pass

                    # Precise countdown; bring the tab forward at T-1s so the burst is not blocked
                    await self._countdown_to(target_dt)

                    # --- Burst phase ---
                    logger.info(f"[bold green]💥 ĐÚNG {hhmm} — ĐANG GIẬT VOUCHER![/bold green]")
                    active_burst = burst_duration if drop["is_major"] else max(4.0, burst_duration * 0.6)
                    burst_res = await self._burst_claim(active_burst)
                    _record(burst_res)
                    await self.close()

                    # --- Post-drop sweep: native reload picks up vouchers unlocked at T=0 ---
                    await asyncio.sleep(2.0)
                    post_res = await self._attached_sweep(scroll_rounds, f"SAU GIỜ VÀNG {hhmm}")
                    _record(post_res)

                    drop_total = burst_res["claimed_count"] + (post_res or {}).get("claimed_count", 0)
                    logger.info(
                        f"[bold green]✅ Xong mốc {hhmm}: +{drop_total} mã ({burst_res['passes']} lượt burst). "
                        f"Tổng 24/7: {total_claimed} mã ({vip_claimed} 🔥).[/bold green]"
                    )

                except (asyncio.CancelledError, KeyboardInterrupt):
                    raise
                except Exception as cycle_err:
                    # Self-healing: Chrome closed / network glitch / tab crashed -> detach, wait, continue
                    logger.warning(f"Lỗi trong ca #{cycle_count}: {cycle_err}. Tự phục hồi sau 30s...")
                    await self.close()
                    await asyncio.sleep(30.0)

            msg = f"Đã hoàn thành {cycle_count} ca 24/7! Tổng cộng lưu được {total_claimed} mã ({vip_claimed} Voucher Khủng)."

        except (asyncio.CancelledError, KeyboardInterrupt):
            msg = f"Đã dừng chế độ 24/7. Tổng cộng đã săn {total_claimed} mã ({vip_claimed} Voucher Khủng)."
        finally:
            await self.close()

        logger.info(f"[bold green]{msg}[/bold green]")
        return {
            "success": True,
            "claimed_count": total_claimed,
            "vip_count": vip_claimed,
            "vouchers": claimed_items,
            "cycles": cycle_count,
            "message": msg,
        }

    def _parse_target_time(self, time_str: str) -> datetime:
        """Parses target time string (HH:MM:SS, HH:MM, or 'auto') into datetime."""
        if time_str.strip().lower() == "auto":
            return self.get_next_golden_drop()["target_dt"]

        now = datetime.now()
        parts = [int(p) for p in time_str.strip().split(":")]
        if len(parts) == 2:
            hour, minute = parts
            second = 0
        elif len(parts) == 3:
            hour, minute, second = parts
        else:
            raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM:SS or HH:MM.")

        target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        # If target has already passed today by more than 5 seconds, schedule for tomorrow
        if target < now - timedelta(seconds=5):
            target += timedelta(days=1)
        return target

    async def close(self) -> None:
        """
        Gracefully disconnects from Chrome and resets state so close() is idempotent.
        Note: When connected over CDP, closing the browser object disconnects Playwright
        without closing the user's running Chrome instance.
        """
        page, browser, context, playwright = self._page, self._browser, self._context, self._playwright
        self._page = self._browser = self._context = self._playwright = None
        self._is_cdp = False

        try:
            if page and browser is None and not page.is_closed():
                await page.close()
        except Exception:
            pass

        try:
            if browser:
                await browser.close()
        except Exception:
            pass

        try:
            if context and browser is None:
                await context.close()
        except Exception:
            pass

        try:
            if playwright:
                await playwright.stop()
        except Exception:
            pass
