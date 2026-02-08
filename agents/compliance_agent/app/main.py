from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import openai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = FastAPI(title="Compliance & Verification Agent")

#REGISTRY_URL = "http://registry:8000"
REGISTRY_URL = "http://localhost:8000"
ASI_API_KEY = os.getenv("ASI_API_KEY")
if not ASI_API_KEY:
    raise ValueError("ASI_API_KEY not set in environment")
client = openai.OpenAI(
    api_key=ASI_API_KEY,
    base_url="https://inference.asicloud.cudos.org/v1",
)

class ComplianceCheck(BaseModel):
    offer: dict
    route: dict

@app.on_event("startup")
async def register_self():
    
    payload = {
        "agent_id": "compliance-1",
        "role": "ComplianceAgent",
        "capabilities": {"checks": ["policy", "region", "trade_compliance", "esg"]},
        #"endpoint": "http://compliance:8004",
        "endpoint": "http://localhost:8004",
        "policies": {"region": "NG", "enforce_level": "strict"},
        "jurisdiction": {
            "country": "Nigeria",
            "state": "Lagos",
            "compliance_standards": ["SON", "NAFDAC"],
            "restricted_regions": ["EU", "US"]
        }
    }
    try:
        requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=8)
        print("Compliance agent registered successfully")
    except Exception as e:
        print(f"Registration failed: {e}")

@app.post("/verify")
def verify_compliance(check: ComplianceCheck):
    prompt = f"""You are a strict compliance verification agent in Nigeria.
    Offer: {check.offer}
    Route: {check.route}

    Check:
    - Region/jurisdiction compliance (must be NG or allowed)
    - Trade policy alignment
    - Basic ESG considerations

    Respond in JSON:
    {{
        "status": "approved" | "rejected" | "conditional",
        "reason": "explanation",
        "risk_level": "low" | "medium" | "high",
        "required_actions": [] or list of strings
    }}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        result = resp.choices[0].message.content.strip()
        # In production you'd parse JSON properly – here we assume LLM returns valid JSON
        return {
            "verification_id": f"comp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "status": "processed",
            "result": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
