from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import json
from pathlib import Path
import random
from datetime import datetime
import openai
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

app = FastAPI(title="Buyer / Procurement Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REGISTRY_URL = os.getenv("REGISTRY_URL", "http://localhost:8000")
ENDPOINT_URL = os.getenv("ENDPOINT_URL", "http://localhost:8002")
COMPLIANCE_URL = os.getenv("COMPLIANCE_URL", "http://localhost:8004")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
try:
    FX_NGN_USD = float(os.getenv("FX_NGN_USD", "0.00065"))
except Exception:
    FX_NGN_USD = 0.00065


REPORT_DIR = Path(__file__).resolve().parents[3] / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "coord_report.json"
print(f"[buyer] report path: {REPORT_PATH}")




if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

class IntentRequest(BaseModel):
    intent: str                    
    region: str | None = None              
    quantity: int | None = None
    origin: str | None = None
    destination: str | None = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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

def _extract_unit_price_from_notes(notes: str):
    if not isinstance(notes, str):
        return None
    import re
    patterns = [
        r'(?i)per unit[^0-9]*([0-9][0-9,]*)',
        r'(?i)unit price[^0-9]*([0-9][0-9,]*)',
        r'(?i)price per unit[^0-9]*([0-9][0-9,]*)',
        r'(?i)(?:ngn|₦)\s*([0-9][0-9,]*)\s*(?:per unit|/unit)',
    ]
    for pat in patterns:
        m = re.search(pat, notes)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except Exception:
                return None
    return None

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

def _matches_part(agent: dict, part: str) -> bool:
    try:
        caps = agent.get("capabilities", {})
        parts = caps.get("parts", [])
        part_lower = part.lower()
        return any(part_lower in str(p).lower() for p in parts)
    except Exception:
        return False

async def _emit_step(agent_id: str, role: str, action: str, result: str):
    await manager.broadcast(
        {
            "type": "step",
            "step": {
                "agentId": agent_id,
                "agentName": agent_id,
                "agentRole": role,
                "action": action,
                "result": result,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
    )

async def _emit_phase(agent_id: str, role: str, action: str):
    await manager.broadcast(
        {
            "type": "phase",
            "phase": {
                "agentId": agent_id,
                "agentName": agent_id,
                "agentRole": role,
                "action": action,
            },
        }
    )

@app.on_event("startup")
async def register_self():
    payloads = [
        {
            "agent_id": "buyer-1",
            "role": "Procurement",
            "capabilities": {"actions": ["orchestrate", "procure", "coordinate", "retry"]},
            "endpoint": ENDPOINT_URL,
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
            "endpoint": ENDPOINT_URL,
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
            "endpoint": ENDPOINT_URL,
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
        await manager.broadcast({"type": "status", "status": "running", "intent": req.intent})
        await _emit_phase("buyer-1", "buyer", "orchestrate")
        # Fill missing fields from intent text
        region = req.region or "NG"
        extracted = _extract_intent_fields(req.intent)
        part = extracted.get("part") or "wheels"
        quantity = req.quantity or extracted.get("quantity") or 50
        origin = req.origin or extracted.get("origin") or "Lagos"
        destination = req.destination or extracted.get("destination") or "Ota"
        report["part"] = part
        report["quantity"] = quantity
        report["origin"] = origin
        report["destination"] = destination
        report["region"] = region


        # ── 1. Semantic discovery ────────────────────────────────────────
        print("[buyer] starting discovery")
        supplier_query = f"{part} supplier"
        await _emit_step("buyer-1", "buyer", "discover_suppliers", f"query: {supplier_query}")
        supplier_params = {"q": supplier_query, "region": region}
        suppliers = requests.get(
            f"{REGISTRY_URL}/discover",
            params=supplier_params,
            timeout=30,
            proxies={"http": None, "https": None},
        ).json()
        print(f"[buyer] primary supplier results: {len(suppliers) if isinstance(suppliers, list) else suppliers}")

        if suppliers:
            suppliers = [s for s in suppliers if _matches_part(s, part)]
        if not suppliers:
            print("[buyer] no suppliers found, invoking LLM parser")
            fallback_query = _extract_supplier_query(req.intent)
            print(f"[buyer] fallback supplier query: {fallback_query}")
            await _emit_step("buyer-1", "buyer", "discover_suppliers_fallback", f"query: {fallback_query}")
            supplier_params = {"q": fallback_query, "region": region}
            suppliers = requests.get(
                f"{REGISTRY_URL}/discover",
                params=supplier_params,
                timeout=30,
                proxies={"http": None, "https": None},
            ).json()
            print(f"[buyer] fallback supplier results: {len(suppliers) if isinstance(suppliers, list) else suppliers}")
            if suppliers:
                suppliers = [s for s in suppliers if _matches_part(s, part)]
        if not suppliers:
            raise ValueError("No suppliers found matching intent and region")

        report["discovery_paths"].append(suppliers[0])
        supplier_endpoint = suppliers[0]["endpoint"] + "/request"
        await _emit_step(suppliers[0]["agent_id"], "supplier", "supplier_selected", "selected for request")
        await _emit_phase(suppliers[0]["agent_id"], "supplier", "request_parts")

        logi_params = {"q": "logistics provider", "region": region}
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
        await _emit_step(logistics_agents[0]["agent_id"], "logistics", "logistics_selected", "selected for routing")
        await _emit_phase(logistics_agents[0]["agent_id"], "logistics", "request_routing")

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
                await _emit_step(selected_supplier["agent_id"], "supplier", "request_parts", str(supplier_data.get("details", ""))[:160])
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
                await _emit_step(selected_supplier["agent_id"], "supplier", "supplier_switched", "fallback after disruption")

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
        await _emit_step(logistics_agents[0]["agent_id"], "logistics", "request_routing", str(logistics_resp.get("details", ""))[:160])

        # ── 5. Call Compliance ───────────────────────────────────────────────
        compliance_resp = requests.post(
            f"{COMPLIANCE_URL}/verify",
            json={"offer": supplier_data, "route": logistics_resp},
            timeout=45,
            proxies={"http": None, "https": None},
        ).json()
        await _emit_phase("compliance-1", "compliance", "verify_compliance")
        if isinstance(compliance_resp, dict):
            compliance_resp["result"] = _parse_json_maybe(compliance_resp.get("result"))

        report["message_exchanges"].append({
            "from": "Buyer",
            "to": "compliance-1",
            "intent": "verify_compliance",
            "response": compliance_resp
        })
        await _emit_step("compliance-1", "compliance", "verify_compliance", str(compliance_resp.get("result", ""))[:160])

        # ── 6. Finalize report ───────────────────────────────────────────────
        report["verification_logic"] = ["Semantic discovery with cosine + policy filter", "LLM-based decision in agents"]
        report["policy_enforcement"] = [f"Region restricted to {region}", "Compliance agent verified offer & route"]
        logistics_details = logistics_resp.get("details") if isinstance(logistics_resp, dict) else {}
        if not isinstance(logistics_details, dict):
            logistics_details = {}
        supplier_details = supplier_data.get("details") if isinstance(supplier_data, dict) else {}
        supplier_details = _parse_json_maybe(supplier_details)
        if not isinstance(supplier_details, dict):
            supplier_details = {}
        offer_price = supplier_details.get("offer_price")
        notes = supplier_details.get("notes", "")
        unit_price = _extract_unit_price_from_notes(notes)
        lead_days = supplier_details.get("lead_days")
        estimated_cost = None
        total_cost_ngn = None
        if isinstance(unit_price, (int, float)):
            estimated_cost = unit_price * quantity
            total_cost_ngn = estimated_cost
        elif isinstance(offer_price, (int, float)):
            if isinstance(notes, str) and "per unit" in notes.lower():
                estimated_cost = offer_price * quantity
                total_cost_ngn = estimated_cost
            else:
                estimated_cost = offer_price
                total_cost_ngn = estimated_cost
        log_cost = logistics_details.get("estimated_cost_ngn")
        if isinstance(log_cost, (int, float)):
            total_cost_ngn = (total_cost_ngn or 0) + log_cost
        total_cost_usd = round(total_cost_ngn * FX_NGN_USD, 2) if isinstance(total_cost_ngn, (int, float)) else None

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

        total_cost_display = total_cost_usd if (region == "NG" and total_cost_usd is not None) else estimated_cost
        report["final_plan"] = {
            "status": compliance_resp.get("status", "pending"),
            "total_cost_estimate": total_cost_display if total_cost_display is not None else "N/A",
            "total_cost_ngn": total_cost_ngn if total_cost_ngn is not None else "N/A",
            "total_cost_usd": total_cost_usd if total_cost_usd is not None else "N/A",
            "lead_time_days": lead_time_days if lead_time_days is not None else "N/A",
            "route": logistics_details.get("route", "Lagos -> Ota"),
            "supplier_used": selected_supplier["agent_id"],
            "resilience_applied": disruption_occurred
        }

        # Save report
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)

        print(json.dumps(report["final_plan"], indent=2))
        await manager.broadcast({"type": "status", "status": "completed"})
        return {"status": "success", "report": report, "report_summary": report["final_plan"]}

    except Exception as e:
        import traceback
        traceback.print_exc()
        report["status"] = "failed"
        report["error"] = str(e)
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)
        await manager.broadcast({"type": "status", "status": "failed", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
