import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import os

# Projektpfad und DB-Pfad
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "career_agent.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
print(f"[DB] Verwende Datenbankpfad: {DB_PATH.resolve()}")

# -----------------------------
# Tabellenanlage
# -----------------------------
def setup_jobs_table(db_path: Path = DB_PATH):
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

def setup_feedback_table(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        profile_id INTEGER,
        feedback_value INTEGER,
        comment TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

# -----------------------------
# Jobs sicherstellen / speichern
# -----------------------------
def ensure_job_exists(job: dict, db_path: Path = DB_PATH) -> int:
    """
    Sichert, dass ein Job in 'jobs' existiert. Legt ihn an, falls nötig.
    Rückgabe: job_id
    """
    setup_jobs_table(db_path)

    refnr = job.get("refnr")
    title = job.get("titel") or job.get("title")
    company = job.get("arbeitgeber") or job.get("company")
    location = job.get("ort") or job.get("location")
    description = job.get("beschreibung") or job.get("description") or ""
    source = job.get("source") or "Bundesagentur für Arbeit"
    url = job.get("url") or (f"https://www.arbeitsagentur.de/jobsuche/suche?id={refnr}" if refnr else None)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1) per refnr in URL
    if refnr:
        cur.execute("SELECT id FROM jobs WHERE url LIKE ? LIMIT 1;", (f"%{refnr}%",))
        row = cur.fetchone()
        if row:
            conn.close()
            return row[0]

    # 2) fallback Titel+Firma+Ort
    cur.execute("""
        SELECT id FROM jobs
        WHERE title = ? AND IFNULL(company,'') = IFNULL(?, '') AND IFNULL(location,'') = IFNULL(?, '')
        LIMIT 1;
    """, (title, company, location))
    row = cur.fetchone()
    if row:
        conn.close()
        return row[0]

    # 3) anlegen
    cur.execute("""
        INSERT INTO jobs (title, company, location, description, source, url, date_posted)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (title, company, location, description, source, url))
    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"[Jobs] Neuer Eintrag: {job_id} ({title})")
    return job_id

def save_jobs_to_db(profile_id: int, user_profile_id: int, jobs: List[Dict[str, Any]], db_path: Path = DB_PATH):
    """
    Batch-Speicherung (wird in deiner App aktuell nicht beim Feedback benutzt).
    """
    if not jobs:
        print(f"[DB] Keine Jobs für Profil {profile_id} zu speichern.")
        return 0

    setup_jobs_table(db_path)
    conn = sqlite3.connect(str(db_path.resolve()))
    cur = conn.cursor()

    inserted = 0
    for job in jobs:
        title = job.get("titel", "").strip()
        company = job.get("arbeitgeber", "").strip()
        location = job.get("ort", "").strip()
        source = job.get("source", "Bundesagentur für Arbeit")
        refnr = job.get("refnr", "")
        desc = job.get("beschreibung", "")
        date_posted = job.get("date_posted", "")
        url = job.get("url", "") or (f"https://www.arbeitsagentur.de/jobsuche/suche?id={refnr}" if refnr else None)

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

# -----------------------------
# Feedback speichern
# -----------------------------
def save_feedback(
    job_id: int,
    profile_id: int,
    feedback_value: int | None = None,
    comment: str | None = None,
    db_path: Path = DB_PATH,
):
    """
    Speichert einen Feedbackeintrag (setzt existierenden job_id voraus).
    """
    setup_feedback_table(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO feedback (job_id, profile_id, feedback_value, comment, timestamp)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (job_id, profile_id, feedback_value, comment),
    )
    conn.commit()
    conn.close()
    print(f"[Feedback] job_id={job_id}, value={feedback_value}, comment={comment}")
    return True