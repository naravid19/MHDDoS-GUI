@echo off
:: ==============================================================================
:: MHDDoS-GUI - Advanced Installer for Windows (v1.6.4)
:: ==============================================================================
title MHDDoS-GUI Professional Installer
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Console colors
set "ESC="
set "G=%ESC%[92m"
set "Y=%ESC%[93m"
set "R=%ESC%[91m"
set "B=%ESC%[96m"
set "W=%ESC%[97m"
set "M=%ESC%[95m"
set "X=%ESC%[0m"
set "BOLD=%ESC%[1m"

echo %BOLD%%M%
echo ╔══════════════════════════════════════════════════════════╗
echo ║          MHDDoS-GUI Professional Installer               ║
echo ║                    v1.6.4 (Windows)                      ║
echo ╚══════════════════════════════════════════════════════════╝%X%
echo.

:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
:: Step 1: Pre-flight Checks
:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo %BOLD%%W%[*] Checking Pre-requisites...%X%

:: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo %R%[ERROR] Python is not installed or not in your PATH. Please install Python 3.11+.%X%
    pause
    exit /b 1
)

:: Verify Python version >= 3.11
python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"
if %errorlevel% neq 0 (
    echo %R%[ERROR] Python version 3.11+ is required. Found:%X%
    python --version
    pause
    exit /b 1
)
echo %G%[ok] Python 3.11+ detected.%X%

:: Check Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo %Y%[WARNING] Git is not installed. Git dependency check might fail for PyRoxy.%X%
) else (
    echo %G%[ok] Git detected.%X%
)

:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
:: Step 2: Virtual Environment Setup
:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo %BOLD%%W%[*] Setting up Python Virtual Environment (.venv)...%X%
if not exist .venv (
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo %R%[ERROR] Failed to create virtual environment.%X%
        pause
        exit /b 1
    )
    echo %G%[ok] Virtual environment created successfully.%X%
) else (
    echo %G%[ok] Existing virtual environment found.%X%
)

:: Activate Virtual Environment
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo %R%[ERROR] Failed to activate virtual environment.%X%
    pause
    exit /b 1
)
echo %G%[ok] Virtual environment activated.%X%

:: Upgrade Pip
echo [*] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
:: Step 3: Package Installations
:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo %BOLD%%W%[*] Installing requirements from requirements.txt...%X%
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo %R%[ERROR] Failed to install standard python requirements.%X%
    pause
    exit /b 1
)
echo %G%[ok] Core packages installed.%X%

:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
:: Step 4: Local Resource Setup (Camoufox & Browser Engines)
:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo %BOLD%%W%[*] Configuring advanced browser engines...%X%

:: Local Camoufox installation
if exist "resource\camoufox\pythonlib" (
    echo [*] Installing local Camoufox resource from resource\camoufox\pythonlib...
    pip install -e "resource\camoufox\pythonlib[geoip]"
    if !errorlevel! neq 0 (
        echo %R%[ERROR] Local Camoufox installation failed.%X%
        pause
        exit /b 1
    )
    echo %G%[ok] Local Camoufox package configured.%X%
) else (
    echo %Y%[WARNING] Local Camoufox path "resource\camoufox\pythonlib" not found. Installing from Pip...%X%
    pip install "camoufox[geoip]>=0.5.2"
)

:: Download Camoufox Browser binary
echo [*] Fetching Camoufox anti-detect browser binaries...
python -m camoufox fetch
if %errorlevel% neq 0 (
    echo %R%[ERROR] Failed to download Camoufox browser binaries.%X%
    pause
    exit /b 1
)
echo %G%[ok] Camoufox browser binaries downloaded.%X%

:: Download Playwright Chromium binary
echo [*] Fetching Playwright Chromium binaries...
playwright install chromium
if %errorlevel% neq 0 (
    echo %R%[ERROR] Failed to download Playwright Chromium.%X%
    pause
    exit /b 1
)
echo %G%[ok] Playwright Chromium binaries downloaded.%X%

:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
:: Step 5: Verification & Launch Guide
:: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo %BOLD%%G%╔══════════════════════════════════════════════════════════╗
echo ║         INSTALLATION COMPLETED SUCCESSFULLY!             ║
echo ╚══════════════════════════════════════════════════════════╝%X%
echo.
echo   To launch the application:
echo.
echo   %BOLD%%B%1. Web Dashboard (Recommended):%X%
echo      python web_gui.py --force
echo.
echo   %BOLD%%B%2. Standalone Desktop GUI:%X%
echo      python desktop_gui.py
echo.
echo   %BOLD%%B%3. Distributed Worker Node:%X%
echo      python worker.py --master http://YOUR_MASTER_IP:8000 --token SECRET
echo.
echo %BOLD%%Y%[Note]%X% Keep this virtual environment activated by running %BOLD%call .venv\Scripts\activate.bat%X% in your terminal before launching commands.
echo.
pause
