"""
Unit and integration tests for FastVoucherHunter and CLI options.
"""

import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from click.testing import CliRunner

from cli import cli
from shopee_tool.modules.fast_voucher_hunter import (
    FastVoucherHunter,
    JS_CLAIM_VOUCHERS,
    JS_FAST_SCROLL,
)


def test_normalize_cdp_url():
    hunter = FastVoucherHunter()
    assert hunter._normalize_cdp_url(9222) == "http://127.0.0.1:9222"
    assert hunter._normalize_cdp_url("9222") == "http://127.0.0.1:9222"
    assert hunter._normalize_cdp_url("http://localhost:9222") == "http://localhost:9222"
    assert hunter._normalize_cdp_url("127.0.0.1:9222") == "http://127.0.0.1:9222"
    assert hunter._normalize_cdp_url("ws://localhost:9222/devtools") == "ws://localhost:9222/devtools"


def test_parse_target_time():
    hunter = FastVoucherHunter()
    now = datetime.now()

    # Time in future today
    future_hour = (now.hour + 1) % 24
    time_str = f"{future_hour:02d}:30:00"
    target = hunter._parse_target_time(time_str)
    assert target.hour == future_hour
    assert target.minute == 30
    assert target.second == 0

    # 2-part format HH:MM
    target_hm = hunter._parse_target_time(f"{future_hour:02d}:45")
    assert target_hm.hour == future_hour
    assert target_hm.minute == 45
    assert target_hm.second == 0

    # Invalid format raises ValueError
    with pytest.raises(ValueError):
        hunter._parse_target_time("invalid_time")

    with pytest.raises(ValueError):
        hunter._parse_target_time("12:00:00:00")


def test_js_snippets_syntax():
    # Verify JS strings are non-empty and well-formed
    assert "claimKeywords" in JS_CLAIM_VOUCHERS
    assert "lưu" in JS_CLAIM_VOUCHERS
    assert "excludeKeywords" in JS_CLAIM_VOUCHERS
    assert "đã lưu" in JS_CLAIM_VOUCHERS
    assert "scrollBy" in JS_FAST_SCROLL


import asyncio


def test_claim_visible_vouchers_mocked():
    async def _run():
        hunter = FastVoucherHunter(cdp="9222")
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(
            return_value={
                "claimed_count": 2,
                "vouchers": [
                    {"button_text": "Lưu", "info": "Giảm 50k đơn từ 250k"},
                    {"button_text": "Lưu mã", "info": "Miễn phí vận chuyển 0đ"},
                ],
            }
        )
        hunter._page = mock_page

        result = await hunter.claim_visible_vouchers()
        assert result["claimed_count"] == 2
        assert len(result["vouchers"]) == 2
        assert "elapsed_ms" in result
        mock_page.evaluate.assert_called_once_with(JS_CLAIM_VOUCHERS)

    asyncio.run(_run())


def test_hunt_vouchers_flow():
    async def _run():
        hunter = FastVoucherHunter(cdp="9222", max_claims=5)

        mock_page = MagicMock()
        mock_page.url = "https://shopee.vn/m/ma-giam-gia"
        mock_page.goto = AsyncMock()
        mock_page.bring_to_front = AsyncMock()

        # Sequence of returns: 2 claimed first, 1 claimed second, 0 afterwards
        eval_returns = [
            {"claimed_count": 2, "vouchers": [{"button_text": "Lưu", "info": "Voucher 1"}, {"button_text": "Lưu", "info": "Voucher 2"}]},
            {"scrollY": 900, "scrollHeight": 3000, "innerHeight": 800},  # scroll
            {"claimed_count": 1, "vouchers": [{"button_text": "Nhận", "info": "Voucher 3"}]},
            {"scrollY": 1800, "scrollHeight": 3000, "innerHeight": 800},  # scroll
            {"claimed_count": 0, "vouchers": []},
            {"claimed_count": 0, "vouchers": []},
        ]

        mock_page.evaluate = AsyncMock(side_effect=lambda script, *args: eval_returns.pop(0) if eval_returns else {"claimed_count": 0, "vouchers": []})

        with patch.object(hunter, "connect", AsyncMock(return_value=mock_page)), patch.object(hunter, "close", AsyncMock()):
            result = await hunter.hunt_vouchers(scroll_rounds=2, scroll_delay=0.01)

            assert result["success"] is True
            assert result["claimed_count"] == 3
            assert len(result["vouchers"]) == 3
            assert "Tổng cộng đã lưu thành công 3 mã" in result["message"]

    asyncio.run(_run())



def test_cli_vouchers_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["vouchers", "--help"])
    assert result.exit_code == 0
    assert "--mode" in result.output
    assert "--cdp" in result.output
    assert "--sniper-time" in result.output
    assert "--all-hubs" in result.output
    assert "--scrolls" in result.output


def test_standalone_cli_forwards_to_vouchers(monkeypatch):
    """The standalone script must forward argv to `main.py vouchers` with --mode auto."""
    import fast_voucher_hunter as standalone

    captured = {}

    def _fake_main(args, prog_name):
        captured["args"] = args
        captured["prog"] = prog_name

    monkeypatch.setattr("cli.cli.main", _fake_main)
    monkeypatch.setattr(sys, "argv", ["fast_voucher_hunter.py", "--cdp", "1234", "--target-time", "12:00"])

    standalone.main()

    assert captured["args"] == [
        "vouchers",
        "--cdp",
        "1234",
        "--sniper-time",
        "12:00",
        "--mode",
        "auto",
    ]


def test_cli_vouchers_cdp_connection_failure():
    runner = CliRunner()
    # Port 65530 is unlikely to have CDP running
    result = runner.invoke(cli, ["vouchers", "--mode", "fast", "--cdp", "65530"])
    # Should exit with code 1 and show helpful guidance
    assert result.exit_code == 1


def test_navigate_to_hub():
    async def _run():
        hunter = FastVoucherHunter()
        mock_page = MagicMock()
        mock_page.url = "https://shopee.vn/m/ma-giam-gia"
        mock_page.goto = AsyncMock()
        hunter._page = mock_page

        # 1. Already on the hub -> should not call goto
        await hunter.navigate_to_hub("https://shopee.vn/m/ma-giam-gia")
        mock_page.goto.assert_not_called()

        # 2. On a different page -> should call goto with Referer to prevent bot checkpoints
        mock_page.url = "https://shopee.vn/"
        await hunter.navigate_to_hub("https://shopee.vn/m/mien-phi-van-chuyen")
        mock_page.goto.assert_called_once_with(
            "https://shopee.vn/m/mien-phi-van-chuyen",
            referer="https://shopee.vn/",
            wait_until="domcontentloaded",
            timeout=30000,
        )

    asyncio.run(_run())


def test_sniper_hunt_target_time():
    async def _run():
        hunter = FastVoucherHunter(cdp="9222", max_claims=5)
        mock_page = MagicMock()
        mock_page.url = "https://shopee.vn/m/ma-giam-gia"
        mock_page.bring_to_front = AsyncMock()

        eval_returns = [
            {"claimed_count": 2, "vouchers": [{"button_text": "Lưu", "info": "Flash Voucher 1"}]},
            {"claimed_count": 0, "vouchers": []},
        ]
        mock_page.evaluate = AsyncMock(side_effect=lambda script, *args: eval_returns.pop(0) if eval_returns else {"claimed_count": 0, "vouchers": []})

        now = datetime.now()
        # Set target time 1 second in the future
        target_t = (now + timedelta(seconds=1)).strftime("%H:%M:%S")

        with patch.object(hunter, "connect", AsyncMock(return_value=mock_page)), patch.object(hunter, "close", AsyncMock()):
            result = await hunter.sniper_hunt(target_time_str=target_t, burst_duration=0.1)

            assert result["success"] is True
            assert result["claimed_count"] >= 1
            assert "Sniper kết thúc" in result["message"]

    asyncio.run(_run())


def test_close_lifecycle():
    async def _run():
        hunter = FastVoucherHunter(cdp="9222")
        mock_page = MagicMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.close = AsyncMock()
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        mock_context = MagicMock()
        mock_context.close = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()

        hunter._page = mock_page
        hunter._browser = mock_browser
        hunter._context = mock_context
        hunter._playwright = mock_playwright
        hunter._is_cdp = True

        await hunter.close()

        # In CDP mode, page and context are NOT closed (so user's Chrome stays alive)
        mock_page.close.assert_not_called()
        mock_context.close.assert_not_called()
        # Browser connection is closed (disconnecting CDP) and Playwright stopped
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    asyncio.run(_run())


def test_js_claim_vouchers_real_dom():
    """Runs JS_CLAIM_VOUCHERS in actual Playwright browser to verify DOM matching & exclusions."""
    async def _run():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            html = """
            <div>
                <button id="b1">Lưu</button>
                <button id="b2">Lưu&nbsp;mã</button>
                <button id="b3">Đã lưu</button>
                <button id="b4">Lưu ý khi sử dụng</button>
                <button id="b5">Lưu vào giỏ</button>
                <div role="button" id="b6"><span>Nhận ngay</span></div>
                <button id="b7">Lưu tất cả</button>
                <button id="b8" disabled>Lưu</button>
            </div>
            """
            await page.set_content(html)
            res = await page.evaluate(JS_CLAIM_VOUCHERS)

            claimed_texts = [v["button_text"] for v in res.get("vouchers", [])]
            # b1, b2, b6, b7 should be claimed
            assert "Lưu" in claimed_texts
            assert "Lưu mã" in claimed_texts or any("Lưu" in t and "mã" in t for t in claimed_texts)
            assert "Nhận ngay" in claimed_texts
            assert "Lưu tất cả" in claimed_texts

            # b3, b4, b5, b8 must NOT be claimed
            assert not any("Đã lưu" in t for t in claimed_texts)
            assert not any("Lưu ý" in t for t in claimed_texts)
            assert not any("Lưu vào" in t for t in claimed_texts)
            assert res["claimed_count"] == 4

            await browser.close()

    asyncio.run(_run())


def test_max_claims_strict_capping():
    """Verify that hunt_vouchers never exceeds max_claims even with excess items returned."""
    async def _run():
        hunter = FastVoucherHunter(cdp="9222", max_claims=2)
        mock_page = MagicMock()
        mock_page.url = "https://shopee.vn/m/ma-giam-gia"
        mock_page.goto = AsyncMock()

        eval_returns = [
            {
                "claimed_count": 3,
                "vouchers": [
                    {"button_text": "Lưu", "info": "Voucher 1"},
                    {"button_text": "Lưu", "info": "Voucher 2"},
                    {"button_text": "Lưu", "info": "Voucher 3"},
                ],
            },
        ]
        mock_page.evaluate = AsyncMock(side_effect=lambda script, *args: eval_returns.pop(0) if eval_returns else {"claimed_count": 0, "vouchers": []})

        with patch.object(hunter, "connect", AsyncMock(return_value=mock_page)), patch.object(hunter, "close", AsyncMock()):
            result = await hunter.hunt_vouchers(scroll_rounds=2, scroll_delay=0.01)
            assert result["success"] is True
            # Exactly capped at max_claims = 2
            assert result["claimed_count"] == 2
            assert len(result["vouchers"]) == 2

    asyncio.run(_run())


def test_default_chrome_user_data_path():
    """Verify get_default_chrome_user_data_dir returns a valid string."""
    from shopee_tool.modules.fast_voucher_hunter import get_default_chrome_user_data_dir
    path_str = get_default_chrome_user_data_dir()
    assert isinstance(path_str, str)
    assert len(path_str) > 0


def test_sniper_auto_refresh_handles_reload_error():
    """Verify that auto-refresh mode catches reload exceptions without crashing."""
    async def _run():
        hunter = FastVoucherHunter(cdp="9222", max_claims=1)
        mock_page = MagicMock()
        mock_page.url = "https://shopee.vn/m/ma-giam-gia"
        # Simulate reload failing on 5th loop, then succeeding
        mock_page.reload = AsyncMock(side_effect=Exception("Network timeout"))

        eval_calls = 0

        async def _eval(script, *args):
            nonlocal eval_calls
            eval_calls += 1
            if eval_calls >= 6:
                return {"claimed_count": 1, "vouchers": [{"button_text": "Lưu", "info": "Late Drop"}]}
            return {"claimed_count": 0, "vouchers": []}

        mock_page.evaluate = AsyncMock(side_effect=_eval)

        with patch.object(hunter, "connect", AsyncMock(return_value=mock_page)), patch.object(hunter, "close", AsyncMock()):
            result = await hunter.sniper_hunt(refresh_interval=0.01)
            assert result["success"] is True
            assert result["claimed_count"] == 1

    asyncio.run(_run())


def test_check_and_handle_verification():
    """Verify that check_and_handle_verification detects captcha page and navigates to recover."""
    async def _run():
        hunter = FastVoucherHunter()
        mock_page = MagicMock()
        mock_page.url = "https://shopee.vn/verify/captcha?anti_bot_tracking_id=123"
        mock_page.evaluate = AsyncMock(return_value="Please Try Again Later. Verification can't be completed.")
        
        mock_btn = MagicMock()
        mock_btn.is_visible = AsyncMock(return_value=True)
        mock_btn.click = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=mock_btn)
        mock_page.goto = AsyncMock()
        hunter._page = mock_page

        recovered = await hunter.check_and_handle_verification()
        assert recovered is True
        mock_btn.click.assert_called_once()

    asyncio.run(_run())


def test_restore_session_cookies_if_needed(tmp_path):
    """Verify restore_session_cookies_if_needed loads cookies from disk into browser context."""
    import json
    from shopee_tool.core.config import Settings

    async def _run():
        session_file = tmp_path / "default.json"
        session_file.write_text(
            json.dumps({"cookies": [{"name": "SPC_U", "value": "106846041", "domain": ".shopee.vn", "path": "/"}]}),
            encoding="utf-8",
        )

        hunter = FastVoucherHunter()
        # Use a custom object so type name doesn't contain 'mock'
        class DummyPage:
            def __init__(self):
                self.reload = AsyncMock()

        hunter._page = DummyPage()
        hunter._context = MagicMock()
        hunter._context.add_cookies = AsyncMock()

        with patch.object(Settings, "get_session_path", return_value=session_file):
            restored = await hunter.restore_session_cookies_if_needed()
            assert restored is True
            hunter._context.add_cookies.assert_called_once()

    asyncio.run(_run())


def test_get_next_golden_drop_and_auto_time():
    """Verify automatic Golden Hour & Peak Drop detection without user input."""
    hunter = FastVoucherHunter()

    # At 11:50:00 -> next major golden hour is 12:00:00
    t_morning = datetime(2026, 11, 4, 11, 50, 0)
    drop_info = hunter.get_next_golden_drop(now=t_morning, major_only=True)
    assert drop_info["time_str"] == "12:00:00"
    assert drop_info["is_major"] is True
    assert "12:00" in drop_info["label"]

    # At 23:55:00 -> wraps around to 00:00:00 next day
    t_late = datetime(2026, 11, 4, 23, 55, 0)
    drop_midnight = hunter.get_next_golden_drop(now=t_late)
    assert drop_midnight["time_str"] == "00:00:00"
    assert drop_midnight["is_major"] is True
    assert drop_midnight["target_dt"].day == 5

    # Mega Sale day check (11/11, 15th, 25th)
    assert hunter.is_big_sale_day(datetime(2026, 11, 11, 10, 0, 0)) is True
    assert hunter.is_big_sale_day(datetime(2026, 11, 15, 10, 0, 0)) is True
    assert hunter.is_big_sale_day(datetime(2026, 11, 25, 10, 0, 0)) is True
    assert hunter.is_big_sale_day(datetime(2026, 11, 4, 10, 0, 0)) is False

    # _parse_target_time("auto") resolves automatically
    auto_dt = hunter._parse_target_time("auto")
    assert isinstance(auto_dt, datetime)
    assert auto_dt > datetime.now()


def test_js_vip_voucher_priority_real_dom():
    """Verify JS_CLAIM_VOUCHERS prioritizes 'Claim All' and 'Voucher Khủng' first and sets is_vip."""
    async def _run():
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            html = """
            <div>
                <div class="voucher-card">
                    <span>Giảm 5k đơn từ 99k</span>
                    <button id="small">Lưu</button>
                </div>
                <div class="voucher-card">
                    <span>Giảm 50% Tối đa 500k Toàn Sàn</span>
                    <button id="vip">Lưu mã</button>
                </div>
                <div class="voucher-card">
                    <button id="all">Lưu tất cả (120)</button>
                </div>
            </div>
            """
            await page.set_content(html)
            res = await page.evaluate(JS_CLAIM_VOUCHERS)
            vouchers = res.get("vouchers", [])
            assert len(vouchers) == 3
            # Highest priority ('Lưu tất cả (120)') clicked first, then 'Giảm 50% Tối đa 500k' second, small voucher last
            assert "Lưu tất cả" in vouchers[0]["button_text"]
            assert vouchers[0]["is_vip"] is True
            assert "500k" in vouchers[1]["info"].lower() or "50%" in vouchers[1]["info"].lower()
            assert vouchers[1]["is_vip"] is True
            assert vouchers[2]["is_vip"] is False

            await browser.close()

    asyncio.run(_run())


def test_auto_247_hunt_single_cycle():
    """Verify 24/7 Auto-Pilot mode runs startup sweep, waits for golden hour, bursts, and sweeps."""
    async def _run():
        hunter = FastVoucherHunter(cdp="9222", max_claims=10)
        mock_page = MagicMock()
        mock_page.url = "https://shopee.vn/m/ma-giam-gia"
        mock_page.goto = AsyncMock()
        mock_page.bring_to_front = AsyncMock()

        claim_eval_calls = 0

        async def _mock_eval(script, *args):
            nonlocal claim_eval_calls
            if "scrollBy" in str(script):
                return {"scrollY": 900, "scrollHeight": 2000, "innerHeight": 800}
            if "claimKeywords" in str(script):
                claim_eval_calls += 1
                if claim_eval_calls == 1:
                    # Startup sweep
                    return {
                        "claimed_count": 2,
                        "vouchers": [
                            {"button_text": "Lưu tất cả", "info": "Claim All (50)", "is_vip": True},
                            {"button_text": "Lưu", "info": "Giảm 500k", "is_vip": True},
                        ],
                    }
                elif claim_eval_calls == 2:
                    # Burst during golden hour
                    return {
                        "claimed_count": 1,
                        "vouchers": [
                            {"button_text": "Lưu", "info": "Flash Voucher 50% Giờ Vàng", "is_vip": True},
                        ],
                    }
                else:
                    return {"claimed_count": 0, "vouchers": []}
            return True

        mock_page.evaluate = AsyncMock(side_effect=_mock_eval)

        soon_dt = datetime.now() + timedelta(seconds=0.2)
        fake_drop = {
            "target_dt": soon_dt,
            "time_str": soon_dt.strftime("%H:%M:%S"),
            "label": "🔥 SIÊU GIỜ VÀNG TEST",
            "is_major": True,
            "is_big_sale": False,
            "seconds_until": 0.2,
        }

        with (
            patch.object(hunter, "connect", AsyncMock(return_value=mock_page)),
            patch.object(hunter, "close", AsyncMock()),
            patch.object(hunter, "_native_reload_hub", AsyncMock()),
            patch.object(hunter, "get_next_golden_drop", return_value=fake_drop),
        ):
            res = await hunter.auto_247_hunt(
                patrol_interval=10.0,
                scroll_rounds=1,
                burst_duration=0.1,
                max_cycles=1,
            )
            assert res["success"] is True
            assert res["claimed_count"] == 3
            assert res["vip_count"] == 3
            assert res["cycles"] == 1

    asyncio.run(_run())


def test_golden_hours_major_has_all_11_slots():
    hours = {slot[0] for slot in FastVoucherHunter.GOLDEN_HOURS_MAJOR.keys()}
    expected = {0, 6, 9, 11, 12, 15, 18, 20, 21, 22, 23}
    assert hours == expected
    assert len(FastVoucherHunter.GOLDEN_HOURS_MAJOR) == 11





