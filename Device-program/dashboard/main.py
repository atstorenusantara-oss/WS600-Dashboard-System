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
async def get_logs(limit: int = 100):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM weather_data ORDER BY id DESC LIMIT ?", (limit,))
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

# Serve static files
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
