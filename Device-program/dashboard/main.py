import sqlite3
import os
from fastapi import FastAPI, HTTPException, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import psutil
import pandas as pd
import io
import time
import shutil

app = FastAPI()

# Path to database (Points to root folder Wheather/ws600_data.db)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ws600_data.db"))

def get_usb_path():
    """Helper untuk mendeteksi letak Flashdisk"""
    for partition in psutil.disk_partitions():
        if 'removable' in partition.opts.lower() or partition.fstype == 'FAT32':
            try:
                test_file = os.path.join(partition.mountpoint, ".test_write")
                with open(test_file, 'w') as f: f.write('1')
                os.remove(test_file)
                return partition.mountpoint
            except: continue
    return None

class WeatherData(BaseModel):
    id: int
    timestamp: str
    wind_speed: float
    wind_direction: float
    temperature: float
    humidity: float
    pressure: float
    rain_total: float

class SystemSettings(BaseModel):
    poll_interval: int
    save_interval: int
    com_port: str
    baudrate: int

from datetime import datetime

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create weather_data table
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
    
    # Create weather_live table
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
    
    # Create system_status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY,
            port_connected INTEGER,
            sensor_responding INTEGER,
            last_check DATETIME
        )
    ''')
    # Initialize first row if empty
    cursor.execute("SELECT COUNT(*) FROM system_status")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO system_status (id, port_connected, sensor_responding, last_check) VALUES (1, 0, 0, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

    # Create system_settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY,
            poll_interval INTEGER DEFAULT 2,
            save_interval INTEGER DEFAULT 10,
            com_port TEXT DEFAULT 'COM21',
            baudrate INTEGER DEFAULT 9600
        )
    """)
    # Insert default settings if not exists
    cursor.execute("SELECT COUNT(*) FROM system_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO system_settings (poll_interval, save_interval, com_port, baudrate) VALUES (2, 10, 'COM21', 9600)")
    
    conn.commit()
    conn.close()

init_db()

@app.get("/api/latest")
async def get_latest_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Mengambil data terbaru dari tabel live (update setiap 2 detik)
        cursor.execute("SELECT * FROM weather_live WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {"error": "No data found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs(
    limit: int = 100, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM weather_data"
        params = []
        
        if start_date and end_date:
            query += " WHERE timestamp BETWEEN ? AND ?"
            params.extend([start_date + " 00:00:00", end_date + " 23:59:59"])
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM system_status WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {"error": "Status not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast")
async def get_forecast():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Ambil 50 data terakhir untuk dianalisis trend-nya
        cursor.execute("SELECT temperature, humidity, wind_speed FROM weather_data ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()

        if len(rows) < 10:
            return {"error": "Data tidak cukup untuk kalkulasi AI"}

        # Linear Regression Sederhana (Manual)
        def predict_next(values):
            n = len(values)
            x = list(range(n))
            y = values[::-1] # Urutkan dari lama ke baru
            
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xx = sum(i*i for i in x)
            sum_xy = sum(i*j for i, j in zip(x, y))
            
            # Slope (m) = (n*sum_xy - sum_x*sum_y) / (n*sum_xx - sum_x**2)
            denominator = (n * sum_xx - sum_x**2)
            if denominator == 0: return y[-1]
            
            m = (n * sum_xy - sum_x * sum_y) / denominator
            b = (sum_y - m * sum_x) / n
            
            # Prediksi untuk step berikutnya (n + 10) -> kira-kira 10-20 menit ke depan
            return m * (n + 10) + b

        temps = [r['temperature'] for r in rows]
        hums = [r['humidity'] for r in rows]
        winds = [r['wind_speed'] for r in rows]

        return {
            "prediction_1h": {
                "temperature": round(predict_next(temps), 1),
                "humidity": round(predict_next(hums), 0),
                "wind_speed": round(max(0, predict_next(winds)), 2)
            },
            "trend": "Menghitung...",
            "confidence": "Sedang-Tinggi"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings")
async def get_settings():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM system_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
async def update_settings(settings: SystemSettings):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE system_settings 
            SET poll_interval = ?, save_interval = ?, com_port = ?, baudrate = ?
            WHERE id = 1
        """, (settings.poll_interval, settings.save_interval, settings.com_port, settings.baudrate))
        conn.commit()
        conn.close()
        return {"message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export-excel")
async def export_excel(start_date: Optional[str] = None, end_date: Optional[str] = None):
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT timestamp, wind_speed, wind_direction, temperature, humidity, pressure, rain_total FROM weather_data"
        params = []
        
        if start_date and end_date:
            query += " WHERE timestamp BETWEEN ? AND ?"
            params.extend([start_date + " 00:00:00", end_date + " 23:59:59"])
        
        query += " ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            raise HTTPException(status_code=404, detail="Tidak ada data untuk diexport")

        # Rename columns for better readability in Excel
        df.columns = ['Waktu', 'Kec. Angin (m/s)', 'Arah Angin (°)', 'Suhu (°C)', 'Kelembaban (%)', 'Tekanan (hPa)', 'Curah Hujan (mm)']

        filename = f"Laporan_Cuaca_{int(time.time())}.xlsx"
        
        # --- LOGIC DETEKSI USB ---
        usb_path = get_usb_path()

        if usb_path:
            # Simpan langsung ke USB
            target_dir = os.path.join(usb_path, "Laporan_Insalusi")
            if not os.path.exists(target_dir): os.makedirs(target_dir)
            
            full_path = os.path.join(target_dir, filename)
            df.to_excel(full_path, index=False)
            return {"status": "saved_to_usb", "path": full_path, "drive": usb_path}
        
        # --- FALLBACK: DOWNLOAD VIA BROWSER ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data Cuaca')
        
        output.seek(0)
        headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-usb")
async def save_to_usb(file: UploadFile = File(...)):
    """Endpoint untuk menerima file (PDF) dan simpan ke USB"""
    try:
        usb_path = get_usb_path()
        if not usb_path:
            return {"status": "no_usb"}
        
        target_dir = os.path.join(usb_path, "Laporan_Insalusi")
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        full_path = os.path.join(target_dir, file.filename)
        with open(full_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"status": "saved_to_usb", "path": full_path, "drive": usb_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
