#!/usr/bin/env python3
"""
Feedback-Logik mit automatischem Lern-Trigger.
"""

import sys
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone

# --------------------------------------------
# Projekt-Root & DB-Pfad (Datei liegt: <root>/src/feedback_logic.py)
# --------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]   # -> <root>
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "career_agent.db"

# Import aus <root>/models/
from models.learning_engine import update_profile_embedding


# --------------------------------------------------
# Feedback speichern
# --------------------------------------------------
def save_feedback(job_id, profile_id, feedback_value, comment=None):
    """Speichert Feedback und triggert sofort das Lernen (im Hintergrund-Thread)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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

    cur.execute("""
        INSERT INTO feedback (job_id, profile_id, feedback_value, comment, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (str(job_id), profile_id, feedback_value, comment, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

    print(f"💾 Feedback gespeichert: job={job_id}, profile={profile_id}, value={feedback_value}")

    # Lernprozess im Hintergrund starten
    print("🤖 Starte Learning Engine synchron ...")
    print(f"⚙️ Learning Engine wird gestartet für Profil {profile_id} ...")
    update_profile_embedding(profile_id)
    print("✅ Learning Engine hat ausgeführt.")
    
    update_profile_embedding(profile_id)
    print("✅ Learning Engine abgeschlossen.")


# --------------------------------------------------
# Manueller Testlauf (nur bei Direktausführung)
# --------------------------------------------------
if __name__ == "__main__":
    print("ROOT:", PROJECT_ROOT)
    print("DB:", DB_PATH)
    print("🔧 Testlauf – Feedback speichern und Lernen starten ...")
    save_feedback(
        job_id="12265-470080_JB4975426-S",
        profile_id=1,
        feedback_value=1,
        comment="Testeintrag – funktioniert der Lernprozess?"
    )