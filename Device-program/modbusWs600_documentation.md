# Dokumentasi Script modbusWs600.py

## Deskripsi Umum
Script `modbusWs600.py` adalah aplikasi Python yang berfungsi untuk membaca data meteorologi dari sensor Weather Station **WS-600** menggunakan protokol **Modbus RTU** melalui koneksi Serial (RS485). Script ini dirancang dengan fitur deteksi otomatis *endianness* (urutan byte/word) dan manajemen koneksi yang tangguh.

## Fitur Utama
- **Modbus RTU over Serial**: Komunikasi standar dengan sensor industri.
- **Auto-Detect Endianness**: Otomatis mendeteksi urutan byte dan word yang paling valid dari 4 kombinasi yang mungkin.
- **Validasi Data**: Memeriksa apakah data yang diterima masuk akal berdasarkan rentang nilai (`FIELD_RANGES`).
- **Robust Connection Management**: Otomatis mendeteksi jika USB dicabut/terputus dan mencoba menghubungkan kembali.
- **Support Data Float 32-bit**: Mengonversi dua register 16-bit menjadi satu nilai float 32-bit.

## Kebutuhan Sistem
### Library Python
Anda perlu menginstal library berikut:
```bash
pip install pymodbus pyserial
```

## Konfigurasi
Konfigurasi utama terdapat di bagian awal script:
- `PORT`: Nama port serial (contoh: `"COM21"` di Windows atau `"/dev/ttyUSB0"` di Linux).
- `BAUDRATE`: Kecepatan transmisi (default: `9600`).
- `SLAVE_ID`: ID Modbus perangkat (default: `1`).
- `REGISTER_COUNT`: Jumlah register yang dibaca (18 register untuk 9 parameter meteorologi).

## Parameter yang Dibaca
Script ini membaca 9 parameter utama:
1. Wind Speed (m/s)
2. Wind Direction (deg)
3. Temperature (degC)
4. Humidity (%)
5. Pressure (hPa)
6. Minute Rain (mm)
7. Hour Rain (mm)
8. Day Rain (mm)
9. Total Rain (mm)

## Penjelasan Logika Program

### 1. Deteksi Endianness Otomatis (`pick_best_dataset`)
Setiap produsen sensor Modbus mungkin menggunakan urutan byte yang berbeda untuk data float. Script mencoba 4 kombinasi:
- `big-endian` (Byte) & `big-endian` (Word)
- `big-endian` (Byte) & `little-endian` (Word)
- `little-endian` (Byte) & `big-endian` (Word)
- `little-endian` (Byte) & `little-endian` (Word)

Kombinasi yang menghasilkan nilai paling masuk akal (berdasarkan `FIELD_RANGES`) akan dipilih secara otomatis jika `AUTO_DETECT_ENDIAN = True`.

### 2. Validasi Data (`score_dataset`)
Setiap nilai yang dibaca dibandingkan dengan rentang nilai fisik yang valid. Misalnya, suhu diperiksa apakah berada di antara -60°C hingga 80°C. Skor diberikan berdasarkan jumlah nilai yang valid.

### 3. Manajemen Koneksi (`ensure_connection`)
Program melakukan pengecekan port serial secara berkala. Jika port tidak ditemukan atau komunikasi gagal, program akan menutup client dan mencoba melakukan inisialisasi ulang pada iterasi berikutnya.

## Cara Penggunaan
1. Pastikan sensor WS-600 terhubung ke komputer melalui adapter RS485 ke USB.
2. Sesuaikan nilai `PORT` di dalam script.
3. Jalankan script:
   ```bash
   python modbusWs600.py
   ```
4. Data akan ditampilkan di terminal setiap beberapa detik.

## Penanganan Error
- **ModbusException**: Terjadi jika ada kesalahan protokol Modbus.
- **PermissionError/OSError**: Terjadi jika USB/Serial dicabut secara fisik saat program berjalan.
- **Data Register Tidak Lengkap**: Terjadi jika respons dari sensor tidak sesuai dengan jumlah register yang diminta.
