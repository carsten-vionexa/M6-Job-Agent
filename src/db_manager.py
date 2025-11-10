import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from pathlib import Path
import os

from pathlib import Path
import os

# Absoluter Projektpfad (eine Ebene über /src)
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "career_agent.db"

# Verzeichnis sicherstellen
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
print(f"[DB] Verwende Datenbankpfad: {DB_PATH.resolve()}")


def setup_jobs_table(db_path: Path = DB_PATH):
    """Erstellt die Tabelle 'jobs', falls sie noch nicht existiert."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        description TEXT,
        source TEXT,
        url TEXT,
        date_posted TEXT,
        application_type TEXT DEFAULT 'Ausschreibung',
        matched_profile_id INTEGER,
        user_profile_id INTEGER,
        match_score REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()


def save_jobs_to_db(profile_id: int, user_profile_id: int, jobs: List[Dict[str, Any]], db_path: Path = DB_PATH):
    """
    Speichert Jobangebote in die Datenbank, inklusive Profilreferenz.
    Überspringt Duplikate (gleiche refnr + source).
    """
    if not jobs:
        print(f"[DB] Keine Jobs für Profil {profile_id} zu speichern.")
        return 0

    conn = sqlite3.connect(str(db_path.resolve()))
    cur = conn.cursor()

    # Sicherstellen, dass Tabelle existiert
    setup_jobs_table(db_path)

    inserted = 0

    for job in jobs:
        title = job.get("titel", "").strip()
        company = job.get("arbeitgeber", "").strip()
        location = job.get("ort", "").strip()
        source = job.get("source", "Bundesagentur für Arbeit")
        refnr = job.get("refnr", "")
        desc = job.get("beschreibung", "")
        date_posted = job.get("date_posted", "")
        url = job.get("url", "")

        # Duplikatsprüfung
        cur.execute("""
            SELECT COUNT(*) FROM jobs
            WHERE title=? AND company=? AND source=? AND matched_profile_id=?;
        """, (title, company, source, profile_id))
        exists = cur.fetchone()[0]

        if exists:
            print(f"[DB] Übersprungen: {title} ({company}) – bereits vorhanden.")
            continue

        cur.execute("""
            INSERT INTO jobs (title, company, location, description, source, url, date_posted, matched_profile_id, user_profile_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, company, location, desc, source, url, date_posted, profile_id, user_profile_id))
        inserted += 1

    conn.commit()
    conn.close()

    print(f"[DB] {inserted} neue Jobs gespeichert (Profil-ID {profile_id}).")
    return inserted