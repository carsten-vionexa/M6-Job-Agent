# models/embeddings.py
from openai import OpenAI
import numpy as np
from pathlib import Path
import sys

client = OpenAI()

# --------------------------------------------------
# Pfadkorrektur (damit src & pages importierbar sind)
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def get_embedding(text: str, model: str = "text-embedding-3-small"):
    """Erstellt einen Embedding-Vektor aus beliebigem Text."""
    if not text or not text.strip():
        return np.zeros(1536)  # leere Eingaben absichern
    response = client.embeddings.create(
        model=model,
        input=text
    )
    return np.array(response.data[0].embedding)