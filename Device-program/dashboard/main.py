import sqlite3
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Path to database (Points to root folder Wheather/ws600_data.db)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ws600_data.db"))

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

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
            return {"error": "Insufficient data for AI forecasting"}

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
            "trend": "Calculating...",
            "confidence": "Medium-High"
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

# Serve static files
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
