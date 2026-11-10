@echo off
chcp 65001 >nul
title Shopee Voucher Auto-Pilot 24/7

cd /d "%~dp0"
call "%~dp0_bootstrap.bat" || (pause & exit /b 1)

echo ======================================================================
echo    SHOPEE AUTO-PILOT 24/7 - TỰ ĐỘNG SĂN VOUCHER MỌI KHUNG GIỜ VÀNG
echo ======================================================================
echo.
echo [*] Đang kết nối vào Google Chrome và kích hoạt hệ thống săn 24/7...
echo [*] Tự động canh giờ: 00:00 - 09:00 - 12:00 - 15:00 - 18:00 - 21:00
echo.

"%PY_CMD%" main.py vouchers --mode auto --cdp 9222

echo.
echo [*] Tiến trình đã dừng lại.
pause
