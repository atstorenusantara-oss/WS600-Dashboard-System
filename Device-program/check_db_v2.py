import sqlite3
import os

db_paths = [
    r"h:\Projek\Wheather\ws600_data.db",
    r"h:\Projek\Wheather\Device-program\ws600_data.db"
]

for path in db_paths:
    print(f"--- Checking {path} ---")
    if not os.path.exists(path):
        print("File does not exist.")
        continue
    
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM weather_data")
        count = cursor.fetchone()[0]
        print(f"Total rows: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, timestamp FROM weather_data ORDER BY id DESC LIMIT 1")
            last = cursor.fetchone()
            print(f"Latest record: ID={last[0]}, Time={last[1]}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
    print()
