"""
ADB Device Manager for Android Emulators & Physical Devices.
Supports automatic discovery of LDPlayer, Nox, MuMu, BlueStacks, and physical Android phones.
Includes Computer Vision button detection when UIAutomator dump is blocked by animations.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import time
from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET

def _ensure_adb_binary() -> Optional[str]:
    """Auto-detect adb.exe from known Windows emulator/SDK paths if not present in PATH."""
    if os.getenv("ADBUTILS_ADB_PATH") and os.path.isfile(os.getenv("ADBUTILS_ADB_PATH")):
        return os.getenv("ADBUTILS_ADB_PATH")
    if shutil.which("adb"):
        return shutil.which("adb")

    candidates = [
        r"C:\LDPlayer\LDPlayer9\adb.exe",
        r"C:\LDPlayer\LDPlayer4.0\adb.exe",
        r"C:\Program Files\Nox\bin\adb.exe",
        r"C:\Program Files (x86)\Nox\bin\adb.exe",
        r"C:\Program Files\Microvirt\MEmu\adb.exe",
        r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            os.environ["ADBUTILS_ADB_PATH"] = c
            adb_dir = os.path.dirname(c)
            if adb_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{adb_dir};{os.environ.get('PATH', '')}"
            return c
    return None

_ensure_adb_binary()

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from adbutils import adb, AdbDevice
except ImportError:
    adb = None
    AdbDevice = None

from shopee_tool.utils.logger import logger


COMMON_EMULATOR_PORTS = [
    5555,   # LDPlayer / Standard ADB / BlueStacks default
    5554,   # Standard Android emulator
    16384,  # MuMu Player 12
    62001,  # NoxPlayer primary
    21503,  # Memu Play
    7555,   # MuMu Player older versions
]


class ADBDeviceManager:
    """Manages connections, commands, and screen interaction with Android devices via ADB."""

    def __init__(self, target_serial: Optional[str] = None):
        self.target_serial = target_serial
        self.current_device: Optional[AdbDevice] = None

    def find_devices(self, probe_common_ports: bool = True) -> List[AdbDevice]:
        """Discover connected devices or probe common emulator ports on localhost."""
        if adb is None:
            raise RuntimeError("adbutils library is not installed.")

        devices = self._list_devices()
        if devices or not probe_common_ports:
            return devices

        logger.info("No active ADB devices found. Probing common emulator ports on localhost...")
        for port in COMMON_EMULATOR_PORTS:
            try:
                adb.connect(f"127.0.0.1:{port}")
            except Exception:
                pass

        devices = self._list_devices()
        if not devices:
            for info in self._raw_list():
                if info.state != "device":
                    logger.warning(
                        f"[!] Phát hiện thiết bị '{info.serial}' nhưng trạng thái là '{info.state}'. "
                        f"Vui lòng MỞ KHOÁ ĐIỆN THOẠI và nhấn [CHO PHÉP GỠ LỖI USB] (Always allow from this computer)!"
                    )
        return devices

    @staticmethod
    def _list_devices() -> List[AdbDevice]:
        try:
            return adb.device_list()
        except Exception as e:
            logger.warning(f"Error listing ADB devices: {e}")
            return []

    @staticmethod
    def _raw_list() -> list:
        try:
            return adb.list()
        except Exception:
            return []

    def connect_device(self, serial: Optional[str] = None) -> AdbDevice:
        """Connect to a specific serial or auto-select the first available device."""
        if adb is None:
            raise RuntimeError("adbutils library is not installed.")

        target = serial or self.target_serial
        if target:
            self.current_device = adb.device(serial=target)
            return self.current_device

        devices = self.find_devices(probe_common_ports=True)
        if not devices:
            unauth_devs = [info for info in self._raw_list() if info.state != "device"]
            if unauth_devs:
                raise ConnectionError(
                    f"Phát hiện thiết bị Android '{unauth_devs[0].serial}' nhưng trạng thái là '{unauth_devs[0].state}'. "
                    f"Vui lòng mở khoá màn hình điện thoại và nhấn [CHO PHÉP GỠ LỖI USB] (Always allow from this computer) rồi thử lại!"
                )
            raise ConnectionError(
                "Không tìm thấy thiết bị Android nào đang kết nối qua USB hoặc giả lập. "
                "Vui lòng cắm cáp USB (chọn Truyền tệp) hoặc mở giả lập trước."
            )

        self.current_device = devices[0]
        return self.current_device

    def keep_awake(self) -> None:
        """Send WAKEUP key event (224) and svc stayon to continuously prevent sleep timer."""
        if not self.current_device:
            self.connect_device()
        try:
            self.current_device.shell("input keyevent 224")
            self.current_device.shell("svc power stayon true")
        except Exception:
            pass

    def ensure_unlocked(self) -> None:
        """Wake up screen and swipe up to unlock if locked."""
        if not self.current_device:
            self.connect_device()
        try:
            self.current_device.shell("input keyevent 224")
            w, h = self.get_screen_size()
            self.current_device.shell(f"input swipe {w//2} {int(h*0.8)} {w//2} {int(h*0.2)} 250")
        except Exception:
            pass

    def launch_app(self, package_name: str = "com.shopee.vn") -> None:
        """Launch an app package on the device."""
        if not self.current_device:
            self.connect_device()
        self.current_device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")

    def is_app_running(self, package_name: str = "com.shopee.vn") -> bool:
        """Check if an app process is active."""
        if not self.current_device:
            self.connect_device()
        output = self.current_device.shell(f"pidof {package_name}")
        return bool(output and output.strip())

    def tap(self, x: int, y: int) -> None:
        """Tap at screen coordinates (x, y)."""
        if not self.current_device:
            self.connect_device()
        self.current_device.shell(f"input tap {x} {y}")

    def rapid_tap(self, x: int, y: int, count: int = 10, interval: float = 0.05) -> int:
        """Rapidly tap at (x, y) count times with a small sleep interval."""
        if not self.current_device:
            self.connect_device()
        tapped = 0
        for _ in range(count):
            self.current_device.shell(f"input tap {x} {y}")
            tapped += 1
            if interval > 0:
                time.sleep(interval)
        return tapped

    def batch_rapid_tap(self, x: int, y: int, count: int = 20, interval: float = 0.02) -> int:
        """
        Execute an in-device batch tap loop inside the Android shell.
        Eliminates per-tap ADB socket round-trip overhead, reducing tap delay from ~50ms to <5ms.
        """
        if not self.current_device:
            self.connect_device()
        sleep_sec = max(0.005, float(interval))
        cmd = f"sh -c 'for i in $(seq 1 {count}); do input tap {x} {y}; sleep {sleep_sec}; done'"
        try:
            self.current_device.shell(cmd)
            return count
        except Exception as e:
            logger.debug(f"In-device batch tap failed ({e}), falling back to rapid_tap")
            return self.rapid_tap(x, y, count=count, interval=interval)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Swipe across screen."""
        if not self.current_device:
            self.connect_device()
        self.current_device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def get_screen_size(self) -> Tuple[int, int]:
        """Get device screen resolution (width, height)."""
        if not self.current_device:
            self.connect_device()
        output = self.current_device.shell("wm size")
        m = re.search(r"(\d+)\s*x\s*(\d+)", output)
        if m:
            return int(m.group(1)), int(m.group(2))
        return 720, 1280

    def dump_hierarchy(self) -> str:
        """Dump current UI hierarchy XML string safely."""
        if not self.current_device:
            self.connect_device()
        try:
            res = self.current_device.dump_hierarchy()
            if res and res.strip().startswith(("<hierarchy", "<?xml")):
                return res
        except Exception:
            pass

        # If direct dump fails (due to continuous Shopee animations), do not hang
        return ""

    FORBIDDEN_KEYWORDS = [
        "mua ngay", "mua hàng", "đặt hàng", "thanh toán", "thêm vào giỏ",
        "mua với voucher", "chọn mua", "checkout", "buy now", "place order",
        "mua", "đặt đơn", "đơn hàng"
    ]

    def find_text_bounds(self, target_text: str) -> List[Tuple[int, int]]:
        """
        Search UI hierarchy for nodes containing target_text (case-insensitive).
        Returns a list of center coordinates (x, y) for each matched node.
        """
        xml_str = self.dump_hierarchy()
        if not xml_str or not xml_str.strip().startswith(("<hierarchy", "<?xml")):
            return []

        matched_centers: List[Tuple[int, int]] = []
        target_lower = target_text.strip().lower()

        try:
            root = ET.fromstring(xml_str)
            for node in root.iter("node"):
                text = (node.attrib.get("text") or "").strip().lower()
                desc = (node.attrib.get("content-desc") or "").strip().lower()
                combined = f"{text} {desc}"
                if any(bad in combined for bad in self.FORBIDDEN_KEYWORDS):
                    continue
                if target_lower in text or target_lower in desc:
                    bounds_str = node.attrib.get("bounds", "")
                    m = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
                    if len(m) == 2:
                        x1, y1 = int(m[0][0]), int(m[0][1])
                        x2, y2 = int(m[1][0]), int(m[1][1])
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        matched_centers.append((center_x, center_y))
        except Exception as e:
            logger.debug(f"Error parsing UI XML: {e}")

        return matched_centers

    def find_voucher_buttons(self, keywords: Optional[List[str]] = None) -> List[Tuple[int, int]]:
        """
        Multi-modal voucher button detection:
        1. Fast Computer Vision color detection on right half of screen (primary).
        2. If vision finds nothing, tries text bounds.

        Returns an empty list when nothing is detected. There is deliberately no
        blind coordinate fallback: tapping pixels that merely look button-shaped
        hits whatever else sits in that grid (variant pickers, "Mua hàng",
        checkout) and reports phantom claims.
        """
        if not self.current_device:
            self.connect_device()

        w, h = self.get_screen_size()

        # 1. Vision detection via in-memory screenshot (fast & immune to Shopee animations)
        if Image:
            try:
                raw_png = self.current_device.shell("screencap -p", encoding=None)
                if raw_png:
                    img = Image.open(io.BytesIO(raw_png)).convert("RGB")
                    grid_w = grid_h = 24
                    x_start, x_end = int(w * 0.52), int(w * 0.98)
                    y_start, y_end = int(h * 0.15), int(h * 0.84)

                    density: dict = {}
                    for y in range(y_start, y_end, 3):
                        for x in range(x_start, x_end, 3):
                            r, g, b = img.getpixel((x, y))
                            # Shopee orange / red: high R, moderate G, low B
                            if r > 195 and g < 115 and b < 70:
                                cell = (y // grid_h, x // grid_w)
                                density[cell] = density.get(cell, 0) + 1

                    centers = [
                        (c * grid_w + grid_w // 2, r * grid_h + grid_h // 2)
                        for (r, c), count in density.items()
                        if count >= 8
                    ]

                    # Merge nearby pixel clusters
                    merged: List[Tuple[int, int]] = []
                    for cx, cy in centers:
                        if not any(abs(cx - mx) < 60 and abs(cy - my) < 60 for mx, my in merged):
                            merged.append((cx, cy))

                    # Checkout zone guard: never tap the bottom payment bar (already excluded by y_end)
                    safe_merged = [(cx, cy) for cx, cy in merged if cy <= int(h * 0.84)]
                    if safe_merged:
                        safe_merged.sort(key=lambda p: p[1])
                        return safe_merged
            except Exception as e:
                logger.debug(f"Vision detection fallback exception: {e}")

        # 2. Try text bounds as secondary fallback
        if keywords:
            for kw in keywords:
                bounds = self.find_text_bounds(kw)
                if bounds:
                    return bounds

        return []
