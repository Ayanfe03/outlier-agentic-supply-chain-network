from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import openai
from dotenv import load_dotenv

load_dotenv()
ASI_API_KEY = os.getenv("ASI_API_KEY")
if not ASI_API_KEY:
    raise ValueError("ASI_API_KEY not set in environment")
client = openai.OpenAI(
    api_key=ASI_API_KEY,
    base_url="https://inference.asicloud.cudos.org/v1",
)

app = FastAPI(title="Supplier Agent")

# REGISTRY_URL = "http://registry:8000"

REGISTRY_URL = "http://localhost:8000"

class Request(BaseModel):
    part: str
    quantity: int

@app.on_event("startup")
async def register_self():
    payload = {
        "agent_id": "supplier-1",
        "role": "Supplier",
        "capabilities": {"parts": ["wheels", "tires", "engines"]},
        # "endpoint": "http://supplier:8001",
        "endpoint": "http://localhost:8001",
        "policies": {"region": "NG", "compliance": "basic"},
        "jurisdiction": {
            "country": "Nigeria",
            "state": "Lagos",
            "compliance_standards": ["SON", "NAFDAC"],
            "restricted_regions": ["EU", "US"]
        }
    }
    try:
        requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=5)
        print("Supplier registered")
    except:
        print("Registry not ready yet - retry later")

@app.post("/request")
def handle_request(req: Request):
    prompt = f"""You are a Supplier agent in Lagos.
    Inventory: 150 {req.part}s available.
    Request: {req.quantity} units.
    Negotiate price, lead time, confirm NG compliance.
    Respond in JSON: {{"offer_price": number, "lead_days": int, "notes": str}}"""
    
    resp = client.chat.completions.create(
        model="gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=200
    )
    try:
        decision = resp.choices[0].message.content.strip()
        return {"status": "offer_sent", "details": decision}
    except:
        return {"status": "error", "details": "LLM failed"}
