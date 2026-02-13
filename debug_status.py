import sqlite3
import os
from datetime import datetime

db_path = r"h:\Projek\Wheather\ws600_data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
cursor.execute("UPDATE system_status SET last_check = ? WHERE id = 1", (now,))
conn.commit()
cursor.execute("SELECT * FROM system_status")
print(cursor.fetchall())
conn.close()
