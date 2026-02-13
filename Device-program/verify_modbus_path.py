import os
import sys

# Simulasi cara modbusWs600.py menentukan path
BASE_DIR = os.path.dirname(os.path.abspath(r"h:\Projek\Wheather\Device-program\modbusWs600.py"))
DB_NAME = os.path.abspath(os.path.join(BASE_DIR, "..", "ws600_data.db"))

print(f"Path yang digunakan oleh modbusWs600.py:")
print(f"Full Path: {DB_NAME}")

if os.path.exists(DB_NAME):
    print("Status: File ditemukan.")
else:
    print("Status: File tidak ditemukan (akan dibuat saat script dijalankan).")
