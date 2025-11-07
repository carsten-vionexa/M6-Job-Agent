#!/usr/bin/env python3
import sqlite3
from pathlib import Path
from typing import List
from .base_classes import Job, ApplicantProfile, Feedback

DB_PATH = Path("data/career_agent.db")

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