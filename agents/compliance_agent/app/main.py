from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import openai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = FastAPI(title="Compliance & Verification Agent")

REGISTRY_URL = os.getenv("REGISTRY_URL", "http://localhost:8000")
ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:8004")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

class ComplianceCheck(BaseModel):
    offer: dict
    route: dict

@app.on_event("startup")
async def register_self():
    
    payloads = [
        {
            "agent_id": "compliance-1",
            "role": "ComplianceAgent",
            "capabilities": {"checks": ["policy", "region", "trade_compliance", "esg"]},
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "NG", "enforce_level": "strict"},
            "jurisdiction": {
                "country": "Nigeria",
                "state": "Lagos",
                "compliance_standards": ["SON", "NAFDAC"],
                "restricted_regions": ["EU", "US"]
            }
        },
        {
            "agent_id": "compliance-2",
            "role": "ComplianceAgent",
            "capabilities": {"checks": ["policy", "region", "trade_compliance", "esg"]},
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "EU", "enforce_level": "strict"},
            "jurisdiction": {
                "country": "Germany",
                "state": "Bavaria",
                "compliance_standards": ["CE", "RoHS", "GDPR"],
                "restricted_regions": ["US"]
            }
        },
        {
            "agent_id": "compliance-3",
            "role": "ComplianceAgent",
            "capabilities": {"checks": ["policy", "region", "trade_compliance", "esg"]},
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "US", "enforce_level": "moderate"},
            "jurisdiction": {
                "country": "United States",
                "state": "California",
                "compliance_standards": ["FTC", "SOX"],
                "restricted_regions": ["EU"]
            }
        },
    ]
    for payload in payloads:
        try:
            r = requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=10)
            r.raise_for_status()
            print(f"Compliance agent registered successfully: {payload['agent_id']}")
        except Exception as e:
            print(f"Compliance registration failed for {payload['agent_id']}: {e}")
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
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300
        )
        result = resp.choices[0].message.content.strip()
        return {
            "verification_id": f"comp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "status": "processed",
            "result": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
