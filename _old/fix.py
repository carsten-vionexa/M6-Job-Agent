#!/usr/bin/env python3
"""
Einmaliges Reparaturskript:
Füllt fehlende base_score- und feedback_score-Werte
in der Tabelle feedback anhand der job_scores-Tabelle nach.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[0] / "data" / "career_agent.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print(f"🔧 Verbunden mit: {DB_PATH}")

# --------------------------------------------------
# Alte Feedbacks ergänzen
# --------------------------------------------------
cur.execute("""
UPDATE feedback
SET base_score = (
    SELECT js.match_score
    FROM job_scores js
    WHERE js.job_id = feedback.job_id
      AND js.profile_id = feedback.profile_id
)
WHERE base_score IS NULL;
""")

cur.execute("""
UPDATE feedback
SET feedback_score = base_score
WHERE feedback_score IS NULL;
""")

conn.commit()

# Prüfen, wie viele geändert wurden
cur.execute("SELECT COUNT(*) FROM feedback WHERE base_score IS NOT NULL;")
count = cur.fetchone()[0]
conn.close()

print(f"✅ {count} Feedback-Einträge mit base_score/feedback_score ergänzt.")