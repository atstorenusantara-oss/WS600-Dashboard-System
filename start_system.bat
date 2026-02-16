@echo off
TITLE WS600 System Runner
echo ======================================================
echo    MENJALANKAN SISTEM INSALUSI WEATHER STATION
echo ======================================================
echo.

:: 1. Jalankan Program Sensor di window baru
echo [*] Menjalankan Service Sensor (modbusWs600.py)...
start "WS600_SENSOR_SERVICE" cmd /k "python modbusWs600.py"

:: 2. Jalankan Dashboard Web di window baru
echo [*] Menjalankan Dashboard Dashboard (FastAPI)...
cd Device-program\dashboard
start "WS600_WEB_DASHBOARD" cmd /k "python main.py"

echo.
echo [*] Menunggu sistem siap...
timeout /t 5 /nobreak >nul

:: 3. Buka browser otomatis
echo [*] Membuka Dashboard di Browser...
start http://localhost:8000

echo.
echo ======================================================
echo    SISTEM BERHASIL DIJALANKAN
echo    Jangan tutup jendela terminal yang baru terbuka!
echo ======================================================
echo.
pause
