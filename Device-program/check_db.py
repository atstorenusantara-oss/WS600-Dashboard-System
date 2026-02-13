import sqlite3
import os

db_path = r"h:\Projek\Wheather\ws600_data.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_data';")
        if cursor.fetchone():
            print("Table 'weather_data' exists.")
            cursor.execute("PRAGMA table_info(weather_data);")
            columns = cursor.fetchall()
            for col in columns:
                print(col)
        else:
            print("Table 'weather_data' does not exist.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
