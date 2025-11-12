#!/usr/bin/env python3
"""
Extrahiert externe Job-IDs aus der URL-Spalte und trägt sie in jobs.external_id ein.
Beispiel: https://www.arbeitsagentur.de/jobsuche/suche?id=14628-00007b0f54a001-S
"""
import sqlite3
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "career_agent.db"

pattern = re.compile(r"id=([A-Za-z0-9\-]+)")

def extract_external_ids():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Spalte anlegen, falls noch nicht vorhanden
    cur.execute("PRAGMA table_info(jobs)")
    cols = [r[1] for r in cur.fetchall()]
    if "external_id" not in cols:
        cur.execute("ALTER TABLE jobs ADD COLUMN external_id TEXT")

    cur.execute("SELECT id, url FROM jobs WHERE url IS NOT NULL")
    rows = cur.fetchall()
    print(f"🔹 {len(rows)} URLs gefunden – starte Extraktion...")

    count = 0
    for job_id, url in rows:
        match = pattern.search(url)
        if match:
            ext_id = match.group(1)
            cur.execute("UPDATE jobs SET external_id = ? WHERE id = ?", (ext_id, job_id))
            count += 1

    conn.commit()
    conn.close()
    print(f"✅ {count} externe IDs erfolgreich eingetragen.")

if __name__ == "__main__":
    extract_external_ids()