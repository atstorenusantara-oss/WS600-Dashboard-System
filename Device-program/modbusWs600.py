import math
import struct
import time
import sqlite3
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
import os
# Path database absolut ke folder root
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
        
        # Mapping parameter ke kolom database
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
def decode_float32_from_registers(
    reg_a: int,
    reg_b: int,
    byte_order: str = BYTE_ORDER,
    word_order: str = WORD_ORDER,
) -> float:
    if word_order == "big":
        words = [reg_a, reg_b]
    else:
        words = [reg_b, reg_a]

    packed = b""
    for word in words:
        packed += word.to_bytes(2, byteorder=byte_order, signed=False)

    return struct.unpack(">f" if byte_order == "big" else "<f", packed)[0]


def decode_dataset(values, byte_order: str, word_order: str):
    data = {}
    for i, field in enumerate(FIELDS):
        idx = i * 2
        val = decode_float32_from_registers(
            values[idx],
            values[idx + 1],
            byte_order=byte_order,
            word_order=word_order,
        )
        data[field] = round(val, 3)
    return data


def score_dataset(data):
    score = 0
    for field, value in data.items():
        if not math.isfinite(value):
            continue
        low, high = FIELD_RANGES[field]
        if low <= value <= high:
            score += 1
    return score


def pick_best_dataset(values):
    combos = [
        ("big", "big"),
        ("big", "little"),
        ("little", "big"),
        ("little", "little"),
    ]
    best = None
    best_score = -1
    for byte_order, word_order in combos:
        data = decode_dataset(values, byte_order, word_order)
        score = score_dataset(data)
        if score > best_score:
            best = (data, byte_order, word_order)
            best_score = score
    return best, best_score


def build_client():
    return ModbusSerialClient(
        port=PORT,
        baudrate=BAUDRATE,
        parity="N",
        stopbits=1,
        bytesize=8,
        timeout=2,
    )


def is_port_detected(port_name: str) -> bool:
    return any(p.device.upper() == port_name.upper() for p in list_ports.comports())


def close_client():
    global client
    if client is not None:
        try:
            client.close()
        except Exception:
            pass
    client = None


def ensure_connection() -> bool:
    global client

    if not is_port_detected(PORT):
        close_client()
        return False

    if client is None:
        client = build_client()

    try:
        if client.connect():
            return True
    except Exception:
        close_client()
        return False

    close_client()
    return False


# Initialize DB
init_db()

# ==============================
# KONEKSI MODBUS RTU
# ==============================
client = None
if ensure_connection():
    print("Terhubung ke WS-600\n")
else:
    print(f"Port {PORT} belum siap. Menunggu perangkat...\n")


# ==============================
# FUNGSI BACA SENSOR
# ==============================
def read_ws600():
    if not ensure_connection():
        return None

    try:
        result = client.read_holding_registers(
            address=START_ADDRESS,
            count=REGISTER_COUNT,
            device_id=SLAVE_ID,
        )
    except ModbusException as err:
        print(f"Gagal komunikasi Modbus: {err}")
        return None
    except (PermissionError, OSError) as err:
        print(f"USB/Serial terputus: {err}")
        close_client()
        return None
    except Exception as err:
        print(f"Error tidak terduga saat baca sensor: {err}")
        close_client()
        return None

    if result.isError():
        print(f"Gagal membaca register: {result}")
        return None

    if not hasattr(result, "registers") or len(result.registers) < REGISTER_COUNT:
        print(f"Data register tidak lengkap: {getattr(result, 'registers', None)}")
        return None

    values = result.registers

    if AUTO_DETECT_ENDIAN:
        picked, score = pick_best_dataset(values)
        data, byte_order_used, word_order_used = picked
        if score < 6:
            raw = ", ".join(f"{r:04X}" for r in values)
    else:
        data = decode_dataset(values, BYTE_ORDER, WORD_ORDER)

    return data


# =============================================
# LOOP PEMBACAAN
# =============================================
last_db_save = 0

try:
    while True:
        current_time = time.time()
        port_detected = is_port_detected(PORT)
        sensor_data = read_ws600()
        
        # Update system status in database
        update_status(port_detected, sensor_data is not None)
        
        if sensor_data:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ===== DATA WS-600 =====")
            for key, value in sensor_data.items():
                print(f"{key:25}: {value:.3f}")
            
            # Simpan ke Database setiap 10 detik
            if current_time - last_db_save >= DB_SAVE_INTERVAL:
                if save_to_db(sensor_data):
                    print("Status: Data berhasil disimpan ke SQLite.")
                    last_db_save = current_time
                else:
                    print("Status: Gagal menyimpan ke database.")
            
            print("========================================\n")
        else:
            if is_port_detected(PORT):
                print("Status: port terhubung, tapi belum ada respons data dari sensor.\n")
            else:
                print(f"Status: USB sensor tidak terdeteksi ({PORT}). Menunggu reconnect...\n")

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("Program dihentikan")

finally:
    close_client()
