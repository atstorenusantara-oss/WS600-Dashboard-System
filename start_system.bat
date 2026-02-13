@echo off
title WS600 System Launcher
echo ==========================================
echo    WS600 Weather Station System
echo ==========================================
echo.
echo Launching Sensor Collector and Dashboard...
echo.

:: Launch Sensor Collector in a new window
echo [DONE] Launching Sensor Collector...
start "WS600 Sensor Collector" cmd /c "run_sensor.bat"

:: Wait a bit for the sensor to initialize
timeout /t 2 /nobreak >nul

:: Launch Dashboard in a new window
echo [DONE] Launching Dashboard...
start "WS600 Dashboard" cmd /c "run_dashboard.bat"

echo.
echo Both components are now running in separate windows.
echo You can close this launcher window.
echo ==========================================
timeout /t 5
exit
