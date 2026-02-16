# Panduan Instalasi Offline - WS600 Dashboard System

Dokumen ini berisi langkah-langkah untuk menginstal seluruh sistem WS600 ke komputer target yang **tidak memiliki koneksi internet**.

## 1. Persiapan File
Pastikan folder `offline_installer` ini sudah berisi:
*   Folder `python_packages/` (Berisi file .whl untuk library Python)
*   File `requirements_offline.txt`
*   Source code program (`modbusWs600.py` dan folder `Device-program/`)

## 2. Instalasi Python
1.  Unduh installer **Python 3.12 (Windows x86-64 executable installer)** dari PC lain.
2.  Instal di komputer target. **PENTING:** Centang opsi **"Add Python to PATH"** saat awal instalasi.

## 3. Instalasi Library Python secara Offline
Buka Terminal/PowerShell di komputer target, masuk ke folder ini, lalu jalankan:

```powershell
pip install --no-index --find-links=python_packages -r requirements_offline.txt
```

Perintah ini akan menginstal FastAPI, Pandas, Pymodbus, dll menggunakan file yang sudah disediakan di folder `python_packages` tanpa memerlukan internet.

## 4. Konfigurasi Dashboard Offline
Dashboard sudah dimodifikasi untuk menggunakan library lokal. Tidak ada langkah tambahan untuk bagian ini.

## 5. Menjalankan Sistem
1.  **Jalankan Interface Sensor**:
    ```powershell
    python modbusWs600.py
    ```
2.  **Jalankan Dashboard (Web)**:
    Buka terminal baru, masuk ke folder `Device-program/dashboard/`:
    ```powershell
    python main.py
    ```
3.  Buka Browser di alamat: `http://localhost:8000`

---
**Catatan:** Pastikan driver USB-to-RS485 (seperti CH340 atau CP2102) sudah terinstal di komputer target agar COM Port bisa terdeteksi.
