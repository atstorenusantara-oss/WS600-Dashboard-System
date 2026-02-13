@echo off
title WS600 Sensor Collector
echo ==========================================
echo    Starting WS600 Sensor Collector...
echo ==========================================
echo.

:: Change to the device program directory
cd /d "%~dp0Device-program"

:: Check for python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python.
    pause
    exit /b
)

:: Check/Install dependencies
echo Checking dependencies...
python -c "import pymodbus, serial" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing required libraries...
    pip install pymodbus pyserial
)

echo.
echo Sensor monitoring is starting...
echo Press Ctrl+C to stop.
echo ==========================================
echo.

:: Run the sensor script
python modbusWs600.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Sensor script failed to start or crashed.
    pause
)

pause
