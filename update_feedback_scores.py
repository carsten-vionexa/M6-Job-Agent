#!/usr/bin/env python3
"""
Aktualisiert feedback.feedback_score anhand der aktuellen job_scores.match_score.
So werden im Dashboard echte Deltas sichtbar.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[0] / "data" / "career_agent.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print(f"🔧 Aktualisiere Feedback-Scores in {DB_PATH.name} ...")

cur.execute("""
UPDATE feedback
SET feedback_score = (
    SELECT js.match_score
    FROM job_scores js
    WHERE js.job_id = feedback.job_id
      AND js.profile_id = feedback.profile_id
)
WHERE feedback.job_id IS NOT NULL;
""")

conn.commit()
conn.close()

print("✅ Feedback-Scores erfolgreich mit aktuellen Match-Scores synchronisiert.")