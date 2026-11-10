"""
Unit tests for DailyCheckin module.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from shopee_tool.modules.checkin import DailyCheckin


def test_checkin_already_claimed():
    async def _run():
        bot = DailyCheckin(cdp="none")
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(
            return_value={"status": "already_claimed", "text": "hôm nay bạn đã nhận"}
        )

        bot.auth.is_logged_in = AsyncMock(return_value=True)

        with patch("shopee_tool.modules.checkin.BrowserManager") as mock_bm_cls, \
             patch("shopee_tool.modules.checkin.CaptchaDetector.is_captcha_present", AsyncMock(return_value=False)):
            mock_bm = MagicMock()
            mock_bm.start = AsyncMock(return_value=mock_page)
            mock_bm.close = AsyncMock()
            mock_bm.save_session = AsyncMock()
            mock_bm_cls.return_value = mock_bm

            res = await bot.execute()
            assert res["success"] is True
            assert res["already_claimed"] is True
            assert "đã điểm danh" in res["message"]

    asyncio.run(_run())


def test_checkin_no_button_found_is_not_success():
    """A page with no claimable button must not be reported as a successful check-in."""

    async def _run():
        bot = DailyCheckin(cdp="none")
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"status": "not_found"})
        bot.auth.is_logged_in = AsyncMock(return_value=True)

        with patch("shopee_tool.modules.checkin.BrowserManager") as mock_bm_cls, \
             patch("shopee_tool.modules.checkin.CaptchaDetector.is_captcha_present", AsyncMock(return_value=False)):
            mock_bm = MagicMock()
            mock_bm.start = AsyncMock(return_value=mock_page)
            mock_bm.close = AsyncMock()
            mock_bm_cls.return_value = mock_bm

            res = await bot.execute()
            assert res["success"] is False
            assert res["already_claimed"] is False
            assert "Không tìm thấy nút" in res["message"]

    asyncio.run(_run())


def test_checkin_cdp_mode():
    async def _run():
        bot = DailyCheckin(cdp="9222")
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"status": "claimed", "text": "nhận ngay"})

        with patch("shopee_tool.modules.checkin.FastVoucherHunter") as mock_fvh_cls:
            mock_fvh = MagicMock()
            mock_fvh.connect = AsyncMock(return_value=mock_page)
            mock_fvh.check_and_handle_verification = AsyncMock(return_value=False)
            mock_fvh.ensure_logged_in = AsyncMock(return_value=True)
            mock_fvh.close = AsyncMock()
            mock_fvh_cls.return_value = mock_fvh

            res = await bot.execute()
            assert res["success"] is True
            assert "nhận ngay" in res["message"]

    asyncio.run(_run())
