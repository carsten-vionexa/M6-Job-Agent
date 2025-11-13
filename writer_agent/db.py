#!/usr/bin/env python3
from pathlib import Path
import sqlite3

# Projekt-Root finden: eine Ebene über writer_agent/
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "career_agent.db"

print("→ Writer-Agent DB-Pfad:", DB_PATH)


def get_job(job_id: int):
    """
    Holt einen Job aus der DB inkl. obsolete_user_profile_id.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, company, url, description, obsolete_user_profile_id
        FROM jobs
        WHERE id=?
    """, (job_id,))

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
        "profile_id": row[5],   # Writer-Agent nutzt dieses Feld weiter
    }


def get_profile(profile_id: int):
    """
    Holt Profilinfos.
    -> description_text = Zusammenfassung / Profilbeschreibung
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, description_text
        FROM profiles
        WHERE id=?
    """, (profile_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "summary": row[2] or "",
    }


def get_resume_text(profile_id: int):
    """
    Holt den passenden Lebenslauftext aus resumes.content_text,
    indem resume.title mit profile.name verglichen wird.
    """
    profile = get_profile(profile_id)
    if not profile:
        return ""

    profile_name = profile["name"].lower()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT title, content_text FROM resumes")
    rows = cur.fetchall()
    conn.close()

    # 1. Matching über Titel der Resume-Datei
    for title, text in rows:
        if title and profile_name in title.lower():
            return text or ""

    # 2. Falls kein direkter Treffer → nimm den ersten Lebenslauf
    if rows:
        return rows[0][1] or ""

    # 3. Nichts gefunden
    return ""


    