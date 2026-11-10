"""
Android Voucher Hunter.
Automates Shopee Mobile App on Real Android Phones & Emulators via ADB.
Provides Computer Vision voucher detection, anti-sleep heartbeats, fast multi-claim,
and continuous 24/7 golden-hour hunting.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import time
from typing import List, Optional, Tuple

from shopee_tool.core.adb_device import ADBDeviceManager
from shopee_tool.utils.logger import console, logger


class AndroidVoucherHunter:
    """Automates voucher claiming on Shopee Android App via ADB."""

    # Kept in sync with FastVoucherHunter.GOLDEN_HOURS_MAJOR so the Android and
    # Chrome hunters target the same drop slots. Extra scans cost little; a missed
    # drop costs a voucher.
    GOLDEN_HOURS = [0, 6, 9, 11, 12, 15, 18, 20, 21, 22, 23]
    CLAIM_KEYWORDS = ["Lưu", "Nhận", "Lấy mã", "Claim", "Collect", "Save", "LƯU", "NHẬN"]

    def __init__(
        self,
        device_serial: Optional[str] = None,
        device_manager: Optional[ADBDeviceManager] = None,
    ):
        self.device_serial = device_serial
        self.manager = device_manager or ADBDeviceManager(target_serial=device_serial)

    def connect(self) -> None:
        """Connect to Android phone or emulator ADB and bring Shopee to the foreground."""
        console.print("[cyan]Đang tìm kiếm và kết nối Thiết bị Android qua ADB...[/cyan]")
        dev = self.manager.connect_device(self.device_serial)
        console.print(f"[bold green]✓ Kết nối thành công tới Thiết bị Android: {dev.serial}[/bold green]")
        # Keep screen awake immediately upon connection
        self.manager.keep_awake()
        # Without this the tool scans whatever app happens to be on screen.
        self.launch_shopee()

    def launch_shopee(self) -> None:
        """Ensure Shopee app is running."""
        console.print("[cyan]Khởi động ứng dụng Shopee (com.shopee.vn)...[/cyan]")
        self.manager.launch_app("com.shopee.vn")
        time.sleep(3)

    def calculate_next_golden_hour(
        self, now: Optional[datetime] = None
    ) -> Tuple[datetime, float]:
        """
        Calculate next target golden hour and seconds remaining.
        Matches 0h, 9h, 12h, 15h, 18h, 20h, 21h, 22h.
        """
        curr = now or datetime.now()
        candidates = []

        for h in self.GOLDEN_HOURS:
            dt = curr.replace(hour=h, minute=0, second=0, microsecond=0)
            if dt > curr:
                candidates.append(dt)

        if not candidates:
            # Tomorrow at 00:00
            tomorrow = curr + timedelta(days=1)
            next_dt = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            next_dt = min(candidates)

        secs_left = (next_dt - curr).total_seconds()
        return next_dt, max(0.0, secs_left)

    def scan_and_claim_vouchers(
        self,
        keywords: Optional[List[str]] = None,
        max_scrolls: int = 3,
    ) -> int:
        """
        Scan screen UI for claimable voucher buttons via multi-modal vision + text,
        tap them, and optionally scroll down to reveal more vouchers.
        Returns total number of vouchers tapped.
        """
        kw_list = keywords or self.CLAIM_KEYWORDS
        total_claimed = 0
        claimed_coords = set()

        w, h = 720, 1280
        try:
            res = self.manager.get_screen_size()
            if isinstance(res, (tuple, list)) and len(res) == 2:
                w, h = int(res[0]), int(res[1])
        except Exception:
            pass

        for scroll_idx in range(max_scrolls):
            # Screen coordinates are only comparable within one viewport: after a
            # scroll the same (x, y) holds a different voucher. Keeping the set
            # across rounds made every voucher below the fold be skipped.
            claimed_coords.clear()
            found_this_round = 0
            targets = []
            # 1. Fast Computer Vision detection (Primary - Instant & immune to Shopee animations)
            if hasattr(self.manager, "find_voucher_buttons"):
                try:
                    res_btn = self.manager.find_voucher_buttons(kw_list)
                    if isinstance(res_btn, list) and res_btn:
                        targets = res_btn
                except Exception as e:
                    logger.debug(f"Vision button detection: {e}")

            # 2. Text bounds fallback (only if vision returned nothing, e.g. mock unit tests)
            if not targets and hasattr(self.manager, "find_text_bounds"):
                for kw in ["Lưu", "Nhận"]:
                    try:
                        res_kw = self.manager.find_text_bounds(kw)
                        if isinstance(res_kw, list) and res_kw:
                            targets.extend(res_kw)
                            break
                    except Exception:
                        pass

            # Safeguard: never tap elements at or below 0.84 * h (bottom checkout bar)
            safe_targets = [t for t in targets if t[1] <= int(h * 0.84)]
            for cx, cy in safe_targets:
                try:
                    cx, cy = int(cx), int(cy)
                except (ValueError, TypeError):
                    continue
                coord_key = (cx // 15, cy // 15)  # bucket to avoid clicking same element twice
                if coord_key in claimed_coords:
                    continue

                claimed_coords.add(coord_key)
                try:
                    self.manager.tap(cx, cy)
                    total_claimed += 1
                    found_this_round += 1
                    console.print(f"[green]✓ Đã chạm nút Voucher tại toạ độ ({cx}, {cy})[/green]")
                    time.sleep(0.12)
                except Exception as e:
                    logger.warning(f"Failed to tap ({cx}, {cy}): {e}")

            if scroll_idx < max_scrolls - 1:
                # Swipe up to reveal next page of vouchers
                start_y = int(h * 0.78)
                end_y = int(h * 0.32)
                center_x = w // 2
                self.manager.swipe(center_x, start_y, center_x, end_y, duration_ms=350)
                time.sleep(1.2)

        return total_claimed

    def sniper_tap(
        self,
        x: int,
        y: int,
        count: int = 30,
        interval: float = 0.02,
        use_batch: bool = False,
    ) -> int:
        """Rapid-fire tap at (x, y) to grab hot drop vouchers at exact timing."""
        console.print(f"[bold yellow]⚡ Bắt đầu bắn tỉa tap liên hoàn ({count} lần) tại ({x}, {y})...[/bold yellow]")
        if use_batch and hasattr(self.manager, "batch_rapid_tap"):
            return self.manager.batch_rapid_tap(x, y, count=count, interval=interval)
        return self.manager.rapid_tap(x, y, count=count, interval=interval)

    def auto_247_hunt(self, max_cycles: Optional[int] = None, lead_time_ms: int = 150) -> int:
        """
        Auto-pilot 24/7 hunting loop with anti-sleep heartbeats and millisecond latency offset:
        1. Immediately claims available vouchers on screen.
        2. Sleeps between golden hours with a 3-minute heartbeat to reset the idle sleep timer.
        3. Wakes up, unlocks screen if needed, and rapid-taps hot voucher drops with lead_time_ms offset.
        """
        cycles_completed = 0
        lead_sec = max(0.0, float(lead_time_ms) / 1000.0)
        console.print("\n[bold magenta]=======================================================[/bold magenta]")
        console.print("[bold yellow]🚀 KHỞI ĐỘNG HỆ THỐNG SĂN VOUCHER THIẾT BỊ ANDROID 24/7[/bold yellow]")
        console.print("[bold cyan]🛡️ Chế độ Chống Khóa Màn Hình (Anti-Sleep Heartbeat) ĐÃ BẬT[/bold cyan]")
        if lead_time_ms > 0:
            console.print(f"[bold green]⚡ Bù trễ mạng/màn hình: -{lead_time_ms}ms trước 00.000s[/bold green]")
        console.print("[bold magenta]=======================================================[/bold magenta]\n")

        # Initial connect & warmup
        if not self.manager.current_device:
            self.connect()

        while True:
            cycles_completed += 1
            console.print(f"\n[cyan][Chu kỳ {cycles_completed}] Bắt đầu quét voucher hiện có...[/cyan]")
            claimed = self.scan_and_claim_vouchers(max_scrolls=2)
            console.print(f"[bold green]✓ Tổng voucher thu thập trong đợt này: {claimed}[/bold green]")

            next_dt, secs_left = self.calculate_next_golden_hour()
            console.print(
                f"[bold yellow]⏰ Khung Giờ Vàng kế tiếp: {next_dt.strftime('%H:%M:%S %d/%m/%Y')} "
                f"(Còn {int(secs_left // 60)} phút {int(secs_left % 60)} giây)[/bold yellow]"
            )

            if max_cycles and cycles_completed >= max_cycles:
                logger.info(f"Hoàn thành {cycles_completed} chu kỳ (đạt giới hạn).")
                break

            # Sleep until 30s before golden hour with periodic heartbeats to prevent 30-min screen sleep
            effective_pre_sleep = secs_left - 30 - lead_sec
            if effective_pre_sleep > 5:
                console.print(f"[blue]💤 Nghỉ ngơi trong {int(effective_pre_sleep)}s (Tự động phát nhịp tim chống khóa màn hình mỗi 3 phút)...[/blue]")
                slept = 0.0
                while slept < effective_pre_sleep:
                    chunk = min(180.0, effective_pre_sleep - slept)
                    time.sleep(chunk)
                    slept += chunk
                    # Send WAKEUP keyevent and stayon
                    self.manager.keep_awake()

            # Ensure screen is unlocked and ready before golden hour
            self.manager.ensure_unlocked()

            # Re-check remaining seconds with lead_time_ms offset
            _, remaining = self.calculate_next_golden_hour()
            effective_wait = remaining - lead_sec
            if effective_wait > 0:
                console.print(f"[yellow]⏳ Thức giấc chuẩn bị! Đếm ngược {effective_wait:.2f}s (bù trễ {lead_time_ms}ms)...[/yellow]")
                time.sleep(effective_wait)

            # Golden hour reached! Rapid claim with batch tap
            console.print("[bold red]🔥 ĐÃ ĐẾN KHUNG GIỜ VÀNG! TỰ ĐỘNG GIẬT MÃ SIÊU TỐC...[/bold red]")
            hot_targets = self.manager.find_voucher_buttons()
            if hot_targets:
                for tx, ty in hot_targets[:4]:  # Prioritize top voucher cards
                    if hasattr(self.manager, "batch_rapid_tap"):
                        self.manager.batch_rapid_tap(tx, ty, count=20, interval=0.02)
                    else:
                        self.manager.rapid_tap(tx, ty, count=15, interval=0.03)
            else:
                self.scan_and_claim_vouchers(max_scrolls=2)

            time.sleep(5)

        return cycles_completed
