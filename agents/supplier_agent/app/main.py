from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import openai
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Supplier Agent")

REGISTRY_URL = os.getenv("REGISTRY_URL", "http://localhost:8000")
ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:8001")

class Request(BaseModel):
    part: str
    quantity: int

@app.on_event("startup")
async def register_self():
    payloads = [
        {
            "agent_id": "supplier-1",
            "role": "Supplier",
            "capabilities": {"parts": ["wheels", "tires", "engines"]},
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "NG", "compliance": "basic"},
            "jurisdiction": {
                "country": "Nigeria",
                "state": "Lagos",
                "compliance_standards": ["SON", "NAFDAC"],
                "restricted_regions": ["EU", "US"]
            }
        },
        {
            "agent_id": "supplier-2",
            "role": "Supplier",
            "capabilities": {"parts": ["sensors", "electronics", "control units"]},
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "EU", "compliance": "strict"},
            "jurisdiction": {
                "country": "Germany",
                "state": "Bavaria",
                "compliance_standards": ["CE", "RoHS"],
                "restricted_regions": ["NG"]
            }
        },
        {
            "agent_id": "supplier-3",
            "role": "Supplier",
            "capabilities": {"parts": ["steel", "aluminum", "fasteners"]},
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "US", "compliance": "standard"},
            "jurisdiction": {
                "country": "United States",
                "state": "Michigan",
                "compliance_standards": ["ASTM", "ISO9001"],
                "restricted_regions": ["EU"]
            }
        },
    ]
    for payload in payloads:
        try:
            r = requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=10)
            r.raise_for_status()
            print(f"Supplier agent registered successfully: {payload['agent_id']}")
        except Exception as e:
            print(f"Supplier registration failed for {payload['agent_id']}: {e}")

@app.post("/request")
def handle_request(req: Request):
    prompt = f"""You are a Supplier agent in Lagos.
    Inventory: 150 {req.part}s available.
    Request: {req.quantity} units.
    Negotiate price, lead time, confirm NG compliance.
    Respond in JSON: {{"offer_price": number, "lead_days": int, "notes": str}}"""
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=200
        )
        print(f"[supplier] raw response: {resp}")
        decision = resp.choices[0].message.content.strip()
        if not decision:
            print("[supplier] empty content from LLM")
        return {"status": "offer_sent", "details": decision}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "details": str(e)}
