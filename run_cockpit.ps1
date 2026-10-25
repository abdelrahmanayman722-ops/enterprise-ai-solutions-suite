<#
.SYNOPSIS
    Global Revenue Engine - Windows PowerShell One-Click Launcher
.DESCRIPTION
    Launches the Executive Pipeline Cockpit web server (FastAPI) and opens
    the command center in the default system browser.
.AUTHOR
    Eng. Abdelrahman Rashad
#>

[CmdletBinding()]
param()

$Host.UI.RawUI.WindowTitle = "Global Revenue Engine - Executive Cockpit"
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   GLOBAL REVENUE ENGINE - EXECUTIVE PIPELINE COCKPIT" -ForegroundColor Green
Write-Host "   Author: Eng. Abdelrahman Rashad" -ForegroundColor Yellow
Write-Host "   Engine: FastAPI REST Server + Real-Time Kanban UI" -ForegroundColor White
Write-Host "   Target: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# Verify Python Availability
$pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python 3 was not detected in your system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/ and retry." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

$pyVersion = & python --version 2>&1
Write-Host "[*] Detected Python runtime: $pyVersion" -ForegroundColor Gray

# Verify Python Dependencies
Write-Host "[*] Checking Python dependencies..." -ForegroundColor Gray
$depsCheck = & python -c "import fastapi, uvicorn, pydantic, requests, httpx" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Missing dependencies detected. Installing via requirements.txt..." -ForegroundColor Yellow
    & python -m pip install -r "$PSScriptRoot\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Dependency installation failed. Please run 'pip install -r requirements.txt' manually." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}
Write-Host "[+] All dependencies satisfied." -ForegroundColor Green

# Open Cockpit in default browser
Write-Host "[*] Launching Cockpit UI in default web browser..." -ForegroundColor Cyan
Start-Process "http://127.0.0.1:8000"

# Start FastAPI Uvicorn Server
Write-Host "[*] Starting FastAPI Server on port 8000..." -ForegroundColor Green
Write-Host "[*] Press Ctrl+C in this console to stop the server." -ForegroundColor Yellow
Write-Host ""

try {
    & python "$PSScriptRoot\cockpit\server.py"
} catch {
    Write-Host "[!] An unexpected error occurred: $_" -ForegroundColor Red
} finally {
    Write-Host "`n[*] Cockpit session ended." -ForegroundColor Gray
}
