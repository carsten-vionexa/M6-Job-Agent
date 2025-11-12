#!/usr/bin/env python3
"""
Berechnet semantische Fit-Scores zwischen einem Profil (profiles) und allen Jobs.
Nutzt Cosine Similarity zwischen den Embeddings in der Datenbank.
"""

import sqlite3
import json
import numpy as np
from pathlib import Path

# --------------------------------------------------
# Pfad zur Datenbank
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "career_agent.db"

# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------
def cosine_similarity(a, b):
    """Berechnet Cosine Similarity zweier Vektoren."""
    a, b = np.array(a), np.array(b)
    if not a.any() or not b.any():
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def load_embedding(blob_or_json):
    """Lädt Embedding (JSON-Text oder BLOB) als numpy-Array."""
    try:
        if isinstance(blob_or_json, bytes):
            blob_or_json = blob_or_json.decode("utf-8")
        return np.array(json.loads(blob_or_json))
    except Exception:
        return np.zeros(1536)

# --------------------------------------------------
# Hauptfunktion
# --------------------------------------------------
def compute_fit_scores(profile_id=1):
    """
    Berechnet Fit-Scores für alle Jobs auf Basis des Embeddings
    eines gewählten Profils aus der Tabelle 'profiles'.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Profil-Embedding laden
    cur.execute("SELECT embedding, name FROM profiles WHERE id = ?", (profile_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        print(f"❌ Kein Embedding für Profil {profile_id} gefunden.")
        conn.close()
        return

    profile_vec = load_embedding(row[0])
    profile_name = row[1]
    print(f"🔹 Berechne Fit-Scores für Profil: {profile_name}")

    # Falls Spalte match_score noch nicht existiert, anlegen
    cur.execute("PRAGMA table_info(jobs)")
    cols = [r[1] for r in cur.fetchall()]
    if "match_score" not in cols:
        cur.execute("ALTER TABLE jobs ADD COLUMN match_score REAL DEFAULT 0")
        conn.commit()

    # Alle Jobs mit Embedding laden
    cur.execute("SELECT id, embedding FROM jobs WHERE embedding IS NOT NULL")
    jobs = cur.fetchall()
    print(f"🔹 {len(jobs)} Job-Embeddings gefunden – starte Berechnung...")

    
    # Alte Scores für dieses Profil löschen
    cur.execute("DELETE FROM job_scores WHERE profile_id = ?", (profile_id,))
    conn.commit()

    for job_id, job_emb in jobs:
        job_vec = load_embedding(job_emb)
        score = cosine_similarity(profile_vec, job_vec)
        cur.execute("""
            INSERT INTO job_scores (profile_id, job_id, match_score)
            VALUES (?, ?, ?)
        """, (profile_id, job_id, score))



    conn.commit()
    conn.close()
    print(f"✅ Fit-Scores für Profil '{profile_name}' aktualisiert und gespeichert.\n")

# --------------------------------------------------
# Direkter Start
# --------------------------------------------------
if __name__ == "__main__":
    compute_fit_scores(profile_id=1)
    compute_fit_scores(profile_id=2)
    compute_fit_scores(profile_id=3)
    print("🎯 Berechnung abgeschlossen.")