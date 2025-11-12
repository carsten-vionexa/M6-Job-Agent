#!/usr/bin/env python3
import sqlite3, re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "career_agent.db"

# Muster:
# 1) reine ID: "14628-00007b0f54a001-S"
# 2) JSON: ... "external_id":"14628-00007b0f54a001-S" ...
# 3) Fallback: irgendwas mit id=... in URLs
RE_ID = re.compile(r"^[A-Za-z0-9\-]+$")
RE_JSON_EXT = re.compile(r'"external_id"\s*:\s*"([A-Za-z0-9\-]+)"')
RE_URL_ID = re.compile(r"id=([A-Za-z0-9\-]+)")

def norm(s: str) -> str:
    # trim, unify dashes, lowercase
    return (s or "").strip().replace("–","-").replace("—","-").lower()

def extract_external_id(text: str) -> str | None:
    if not text:
        return None
    t = text.strip()
    # akzeptiere alles mit Ziffern, Buchstaben, Minus oder Unterstrich
    if re.match(r"^[A-Za-z0-9\-_]+$", t):
        return t
    # Fallbacks
    m = RE_URL_ID.search(t)
    if m:
        return m.group(1)
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Spalte sicherstellen
    cur.execute("PRAGMA table_info(feedback)")
    cols = [r[1] for r in cur.fetchall()]
    if "external_id" not in cols:
        cur.execute("ALTER TABLE feedback ADD COLUMN external_id TEXT")

    cur.execute("SELECT id, job_id FROM feedback")
    rows = cur.fetchall()
    updated = 0
    for fid, job_id in rows:
        ext = extract_external_id(job_id if isinstance(job_id, str) else "")
        if ext:
            cur.execute("UPDATE feedback SET external_id = ? WHERE id = ?", (norm(ext), fid))
            updated += 1

    # Normierung auf beiden Seiten
    cur.execute("UPDATE jobs SET external_id = lower(replace(replace(trim(external_id),'–','-'),'—','-')) WHERE external_id IS NOT NULL")
    cur.execute("UPDATE feedback SET external_id = lower(replace(replace(trim(external_id),'–','-'),'—','-')) WHERE external_id IS NOT NULL")

    conn.commit()
    conn.close()
    print(f"✅ {updated} Feedback-Zeilen mit external_id gefüllt & normalisiert.")

if __name__ == "__main__":
    main()