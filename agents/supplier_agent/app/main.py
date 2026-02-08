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
    payloads = [
        {
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
        },
        {
            "agent_id": "supplier-2",
            "role": "Supplier",
            "capabilities": {"parts": ["sensors", "electronics", "control units"]},
            "endpoint": "http://localhost:8001",
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
            "endpoint": "http://localhost:8001",
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
            requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=5)
            print(f"Supplier agent registered successfully: {payload['agent_id']}")
        except Exception as e:
            print(f"Registry not ready for {payload['agent_id']} - retry later: {e}")

@app.post("/request")
def handle_request(req: Request):
    prompt = f"""You are a Supplier agent in Lagos.
    Inventory: 150 {req.part}s available.
    Request: {req.quantity} units.
    Negotiate price, lead time, confirm NG compliance.
    Respond in JSON: {{"offer_price": number, "lead_days": int, "notes": str}}"""
    
    try:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=200
        )
        decision = resp.choices[0].message.content.strip()
        return {"status": "offer_sent", "details": decision}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "details": str(e)}
