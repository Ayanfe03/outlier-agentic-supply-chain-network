import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def embed_text(text: str):
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return resp.data[0].embedding

def flatten_metadata(role: str, cap: dict, pol: dict, jur: dict) -> str:
    parts = [f"role: {role}"]
    for k, v in cap.items(): parts.append(f"{k}: {v}")
    for k, v in pol.items(): parts.append(f"{k}: {v}")
    for k, v in jur.items(): parts.append(f"{k}: {v}")
    return " ".join(parts)
