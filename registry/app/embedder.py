from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_text(text: str) -> np.ndarray:
    return model.encode(text, convert_to_numpy=True)

def flatten_metadata(role: str, cap: dict, pol: dict, jur: dict) -> str:
    parts = [f"role: {role}"]
    for k, v in cap.items(): parts.append(f"{k}: {v}")
    for k, v in pol.items(): parts.append(f"{k}: {v}")
    for k, v in jur.items(): parts.append(f"{k}: {v}")
    return " ".join(parts)
