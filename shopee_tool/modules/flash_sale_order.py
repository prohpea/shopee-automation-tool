"""
Flash Sale & 0đ Auto-Order Engine for Shopee.
Handles countdown synchronization, variant selection, fast checkout,
voucher auto-application, and financial safety gates (max price protection).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import re
import time
from typing import Dict, List, Optional, Tuple, Union

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from shopee_tool.core.browser import BrowserManager
from shopee_tool.utils.logger import console, logger


class FlashSaleOrderHunter:
    """Automates Flash Sale sniping and 0đ order placement on Shopee Desktop via Chrome CDP."""

    def __init__(
        self,
        item_url: str,
        target_time_str: Optional[str] = "now",
        variant: Optional[str] = None,
        max_price: int = 0,
        payment_method: str = "COD",
        cdp: Union[str, int] = "9222",
        dry_run: bool = False,
        headless: bool = False,
    ):
        self.item_url = item_url.strip()
        self.target_time_str = target_time_str or "now"
        self.variant = variant.strip() if variant else None
        self.max_price = int(max_price)
        self.payment_method = payment_method.upper()
        self.cdp = cdp
        self.dry_run = dry_run
        self.headless = headless

        self.browser_mgr: Optional[BrowserManager] = None
        self.page: Optional[Page] = None

    async def connect(self) -> Page:
        """Connect to Google Chrome via CDP debugging port or standalone browser."""
        console.print("[cyan]Đang kết nối tới trình duyệt Google Chrome (CDP port 9222)...[/cyan]")
        self.browser_mgr = BrowserManager(headless=self.headless, cdp=self.cdp)
        try:
            self.page = await self.browser_mgr.start()
            console.print("[bold green]✓ Kết nối thành công tới Google Chrome Desktop![/bold green]")
            return self.page
        except Exception as e:
            console.print(f"[bold red]✗ Không thể kết nối tới Google Chrome: {e}[/bold red]")
            console.print("[yellow][!] Vui lòng chạy file 'start_chrome.bat' để mở Chrome và đăng nhập Shopee trước.[/yellow]")
            raise ConnectionError(f"Chrome CDP connection failed: {e}")

    def calculate_countdown(self, target_str: str) -> Tuple[datetime, float]:
        """
        Calculate seconds remaining until target flash drop time.
        Format accepted: 'HH:MM:SS', 'HH:MM', or 'now'.
        """
        if not target_str or target_str.lower() in ("now", "ngay", "0"):
            return datetime.now(), 0.0

        now = datetime.now()
        parts = [int(p) for p in target_str.strip().split(":")]
        while len(parts) < 3:
            parts.append(0)
        # Extra segments (e.g. '12:00:00:00') are a malformed time, not a longer one.
        if len(parts) > 3:
            raise ValueError(f"Invalid time format '{target_str}'. Expected HH:MM:SS or HH:MM.")

        target_dt = now.replace(hour=parts[0], minute=parts[1], second=parts[2], microsecond=0)
        if target_dt <= now:
            target_dt += timedelta(days=1)
        return target_dt, (target_dt - now).total_seconds()

    async def wait_for_drop(self, early_ms: int = 200) -> None:
        """High-precision countdown loop until flash sale drop time."""
        target_dt, secs = self.calculate_countdown(self.target_time_str)
        if secs <= 0:
            console.print("[bold yellow]⚡ Chế độ: SĂN NGAY LẬP TỨC (Không chờ đếm ngược)[/bold yellow]")
            return

        console.print(f"[cyan]Canh giờ săn Flash Sale mục tiêu: [bold white]{target_dt.strftime('%H:%M:%S')}[/bold white][/cyan]")
        console.print(f"[cyan]Thời gian chờ: [bold yellow]{secs:.1f}s[/bold yellow] (Reload trước {early_ms}ms để đón đầu)...[/cyan]")

        while True:
            remaining = (target_dt - datetime.now()).total_seconds()
            if remaining <= (early_ms / 1000.0):
                break
            if remaining > 5.0:
                await asyncio.sleep(1.0)
            elif remaining > 1.0:
                await asyncio.sleep(0.2)
            else:
                await asyncio.sleep(0.01)

        console.print("[bold green]🔥 GIỜ G ĐÃ TỚI! BẮT ĐẦU KÍCH HOẠT TIẾN TRÌNH ĐẶT ĐƠN SIÊU TỐC...[/bold green]")

    async def select_variant_if_any(self) -> None:
        """Select item variant/classification (color, size) if applicable."""
        if not self.page:
            return

        try:
            # Check for Shopee variant button groups
            variant_buttons = await self.page.query_selector_all(
                "button.product-variation, button[aria-label*='variation'], .product-variation"
            )
            if not variant_buttons:
                return

            if self.variant:
                console.print(f"[cyan]Đang tìm chọn phân loại hàng: '{self.variant}'...[/cyan]")
                clicked = False
                for btn in variant_buttons:
                    txt = (await btn.inner_text()).strip()
                    if self.variant.lower() in txt.lower():
                        await btn.click()
                        console.print(f"[green]✓ Đã chọn phân loại: {txt}[/green]")
                        clicked = True
                        break
                if not clicked and variant_buttons:
                    # Fallback to first available variant
                    await variant_buttons[0].click()
                    console.print("[yellow][!] Không thấy tên biến thể chỉ định, tự động chọn phân loại đầu tiên.[/yellow]")
            else:
                # Click first available enabled variant
                for btn in variant_buttons:
                    disabled = await btn.get_attribute("aria-disabled")
                    if disabled != "true":
                        await btn.click()
                        console.print(f"[green]✓ Đã tự động chọn phân loại: {(await btn.inner_text()).strip()}[/green]")
                        break
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.debug(f"Variant selection note: {e}")

    async def _click_first_enabled(
        self, selectors: List[str], attempts: int = 15, pause: float = 0.1
    ) -> bool:
        """Clicks the first visible, enabled button among `selectors`, retrying briefly."""
        if not self.page:
            return False
        for _ in range(attempts):
            for sel in selectors:
                try:
                    btn = await self.page.query_selector(sel)
                    if not btn:
                        continue
                    if await btn.get_attribute("disabled"):
                        continue
                    if await btn.get_attribute("aria-disabled") == "true":
                        continue
                    await btn.click(timeout=1000)
                    return True
                except Exception:
                    pass
            await asyncio.sleep(pause)
        return False

    async def click_buy_now(self) -> bool:
        """Click 'Mua Ngay' (Buy Now) button with fast retries."""
        console.print("[cyan]Đang bấm nút 'Mua Ngay'...[/cyan]")
        start_time = time.time()
        clicked = await self._click_first_enabled(
            [
                "button.btn-solid-primary:has-text('Mua ngay')",
                "button:has-text('Mua Ngay')",
                "button:has-text('Mua ngay')",
                "button.btn-solid-primary:has-text('Mua Với Voucher')",
                "button:has-text('Mua Với Voucher')",
                "button.btn-solid-primary",
            ]
        )
        if clicked:
            console.print(
                f"[bold green]✓ Đã bấm 'Mua Ngay' thành công trong "
                f"{(time.time() - start_time) * 1000:.0f}ms![/bold green]"
            )
        return clicked

    async def navigate_to_checkout(self) -> bool:
        """Ensure page transitions to Shopee Checkout (/checkout)."""
        if not self.page:
            return False

        console.print("[cyan]Đang chuyển hướng tới trang Thanh Toán (Checkout)...[/cyan]")
        for _ in range(25):
            curr_url = self.page.url
            if "/checkout" in curr_url:
                console.print("[bold green]✓ Đã vào trang Thanh Toán Shopee thành công![/bold green]")
                await self.page.wait_for_load_state("domcontentloaded", timeout=4000)
                return True
            if "/cart" in curr_url:
                # If in Cart page, click 'Mua Hàng' (Checkout)
                console.print("[yellow]Đang ở giỏ hàng, bấm nút 'Mua Hàng' để qua Checkout...[/yellow]")
                checkout_btn = await self.page.query_selector("button:has-text('Mua Hàng'), button:has-text('Mua hàng')")
                if checkout_btn:
                    await checkout_btn.click()
            await asyncio.sleep(0.2)

        return "/checkout" in self.page.url

    async def auto_apply_vouchers(self) -> None:
        """Open Shopee Voucher modal and apply best FreeShip + Discount vouchers."""
        if not self.page:
            return

        console.print("[cyan]Đang tối ưu hoá Voucher Shopee (FreeShip & Giảm Giá 0đ)...[/cyan]")
        try:
            # Click voucher selector in checkout
            voucher_btn = await self.page.query_selector(
                "div:has-text('Shopee Voucher') + button, "
                "button:has-text('Chọn hoặc nhập mã'), "
                "div:has-text('Chọn hoặc nhập mã'), "
                ".checkout-voucher-popup"
            )
            if voucher_btn:
                await voucher_btn.click()
                await asyncio.sleep(0.5)

                # Click OK / Apply button in modal
                modal_ok = await self.page.query_selector("button:has-text('Đồng ý'), button:has-text('Áp dụng')")
                if modal_ok:
                    await modal_ok.click()
                    console.print("[green]✓ Đã xác nhận áp dụng Voucher tối ưu![/green]")
                await asyncio.sleep(0.3)
        except Exception as e:
            logger.debug(f"Auto voucher note: {e}")

    async def select_payment_channel(self) -> None:
        """Select preferred payment method (COD or ShopeePay)."""
        if not self.page:
            return

        try:
            if self.payment_method == "COD":
                cod_btn = await self.page.query_selector(
                    "button:has-text('Thanh toán khi nhận hàng'), "
                    "div:has-text('Thanh toán khi nhận hàng'), "
                    "button:has-text('Cash on Delivery')"
                )
                if cod_btn:
                    await cod_btn.click()
                    console.print("[green]✓ Đã chọn phương thức: Thanh toán khi nhận hàng (COD)[/green]")
            elif "SHOPEEPAY" in self.payment_method:
                sp_btn = await self.page.query_selector(
                    "button:has-text('Ví ShopeePay'), div:has-text('Ví ShopeePay')"
                )
                if sp_btn:
                    await sp_btn.click()
                    console.print("[green]✓ Đã chọn phương thức: Ví ShopeePay[/green]")
        except Exception as e:
            logger.debug(f"Payment selection note: {e}")

    async def extract_total_payment(self) -> Optional[int]:
        """
        Extract the total payment amount from the Checkout page in VND.

        Returns None when the amount cannot be read: the caller must treat an
        unknown total as a failed safety check, never as a 0đ order.
        """
        if not self.page:
            return None

        try:
            # Look for total payment text e.g. "₫0", "0₫", "₫1.000", "₫150.000"
            elem = await self.page.query_selector(
                ".checkout-payment-summary__total-amount, "
                "div:has-text('Tổng thanh toán') + div, "
                ".checkout-total-price"
            )
            if elem:
                text = (await elem.inner_text()).strip()
                # Clean digits
                digits = re.sub(r"[^\d]", "", text)
                if digits:
                    return int(digits)

            # Fallback: scan text on whole page for 'Tổng thanh toán'
            content = await self.page.content()
            match = re.search(r"Tổng thanh toán[^\d]*([\d.,]+)\s*₫?", content)
            if match:
                raw_num = match.group(1).replace(".", "").replace(",", "")
                if raw_num.isdigit():
                    return int(raw_num)
        except Exception as e:
            logger.warning(f"Error parsing total payment: {e}")

        return None

    async def place_order_with_safety_check(self) -> Dict[str, Union[bool, str, int]]:
        """
        Verify that total payment <= max_price before clicking Place Order.
        Guarantees zero unintended purchases.
        """
        if not self.page:
            return {"success": False, "message": "Trang không sẵn sàng"}

        total_price = await self.extract_total_payment()

        # 1. FINANCIAL SAFETY GATE (fail closed: an unreadable total is never a 0đ order)
        if total_price is None:
            err_msg = (
                "CHỐT CHẶN AN TOÀN KÍCH HOẠT: không đọc được Tổng thanh toán trên trang Checkout. "
                "Đã DỪNG LẠI NGAY LẬP TỨC thay vì đặt đơn khi chưa xác minh được giá."
            )
            console.print(f"[bold red]✗ {err_msg}[/bold red]")
            return {"success": False, "message": err_msg}

        console.print(f"[bold cyan]>> TỔNG TIỀN THANH TOÁN THỰC TẾ: [bold white]{total_price:,} đ[/bold white] (Ngưỡng tối đa cho phép: {self.max_price:,} đ)[/bold cyan]")

        if total_price > self.max_price:
            err_msg = (
                f"CHỐT CHẶN AN TOÀN KÍCH HOẠT: Giá đơn hàng là {total_price:,} đ, "
                f"vượt quá mức tối đa cài đặt ({self.max_price:,} đ)! "
                f"Đã DỪNG LẠI NGAY LẬP TỨC để bảo vệ tài khoản của bạn."
            )
            console.print(f"[bold red]✗ {err_msg}[/bold red]")
            return {"success": False, "message": err_msg, "total_price": total_price}

        # 2. DRY-RUN CHECK
        if self.dry_run:
            succ_msg = (
                f"[DRY-RUN THÀNH CÔNG] Đơn hàng đạt điều kiện {total_price:,} đ <= {self.max_price:,} đ. "
                f"Chế độ chạy thử không bấm nút 'Đặt hàng'. Bạn có thể kiểm tra màn hình Chrome!"
            )
            console.print(f"[bold green]✓ {succ_msg}[/bold green]")
            return {"success": True, "message": succ_msg, "total_price": total_price}

        # 3. CLICK 'ĐẶT HÀNG' (PLACE ORDER)
        console.print("[bold yellow]⚡ GIÁ HỢP LỆ! ĐANG BẤM NÚT 'ĐẶT HÀNG' SIÊU TỐC...[/bold yellow]")
        placed = await self._click_first_enabled(
            [
                "button:has-text('Đặt hàng')",
                "button:has-text('Đặt Hàng')",
                "button.stardust-button--primary:has-text('Đặt hàng')",
                "button:has-text('Place Order')",
            ],
            attempts=10,
        )
        if not placed:
            return {"success": False, "message": "Không tìm thấy hoặc không click được nút Đặt hàng."}

        console.print("[bold green]🎉 CHÚC MỪNG! ĐÃ BẤM ĐẶT HÀNG THÀNH CÔNG RỰC RỠ![/bold green]")
        await asyncio.sleep(2.0)
        return {
            "success": True,
            "message": f"Đặt đơn 0đ thành công với giá {total_price:,} đ!",
            "total_price": total_price,
        }

    async def execute_hunt(self) -> Dict[str, Union[bool, str, int]]:
        """Main execution loop for Flash Sale 0đ Snipe & Order."""
        await self.connect()

        console.print(f"[cyan]Đang mở trang sản phẩm: [underline]{self.item_url}[/underline][/cyan]")
        await self.page.goto(self.item_url, wait_until="domcontentloaded", timeout=30000)

        # Wait for drop countdown
        await self.wait_for_drop(early_ms=200)

        # Fast reload to grab drop state if target time was in the future
        if self.target_time_str.lower() not in ("now", "ngay", "0"):
            await self.page.reload(wait_until="domcontentloaded")

        # Select variant
        await self.select_variant_if_any()

        # Click Buy Now
        bought = await self.click_buy_now()
        if not bought:
            # Fallback retry reload once
            console.print("[yellow]Chưa thấy nút 'Mua Ngay', reload trang nhanh...[/yellow]")
            await self.page.reload(wait_until="domcontentloaded")
            await self.select_variant_if_any()
            bought = await self.click_buy_now()

        if not bought:
            return {"success": False, "message": "Không thể bấm nút 'Mua Ngay'. Có thể sản phẩm chưa mở bán hoặc hết hàng."}

        # Navigate to checkout
        in_checkout = await self.navigate_to_checkout()
        if not in_checkout:
            return {"success": False, "message": "Không thể chuyển tới trang thanh toán Checkout."}

        # Auto-apply vouchers & payment method
        await self.auto_apply_vouchers()
        await self.select_payment_channel()
        await asyncio.sleep(0.5)

        # Place order with safety gate
        return await self.place_order_with_safety_check()
