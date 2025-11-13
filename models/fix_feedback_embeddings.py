import sqlite3, json
from embeddings import get_embedding

DB_PATH = "../data/career_agent.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT id, comment FROM feedback WHERE comment IS NOT NULL AND TRIM(comment) != ''")
rows = cur.fetchall()

print(f"🧩 {len(rows)} Kommentare gefunden – starte Embedding-Update...")

for fid, comment in rows:
    try:
        emb = get_embedding(comment)
        emb_json = json.dumps(emb.tolist())
        cur.execute("UPDATE feedback SET embedding = ? WHERE id = ?", (emb_json, fid))
    except Exception as e:
        print(f"⚠️ Fehler bei ID {fid}: {e}")

conn.commit()
conn.close()
print("✅ Alle Kommentare vektorisiert und gespeichert.")