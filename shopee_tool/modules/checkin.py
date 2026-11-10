"""
Shopee Automation Tool - Daily Coins Check-In Module.
Automates daily Shopee Coins reward collection, supporting direct Google Chrome CDP or standalone sessions.
"""

import asyncio
from typing import Any, Dict, Optional, Union
from ..core.browser import BrowserManager
from ..core.config import settings
from ..core.human import sleep_random
from ..modules.auth import AuthManager
from ..modules.fast_voucher_hunter import FastVoucherHunter
from ..utils.logger import logger
from ..utils.captcha import CaptchaDetector

# Clicks the single claimable check-in button, or reports the current state.
JS_CHECKIN = """() => {
    const alreadyKeywords = ["đã nhận", "đã điểm danh", "claimed", "checked in", "bạn đã nhận", "quay lại vào ngày mai"];
    const checkinKeywords = ["nhận ngay hôm nay", "nhận xu", "điểm danh nhận xu", "nhận ngay", "check in", "claim"];
    const excludeKeywords = ["xác nhận", "nhận thông báo", "nhận tin", "nhận mã", "nhận voucher", "điều khoản"];

    const allElements = Array.from(document.querySelectorAll("button, [role='button'], div, span"));

    // 1. Check if already claimed
    for (const el of allElements) {
        const txt = (el.innerText || el.textContent || "").replace(/[\\u00A0\\s]+/g, " ").trim().toLowerCase();
        if (txt.length > 0 && txt.length < 45 && alreadyKeywords.some(kw => txt.includes(kw))) {
            return { status: "already_claimed", text: txt };
        }
    }

    // 2. Look for claimable button
    for (const el of allElements) {
        if (el.children.length > 0 && el.tagName !== "BUTTON" && el.getAttribute("role") !== "button") continue;
        if (el.disabled || el.getAttribute("aria-disabled") === "true") continue;
        const style = window.getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") continue;

        const txt = (el.innerText || el.textContent || "").replace(/[\\u00A0\\s]+/g, " ").trim().toLowerCase();
        if (txt.length > 0 && txt.length < 35) {
            if (excludeKeywords.some(ex => txt.includes(ex))) continue;
            const isCheckin = checkinKeywords.some(kw => txt === kw || txt.startsWith(kw + " ")) || /^nhận\\s*\\+?\\d+\\s*xu/.test(txt);
            if (isCheckin) {
                const target = el.closest("button, [role='button'], div[class*='btn'], div[class*='checkin']") || el;
                const opts = { bubbles: true, cancelable: true, view: window };
                if (typeof window.PointerEvent !== "undefined") {
                    target.dispatchEvent(new PointerEvent('pointerdown', opts));
                    target.dispatchEvent(new PointerEvent('pointerup', opts));
                }
                target.dispatchEvent(new MouseEvent('mousedown', opts));
                target.dispatchEvent(new MouseEvent('mouseup', opts));
                target.click();
                return { status: "claimed", text: txt };
            }
        }
    }

    return { status: "not_found" };
}"""


class DailyCheckin:
    """Automates daily check-in to claim Shopee Coins."""

    def __init__(
        self,
        session_name: Optional[str] = None,
        headless: bool = False,
        cdp: Optional[Union[str, int]] = "9222",
    ):
        self.session_name = session_name or settings.default_session_name
        self.headless = headless
        self.cdp = cdp
        self.auth = AuthManager(self.session_name)

    async def execute(self) -> Dict[str, Any]:
        """Executes the daily coins check-in flow."""
        logger.info(
            "[bold cyan]Bắt đầu điểm danh nhận Shopee Xu (Daily Coins Check-In)...[/bold cyan]"
        )
        coins_url = settings.coins_url

        if self.cdp and str(self.cdp).lower() != "none":
            hunter = FastVoucherHunter(cdp=self.cdp, headless=self.headless)
            try:
                page = await hunter.connect()
                logger.info(f"Đang mở trang Shopee Xu: [bold cyan]{coins_url}[/bold cyan]...")
                await page.goto(
                    coins_url,
                    referer=f"{settings.base_url}/",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await asyncio.sleep(1.5)
                await hunter.check_and_handle_verification()
                await hunter.ensure_logged_in(timeout_sec=60)
                return await self._claim(page)
            except Exception as e:
                msg = f"Điểm danh qua Chrome gặp lỗi: {e}"
                logger.error(msg)
                return {"success": False, "already_claimed": False, "message": msg}
            finally:
                await hunter.close()

        mgr = BrowserManager(headless=self.headless, session_name=self.session_name)
        try:
            page = await mgr.start()
            logger.info(f"Navigating to Shopee Coins page: {coins_url}")
            await page.goto(coins_url, wait_until="domcontentloaded")
            await sleep_random(2.0, 3.5)

            if not await self.auth.is_logged_in(page):
                msg = f"User is not logged in! Please run 'login' command for session '{self.session_name}'."
                logger.error(f"[bold red]{msg}[/bold red]")
                return {"success": False, "already_claimed": False, "message": msg}

            detector = CaptchaDetector(page)
            if await detector.is_captcha_present():
                logger.warning("Captcha encountered on coins page.")
                if not await detector.wait_for_manual_solve(timeout_seconds=45):
                    return {
                        "success": False,
                        "already_claimed": False,
                        "message": "Captcha challenge not resolved.",
                    }

            result = await self._claim(page)
            if result["success"]:
                await mgr.save_session()
            return result
        except Exception as e:
            msg = f"Check-in failed with error: {e}"
            logger.error(msg)
            return {"success": False, "already_claimed": False, "message": msg}
        finally:
            await mgr.close()

    @staticmethod
    async def _claim(page) -> Dict[str, Any]:
        """Runs the claim script and maps its status to a result dict."""
        res = await page.evaluate(JS_CHECKIN)
        status = res.get("status")
        text = res.get("text", "")

        if status == "already_claimed":
            message = f"Hôm nay bạn đã điểm danh nhận Xu rồi! ({text})"
            logger.info(f"[bold green]✓ {message}[/bold green]")
            return {"success": True, "already_claimed": True, "message": message}

        if status == "claimed":
            message = f"Điểm danh thành công! Đã bấm nhận Xu ({text})"
            logger.info(f"[bold green]🎉 {message}[/bold green]")
            return {"success": True, "already_claimed": False, "message": message}

        message = (
            "Không tìm thấy nút nhận Xu trên trang. Có thể bạn đã điểm danh trên "
            "điện thoại hôm nay, hoặc giao diện trang Shopee Xu đã thay đổi."
        )
        logger.warning(f"[yellow]{message}[/yellow]")
        return {"success": False, "already_claimed": False, "message": message}
