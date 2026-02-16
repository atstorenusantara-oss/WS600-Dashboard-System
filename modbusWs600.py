import math
import struct
import time
import sqlite3
from datetime import datetime

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from serial.tools import list_ports

# ==============================
# KONFIGURASI DEFAULT (Akan diupdate dari Database)
# ==============================
PORT = "COM11"          
BAUDRATE = 9600         
SLAVE_ID = 1           
START_ADDRESS = 0      
REGISTER_COUNT = 18    
BYTE_ORDER = "big"     
WORD_ORDER = "big"     
AUTO_DETECT_ENDIAN = True
READ_INTERVAL = 2.0    # sampling aman (2 detik)
DB_SAVE_INTERVAL = 10  
DB_NAME = "ws600_data.db"
CHECK_SETTINGS_INTERVAL = 5 # Cek perubahan setting setiap 5 detik

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
    # 1. Tabel Histori (Log berkala)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            wind_speed REAL, wind_direction REAL, temperature REAL,
            humidity REAL, pressure REAL, rain_minute REAL,
            rain_hour REAL, rain_day REAL, rain_total REAL
        )
    ''')
    # 2. Tabel LIVE (Data Terkini untuk Dashboard)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_live (
            id INTEGER PRIMARY KEY,
            timestamp DATETIME,
            wind_speed REAL, wind_direction REAL, temperature REAL,
            humidity REAL, pressure REAL, rain_total REAL
        )
    ''')
    # 3. Tabel STATUS SISTEM
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY,
            port_connected INTEGER,
            sensor_responding INTEGER, 
            last_check DATETIME
        )
    ''')
    # 4. Tabel Pengaturan
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY,
            poll_interval REAL DEFAULT 2.0,
            save_interval INTEGER DEFAULT 10,
            com_port TEXT DEFAULT 'COM11',
            baudrate INTEGER DEFAULT 9600
        )
    ''')
    
    # Isi default jika kosong
    cursor.execute("SELECT COUNT(*) FROM system_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO system_settings (id, com_port, baudrate, poll_interval) VALUES (1, 'COM11', 9600, 2.0)")
    
    conn.commit()
    conn.close()

def load_settings():
    global PORT, BAUDRATE, READ_INTERVAL, DB_SAVE_INTERVAL
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT com_port, baudrate, poll_interval, save_interval FROM system_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            new_port, new_baud, new_poll, new_save = row
            changed = (PORT != new_port or BAUDRATE != new_baud)
            PORT, BAUDRATE, READ_INTERVAL, DB_SAVE_INTERVAL = new_port, new_baud, new_poll, new_save
            return changed
    except Exception as e:
        print(f"Gagal memuat pengaturan: {e}")
    return False

def update_live_data(data, port_ok, sensor_ok):
    """Update tabel LIVE dan STATUS secepat mungkin (Non-blocking I/O)"""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=1) # Timeout cepat agar tidak nge-lag
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update Status Sistem
        cursor.execute('''
            INSERT OR REPLACE INTO system_status (id, port_connected, sensor_responding, last_check)
            VALUES (1, ?, ?, ?)
        ''', (1 if port_ok else 0, 1 if sensor_ok else 0, now_str))
        
        # Update Data Live (Jika ada data)
        if data:
            cursor.execute('''
                INSERT OR REPLACE INTO weather_live (
                    id, timestamp, wind_speed, wind_direction, temperature, 
                    humidity, pressure, rain_total
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                now_str, data["Wind Speed (m/s)"], data["Wind Direction (deg)"],
                data["Temperature (degC)"], data["Humidity (%)"], data["Pressure (hPa)"],
                data["Total Rain (mm)"]
            ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        # Jangan gunakan print biasa di loop cepat jika error terus menerus
        pass

def save_to_history(data):
    """Penyimpanan ke tabel histori (dilakukan berkala)"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        query = '''
            INSERT INTO weather_data (
                timestamp, wind_speed, wind_direction, temperature, 
                humidity, pressure, rain_minute, rain_hour, rain_day, rain_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        values = (
            now_str, data["Wind Speed (m/s)"], data["Wind Direction (deg)"],
            data["Temperature (degC)"], data["Humidity (%)"], data["Pressure (hPa)"],
            data["Minute Rain (mm)"], data["Hour Rain (mm)"], data["Day Rain (mm)"], data["Total Rain (mm)"]
        )
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Gagal simpan histori: {e}")
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
        if not client.connected:
            return client.connect()
        return True
    except Exception:
        close_client()
        return False

def read_ws600():
    # Cek Port
    port_ok = is_port_detected(PORT)
    if not port_ok:
        update_live_data(None, False, False)
        close_client()
        return None

    # Cek Koneksi Modbus
    if not ensure_connection():
        update_live_data(None, True, False)
        return None

    try:
        result = client.read_holding_registers(
            address=START_ADDRESS,
            count=REGISTER_COUNT,
            slave=SLAVE_ID, # Perbaikan: Gunakan 'slave' untuk v3.x
        )
        
        if result.isError():
            update_live_data(None, True, False)
            return None

        update_live_data(None, True, True) # Sinyal OK
        values = result.registers
        
        if AUTO_DETECT_ENDIAN:
            picked, _ = pick_best_dataset(values)
            data, _, _ = picked
        else:
            data = decode_dataset(values, BYTE_ORDER, WORD_ORDER)
            
        return data

    except Exception as err:
        update_live_data(None, True, False)
        return None

# =============================================
# MAIN LOOP (FAST SAMPLING)
# =============================================
init_db()
client = None
last_db_save = 0
last_settings_check = 0

print(f"[*] WS-600 High-Speed Service Started")
print(f"[*] Port: {PORT}, Sampling: Setiap {READ_INTERVAL}s")

try:
    while True:
        loop_start = time.time()
        
        # 1. Cek perubahan setting (Port/Interval) secara berkala
        if loop_start - last_settings_check >= CHECK_SETTINGS_INTERVAL:
            if load_settings():
                print(f"[!] Pengaturan Berubah: Port {PORT}, Sampling {READ_INTERVAL}s")
                close_client()
            last_settings_check = loop_start

        # 2. Baca Sensor
        data = read_ws600()
        
        if data:
            # 3. Update Live Dashboard (Cepat)
            update_live_data(data, True, True)
            
            # 4. Simpan Histori (Berkala)
            if loop_start - last_db_save >= DB_SAVE_INTERVAL:
                if save_to_history(data):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Data saved to history.")
                    last_db_save = loop_start
        
        # 5. Precise Timing
        elapsed = time.time() - loop_start
        wait_time = max(0, READ_INTERVAL - elapsed)
        time.sleep(wait_time)

except KeyboardInterrupt:
    print("\n[!] Program dihentikan pengguna.")
finally:
    close_client()
