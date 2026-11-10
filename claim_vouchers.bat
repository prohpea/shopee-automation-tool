@echo off
chcp 65001 >nul
title Quét Và Lưu Nhanh Voucher Shopee

cd /d "%~dp0"
call "%~dp0_bootstrap.bat" || (pause & exit /b 1)

echo [*] Đang quét và tự động bấm Lưu tất cả voucher hiện có...
echo.
"%PY_CMD%" main.py vouchers --mode fast --cdp 9222
echo.
pause
