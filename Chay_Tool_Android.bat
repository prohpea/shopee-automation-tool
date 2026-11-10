@echo off
chcp 65001 >nul
title Shopee Automation Tool - Chế độ Giả lập Android (LDPlayer / MuMu / Nox) ^& Điện thoại Thật

cd /d "%~dp0"

:: Tự động cấu hình ADB nếu phát hiện LDPlayer hoặc các giả lập khác
if exist "C:\LDPlayer\LDPlayer9\adb.exe" (
    set "PATH=C:\LDPlayer\LDPlayer9;%PATH%"
    set "ADBUTILS_ADB_PATH=C:\LDPlayer\LDPlayer9\adb.exe"
) else if exist "C:\Program Files\Nox\bin\adb.exe" (
    set "PATH=C:\Program Files\Nox\bin;%PATH%"
    set "ADBUTILS_ADB_PATH=C:\Program Files\Nox\bin\adb.exe"
)

call "%~dp0_bootstrap.bat" || (pause & exit /b 1)

:MENU
cls
echo ======================================================================
echo      SHOPEE AUTOMATION TOOL - CHẾ ĐỘ ANDROID (ADB ^& ĐIỆN THOẠI THẬT)
echo ======================================================================
echo.
echo   [1] TỰ ĐỘNG SĂN VOUCHER 24/7 (Canh mọi Khung Giờ Vàng: 0h, 9h, 12h, 15h, 18h, 21h)
echo   [2] Quét và Lưu nhanh toàn bộ Voucher hiện có trên màn hình App
echo   [3] Bắn tỉa siêu tốc (Sniper Tap liên hoàn) giật Voucher cực hiếm
echo   [4] Tự động bật ứng dụng Shopee (com.shopee.vn) trên thiết bị
echo   [5] SĂN SALE CHỚP NHOÁNG ^& ĐẶT ĐƠN 0Đ (Chuyển sang Chrome Desktop Sniper)
echo   [6] Kiểm tra kết nối ADB (Điện thoại cắm cáp USB / LDPlayer / MuMu / Nox)
echo   [7] Chuyển về Menu Trình duyệt Chrome Desktop
echo   [0] Thoát
echo.
echo ======================================================================
set "CHOICE="
set /p CHOICE=">> Nhập lựa chọn [0-7] (Nhấn Enter = Chọn [1] Săn 24/7): "

if "%CHOICE%"=="" goto ANDROID_247
if "%CHOICE%"=="1" goto ANDROID_247
if "%CHOICE%"=="2" goto ANDROID_FAST
if "%CHOICE%"=="3" goto ANDROID_SNIPER
if "%CHOICE%"=="4" goto LAUNCH_APP
if "%CHOICE%"=="5" goto FLASH_ORDER_0D
if "%CHOICE%"=="6" goto CHECK_ADB
if "%CHOICE%"=="7" goto SWITCH_CHROME
if "%CHOICE%"=="0" goto EXIT_TOOL
goto MENU

:ANDROID_247
cls
echo [*] Đang khởi động chế độ SĂN VOUCHER 24/7 TRÊN THIẾT BỊ ANDROID...
echo [*] Tool sẽ tự dò tìm thiết bị/giả lập và canh giờ săn...
echo.
"%PY_CMD%" main.py android --mode auto
echo.
pause
goto MENU

:ANDROID_FAST
cls
echo [*] Đang quét và tự động bấm Lưu tất cả voucher hiện có trên App...
echo.
"%PY_CMD%" main.py android --mode fast --scrolls 3
echo.
pause
goto MENU

:ANDROID_SNIPER
cls
echo [*] Chế độ Bắn tỉa Voucher siêu tốc...
set "COORD_X="
set "COORD_Y="
set /p COORD_X=">> Nhập toạ độ X của nút Lưu (Bỏ trống = Tự động nhận diện): "
set /p COORD_Y=">> Nhập toạ độ Y của nút Lưu (Bỏ trống = Tự động nhận diện): "

if "%COORD_X%"=="" (
    "%PY_CMD%" main.py android --mode sniper
) else (
    "%PY_CMD%" main.py android --mode sniper --x %COORD_X% --y %COORD_Y% --tap-count 50
)
echo.
pause
goto MENU

:LAUNCH_APP
cls
echo [*] Đang gửi lệnh mở App Shopee trên thiết bị...
echo.
"%PY_CMD%" -c "from shopee_tool.core.adb_device import ADBDeviceManager; m = ADBDeviceManager(); m.connect_device(); m.launch_app(); print('Da bat Shopee!')"
echo.
pause
goto MENU

:FLASH_ORDER_0D
call "%~dp0San_Sale_0D.bat"
goto MENU

:CHECK_ADB
cls
echo ======================================================================
echo               KIỂM TRA DANH SÁCH THIẾT BỊ ADB ĐANG KẾT NỐI
echo ======================================================================
echo.
"%PY_CMD%" -c "from shopee_tool.core.adb_device import ADBDeviceManager; m = ADBDeviceManager(); devs = m.find_devices(); print('Danh sach thiet bi ket noi thanh cong:'); [print('  - Serial:', d.serial) for d in devs] if devs else print('  [!] Chua co thiet bi nao san sang. Vui long kiem tra cap USB hoac mo LDPlayer.')"
echo.
pause
goto MENU

:SWITCH_CHROME
call "%~dp0Chay_Tool_Shopee.bat"
goto EXIT_TOOL

:EXIT_TOOL
exit /b 0
