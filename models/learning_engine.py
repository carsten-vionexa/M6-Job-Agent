#!/usr/bin/env python3
"""
Learning Engine v3
------------------
Lernt nur aus neuen Feedback-Einträgen.
Berücksichtigt Likes/Dislikes UND Kommentare.
Kompatibel mit internen Job-IDs (int) und externen Arbeitsagentur-IDs (text).
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from models.compute_fit_score import compute_fit_scores, load_embedding
from models.embeddings import get_embedding

# --------------------------------------------------
# Pfad zur Datenbank
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "career_agent.db"


# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------
def load_profile_vector(conn, profile_id):
    """Lädt das Profil-Embedding als numpy-Array."""
    cur = conn.cursor()
    cur.execute("SELECT embedding FROM profiles WHERE id = ?", (profile_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return None
    return load_embedding(row[0])


def get_last_run(conn, profile_id):
    """Liest den letzten Lernzeitpunkt aus der Tabelle learning_state."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_state (
            profile_id INTEGER PRIMARY KEY,
            last_run TEXT
        )
    """)
    cur.execute("SELECT last_run FROM learning_state WHERE profile_id = ?", (profile_id,))
    row = cur.fetchone()
    return row[0] if row else "1970-01-01T00:00:00"


def set_last_run(conn, profile_id):
    """Schreibt den aktuellen Zeitpunkt als letzten Lernlauf."""
    now = datetime.utcnow().isoformat()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO learning_state (profile_id, last_run)
        VALUES (?, ?)
        ON CONFLICT(profile_id) DO UPDATE SET last_run = excluded.last_run
    """, (profile_id, now))
    conn.commit()


# --------------------------------------------------
# Hauptfunktion: Lernen aus neuen Feedbacks
# --------------------------------------------------
def update_profile_embedding(profile_id=1, learn_rate=0.05, comment_weight=0.5):
    """
    Aktualisiert das Profil-Embedding basierend auf neuen Feedback-Einträgen.
    - learn_rate: Lernrate für Likes/Dislikes
    - comment_weight: Gewicht für Kommentare
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    user_vec = load_profile_vector(conn, profile_id)
    if user_vec is None:
        print("❌ Kein Profil-Embedding gefunden.")
        conn.close()
        return

    # 🔹 HIER: letzten Laufzeitpunkt abrufen
    last_run = get_last_run(conn, profile_id)
    print(f"🕓 Letzter Lernlauf für Profil {profile_id}: {last_run}")

    cur.execute(f"""
        SELECT f.job_id, f.feedback_value, f.comment, j.embedding
        FROM feedback f
        JOIN jobs j
        ON (
            (typeof(f.job_id)='integer' AND f.job_id=j.id)
            OR (typeof(f.job_id)='text' AND LOWER(TRIM(f.job_id))=LOWER(TRIM(j.external_id)))
        )
        WHERE j.embedding IS NOT NULL
          AND datetime(f.timestamp) > datetime(?)
          AND (f.feedback_value IS NOT NULL
               OR (f.comment IS NOT NULL AND TRIM(f.comment)!=''))
    """, (last_run,))

    feedback_rows = cur.fetchall()

    if not feedback_rows:
        print("⚠️ Keine neuen Feedbacks seit dem letzten Lernlauf.")
        set_last_run(conn, profile_id)
        conn.close()
        return

    print(f"🔹 {len(feedback_rows)} neue Feedbacks gefunden – starte Lern-Update...")

    for job_id, feedback_value, comment, job_emb in feedback_rows:
        job_vec = load_embedding(job_emb)
        delta = np.zeros_like(user_vec)

        # 1️⃣ Like/Dislike
        if feedback_value is not None:
            delta += learn_rate * feedback_value * (job_vec - user_vec)

        # 2️⃣ Kommentarinhalt
        if comment and comment.strip():
            try:
                comment_vec = get_embedding(comment)
                delta += comment_weight * learn_rate * (comment_vec - user_vec)
            except Exception as e:
                print(f"⚠️ Kommentar-Embedding für Job {job_id} fehlgeschlagen: {e}")

        user_vec = user_vec + delta

    # Profil-Embedding speichern
    emb_json = json.dumps(user_vec.tolist())
    cur.execute("UPDATE profiles SET embedding = ? WHERE id = ?", (emb_json, profile_id))
    conn.commit()
    set_last_run(conn, profile_id)

    # --------------------------------------------------
    # matched_profile_id in jobs aktualisieren
    # --------------------------------------------------
    cur.execute("""
    UPDATE jobs
    SET matched_profile_id = (
        SELECT js.profile_id
        FROM job_scores js
        WHERE js.job_id = jobs.id
        ORDER BY js.match_score DESC
        LIMIT 1
    )
    WHERE id IN (
        SELECT DISTINCT job_id FROM job_scores
    );
    """)

    conn.commit()
    print("🔗 matched_profile_id in jobs aktualisiert.")

   
    # --------------------------------------------------
    # Feedback-Scores automatisch aktualisieren
    # --------------------------------------------------
    cur.execute("""
    UPDATE feedback
    SET feedback_score = (
        SELECT js.match_score
        FROM job_scores js
        WHERE js.job_id = feedback.job_id
        AND js.profile_id = feedback.profile_id
    )
    WHERE feedback.profile_id = ?;
    """, (profile_id,))

    conn.commit()
    print("🔁 Feedback-Scores für aktuelles Profil synchronisiert.")
    
    
    
    conn.close()

    print("✅ Profil-Embedding aktualisiert.")
    compute_fit_scores(profile_id=profile_id)
    print("🎯 Fit-Scores nach Lernupdate neu berechnet.")

    

# --------------------------------------------------
# Direkter Start
# --------------------------------------------------
if __name__ == "__main__":
    for pid in (1, 2, 3):
        update_profile_embedding(profile_id=pid)