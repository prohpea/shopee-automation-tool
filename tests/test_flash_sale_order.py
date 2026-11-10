"""
Unit tests for Flash Sale countdown parsing and the 0đ order safety gate.

The gate is the only thing standing between the tool and an unintended purchase,
so an unreadable total must block the order rather than be treated as 0đ.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from shopee_tool.modules.flash_sale_order import FlashSaleOrderHunter


def _hunter(**kwargs):
    return FlashSaleOrderHunter(item_url="https://shopee.vn/x-i.1.2", **kwargs)


def _run(coro):
    return asyncio.run(coro)


def test_countdown_now_is_immediate():
    target, secs = _hunter().calculate_countdown("now")
    assert secs == 0.0
    assert isinstance(target, datetime)


def test_countdown_hh_mm_and_hh_mm_ss_agree():
    hunter = _hunter()
    now = datetime.now()
    fmt = "%H:%M:%S"
    later = now + timedelta(minutes=5, seconds=30)
    _, secs_short = hunter.calculate_countdown(later.strftime("%H:%M"))
    _, secs_long = hunter.calculate_countdown(later.strftime(fmt))
    assert abs(secs_short - secs_long) < 60


def test_countdown_rejects_extra_segments():
    with pytest.raises(ValueError):
        _hunter().calculate_countdown("12:00:00:00")


def test_unreadable_total_blocks_order():
    hunter = _hunter(max_price=0)
    hunter.page = AsyncMock()
    hunter.extract_total_payment = AsyncMock(return_value=None)

    res = _run(hunter.place_order_with_safety_check())

    assert res["success"] is False
    assert "không đọc được" in res["message"]
    hunter.page.query_selector.assert_not_called()


def test_total_above_max_price_blocks_order():
    hunter = _hunter(max_price=0)
    hunter.page = AsyncMock()
    hunter.extract_total_payment = AsyncMock(return_value=50000)

    res = _run(hunter.place_order_with_safety_check())

    assert res["success"] is False
    assert res["total_price"] == 50000
    hunter.page.query_selector.assert_not_called()


def test_dry_run_does_not_click_place_order():
    hunter = _hunter(max_price=100000, dry_run=True)
    hunter.page = AsyncMock()
    hunter.extract_total_payment = AsyncMock(return_value=100000)

    res = _run(hunter.place_order_with_safety_check())

    assert res["success"] is True
    assert res["total_price"] == 100000
    hunter.page.query_selector.assert_not_called()
