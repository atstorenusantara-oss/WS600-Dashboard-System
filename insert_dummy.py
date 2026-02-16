import sqlite3
import os
import random
from datetime import datetime, timedelta

# Path ke database
DB_PATH = r"D:\Produk INsalusi\AQMS\WS600\WS600-Dashboard-System\ws600_data.db"

def insert_dummy_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"Mengisi data dummy ke: {DB_PATH}")

        # 1. Pastikan tabel ada (sama dengan struktur di main.py)
        cursor.execute('''CREATE TABLE IF NOT EXISTS weather_data (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME, wind_speed REAL, wind_direction REAL, temperature REAL, humidity REAL, pressure REAL, rain_minute REAL, rain_hour REAL, rain_day REAL, rain_total REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS weather_live (id INTEGER PRIMARY KEY, timestamp DATETIME, wind_speed REAL, wind_direction REAL, temperature REAL, humidity REAL, pressure REAL, rain_total REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_status (id INTEGER PRIMARY KEY, port_connected INTEGER, sensor_responding INTEGER, last_check DATETIME)''')

        # 2. Isi data Historis (untuk Log) - 20 data terakhir
        now = datetime.now()
        for i in range(20):
            timestamp = (now - timedelta(minutes=i*2)).strftime("%Y-%m-%d %H:%M:%S")
            wind_speed = round(random.uniform(0.5, 5.0), 2)
            wind_dir = round(random.uniform(0, 360), 0)
            temp = round(random.uniform(25.0, 32.0), 1)
            hum = round(random.uniform(60.0, 85.0), 0)
            pres = round(random.uniform(1005.0, 1012.0), 1)
            rain = round(random.uniform(0, 10), 2)
            
            cursor.execute('''
                INSERT INTO weather_data (timestamp, wind_speed, wind_direction, temperature, humidity, pressure, rain_minute, rain_hour, rain_day, rain_total) 
                VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?)
            ''', (timestamp, wind_speed, wind_dir, temp, hum, pres, rain, rain))

        # 3. Isi data Live (untuk Card utama)
        cursor.execute('''
            INSERT OR REPLACE INTO weather_live (id, timestamp, wind_speed, wind_direction, temperature, humidity, pressure, rain_total)
            VALUES (1, ?, 2.5, 180.0, 28.5, 75.0, 1010.0, 15.2)
        ''', (now.strftime("%Y-%m-%d %H:%M:%S"),))

        # 4. Isi status sistem (Agar dot berwarna hijau/aktif)
        cursor.execute('''
            INSERT OR REPLACE INTO system_status (id, port_connected, sensor_responding, last_check)
            VALUES (1, 1, 1, ?)
        ''', (now.strftime("%Y-%m-%d %H:%M:%S"),))

        conn.commit()
        conn.close()
        print("✅ Berhasil: Data dummy telah dimasukkan dan tabel telah siap.")
        return True
    except Exception as e:
        print(f"❌ Gagal: {e}")
        return False

if __name__ == "__main__":
    insert_dummy_data()
