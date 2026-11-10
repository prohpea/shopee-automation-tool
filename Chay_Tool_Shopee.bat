@echo off
chcp 65001 >nul
title Shopee Automation Tool v2.0 - Auto-Pilot 24/7

cd /d "%~dp0"
call "%~dp0_bootstrap.bat" || (pause & exit /b 1)

:MENU
cls
echo ======================================================================
echo           SHOPEE AUTOMATION TOOL v2.0 - AUTO-PILOT 24/7
echo ======================================================================
echo.
echo   --- [ BƯỚC 1: KHỞI TẠO VÀ XÁC MINH PHIÊN ĐĂNG NHẬP ] -----------------
echo   [1] MỞ CHROME XÁC MINH VÀ ĐĂNG NHẬP (Làm 1 lần duy nhất - BẮT BUỘC)
echo.
echo   --- [ BƯỚC 2: TỰ ĐỘNG SĂN VOUCHER ] ---------------------------------
echo   [2] TỰ ĐỘNG SĂN VOUCHER KHỦNG 24/7 (Canh mọi Khung Giờ Vàng)
echo   [3] Quét và Lưu nhanh toàn bộ Voucher hiện có (Chạy 1 lượt rồi dừng)
echo   [4] Phục kích Khung Giờ Vàng gần nhất (Chế độ Bắn tỉa Sniper)
echo   [5] SĂN SALE CHỚP NHOÁNG ^& TỰ ĐỘNG ĐẶT ĐƠN 0Đ (Flash Sale 0đ Auto-Order)
echo.
echo   --- [ TIỆN ÍCH MỞ RỘNG ] --------------------------------------------
echo   [6] Tự động Điểm danh nhận Shopee Xu hàng ngày
echo   [7] Tìm kiếm và trích xuất dữ liệu sản phẩm Shopee ra file Excel
echo   [8] Chuyển sang Chế độ Thiết bị ^& Giả lập Android (ADB)
echo   [0] Thoát
echo.
echo ======================================================================
set "CHOICE="
set /p CHOICE=">> Nhập lựa chọn [0-8] (Khuyên dùng: [1] nếu chưa xác minh, hoặc [2] Săn 24/7): "

if "%CHOICE%"=="" goto MENU
if "%CHOICE%"=="1" goto VERIFY_LOGIN
if "%CHOICE%"=="2" goto AUTO_247
if "%CHOICE%"=="3" goto FAST_HUNT
if "%CHOICE%"=="4" goto AUTO_SNIPER
if "%CHOICE%"=="5" goto FLASH_ORDER_0D
if "%CHOICE%"=="6" goto DAILY_CHECKIN
if "%CHOICE%"=="7" goto SEARCH_SCRAPE
if "%CHOICE%"=="8" goto SWITCH_ANDROID
if "%CHOICE%"=="0" goto EXIT_TOOL
goto MENU

:VERIFY_LOGIN
cls
echo ======================================================================
echo   BƯỚC 1: ĐĂNG NHẬP VÀ GIẢI XÁC MINH TRÊN GOOGLE CHROME (LÀM 1 LẦN)
echo ======================================================================
echo.
echo [*] Đang khởi động Google Chrome và kết nối qua cổng CDP 9222...
call start_chrome.bat
echo.
echo ======================================================================
echo  HƯỚNG DẪN:
echo  1. Cửa sổ Google Chrome thật trên máy tính của bạn đã được mở ra.
echo  2. Nếu Shopee hiển thị xác minh (kéo thanh trượt captcha / OTP),
echo     bạn hãy kéo thanh trượt giải bằng tay trực tiếp trên Chrome.
echo  3. Kiểm tra đảm bảo tài khoản Shopee của bạn đã đăng nhập sẵn sàng.
echo ======================================================================
echo.
echo ^>^> Khi bạn đã giải xong xác minh trên Chrome, hãy nhấn PHÍM BẤT KỲ tại đây
echo ^>^> để Tool tự động LƯU LẠI PHIÊN ĐĂNG NHẬP SẠCH vĩnh viễn...
pause >nul
echo.
echo [*] Đang đồng bộ và lưu phiên đăng nhập sạch vào máy...
"%PY_CMD%" main.py verify
echo.
echo [✓] ĐÃ LƯU PHIÊN ĐĂNG NHẬP THÀNH CÔNG!
echo.
set "GO_HUNT="
set /p GO_HUNT=">> Bạn có muốn kích hoạt [2] SĂN VOUCHER 24/7 NGAY BÂY GIỜ? (Y/N, Enter = Y): "
if /i "%GO_HUNT%"=="" goto AUTO_247
if /i "%GO_HUNT%"=="y" goto AUTO_247
goto MENU

:AUTO_247
cls
echo [*] Đang kích hoạt chế độ AUTO-PILOT 24/7 (Tự động quét ngay + Canh mọi Khung Giờ Vàng)...
echo.
"%PY_CMD%" main.py vouchers --mode auto --cdp 9222
echo.
pause
goto MENU

:FAST_HUNT
cls
echo [*] Đang kích hoạt chế độ quét nhanh toàn bộ voucher hiện có...
echo.
"%PY_CMD%" main.py vouchers --mode fast --cdp 9222
echo.
pause
goto MENU

:AUTO_SNIPER
cls
echo [*] Chế độ phục kích Khung Giờ Vàng tiếp theo (Tự động nhận diện giờ vàng)...
echo.
"%PY_CMD%" main.py vouchers --mode sniper --cdp 9222 --sniper-time auto
echo.
pause
goto MENU

:FLASH_ORDER_0D
call "%~dp0San_Sale_0D.bat"
goto MENU

:DAILY_CHECKIN
cls
echo [*] Đang nhận Xu Shopee hàng ngày...
echo.
"%PY_CMD%" main.py checkin
echo.
pause
goto MENU

:SEARCH_SCRAPE
cls
echo Nhập từ khóa sản phẩm muốn tìm:
set "KEYWORD="
set /p KEYWORD=">> Từ khóa: "
if not "%KEYWORD%"=="" (
    "%PY_CMD%" main.py search --keyword "%KEYWORD%" --limit 20 --export csv
)
echo.
pause
goto MENU

:SWITCH_ANDROID
if exist "%~dp0Chay_Tool_Android.bat" (
    call "%~dp0Chay_Tool_Android.bat"
)
goto MENU

:EXIT_TOOL
exit /b 0
