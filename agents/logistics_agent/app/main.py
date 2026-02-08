from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import openai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Logistics & Routing Agent")

#REGISTRY_URL = "http://registry:8000"
REGISTRY_URL = "http://localhost:8000"
ASI_API_KEY = os.getenv("ASI_API_KEY")
if not ASI_API_KEY:
    raise ValueError("ASI_API_KEY not set in environment")
client = openai.OpenAI(
    api_key=ASI_API_KEY,
    base_url="https://inference.asicloud.cudos.org/v1",
)

class RouteRequest(BaseModel):
    origin: str
    destination: str
    quantity: int
    part: str = "unknown"

@app.on_event("startup")
async def register_self():
    payloads = [
        {
            "agent_id": "logistics-1",
            "role": "LogisticsProvider",
            "capabilities": {"regions": ["NG", "West Africa"], "modes": ["road", "port", "hub"]},
            #"endpoint": "http://logistics:8003",
            "endpoint": "http://localhost:8003",
            "policies": {"region": "NG", "lead_time_max_days": 7},
            "jurisdiction": {
                "country": "Nigeria",
                "state": "Lagos",
                "compliance_standards": ["SON", "NAFDAC"],
            }
        },
        {
            "agent_id": "logistics-2",
            "role": "LogisticsProvider",
            "capabilities": {"regions": ["EU"], "modes": ["air", "hub"]},
            "endpoint": "http://localhost:8003",
            "policies": {"region": "EU", "lead_time_max_days": 3},
            "jurisdiction": {
                "country": "Netherlands",
                "state": "North Holland",
                "compliance_standards": ["EU-SEC", "CE"],
            }
        },
        {
            "agent_id": "logistics-3",
            "role": "LogisticsProvider",
            "capabilities": {"regions": ["US"], "modes": ["rail", "road"]},
            "endpoint": "http://localhost:8003",
            "policies": {"region": "US", "lead_time_max_days": 5},
            "jurisdiction": {
                "country": "United States",
                "state": "Illinois",
                "compliance_standards": ["DOT", "FMCSA"],
            }
        },
    ]
    for payload in payloads:
        try:
            requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=8)
            print(f"Logistics agent registered successfully: {payload['agent_id']}")
        except Exception as e:
            print(f"Registration failed for {payload['agent_id']}: {e}")

@app.post("/route")
def propose_route(req: RouteRequest):
    prompt = f"""You are a logistics routing agent based in Lagos, Nigeria.
    Request: Transport {req.quantity} units of {req.part} from {req.origin} to {req.destination}.

    Consider:
    - Current Lagos port/hub status
    - Road/port options
    - Estimated cost and time
    - Disruptions (simulate minor risk)

    Respond in JSON:
    {{
        "route": "description",
        "estimated_days": int,
        "estimated_cost_ngn": float,
        "risk_level": "low|medium|high",
        "notes": "any warnings"
    }}
    """

    try:
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.45,
            max_tokens=250
        )
        result = resp.choices[0].message.content.strip()
        return {
            "proposal_id": f"log-{os.urandom(4).hex()}",
            "status": "proposed",
            "details": result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
