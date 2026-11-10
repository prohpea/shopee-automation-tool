"""
Tests for AndroidVoucherHunter module.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from shopee_tool.modules.android_voucher_hunter import AndroidVoucherHunter


def test_calculate_next_golden_hour():
    hunter = AndroidVoucherHunter()
    # At 08:30, next golden hour should be 09:00
    fake_now = datetime(2026, 11, 5, 8, 30, 0)
    next_time, secs = hunter.calculate_next_golden_hour(now=fake_now)
    assert next_time.hour == 9
    assert next_time.minute == 0
    assert secs == 1800

    # At 21:30 the 22:00 slot is still today
    fake_now = datetime(2026, 11, 5, 21, 30, 0)
    next_time, secs = hunter.calculate_next_golden_hour(now=fake_now)
    assert next_time.hour == 22
    assert next_time.day == 5
    assert secs == 1800

    # At 22:30 the 23:00 slot is still today
    fake_now = datetime(2026, 11, 5, 22, 30, 0)
    next_time, secs = hunter.calculate_next_golden_hour(now=fake_now)
    assert next_time.hour == 23
    assert next_time.day == 5
    assert secs == 1800

    # After the last slot of the day (23:00), roll over to 00:00 next day
    fake_now = datetime(2026, 11, 5, 23, 30, 0)
    next_time, secs = hunter.calculate_next_golden_hour(now=fake_now)
    assert next_time.hour == 0
    assert next_time.day == 6
    assert secs == 1800


def test_golden_hours_cover_both_hunters():
    """Android slots must not be a subset of the Chrome slots."""
    from shopee_tool.modules.fast_voucher_hunter import FastVoucherHunter

    chrome_slots = {h for h, _m in FastVoucherHunter.GOLDEN_HOURS_MAJOR}
    assert chrome_slots <= set(AndroidVoucherHunter.GOLDEN_HOURS)
    assert 20 in AndroidVoucherHunter.GOLDEN_HOURS
    assert 22 in AndroidVoucherHunter.GOLDEN_HOURS


def test_scan_and_claim_vouchers():
    mock_mgr = MagicMock()
    # 2 "Lưu" buttons found
    mock_mgr.find_text_bounds.return_value = [(300, 400), (300, 600)]
    hunter = AndroidVoucherHunter(device_manager=mock_mgr)

    claimed = hunter.scan_and_claim_vouchers(max_scrolls=1)
    assert claimed == 2
    assert mock_mgr.tap.call_count == 2
    mock_mgr.tap.assert_any_call(300, 400)
    mock_mgr.tap.assert_any_call(300, 600)


def test_sniper_tap():
    mock_mgr = MagicMock()
    mock_mgr.rapid_tap.return_value = 20
    hunter = AndroidVoucherHunter(device_manager=mock_mgr)

    count = hunter.sniper_tap(x=400, y=800, count=20, interval=0.01)
    assert count == 20
    mock_mgr.rapid_tap.assert_called_once_with(400, 800, count=20, interval=0.01)


@patch("shopee_tool.modules.android_voucher_hunter.time.sleep")
def test_auto_247_single_cycle(mock_sleep):
    mock_mgr = MagicMock()
    mock_mgr.find_text_bounds.return_value = [(300, 400)]
    hunter = AndroidVoucherHunter(device_manager=mock_mgr)

    # Force next golden hour to be immediately (secs_left = 0)
    with patch.object(hunter, "calculate_next_golden_hour", return_value=(datetime.now(), 0)):
        cycles = hunter.auto_247_hunt(max_cycles=1)
        assert cycles == 1
        assert mock_mgr.rapid_tap.called or mock_mgr.tap.called


def test_scan_and_claim_taps_new_voucher_after_each_scroll():
    """After a scroll the same screen spot holds a different voucher, so it must be tapped."""
    mock_mgr = MagicMock()
    mock_mgr.get_screen_size.return_value = (1080, 2400)
    # Vision reports one button at the same coordinates in every round.
    mock_mgr.find_voucher_buttons.return_value = [(900, 800)]
    hunter = AndroidVoucherHunter(device_manager=mock_mgr)

    claimed = hunter.scan_and_claim_vouchers(max_scrolls=3)

    assert claimed == 3
    assert mock_mgr.tap.call_count == 3


def test_connect_brings_shopee_to_foreground():
    """connect() must launch the Shopee app before any screen scanning happens."""
    mock_mgr = MagicMock()
    mock_mgr.connect_device.return_value = MagicMock(serial="emulator-5554")
    hunter = AndroidVoucherHunter(device_manager=mock_mgr)

    hunter.connect()

    mock_mgr.launch_app.assert_called_once_with("com.shopee.vn")


def test_sniper_tap_with_batch():
    mock_mgr = MagicMock()
    mock_mgr.batch_rapid_tap.return_value = 25
    hunter = AndroidVoucherHunter(device_manager=mock_mgr)

    count = hunter.sniper_tap(x=400, y=800, count=25, interval=0.01, use_batch=True)
    assert count == 25
    mock_mgr.batch_rapid_tap.assert_called_once_with(400, 800, count=25, interval=0.01)


@patch("shopee_tool.modules.android_voucher_hunter.time.sleep")
def test_auto_247_hunt_with_lead_time(mock_sleep):
    mock_mgr = MagicMock()
    mock_mgr.find_voucher_buttons.return_value = [(300, 400)]
    hunter = AndroidVoucherHunter(device_manager=mock_mgr)

    with patch.object(hunter, "calculate_next_golden_hour", return_value=(datetime.now(), 0)):
        cycles = hunter.auto_247_hunt(max_cycles=1, lead_time_ms=200)
        assert cycles == 1
        assert mock_mgr.tap.called
