from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
import json
from pathlib import Path
import random
from datetime import datetime
import openai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Buyer / Procurement Agent")

#REGISTRY_URL = "http://registry:8000"
REGISTRY_URL = "http://localhost:8000"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

REPORT_DIR = Path(__file__).resolve().parents[3] / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "coord_report.json"


if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

class IntentRequest(BaseModel):
    intent: str                    
    region: str = "NG"              
    quantity: int | None = None
    origin: str | None = None
    destination: str | None = None

def _parse_json_maybe(value):
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("```"):
            # Strip markdown code fences if present
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        # Try to extract the first JSON object in the string
        if "{" in cleaned and "}" in cleaned:
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            candidate = cleaned[start:end]
            try:
                return json.loads(candidate)
            except Exception:
                pass
        try:
            return json.loads(cleaned)
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
            model="gpt-4o-mini",
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

def _extract_intent_fields(intent: str) -> dict:
    prompt = (
        "Extract structured fields from the intent. Return JSON only:\n"
        "{\"part\": str or null, \"quantity\": int or null, \"origin\": str or null, \"destination\": str or null}\n"
        "If missing, return null for that field."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured fields from intents."},
                {"role": "user", "content": f"Intent: {intent}\n{prompt}"},
            ],
            temperature=0.1,
            max_tokens=80,
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"part": None, "quantity": None, "origin": None, "destination": None}

@app.on_event("startup")
async def register_self():
    payloads = [
        {
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
        },
        {
            "agent_id": "buyer-2",
            "role": "Procurement",
            "capabilities": {"actions": ["orchestrate", "procure", "coordinate"]},
            "endpoint": "http://localhost:8002",
            "policies": {"region": "EU", "compliance_required": "high", "resilience": "enabled"},
            "jurisdiction": {
                "country": "Germany",
                "state": "Bavaria",
                "compliance_standards": ["CE", "RoHS"],
                "restricted_regions": ["US"]
            }
        },
        {
            "agent_id": "buyer-3",
            "role": "Procurement",
            "capabilities": {"actions": ["orchestrate", "procure", "coordinate"]},
            "endpoint": "http://localhost:8002",
            "policies": {"region": "US", "compliance_required": "medium", "resilience": "enabled"},
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
            print(f"Buyer agent registered successfully: {payload['agent_id']}")
        except Exception as e:
            print(f"Buyer registration failed for {payload['agent_id']}: {e}")

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
        # Fill missing fields from intent text
        extracted = _extract_intent_fields(req.intent)
        part = extracted.get("part") or "wheels"
        quantity = req.quantity or extracted.get("quantity") or 50
        origin = req.origin or extracted.get("origin") or "Lagos"
        destination = req.destination or extracted.get("destination") or "Ota"
        report["part"] = part
        report["quantity"] = quantity
        report["origin"] = origin
        report["destination"] = destination


        # ── 1. Semantic discovery ────────────────────────────────────────
        print("[buyer] starting discovery")
        supplier_params = {"q": f"{req.intent} supplier", "region": req.region}
        suppliers = requests.get(
            f"{REGISTRY_URL}/discover",
            params=supplier_params,
            timeout=30,
            proxies={"http": None, "https": None},
        ).json()
        print(f"[buyer] primary supplier results: {len(suppliers) if isinstance(suppliers, list) else suppliers}")

        if not suppliers:
            print("[buyer] no suppliers found, invoking LLM parser")
            fallback_query = _extract_supplier_query(req.intent)
            print(f"[buyer] fallback supplier query: {fallback_query}")
            supplier_params = {"q": fallback_query, "region": req.region}
            suppliers = requests.get(
                f"{REGISTRY_URL}/discover",
                params=supplier_params,
                timeout=30,
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
                    json={"part": part, "quantity": quantity},
                    timeout=12,
                    proxies={"http": None, "https": None},
                )
                supplier_resp.raise_for_status()
                supplier_data = supplier_resp.json()
                print(f"[buyer] supplier details raw: {supplier_data.get('details') if isinstance(supplier_data, dict) else supplier_data}")

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
            json={"origin": origin, "destination": destination, "quantity": quantity, "part": part},
            timeout=45,
            proxies={"http": None, "https": None},
        ).json()
        if isinstance(logistics_resp, dict):
            logistics_resp["details"] = _parse_json_maybe(logistics_resp.get("details"))
        print(f"[buyer] logistics details raw: {logistics_resp.get('details') if isinstance(logistics_resp, dict) else logistics_resp}")

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
            timeout=45,
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
        supplier_details = supplier_data.get("details") if isinstance(supplier_data, dict) else {}
        supplier_details = _parse_json_maybe(supplier_details)
        if not isinstance(supplier_details, dict):
            supplier_details = {}
        offer_price = supplier_details.get("offer_price")
        lead_days = supplier_details.get("lead_days")
        estimated_cost = None
        if isinstance(offer_price, (int, float)):
            estimated_cost = offer_price * quantity

        lead_time_days = None
        try:
            log_days = logistics_details.get("estimated_days")
            if isinstance(lead_days, (int, float)) and isinstance(log_days, (int, float)):
                lead_time_days = int(max(lead_days, log_days))
            elif isinstance(lead_days, (int, float)):
                lead_time_days = int(lead_days)
            elif isinstance(log_days, (int, float)):
                lead_time_days = int(log_days)
        except Exception:
            lead_time_days = None

        report["final_plan"] = {
            "status": compliance_resp.get("status", "pending"),
            "total_cost_estimate": estimated_cost if estimated_cost is not None else "N/A",
            "lead_time_days": lead_time_days if lead_time_days is not None else "N/A",
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
