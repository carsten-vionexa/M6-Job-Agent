# src/learning_engine.py
from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np

# Neuer Chroma-Client (seit v0.5)
client = chromadb.PersistentClient(path="data/chroma")
collection = client.get_or_create_collection(name="job_feedback")

embedder = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str):
    """Erzeugt Vektor für beliebigen Text."""
    return embedder.encode([text])[0].tolist()


def store_feedback(job: dict, profile_id: int, feedback_value: int, base_score: float, comment: str = None):
    """Speichert Feedback-Eintrag in Chroma."""
    text_parts = [
        job.get("titel") or job.get("title") or "",
        job.get("beschreibung") or "",
        comment or "",
    ]
    text = "\n".join([t for t in text_parts if t.strip()])
    embedding = embed_text(text)

    doc_id = f"{profile_id}_{job.get('refnr','unknown')}"
    metadata = {
        "job_id": job.get("id"),
        "profile_id": profile_id,
        "base_score": base_score,
        "feedback_value": feedback_value,
        "title": job.get("titel") or job.get("title"),
        "company": job.get("arbeitgeber") or job.get("company"),
        "location": job.get("ort") or job.get("location"),
    }

    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata],
    )
    #client.persist()


def predict_fit_score(job: dict, base_score: float):
    """Berechnet persönlichen Fit-Score aus BaseScore + Chroma-Ähnlichkeiten."""
    text = " ".join([
        job.get("titel") or job.get("title") or "",
        job.get("beschreibung") or "",
    ])
    emb = np.array(embed_text(text))

    # Daten aus Chroma holen
    all_data = collection.get(include=["embeddings", "metadatas"])
    embeddings = None
    metas = []

    if isinstance(all_data, dict):
        embeddings = all_data.get("embeddings")
        metas = all_data.get("metadatas", [])

    # ✅ Sicher prüfen, ob wirklich Vektoren vorhanden sind
    if embeddings is None:
        return base_score
    if isinstance(embeddings, list) and len(embeddings) == 0:
        return base_score
    if isinstance(embeddings, np.ndarray) and embeddings.size == 0:
        return base_score

    embs = np.array(embeddings)
    if embs.ndim == 0 or embs.size == 0:
        return base_score

    # Kosinusähnlichkeiten berechnen
    norms = np.linalg.norm(embs, axis=1) * np.linalg.norm(emb)
    sims = np.dot(embs, emb) / (norms + 1e-8)
    sims = np.nan_to_num(sims)

    # Feedback-Werte
    weights = np.array([m.get("feedback_value", 0) for m in metas])
    if weights.size == 0:
        return base_score

    learned_signal = np.sum(sims * weights) / (np.sum(np.abs(weights)) + 1e-6)

    # Kombinieren mit BaseScore
    fit_score = 0.6 * base_score + 0.4 * (learned_signal + 1) / 2  # Normierung 0–1
    return float(np.clip(fit_score, 0, 1))