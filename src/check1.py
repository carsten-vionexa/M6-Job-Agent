import sys
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "career_agent.db"

print("DB_PATH:", DB_PATH)
print("EXIST:", DB_PATH.exists())

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT id, title FROM jobs LIMIT 5")
rows = cur.fetchall()

print("Rows:", rows)
conn.close()