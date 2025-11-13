#!/usr/bin/env python3
"""
Learning Engine v3
------------------
Lernt nur aus neuen Feedback-Einträgen.
Berücksichtigt Likes/Dislikes UND Kommentare.
Kompatibel mit internen Job-IDs (int) und externen Arbeitsagentur-IDs (text).
"""

import sys
import json
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime

# --------------------------------------------------
# Pfadkorrektur (damit "models" importierbar ist)
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models.compute_fit_score import compute_fit_scores, load_embedding, cosine_similarity
from models.embeddings import get_embedding

print("✅ learning_engine.py wurde gestartet")

# --------------------------------------------------
# Datenbankpfad
# --------------------------------------------------
DB_PATH = ROOT_DIR / "data" / "career_agent.db"


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


# --------------------------------------------------
# Lernlogik
# --------------------------------------------------
def update_profile_embedding(profile_id=1, learn_rate=0.03, comment_weight=0.4):
    """Lernt auf Basis neuer Feedbacks (Likes/Dislikes + Kommentare)."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # Profil laden
        cur.execute("SELECT embedding FROM profiles WHERE id=?", (profile_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            print("❌ Kein Profil-Embedding gefunden.")
            return
        profile_vec = load_embedding(row[0])

        # Feedbacks mit Job-Embedding
        cur.execute("""
            SELECT f.job_id, f.feedback_value, f.comment, j.embedding
            FROM feedback f
            JOIN jobs j ON f.job_id = j.id
            WHERE f.profile_id = ?
              AND j.embedding IS NOT NULL
              AND (f.feedback_value IS NOT NULL OR TRIM(COALESCE(f.comment, '')) != '')
            ORDER BY f.timestamp DESC
            LIMIT 50
        """, (profile_id,))
        rows = cur.fetchall()

        if not rows:
            print(f"⚠️ Keine neuen Feedbacks für Profil {profile_id}.")
            return

        print(f"🔹 {len(rows)} Feedbacks für Profil {profile_id} – starte Anpassung...")

        for job_id, fb_value, comment, job_emb in rows:
            job_vec = load_embedding(job_emb)
            if job_vec is None:
                continue

            # Like/Dislike-Effekt
            if fb_value == 1:
                profile_vec += learn_rate * (job_vec - profile_vec)
            elif fb_value == -1:
                profile_vec -= learn_rate * (job_vec - profile_vec)

            # Kommentar-Effekt
            if comment and comment.strip():
                try:
                    cvec = get_embedding(comment)
                    profile_vec += comment_weight * learn_rate * (cvec - profile_vec)
                except Exception as e:
                    print(f"⚠️ Kommentar-Embedding-Fehler: {e}")

        # Normalisieren & speichern
        norm = np.linalg.norm(profile_vec)
        if norm > 0:
            profile_vec /= norm

        cur.execute(
            "UPDATE profiles SET embedding=? WHERE id=?",
            (json.dumps(profile_vec.tolist()), profile_id)
        )
        conn.commit()
        print(f"✅ Profil {profile_id} erfolgreich aktualisiert.")

    compute_fit_scores(profile_id=profile_id)
    print("🎯 Fit-Scores nach Lernupdate neu berechnet.")


# --------------------------------------------------
# Direkter Start
# --------------------------------------------------
if __name__ == "__main__":
    print("🔧 Main-Block erreicht")
    for pid in (1, 2, 3):
        update_profile_embedding(profile_id=pid)
    print("🏁 Ende erreicht.")