@echo off
chcp 65001 >nul
title Khởi động Google Chrome Desktop (CDP 9222)

cd /d "%~dp0"

set "CHROME_EXE="
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if "%CHROME_EXE%"=="" (
    echo [!] Không tìm thấy Google Chrome trên máy tính.
    pause
    exit /b 1
)

echo [*] Đang khởi động Google Chrome kết nối Shopee qua cổng CDP 9222...
start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%~dp0data\profiles\desktop_chrome" https://shopee.vn
echo [✓] Đã mở Chrome thành công! Bạn có thể kiểm tra hoặc đăng nhập Shopee tại đây.
timeout /t 3 >nul
exit /b 0
