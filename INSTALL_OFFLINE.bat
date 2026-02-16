@echo off
TITLE Instalasi Offline WS600 Weather Station
echo ======================================================
echo    INSTALASI OFFLINE - INSALUSI WEATHER STATION
echo ======================================================
echo.

:: 1. Cek apakah Python sudah terinstal
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan! 
    echo Silakan instal Python 3.12 terlebih dahulu dari folder installer.
    echo Pastikan centang "Add Python to PATH" saat instalasi.
    pause
    exit /b
)

echo [*] Python terdeteksi. Memulai instalasi library...
echo.

:: 2. Jalankan instalasi pip secara offline
pip install --no-index --find-links=offline_installer\python_packages -r requirements_offline.txt

if %errorlevel% equ 0 (
    echo.
    echo ======================================================
    echo    BERHASIL: Semua library telah terinstal!
    echo ======================================================
    echo Anda sekarang bisa menjalankan sistem menggunakan START_SYSTEM.bat
) else (
    echo.
    echo [ERROR] Terjadi kesalahan saat instalasi.
    echo Cek apakah ada program Python lain yang sedang berjalan.
)

echo.
pause
