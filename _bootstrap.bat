@echo off
:: Shared Python bootstrap for every .bat launcher.
:: Creates .venv and installs requirements on first run, then exposes:
::   PY_CMD     - python executable to use
::   PYTHONPATH - project .venv site-packages
:: Call it as:  call "%~dp0_bootstrap.bat" || exit /b 1

set "PYTHONPATH=%~dp0.venv\Lib\site-packages;%PYTHONPATH%"
set "PY_CMD=%~dp0.venv\Scripts\python.exe"

if exist "%PY_CMD%" (
    "%PY_CMD%" -c "import ctypes" >nul 2>&1
    if not errorlevel 1 exit /b 0
)

where python >nul 2>&1
if not errorlevel 1 (
    python -c "import ctypes" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
        exit /b 0
    )
)

echo ======================================================================
echo   [*] PHAT HIEN LAN DAU KHOI CHAY HOAC MOI TRUONG CHUA CO SAN
echo   [*] Dang tu dong tao moi truong va cai dat thu vien can thiet...
echo   [*] Qua trinh nay chi dien ra 1 lan duy nhat. Vui long doi...
echo ======================================================================
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] May tinh chua cai dat Python hoac chua them vao bien moi truong PATH!
    echo Vui long cai dat Python 3.10+ va tich vao Add Python to PATH.
    exit /b 1
)

python -m venv "%~dp0.venv"
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [LOI] Cai dat thu vien that bai! Vui long kiem tra ket noi mang.
    exit /b 1
)

echo [*] Thiet lap moi truong hoan tat!
timeout /t 2 >nul
set "PY_CMD=%~dp0.venv\Scripts\python.exe"
exit /b 0
