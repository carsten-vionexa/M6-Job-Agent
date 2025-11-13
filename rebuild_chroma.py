#!/usr/bin/env python3
from chromadb import PersistentClient
import sqlite3, json, numpy as np
from pathlib import Path

DB_PATH = Path("data/career_agent.db")
CHROMA_PATH = Path("data/chroma_data")
CHROMA_PATH.mkdir(parents=True, exist_ok=True)

client = PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection("feedback_embeddings")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
    SELECT f.id, f.comment, f.profile_id, f.feedback_value, j.title, j.embedding
    FROM feedback f
    JOIN jobs j ON f.job_id = j.id
    WHERE f.comment IS NOT NULL AND f.comment != '' AND j.embedding IS NOT NULL
""")

rows = cur.fetchall()
conn.close()

for fid, comment, pid, fval, title, emb_json in rows:
    try:
        job_vec = np.array(json.loads(emb_json))
        metadata = {
            "profile_id": pid,
            "feedback_value": fval,
            "title": title,
            "comment": comment,
        }
        collection.add(
            ids=[str(fid)],
            embeddings=[job_vec.tolist()],
            metadatas=[metadata],
        )
    except Exception as e:
        print(f"⚠️ Fehler bei ID {fid}: {e}")

print(f"✅ Chroma DB neu aufgebaut – {collection.count()} Einträge.")