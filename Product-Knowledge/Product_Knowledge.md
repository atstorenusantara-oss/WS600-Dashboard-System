# PRODUK KNOWLEDGE: WS600 DASHBOARD MONITORING SYSTEM

## 1. Deskripsi Produk
WS600 Dashboard Monitoring System adalah solusi pemantauan cuaca dan kualitas udara (AQMS) yang dirancang untuk memberikan data meteorologi secara real-time dan akurat. Sistem ini mengintegrasikan sensor profesional WS-600 dengan antarmuka dashboard digital yang modern, interaktif, dan mudah digunakan.

## 2. Fitur Unggulan
- **Real-Time Data Acquisition**: Membaca data dari sensor secara kontinu menggunakan protokol Modbus RTU.
- **Auto-Detect Endianness**: Teknologi pintar yang secara otomatis mendeteksi konfigurasi urutan byte sensor, memudahkan instalasi tanpa kalibrasi manual yang rumit.
- **Dynamic Dashboard**: Antarmuka berbasis web yang menampilkan grafik tren, nilai instan, dan analisis statistik secara visual.
- **Wind Rose Analysis**: Visualisasi arah dan kecepatan angin yang mendalam untuk analisis pola udara dan distribusi angin.
- **Robust Connectivity**: Fitur pemulihan koneksi otomatis jika kabel sensor atau USB terlepas, memastikan integritas data tetap terjaga.
- **Automated Export**: Kemampuan ekspor laporan dalam format Excel dan PDF langsung ke USB Flash Drive atau penyimpanan lokal.

## 3. Parameter yang Dipantau
Sistem ini memantau 9 parameter meteorologi utama dari sensor WS-600:
1. **Kecepatan Angin (Wind Speed)**: Satuan m/s
2. **Arah Angin (Wind Direction)**: Satuan Derajat (°)
3. **Temperatur (Temperature)**: Satuan °C
4. **Kelembapan Udara (Humidity)**: Satuan %
5. **Tekanan Udara (Pressure)**: Satuan hPa
6. **Curah Hujan Menit (Minute Rain)**: Satuan mm
7. **Curah Hujan Jam (Hour Rain)**: Satuan mm
8. **Curah Hujan Harian (Day Rain)**: Satuan mm
9. **Total Curah Hujan (Total Rain)**: Satuan mm

## 4. Spesifikasi Teknis
- **Hardware Pendukung**: Sensor WS-600, RS485 to USB Converter, Host PC (Mini PC/Laptop).
- **Backend**: Python 3.x (FastAPI, Pymodbus, Pandas).
- **Frontend**: Dashboard berbasis web (HTML5, CSS3, JavaScript).
- **Database**: SQLite untuk penyimpanan data jangka panjang yang ringan dan efisien.

## 5. Cara Pengoperasian
1. Pastikan Sensor WS-600 terhubung ke USB Port melalui konverter RS485.
2. Jalankan file `start_system.bat` di direktori utama.
3. Dashboard akan terbuka secara otomatis di browser default.
4. Data akan mulai masuk dan tercatat di database secara otomatis.
5. Gunakan menu **Export** pada dashboard untuk mengunduh laporan ke USB atau penyimpanan lokal.
