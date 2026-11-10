@echo off
chcp 65001 >nul
title Phục Kích Săn Voucher Khung Giờ Vàng (Sniper)

cd /d "%~dp0"
call "%~dp0_bootstrap.bat" || (pause & exit /b 1)

echo [*] Đang chuẩn bị phục kích khung giờ vàng gần nhất...
echo.
"%PY_CMD%" main.py vouchers --mode sniper --cdp 9222 --sniper-time auto
echo.
pause
