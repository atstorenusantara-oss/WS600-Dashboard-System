@echo off
title WS600 Weather Station Dashboard
echo ==========================================
echo    Starting WS600 Weather Dashboard...
echo ==========================================
echo.

:: Change to the dashboard directory
cd /d "%~dp0Device-program\dashboard"

:: Check for python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python.
    pause
    exit /b
)

:: Check/Install dependencies
echo Checking dependencies...
python -c "import fastapi, uvicorn, pydantic" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing required libraries...
    pip install fastapi uvicorn pydantic
)

echo.
echo Dashboard is starting...
echo URL: http://localhost:8000
echo.
echo Press Ctrl+C to stop the dashboard.
echo ==========================================
echo.

:: Run the dashboard
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dashboard failed to start or crashed.
    pause
)

pause
