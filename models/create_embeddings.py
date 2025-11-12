#!/usr/bin/env python3
"""
Erzeugt initiale Embeddings für Jobs, Profile und Feedback-Einträge.
Führt keine Änderungen an bestehenden Daten durch, außer das Einfügen von Embeddings.
"""

import sqlite3
import json
from pathlib import Path

# --------------------------------------------------
# Lokaler Import (gleicher Ordner)
# --------------------------------------------------
from embeddings import get_embedding

# --------------------------------------------------
# Pfad zur Datenbank
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]   # eine Ebene hoch = Projektroot
DB_PATH = PROJECT_ROOT / "data" / "career_agent.db"
print(f"📂 Verwende Datenbank: {DB_PATH}")

def update_table_embeddings(table, text_field, id_field="id"):
    """Erzeugt Embeddings für die angegebene Tabelle"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print(f"🔹 Generiere Embeddings für Tabelle: {table}")
    cur.execute(f"SELECT {id_field}, {text_field} FROM {table} WHERE {text_field} IS NOT NULL")
    rows = cur.fetchall()

    for row_id, text in rows:
        try:
            emb = get_embedding(text)
            emb_json = json.dumps(emb.tolist())
            cur.execute(f"UPDATE {table} SET embedding = ? WHERE {id_field} = ?", (emb_json, row_id))
        except Exception as e:
            print(f"⚠️ Fehler bei ID {row_id}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Embeddings für {table} abgeschlossen.\n")


if __name__ == "__main__":
    update_table_embeddings("jobs", "description")
    update_table_embeddings("user_profile", "summary")
    update_table_embeddings("feedback", "comment")
    update_table_embeddings("profiles", text_field="description_text")
    print("🎉 Alle Embeddings erfolgreich erstellt und gespeichert.")