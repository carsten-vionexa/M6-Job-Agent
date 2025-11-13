#!/usr/bin/env python3
"""
Feedback-Logik mit automatischem Lern-Trigger.
Sorgt dafür, dass bei jedem Feedback-Ereignis:
  • das Feedback gespeichert wird,
  • das zugehörige Job-Embedding existiert (wird ggf. erzeugt),
  • und die Learning Engine sofort gestartet wird.
"""

import sqlite3
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
import sys

# --------------------------------------------------
# Projekt-Root & DB-Pfad
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "career_agent.db"

# Pfad zum Projekt-Root eintragen, damit models importierbar ist
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.embeddings import get_embedding
from models.learning_engine import update_profile_embedding


# --------------------------------------------------
# Feedback speichern + Lernprozess starten
# --------------------------------------------------
def save_feedback(job_id, profile_id, feedback_value, comment=None):
    """
    Speichert ein Feedback-Ereignis in der Datenbank,
    erzeugt falls nötig das Job-Embedding,
    und startet den Lernprozess synchron.
    """

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Tabelle sicherstellen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            profile_id INTEGER,
            feedback_value INTEGER,
            comment TEXT,
            timestamp TEXT
        )
    """)

    # Feedback eintragen
    ts = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO feedback (job_id, profile_id, feedback_value, comment, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (str(job_id), profile_id, feedback_value, comment, ts))
    conn.commit()
    conn.close()
    print(f"💾 Feedback gespeichert: job={job_id}, profile={profile_id}, value={feedback_value}")

    # --------------------------------------------------
    # 🧠 Job-Embedding prüfen / erzeugen
    # --------------------------------------------------
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT description, embedding FROM jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        if row and (not row[1]) and row[0] and row[0].strip():
            try:
                vec = get_embedding(row[0])
                cur.execute("UPDATE jobs SET embedding=? WHERE id=?", (json.dumps(vec.tolist()), job_id))
                conn.commit()
                print(f"🧠 Embedding erzeugt für Job {job_id}")
            except Exception as e:
                print(f"⚠️ Fehler beim Erzeugen des Embeddings für Job {job_id}: {e}")
        conn.close()
    except Exception as e:
        print(f"⚠️ Datenbankfehler beim Embedding-Check: {e}")

    # --------------------------------------------------
    # 🤖 Learning Engine starten (synchron)
    # --------------------------------------------------
    print(f"🤖 Starte Learning Engine für Profil {profile_id} ...")
    try:
        update_profile_embedding(profile_id)
        print("✅ Learning Engine abgeschlossen.")
    except Exception as e:
        print(f"⚠️ Fehler während des Lernprozesses: {e}")


# --------------------------------------------------
# Testlauf (optional)
# --------------------------------------------------
if __name__ == "__main__":
    print("🔧 Testlauf – Feedback speichern und Lernen starten ...")
    save_feedback(job_id=1, profile_id=1, feedback_value=1, comment="Testeintrag – funktioniert der Lernprozess?")