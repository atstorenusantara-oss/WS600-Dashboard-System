import math
import struct
import time
import sqlite3
import os
from datetime import datetime

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from serial.tools import list_ports

# ==============================
# KONFIGURASI
# ==============================
PORT = "COM21"          # Ganti sesuai port (Linux: '/dev/ttyUSB0')
BAUDRATE = 9600
SLAVE_ID = 1           # Ganti sesuai ID sensor
START_ADDRESS = 0      # 40001 biasanya address 0 di Modbus
REGISTER_COUNT = 18    # Total 18 register (40001-40018), tanpa radiasi
BYTE_ORDER = "big"     # "big" atau "little" untuk urutan byte dalam register 16-bit
WORD_ORDER = "big"     # "big" atau "little" untuk urutan pasangan register float 32-bit
AUTO_DETECT_ENDIAN = True
READ_INTERVAL = 2      # detik (untuk tampil di terminal)
DB_SAVE_INTERVAL = 10  # detik (untuk simpan ke database)

# Path database absolut ke folder root
# Karena file ini di Device-program/, maka database ada di ../ws600_data.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.abspath(os.path.join(BASE_DIR, "..", "ws600_data.db"))

FIELDS = [
    "Wind Speed (m/s)",
    "Wind Direction (deg)",
    "Temperature (degC)",
    "Humidity (%)",
    "Pressure (hPa)",
    "Minute Rain (mm)",
    "Hour Rain (mm)",
    "Day Rain (mm)",
    "Total Rain (mm)",
]

FIELD_RANGES = {
    "Wind Speed (m/s)": (0.0, 80.0),
    "Wind Direction (deg)": (0.0, 360.0),
    "Temperature (degC)": (-60.0, 80.0),
    "Humidity (%)": (0.0, 100.0),
    "Pressure (hPa)": (800.0, 1200.0),
    "Minute Rain (mm)": (0.0, 200.0),
    "Hour Rain (mm)": (0.0, 400.0),
    "Day Rain (mm)": (0.0, 1000.0),
    "Total Rain (mm)": (0.0, 20000.0),
}

# ==============================
# DATABASE FUNCTIONS
# ==============================
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                wind_speed REAL,
                wind_direction REAL,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                rain_minute REAL,
                rain_hour REAL,
                rain_day REAL,
                rain_total REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather_live (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME,
                wind_speed REAL,
                wind_direction REAL,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                rain_total REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_status (
                id INTEGER PRIMARY KEY,
                port_connected INTEGER,
                sensor_responding INTEGER,
                last_check DATETIME
            )
        ''')
        # Initialize first row if empty
        cursor.execute("INSERT OR IGNORE INTO system_status (id, port_connected, sensor_responding, last_check) VALUES (1, 0, 0, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error init_db: {e}")

def update_live_data(data):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        query = '''
            INSERT OR REPLACE INTO weather_live (
                id, timestamp, wind_speed, wind_direction, 
                temperature, humidity, pressure, rain_total
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        '''
        values = (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data["Wind Speed (m/s)"],
            data["Wind Direction (deg)"],
            data["Temperature (degC)"],
            data["Humidity (%)"],
            data["Pressure (hPa)"],
            data["Total Rain (mm)"]
        )
        cursor.execute(query, values)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Gagal update live data: {e}")

def update_status(port_ok, sensor_ok):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE system_status 
            SET port_connected = ?, sensor_responding = ?, last_check = ?
            WHERE id = 1
        ''', (1 if port_ok else 0, 1 if sensor_ok else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Gagal update status: {e}")

def save_to_db(data):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        query = '''
            INSERT INTO weather_data (
                timestamp, wind_speed, wind_direction, temperature, 
                humidity, pressure, rain_minute, rain_hour, rain_day, rain_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        values = (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data["Wind Speed (m/s)"],
            data["Wind Direction (deg)"],
            data["Temperature (degC)"],
            data["Humidity (%)"],
            data["Pressure (hPa)"],
            data["Minute Rain (mm)"],
            data["Hour Rain (mm)"],
            data["Day Rain (mm)"],
            data["Total Rain (mm)"]
        )
        
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Gagal menyimpan ke database: {e}")
        return False

# ==============================
# MODBUS FUNCTIONS
# ==============================
def decode_float32_from_registers(reg_a, reg_b, byte_order=BYTE_ORDER, word_order=WORD_ORDER):
    if word_order == "big":
        words = [reg_a, reg_b]
    else:
        words = [reg_b, reg_a]
    packed = b""
    for word in words:
        packed += word.to_bytes(2, byteorder=byte_order, signed=False)
    return struct.unpack(">f" if byte_order == "big" else "<f", packed)[0]

def decode_dataset(values, byte_order, word_order):
    data = {}
    for i, field in enumerate(FIELDS):
        idx = i * 2
        val = decode_float32_from_registers(values[idx], values[idx + 1], byte_order=byte_order, word_order=word_order)
        data[field] = round(val, 3)
    return data

def score_dataset(data):
    score = 0
    for field, value in data.items():
        if not math.isfinite(value): continue
        low, high = FIELD_RANGES[field]
        if low <= value <= high: score += 1
    return score

def pick_best_dataset(values):
    combos = [("big", "big"), ("big", "little"), ("little", "big"), ("little", "little")]
    best, best_score = None, -1
    for byte_order, word_order in combos:
        data = decode_dataset(values, byte_order, word_order)
        score = score_dataset(data)
        if score > best_score:
            best = (data, byte_order, word_order)
            best_score = score
    return best, best_score

def build_client():
    return ModbusSerialClient(port=PORT, baudrate=BAUDRATE, parity="N", stopbits=1, bytesize=8, timeout=2)

def is_port_detected(port_name):
    return any(p.device.upper() == port_name.upper() for p in list_ports.comports())

def close_client():
    global client
    if client is not None:
        try: client.close()
        except: pass
    client = None

def ensure_connection():
    global client
    if not is_port_detected(PORT):
        close_client()
        return False
    if client is None:
        client = build_client()
    try:
        if client.connect(): return True
    except:
        close_client()
        return False
    close_client()
    return False

# ==============================
# MAIN SCRIPT
# ==============================
init_db()
client = None

def read_ws600():
    if not ensure_connection(): return None
    try:
        # Pymodbus version in this environment uses 'device_id' as keyword-only argument
        result = client.read_holding_registers(address=START_ADDRESS, count=REGISTER_COUNT, device_id=SLAVE_ID)
        if result.isError(): return None
        if not hasattr(result, "registers") or len(result.registers) < REGISTER_COUNT: return None
        picked, _ = pick_best_dataset(result.registers)
        return picked[0]
    except Exception as e:
        print(f"Error baca sensor: {e}")
        close_client()
        return None

last_db_save = 0
print(f"Memulai monitoring WS-600 pada {PORT}...")

try:
    while True:
        current_time = time.time()
        port_detected = is_port_detected(PORT)
        sensor_data = read_ws600()
        
        # UPDATE STATUS KE DATABASE
        update_status(port_detected, sensor_data is not None)
        
        if sensor_data:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Data diterima.")
            
            # Update data live setiap 2 detik (Real-time di Dashboard)
            update_live_data(sensor_data)
            
            # Simpan ke Database Historis setiap 10 detik
            if current_time - last_db_save >= DB_SAVE_INTERVAL:
                if save_to_db(sensor_data):
                    last_db_save = current_time
        else:
            if port_detected:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Cek Wiring Sensor")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Cek USB TTL")

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("Berhenti.")
finally:
    close_client()
