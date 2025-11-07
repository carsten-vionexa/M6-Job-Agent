#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import sqlite3
from docx import Document

DB_PATH = "data/career_agent.db"
RESUME_DIR = Path("data/resumes")
PROFILE_DIR = Path("data/profiles")

def now(): return datetime.now().isoformat(timespec="seconds")

def extract_docx_text(p: Path) -> str:
    doc = Document(str(p))
    return "\n".join(par.text for par in doc.paragraphs).strip()

def ensure_tables(conn):
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        file_path TEXT NOT NULL,
        content_text TEXT,
        embedding BLOB,
        created_at TEXT NOT NULL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        file_path TEXT,
        description_text TEXT,
        resume_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(resume_id) REFERENCES resumes(id)
    )
    """)

def get_resume_id(conn, file_path: Path, title: str) -> int:
    cur = conn.execute("SELECT id FROM resumes WHERE file_path = ?", (str(file_path),))
    row = cur.fetchone()
    if row:
        return row[0]
    text = extract_docx_text(file_path)
    cur = conn.execute("""
        INSERT INTO resumes (title, file_path, content_text, embedding, created_at)
        VALUES (?, ?, ?, NULL, ?)
    """, (title, str(file_path), text, now()))
    return cur.lastrowid

def upsert_profile(conn, name: str, file_path: Path, resume_id: int) -> int:
    cur = conn.execute("SELECT id FROM profiles WHERE name = ?", (name,))
    text = extract_docx_text(file_path)
    row = cur.fetchone()
    if row:
        conn.execute("""
            UPDATE profiles
            SET file_path=?, description_text=?, resume_id=?
            WHERE id=?
        """, (str(file_path), text, resume_id, row[0]))
        return row[0]
    cur = conn.execute("""
        INSERT INTO profiles (name, file_path, description_text, resume_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (name, str(file_path), text, resume_id, now()))
    return cur.lastrowid

def find_one(prefix: str) -> Path:
    # robust gegen Leerzeichen/Bindestriche, nimmt die "längste" Übereinstimmung
    cands = list(PROFILE_DIR.glob(prefix + "*.docx"))
    if not cands:
        raise FileNotFoundError(f"Keine Datei gefunden für Prefix: {prefix} in {PROFILE_DIR}")
    return sorted(cands, key=lambda p: len(p.name), reverse=True)[0]

def main():
    mappings = [
        {
            "profile_name": "Profil 1 – KI-Enablement Manager",
            "profile_file": find_one("Profil-1-KI-Enablement"),
            "resume_title": "Lebenslauf – Profil 1 (CV)",
            "resume_file":  RESUME_DIR / "Profil-1-CV.docx",
        },
        {
            "profile_name": "Profil 2 – Office & CRM Coordinator",
            "profile_file": find_one("Profil-2-Office-CRM"),
            "resume_title": "Lebenslauf – Profil 2 (CV)",
            "resume_file":  RESUME_DIR / "Profil-2-CV.docx",
        },
        {
            "profile_name": "Profil 3 – Marketing Operations & Content Manager",
            "profile_file": find_one("Profil-3-Marketing-Operations-Content-Manager"),
            "resume_title": "Lebenslauf – Profil 3 (CV)",
            "resume_file":  RESUME_DIR / "Profil-3-CV.docx",
        },
    ]

    neutral_cv = RESUME_DIR / "CV-allgemein.docx"

    with sqlite3.connect(DB_PATH) as conn:
        ensure_tables(conn)

        if neutral_cv.exists():
            nid = get_resume_id(conn, neutral_cv, "Lebenslauf – Allgemein (vollständig)")
            print(f"[OK] Neutraler CV id={nid}")
        else:
            print(f"[WARN] Neutraler CV fehlt: {neutral_cv}")

        for m in mappings:
            if not m["resume_file"].exists():
                print(f"[ERR] CV fehlt: {m['resume_file']}")
                continue
            rid = get_resume_id(conn, m["resume_file"], m["resume_title"])
            pf = m["profile_file"]
            if not pf.exists():
                print(f"[ERR] Profilbeschreibung fehlt: {pf}")
                continue
            pid = upsert_profile(conn, m["profile_name"], pf, rid)
            print(f"[OK] Profil '{m['profile_name']}' -> CV id={rid} (profile_id={pid})")

        conn.commit()

if __name__ == "__main__":
    main()