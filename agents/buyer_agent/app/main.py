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
import anyio

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
try:
    FX_EUR_USD = float(os.getenv("FX_EUR_USD", "1.08"))
except Exception:
    FX_EUR_USD = 1.08
try:
    FX_USD_USD = float(os.getenv("FX_USD_USD", "1.0"))
except Exception:
    FX_USD_USD = 1.0


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

def _infer_region(intent: str, origin: str | None, destination: str | None) -> str | None:
    text = f"{intent} {origin or ''} {destination or ''}".lower()
    ng = ["nigeria", "lagos", "abuja", "kano", "ibadan", "ota", "ogun", "port harcourt"]
    eu = ["eu", "europe", "germany", "berlin", "munich", "bavaria", "france", "paris", "netherlands", "amsterdam", "london", "uk", "united kingdom", "england", "spain", "italy"]
    us = ["us", "usa", "united states", "america", "california", "texas", "new york", "illinois", "chicago", "michigan"]
    if any(k in text for k in ng):
        return "NG"
    if any(k in text for k in eu):
        return "EU"
    if any(k in text for k in us):
        return "US"
    return None

async def _get_json(url: str, **kwargs):
    def _do():
        resp = requests.get(url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    return await anyio.to_thread.run_sync(_do)

async def _post_json(url: str, **kwargs):
    def _do():
        resp = requests.post(url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    return await anyio.to_thread.run_sync(_do)

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
            temperature=0.0,
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
        "{\"part\": str or null, \"quantity\": int or null, \"origin\": str or null, \"destination\": str or null, \"region\": str or null}\n"
        "If missing, return null for that field."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured fields from intents."},
                {"role": "user", "content": f"Intent: {intent}\n{prompt}"},
            ],
            temperature=0.0,
            max_tokens=80,
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"part": None, "quantity": None, "origin": None, "destination": None, "region": None}

def _infer_region_llm(origin: str | None, destination: str | None, intent: str) -> str | None:
    prompt = (
        "Infer the supply chain region from the origin/destination and intent. "
        "Return JSON only: {\"region\": \"NG\"|\"EU\"|\"US\"|null}."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You infer regions from locations."},
                {"role": "user", "content": f"Origin: {origin}\nDestination: {destination}\nIntent: {intent}\n{prompt}"},
            ],
            temperature=0.0,
            max_tokens=50,
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        region = data.get("region")
        if isinstance(region, str) and region.strip():
            return region.strip()
    except Exception:
        pass
    return None

def _matches_part(agent: dict, part: str) -> bool:
    try:
        caps = agent.get("capabilities", {})
        parts = caps.get("parts", [])
        part_lower = part.lower()
        synonyms = {
            "aluminium": "aluminum",
            "tyres": "tires",
            "colour": "color",
            "fibre": "fiber",
        }
        if part_lower in synonyms:
            part_lower = synonyms[part_lower]
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
        extracted = _extract_intent_fields(req.intent)
        part = extracted.get("part") or "wheels"
        quantity = req.quantity or extracted.get("quantity") or 50
        origin = req.origin or extracted.get("origin")
        destination = req.destination or extracted.get("destination")
        region = req.region or extracted.get("region") or _infer_region(req.intent, origin, destination)
        if not region and (origin or destination):
            region = _infer_region_llm(origin, destination, req.intent)
        report["part"] = part
        report["quantity"] = quantity
        report["origin"] = origin
        report["destination"] = destination
        if region:
            report["region"] = region
        else:
            if not origin and not destination:
                await manager.broadcast({"type": "status", "status": "failed", "error": "region_required"})
                raise HTTPException(
                    status_code=400,
                    detail="Please specify a region or include an origin/destination in your intent.",
                )


        # ── 1. Semantic discovery ────────────────────────────────────────
        print("[buyer] starting discovery")
        supplier_query = f"{part} supplier"
        await _emit_step("buyer-1", "buyer", "discover_suppliers", f"query: {supplier_query}")
        supplier_params = {"q": supplier_query}
        if region:
            supplier_params["region"] = region
        suppliers = await _get_json(
            f"{REGISTRY_URL}/discover",
            params=supplier_params,
            timeout=30,
            proxies={"http": None, "https": None},
        )
        print(f"[buyer] primary supplier results: {len(suppliers) if isinstance(suppliers, list) else suppliers}")

        if suppliers:
            suppliers = [s for s in suppliers if _matches_part(s, part)]
        if not suppliers:
            print("[buyer] no suppliers found, invoking LLM parser")
            fallback_query = _extract_supplier_query(req.intent)
            print(f"[buyer] fallback supplier query: {fallback_query}")
            await _emit_step("buyer-1", "buyer", "discover_suppliers_fallback", f"query: {fallback_query}")
            supplier_params = {"q": fallback_query}
            if region:
                supplier_params["region"] = region
            suppliers = await _get_json(
                f"{REGISTRY_URL}/discover",
                params=supplier_params,
                timeout=30,
                proxies={"http": None, "https": None},
            )
            print(f"[buyer] fallback supplier results: {len(suppliers) if isinstance(suppliers, list) else suppliers}")
            if suppliers:
                suppliers = [s for s in suppliers if _matches_part(s, part)]
        if not suppliers:
            raise ValueError("No suppliers found matching intent and region")

        report["discovery_paths"].append(suppliers[0])
        if not region:
            region = suppliers[0].get("policies", {}).get("region") or region
            if region:
                report["region"] = region
        if not origin:
            origin = (
                suppliers[0].get("jurisdiction", {}).get("state")
                or suppliers[0].get("jurisdiction", {}).get("country")
            )
            report["origin"] = origin
        if not destination:
            destination = origin
            report["destination"] = destination
        supplier_endpoint = suppliers[0]["endpoint"] + "/request"
        await _emit_step(suppliers[0]["agent_id"], "supplier", "supplier_selected", "selected for request")
        await _emit_phase(suppliers[0]["agent_id"], "supplier", "request_parts")

        logi_params = {"q": "logistics provider"}
        if region:
            logi_params["region"] = region
        logistics_agents = await _get_json(
            f"{REGISTRY_URL}/discover",
            params=logi_params,
            timeout=30,
            proxies={"http": None, "https": None},
        )
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

                supplier_data = await _post_json(
                    supplier_endpoint,
                    json={"part": part, "quantity": quantity, "region": region},
                    timeout=12,
                    proxies={"http": None, "https": None},
                )
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
                new_suppliers = await _get_json(
                    f"{REGISTRY_URL}/discover",
                    params=supplier_params,
                    timeout=30,
                    proxies={"http": None, "https": None},
                )
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
        logistics_resp = await _post_json(
            logistics_endpoint,
            json={"origin": origin, "destination": destination, "quantity": quantity, "part": part},
            timeout=45,
            proxies={"http": None, "https": None},
        )
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
        compliance_params = {"q": "compliance agent"}
        if region:
            compliance_params["region"] = region
        compliance_agents = await _get_json(
            f"{REGISTRY_URL}/discover",
            params=compliance_params,
            timeout=30,
            proxies={"http": None, "https": None},
        )
        compliance_agent = compliance_agents[0] if compliance_agents else None
        if compliance_agent:
            report["discovery_paths"].append(compliance_agent)
        compliance_endpoint = (
            compliance_agent["endpoint"] + "/verify"
            if compliance_agent and compliance_agent.get("endpoint")
            else f"{COMPLIANCE_URL}/verify"
        )
        await _emit_step(
            (compliance_agent["agent_id"] if compliance_agent else "compliance-1"),
            "compliance",
            "compliance_selected",
            "selected for verification",
        )
        await _emit_phase(
            (compliance_agent["agent_id"] if compliance_agent else "compliance-1"),
            "compliance",
            "verify_compliance",
        )
        compliance_resp = await _post_json(
            compliance_endpoint,
            json={
                "offer": supplier_data,
                "route": logistics_resp,
                "region": region,
                "jurisdiction": compliance_agent.get("jurisdiction") if compliance_agent else None,
            },
            timeout=45,
            proxies={"http": None, "https": None},
        )
        if isinstance(compliance_resp, dict):
            compliance_resp["result"] = _parse_json_maybe(compliance_resp.get("result"))

        report["message_exchanges"].append({
            "from": "Buyer",
            "to": (compliance_agent["agent_id"] if compliance_agent else "compliance-1"),
            "intent": "verify_compliance",
            "response": compliance_resp
        })
        await _emit_step(
            (compliance_agent["agent_id"] if compliance_agent else "compliance-1"),
            "compliance",
            "verify_compliance",
            str(compliance_resp.get("result", ""))[:160],
        )

        # ── 6. Finalize report ───────────────────────────────────────────────
        report["verification_logic"] = ["Semantic discovery with cosine + policy filter", "LLM-based decision in agents"]
        report["policy_enforcement"] = [
            f"Region restricted to {region}",
            f"Compliance agent verified offer & route ({compliance_agent['agent_id'] if compliance_agent else 'compliance-1'})"
        ]
        logistics_details = logistics_resp.get("details") if isinstance(logistics_resp, dict) else {}
        if not isinstance(logistics_details, dict):
            logistics_details = {}
        supplier_details = supplier_data.get("details") if isinstance(supplier_data, dict) else {}
        supplier_details = _parse_json_maybe(supplier_details)
        if not isinstance(supplier_details, dict):
            supplier_details = {}
        unit_price = supplier_details.get("unit_price")
        supplier_currency = supplier_details.get("currency")
        available_now = supplier_details.get("available_now")
        remaining_qty = supplier_details.get("remaining_qty")
        lead_days_remaining = supplier_details.get("lead_days_remaining")
        total_price_full = supplier_details.get("total_price_full")
        total_price_now = supplier_details.get("total_price_now")
        offer_price = supplier_details.get("offer_price")
        if total_price_full is None and isinstance(unit_price, (int, float)) and isinstance(quantity, (int, float)):
            total_price_full = unit_price * quantity
        if total_price_full is None and isinstance(offer_price, (int, float)):
            total_price_full = offer_price
        estimated_cost = total_price_full if isinstance(total_price_full, (int, float)) else None
        lead_days = lead_days_remaining if isinstance(lead_days_remaining, (int, float)) else supplier_details.get("lead_days")
        total_cost_ngn = None
        total_cost_usd = None
        if isinstance(estimated_cost, (int, float)):
            if (supplier_currency or "").upper() == "EUR":
                total_cost_usd = (total_cost_usd or 0) + (estimated_cost * FX_EUR_USD)
            elif (supplier_currency or "").upper() == "USD":
                total_cost_usd = (total_cost_usd or 0) + (estimated_cost * FX_USD_USD)
            else:
                total_cost_ngn = (total_cost_ngn or 0) + estimated_cost
        log_cost = logistics_details.get("estimated_cost")
        log_currency = None
        if isinstance(logistics_details, dict):
            log_currency = logistics_details.get("currency")
        if log_cost is None:
            log_cost = logistics_details.get("estimated_cost_ngn")
            if log_cost is not None:
                log_currency = "NGN"
        if isinstance(log_cost, (int, float)):
            if (log_currency or "").upper() == "EUR":
                total_cost_usd = (total_cost_usd or 0) + (log_cost * FX_EUR_USD)
            elif (log_currency or "").upper() == "USD":
                total_cost_usd = (total_cost_usd or 0) + (log_cost * FX_USD_USD)
            else:
                total_cost_ngn = (total_cost_ngn or 0) + log_cost
        if total_cost_usd is None and isinstance(total_cost_ngn, (int, float)):
            total_cost_usd = total_cost_ngn * FX_NGN_USD
        total_cost_usd = round(total_cost_usd, 2) if isinstance(total_cost_usd, (int, float)) else None

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

        total_cost_display = total_cost_usd if total_cost_usd is not None else estimated_cost
        report["final_plan"] = {
            "status": compliance_resp.get("status", "pending"),
            "total_cost_estimate": total_cost_usd if total_cost_usd is not None else "N/A",
            "total_cost_ngn": total_cost_ngn if total_cost_ngn is not None else "N/A",
            "total_cost_usd": total_cost_usd if total_cost_usd is not None else "N/A",
            "lead_time_days": lead_time_days if lead_time_days is not None else "N/A",
            "route": logistics_details.get("route", "Lagos -> Ota"),
            "supplier_used": selected_supplier["agent_id"],
            "resilience_applied": disruption_occurred
        }

        # Human-friendly summary
        shipment_note = (
            f"Supplier can ship {available_now} units now and {remaining_qty} later (~{lead_days_remaining} days)."
            if isinstance(remaining_qty, (int, float)) and remaining_qty > 0
            else "Supplier can fulfill the full order immediately."
        )
        route_note = f"Logistics proposes: {logistics_details.get('route', 'route pending')}."
        cost_note = (
            f"Estimated total cost: ${round(total_cost_display, 2)}."
            if isinstance(total_cost_display, (int, float))
            else "Estimated total cost: N/A."
        )
        report["human_summary"] = f"{shipment_note} {route_note} Lead time: {lead_time_days} days. {cost_note}"
        brief_points = []
        if isinstance(unit_price, (int, float)):
            price_line = f"Supplier unit price: {unit_price} {supplier_currency or ''}".strip()
            if isinstance(available_now, (int, float)) and isinstance(remaining_qty, (int, float)):
                price_line += f" (available now: {int(available_now)}, remaining: {int(remaining_qty)})"
            brief_points.append(price_line)
        if isinstance(total_price_full, (int, float)):
            brief_points.append(f"Supplier total: {total_price_full} {supplier_currency or ''}".strip())
        if isinstance(logistics_details, dict) and logistics_details.get("route"):
            brief_points.append(f"Logistics route: {logistics_details.get('route')}")
        if isinstance(logistics_details, dict):
            log_cost = logistics_details.get("estimated_cost") or logistics_details.get("estimated_cost_ngn")
            log_curr = logistics_details.get("currency") or ("NGN" if logistics_details.get("estimated_cost_ngn") else "")
            if isinstance(log_cost, (int, float)):
                brief_points.append(f"Logistics cost: {log_cost} {log_curr}".strip())
        if isinstance(compliance_resp, dict):
            comp_status = compliance_resp.get("result", {}).get("status") if isinstance(compliance_resp.get("result"), dict) else compliance_resp.get("status")
            if comp_status:
                brief_points.append(f"Compliance: {comp_status}")
        report["brief_points"] = brief_points

        # Save report
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)

        print(json.dumps(report["final_plan"], indent=2))
        await manager.broadcast({"type": "status", "status": "completed"})
        return {"status": "success", "report": report, "report_summary": report["final_plan"], "human_summary": report["human_summary"], "brief_points": report["brief_points"]}

    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        report["status"] = "failed"
        report["error"] = str(e)
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)
        await manager.broadcast({"type": "status", "status": "failed", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
