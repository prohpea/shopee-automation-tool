@echo off
chcp 65001 >nul
title Shopee Automation Tool - Săn Sale Chớp Nhoáng ^& Đặt Đơn 0đ

cd /d "%~dp0"
call "%~dp0_bootstrap.bat" || (pause & exit /b 1)

:APP_RUN
cls
echo ======================================================================
echo       SHOPEE AUTO-ORDER: SĂN SALE CHỚP NHOÁNG ^& ĐẶT ĐƠN 0Đ
echo ======================================================================
echo.
echo   [*] TÍNH NĂNG NỔI BẬT:
echo       1. Canh thời gian đếm ngược chính xác từng mili-giây tới Giờ G
echo       2. Tự động chọn biến thể / màu sắc / kích cỡ sản phẩm
echo       3. Tự động bấm 'Mua Ngay' và chuyển thẳng vào trang Thanh Toán
echo       4. Tự động áp dụng Shopee Voucher (FreeShip 0đ + Mã giảm giá tốt nhất)
echo       5. CHỐT CHẶN AN TOÀN: Chỉ đặt hàng nếu Tổng tiền ^<= Giá tối đa cài đặt
echo          (Nếu voucher bị lỗi làm giá ^> 0đ, Tool sẽ DỪNG LẠI NGAY để bảo vệ ví)
echo.
echo ======================================================================
echo.

:: Kiem tra Chrome CDP 9222 co dang bat khong
powershell -NoProfile -Command "try { $c = [System.Net.Sockets.TcpClient]::new('127.0.0.1', 9222); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [!] Phát hiện Google Chrome ^(CDP 9222^) chưa được bật.
    echo [*] Đang tự động mở Chrome để bạn đăng nhập Shopee...
    call "%~dp0start_chrome.bat"
    echo.
    echo [*] Vui lòng kiểm tra trên Chrome và đảm bảo bạn đã đăng nhập tài khoản Shopee!
    pause
)

:INPUT_URL
set "ITEM_URL="
set /p ITEM_URL=">> [1] Nhập Link sản phẩm Shopee cần săn: "
if "%ITEM_URL%"=="" (
    echo [LOI] Link sản phẩm không được để trống! Vui lòng nhập lại.
    goto INPUT_URL
)

echo.
set "DROP_TIME="
set /p DROP_TIME=">> [2] Nhập Giờ mở bán Flash Sale [HH:MM:SS] (Bỏ trống = Săn NGAY LẬP TỨC): "
if "%DROP_TIME%"=="" set "DROP_TIME=now"

echo.
set "MAX_PRICE="
set /p MAX_PRICE=">> [3] Nhập Giá thanh toán tối đa [VND] (Mặc định = 0 đ): "
if "%MAX_PRICE%"=="" set "MAX_PRICE=0"

echo.
set "VARIANT_NAME="
set /p VARIANT_NAME=">> [4] Nhập Tên phân loại hàng (Ví dụ: Đen / Size L - Bỏ trống = Tự động chọn): "

echo.
set "DRY_RUN_CHOICE="
set /p DRY_RUN_CHOICE=">> [5] Bật chế độ CHẠY THỬ (Dry-run: Chỉ kiểm tra giá, không bấm nút Đặt) [Y/N, Mặc định=N]: "

set "EXTRA_FLAGS="
if not "%VARIANT_NAME%"=="" set EXTRA_FLAGS=%EXTRA_FLAGS% --variant "%VARIANT_NAME%"
if /i "%DRY_RUN_CHOICE%"=="Y" set EXTRA_FLAGS=%EXTRA_FLAGS% --dry-run

echo.
echo ======================================================================
echo [*] BẮT ĐẦU KÍCH HOẠT TIẾN TRÌNH SĂN SALE 0Đ...
echo [*] Link: %ITEM_URL%
echo [*] Giờ săn: %DROP_TIME% ^| Ngưỡng giá tối đa: %MAX_PRICE% đ
echo ======================================================================
echo.

"%PY_CMD%" main.py order --url "%ITEM_URL%" --time "%DROP_TIME%" --max-price %MAX_PRICE% %EXTRA_FLAGS%

echo.
echo ======================================================================
echo [*] Quá trình thực thi hoàn tất.
pause
