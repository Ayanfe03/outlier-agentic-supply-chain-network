from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
import json
from pathlib import Path
import random
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Buyer / Procurement Agent")

#REGISTRY_URL = "http://registry:8000"
REGISTRY_URL = "http://localhost:8000"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

REPORT_DIR = Path(__file__).resolve().parents[3] / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "coord_report.json"


if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set in environment")

client = Groq(api_key=GROQ_API_KEY)

class IntentRequest(BaseModel):
    intent: str                     # e.g. "Buy 100 wheels for Ferrari assembly"
    quantity: int = 50
    region: str = "NG"              # default to Nigeria / Lagos context
    origin: str = "Lagos"
    destination: str = "Ota"

def _parse_json_maybe(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value

def _extract_supplier_query(intent: str) -> str:
    prompt = (
        "Extract the main supply item from the user's intent for supplier search. "
        "Return JSON only: {\"query\": \"<concise supplier search phrase>\"}. "
        "Example input: \"Buy 100 wheels for Ferrari assembly\" -> "
        "{\"query\": \"wheels supplier\"}."
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You extract concise supplier search queries."},
                {"role": "user", "content": f"Intent: {intent}\n{prompt}"},
            ],
            temperature=0.1,
            max_tokens=80,
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        query = data.get("query")
        if isinstance(query, str) and query.strip():
            return query.strip()
    except Exception:
        pass
    return f"{intent} supplier"

@app.on_event("startup")
async def register_self():
    payload = {
        "agent_id": "buyer-1",
        "role": "Procurement",
        "capabilities": {"actions": ["orchestrate", "procure", "coordinate", "retry"]},
        #"endpoint": "http://buyer:8002",
        "endpoint": "http://localhost:8002",
        "policies": {"region": "NG", "compliance_required": "high", "resilience": "enabled"},
        "jurisdiction": {
            "country": "Nigeria",
            "state": "Lagos",
            "compliance_standards": ["SON", "NAFDAC"],
            "restricted_regions": ["EU", "US"]
        }
    }
    try:
        r = requests.post(f"{REGISTRY_URL}/register", json=payload, timeout=10)
        r.raise_for_status()
        print("Buyer agent registered successfully")
    except Exception as e:
        print(f"Buyer registration failed: {e}")

@app.post("/intent")
async def execute_intent(req: IntentRequest):
    report = {
        "intent": req.intent,
        "quantity": req.quantity,
        "region": req.region,
        "timestamp": datetime.utcnow().isoformat(),
        "discovery_paths": [],
        "message_exchanges": [],
        "verification_logic": [],
        "policy_enforcement": [],
        "final_plan": {},
        "disruptions": []
    }

    try:
        # ── 1. Semantic discovery ────────────────────────────────────────
        supplier_params = {"q": f"{req.intent} supplier", "region": req.region}
        suppliers = requests.get(
            f"{REGISTRY_URL}/discover",
            params=supplier_params,
            timeout=30,
            proxies={"http": None, "https": None},
        ).json()

        if not suppliers:
            fallback_query = _extract_supplier_query(req.intent)
            print(f"[buyer] fallback supplier query: {fallback_query}")
            supplier_params = {"q": fallback_query, "region": req.region}
            suppliers = requests.get(
                f"{REGISTRY_URL}/discover",
                params=supplier_params,
                timeout=8,
                proxies={"http": None, "https": None},
            ).json()
            print(f"[buyer] fallback supplier results: {len(suppliers) if isinstance(suppliers, list) else suppliers}")
        if not suppliers:
            raise ValueError("No suppliers found matching intent and region")

        report["discovery_paths"].append(suppliers[0])
        supplier_endpoint = suppliers[0]["endpoint"] + "/request"

        logi_params = {"q": "logistics provider", "region": req.region}
        logistics_agents = requests.get(
            f"{REGISTRY_URL}/discover",
            params=logi_params,
            timeout=30,
            proxies={"http": None, "https": None},
        ).json()
        if not logistics_agents:
            raise ValueError("No logistics providers found")
        report["discovery_paths"].append(logistics_agents[0])
        logistics_endpoint = logistics_agents[0]["endpoint"] + "/route"

        # CrewAI orchestration removed to avoid dependency conflicts

        # ── 3. Call Supplier with disruption simulation & retry ───────────────
        disruption_occurred = False
        selected_supplier = suppliers[0]

        for attempt in range(1, 4):  # up to 3 attempts
            try:
                # Simulate realistic disruption (30% chance first attempt, 10% later)
                if random.random() < (0.3 if attempt == 1 else 0.1):
                    raise requests.exceptions.RequestException(
                        f"Simulated disruption: supplier timeout / port closure / inventory issue"
                    )

                supplier_resp = requests.post(
                    supplier_endpoint,
                    json={"part": "wheels", "quantity": req.quantity},
                    timeout=12,
                    proxies={"http": None, "https": None},
                )
                supplier_resp.raise_for_status()
                supplier_data = supplier_resp.json()

                report["message_exchanges"].append({
                    "from": "Buyer",
                    "to": selected_supplier["agent_id"],
                    "intent": "request_parts",
                    "response": supplier_data
                })
                break

            except Exception as exc:
                disruption_occurred = True
                error_detail = f"Attempt {attempt} failed: {str(exc)}"
                report["disruptions"].append(error_detail)
                report["message_exchanges"].append({"disruption": error_detail})

                if attempt == 3:
                    raise HTTPException(503, "Supplier unavailable after retries")

                # Rediscover alternative
                new_suppliers = requests.get(
                    f"{REGISTRY_URL}/discover",
                    params=supplier_params,
                    timeout=30,
                    proxies={"http": None, "https": None},
                ).json()
                if not new_suppliers or new_suppliers[0]["agent_id"] == selected_supplier["agent_id"]:
                    report["message_exchanges"].append({"note": "No better alternative found"})
                    continue

                selected_supplier = new_suppliers[0]
                supplier_endpoint = selected_supplier["endpoint"] + "/request"
                report["discovery_paths"].append({
                    "rediscovered": selected_supplier,
                    "reason": "Fallback after disruption"
                })
                report["message_exchanges"].append({
                    "resolution": f"Switched to alternative supplier: {selected_supplier['agent_id']}"
                })

        # ── 4. Call Logistics ────────────────────────────────────────────────
        logistics_resp = requests.post(
            logistics_endpoint,
            json={"origin": req.origin, "destination": req.destination, "quantity": req.quantity, "part": "wheels"},
            timeout=10,
            proxies={"http": None, "https": None},
        ).json()
        if isinstance(logistics_resp, dict):
            logistics_resp["details"] = _parse_json_maybe(logistics_resp.get("details"))

        report["message_exchanges"].append({
            "from": "Buyer",
            "to": logistics_agents[0]["agent_id"],
            "intent": "request_routing",
            "response": logistics_resp
        })

        # ── 5. Call Compliance ───────────────────────────────────────────────
        compliance_resp = requests.post(
            #"http://compliance:8004/verify",
            "http://localhost:8004/verify",
            json={"offer": supplier_data, "route": logistics_resp},
            timeout=10,
            proxies={"http": None, "https": None},
        ).json()
        if isinstance(compliance_resp, dict):
            compliance_resp["result"] = _parse_json_maybe(compliance_resp.get("result"))

        report["message_exchanges"].append({
            "from": "Buyer",
            "to": "compliance-1",
            "intent": "verify_compliance",
            "response": compliance_resp
        })

        # ── 6. Finalize report ───────────────────────────────────────────────
        report["verification_logic"] = ["Semantic discovery with cosine + policy filter", "LLM-based decision in agents"]
        report["policy_enforcement"] = [f"Region restricted to {req.region}", "Compliance agent verified offer & route"]
        logistics_details = logistics_resp.get("details") if isinstance(logistics_resp, dict) else {}
        if not isinstance(logistics_details, dict):
            logistics_details = {}
        report["final_plan"] = {
            "status": compliance_resp.get("status", "pending"),
            "total_cost_estimate": 2250.0,  # placeholder — in real version parse from responses
            "lead_time_days": 5,
            "route": logistics_details.get("route", "Lagos -> Ota"),
            "supplier_used": selected_supplier["agent_id"],
            "resilience_applied": disruption_occurred
        }

        # Save report
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)

        print(json.dumps(report["final_plan"], indent=2))
        return {"status": "success", "report_summary": report["final_plan"]}

    except Exception as e:
        import traceback
        traceback.print_exc()
        report["status"] = "failed"
        report["error"] = str(e)
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)
        raise HTTPException(status_code=500, detail=str(e))
