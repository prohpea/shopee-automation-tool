"""
Tests for ADB Device Manager and emulator discovery.
"""

from unittest.mock import MagicMock, patch

from shopee_tool.core.adb_device import ADBDeviceManager, COMMON_EMULATOR_PORTS


def test_common_ports_defined():
    assert 5555 in COMMON_EMULATOR_PORTS
    assert 16384 in COMMON_EMULATOR_PORTS
    assert 62001 in COMMON_EMULATOR_PORTS


@patch("shopee_tool.core.adb_device.adb")
def test_find_devices_when_already_connected(mock_adb):
    mock_dev = MagicMock()
    mock_dev.serial = "127.0.0.1:5555"
    mock_adb.device_list.return_value = [mock_dev]

    manager = ADBDeviceManager()
    devices = manager.find_devices()
    assert len(devices) == 1
    assert devices[0].serial == "127.0.0.1:5555"


@patch("shopee_tool.core.adb_device.adb")
def test_find_devices_probes_common_ports_if_empty(mock_adb):
    mock_adb.device_list.side_effect = [[], [MagicMock(serial="127.0.0.1:5555")]]
    mock_adb.connect.return_value = "connected to 127.0.0.1:5555"

    manager = ADBDeviceManager()
    devices = manager.find_devices(probe_common_ports=True)
    assert len(devices) == 1
    mock_adb.connect.assert_any_call("127.0.0.1:5555")


@patch("shopee_tool.core.adb_device.adb")
def test_connect_device(mock_adb):
    mock_dev = MagicMock()
    mock_dev.serial = "emulator-5554"
    mock_adb.device.return_value = mock_dev

    manager = ADBDeviceManager()
    dev = manager.connect_device("emulator-5554")
    assert dev == mock_dev
    assert manager.current_device == mock_dev


def test_rapid_tap():
    manager = ADBDeviceManager()
    mock_dev = MagicMock()
    manager.current_device = mock_dev

    tapped = manager.rapid_tap(500, 1000, count=5, interval=0.01)
    assert tapped == 5
    assert mock_dev.shell.call_count == 5
    mock_dev.shell.assert_called_with("input tap 500 1000")


def test_find_text_bounds_from_xml():
    xml_sample = """
    <hierarchy rotation="0">
        <node bounds="[100,200][300,400]" text="Lưu" class="android.widget.TextView" />
        <node bounds="[400,500][600,700]" text="Mã Giảm Giá" class="android.widget.TextView" />
    </hierarchy>
    """
    manager = ADBDeviceManager()
    mock_dev = MagicMock()
    mock_dev.dump_hierarchy.return_value = xml_sample
    manager.current_device = mock_dev

    bounds = manager.find_text_bounds("Lưu")
    assert len(bounds) == 1
    assert bounds[0] == (200, 300)  # center of [100, 200] and [300, 400]


def test_find_voucher_buttons_returns_empty_when_nothing_detected():
    """No blind grid fallback: undetected buttons must yield no tap targets."""
    manager = ADBDeviceManager()
    mock_dev = MagicMock()
    mock_dev.dump_hierarchy.return_value = "<hierarchy rotation='0' />"
    manager.current_device = mock_dev
    manager.get_screen_size = lambda: (1080, 2400)

    assert manager.find_voucher_buttons(["Lưu", "Nhận"]) == []


def test_batch_rapid_tap_executes_single_shell_loop():
    manager = ADBDeviceManager()
    mock_dev = MagicMock()
    manager.current_device = mock_dev

    tapped = manager.batch_rapid_tap(350, 700, count=25, interval=0.02)
    assert tapped == 25
    assert mock_dev.shell.call_count == 1
    call_arg = mock_dev.shell.call_args[0][0]
    assert "seq 1 25" in call_arg
    assert "input tap 350 700" in call_arg


def test_batch_rapid_tap_fallback_to_rapid_tap_on_error():
    manager = ADBDeviceManager()
    mock_dev = MagicMock()
    # First call (shell batch) raises exception, fallback calls rapid_tap
    mock_dev.shell.side_effect = [RuntimeError("seq not found"), None, None, None]
    manager.current_device = mock_dev

    tapped = manager.batch_rapid_tap(350, 700, count=3, interval=0.01)
    assert tapped == 3


def test_find_text_bounds_filters_forbidden_keywords():
    xml_sample = """
    <hierarchy rotation="0">
        <node bounds="[100,200][300,400]" text="Lưu" class="android.widget.TextView" />
        <node bounds="[400,500][600,700]" text="Mua ngay để nhận voucher" class="android.widget.TextView" />
        <node bounds="[100,800][300,900]" text="Đặt hàng" class="android.widget.TextView" />
        <node bounds="[100,1000][300,1100]" text="Thanh toán" class="android.widget.TextView" />
    </hierarchy>
    """
    manager = ADBDeviceManager()
    mock_dev = MagicMock()
    mock_dev.dump_hierarchy.return_value = xml_sample
    manager.current_device = mock_dev

    # "Lưu" is safe
    bounds = manager.find_text_bounds("Lưu")
    assert len(bounds) == 1
    assert bounds[0] == (200, 300)

    # "Mua ngay", "Đặt hàng", "Thanh toán" are blacklisted
    assert manager.find_text_bounds("Mua ngay") == []
    assert manager.find_text_bounds("Đặt hàng") == []
    assert manager.find_text_bounds("Thanh toán") == []


def test_keep_awake_includes_stayon():
    manager = ADBDeviceManager()
    mock_dev = MagicMock()
    manager.current_device = mock_dev

    manager.keep_awake()
    mock_dev.shell.assert_any_call("input keyevent 224")
    mock_dev.shell.assert_any_call("svc power stayon true")
