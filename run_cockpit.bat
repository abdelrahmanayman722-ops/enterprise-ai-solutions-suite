@echo off
setlocal enabledelayedexpansion

title Global Revenue Engine - Executive Cockpit
cd /d "%~dp0"

echo ========================================================================
echo   GLOBAL REVENUE ENGINE - EXECUTIVE PIPELINE COCKPIT
echo   Author: Eng. Abdelrahman Rashad
echo   Architecture: FastAPI REST Backend + Real-Time Kanban UI
echo ========================================================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3 is not found in your system PATH.
    echo Please install Python 3.10+ and ensure "Add python.exe to PATH" is checked.
    echo.
    pause
    exit /b 1
)

echo [*] Checking dependencies...
python -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Missing core dependencies. Installing requirements from requirements.txt...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo [*] Launching Executive Cockpit Web Interface...
start "" "http://127.0.0.1:8000"

echo [*] Initializing FastAPI Server on port 8000...
echo [*] Press Ctrl+C to terminate the server.
echo.
python cockpit/server.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Server exited with code %ERRORLEVEL%.
    pause
)
