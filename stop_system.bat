@echo off
title WS600 System Stopper
echo ==========================================
echo    Stopping WS600 Weather Station System
echo ==========================================
echo.

echo [1/2] Stopping Dashboard (Port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)

echo [2/2] Stopping all Python processes...
taskkill /F /IM python.exe /T 2>nul

echo.
echo ==========================================
echo    System stopped successfully.
echo ==========================================
timeout /t 3
exit
