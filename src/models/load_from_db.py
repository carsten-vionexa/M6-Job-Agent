#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from typing import List
from .models.base_classes import Job, ApplicantProfile, Feedback

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "career_agent.db"

# ------------------------------------------------------------
# Hilfsfunktion für DB-Verbindung
# ------------------------------------------------------------
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------------------------------------------------
# Jobs laden
# ------------------------------------------------------------
def load_jobs(limit: int = 20) -> List[Job]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT id, title, company, location, description, source, url,
                   date_posted, application_type, matched_profile_id, match_score
            FROM jobs
            ORDER BY date_posted DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [Job(**dict(row)) for row in rows]

# ------------------------------------------------------------
# Profile laden
# ------------------------------------------------------------
def load_profiles() -> List[ApplicantProfile]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT id, name, file_path, description_text, resume_id, created_at
            FROM profiles
            ORDER BY id
        """).fetchall()
        return [ApplicantProfile(**dict(row)) for row in rows]

# ------------------------------------------------------------
# Feedback laden
# ------------------------------------------------------------
def load_feedback(job_id: int = None) -> List[Feedback]:
    query = """
        SELECT id, job_id, profile_id, resume_id, match_score, comment, created_at
        FROM feedback
    """
    params = ()
    if job_id:
        query += " WHERE job_id = ?"
        params = (job_id,)
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [Feedback(**dict(row)) for row in rows]

 # ------------------------------------------------------------
# Feedback laspeichern
# ------------------------------------------------------------   

    def save_feedback(job_id: int,
                  feedback_value: int,
                  profile_id: int = None,
                  match_score: float = None,
                  comment: str = None) -> int:
        """Speichert neues Feedback für einen Job und gibt die ID zurück"""
        from datetime import datetime
        ts = datetime.now().isoformat(timespec="seconds")
        with _connect() as conn:
            cur = conn.execute("""
                INSERT INTO feedback
                (job_id, feedback_value, timestamp, profile_id, match_score, comment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (job_id, feedback_value, ts, profile_id, match_score, comment))
            conn.commit()
            return cur.lastrowid
        

    # ------------------------------------------------------------
    # Writer Agent
    # ------------------------------------------------------------ 

    import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "career_agent.db"


def get_job(job_id: int) -> dict | None:
    """
    Holt einen Job inklusive evtl. verknüpfter profile_id.
    Erwartet Spalten: id, title, company, url, description, profile_id
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, company, url, description, profile_id
        FROM jobs
        WHERE id = ?
        """,
        (job_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "company": row[2],
        "url": row[3],
        "description": row[4],
        "profile_id": row[5],
    }


def get_profile(profile_id: int) -> dict | None:
    """
    Holt die Basis-Infos zum Profil.
    Erwartet mindestens: id, name, summary.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, summary
        FROM profiles
        WHERE id = ?
        """,
        (profile_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "summary": row[2] or "",
    }


def get_resume_text_for_profile(profile_id: int) -> str:
    """
    Holt den Lebenslauf-Text zu einem Profil.
    Variante A: es gibt eine Tabelle resumes mit Spalte text.
    Passe die Query an deine konkrete DB an.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # ❗ Falls du andere Spaltennamen hast, hier anpassen
    try:
        cur.execute(
            """
            SELECT text
            FROM resumes
            WHERE profile_id = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (profile_id,),
        )
        row = cur.fetchone()
    except sqlite3.OperationalError:
        # Fallback: kein resumes-Table → leere Zeichenkette
        row = None

    conn.close()
    return row[0] if row and row[0] else ""