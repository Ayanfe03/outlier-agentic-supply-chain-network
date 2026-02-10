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
    region: str | None = None

SUPPLIER_CATALOG = [
    {
        "agent_id": "supplier-1",
        "inventory": {
            "wheels": {"unit_price": 5000, "available": 150},
            "tires": {"unit_price": 7000, "available": 80},
            "engines": {"unit_price": 120000, "available": 20},
        },
        "currency": "NGN",
    },
    {
        "agent_id": "supplier-2",
        "inventory": {
            "sensors": {"unit_price": 18, "available": 400},
            "electronics": {"unit_price": 55, "available": 250},
            "control units": {"unit_price": 75, "available": 150},
        },
        "currency": "EUR",
    },
    {
        "agent_id": "supplier-3",
        "inventory": {
            "steel": {"unit_price": 30, "available": 300},
            "aluminum": {"unit_price": 25, "available": 150},
            "fasteners": {"unit_price": 5, "available": 1000},
        },
        "currency": "USD",
    },
]

REGION_TO_CURRENCY = {
    "NG": "NGN",
    "EU": "EUR",
    "US": "USD",
}

@app.on_event("startup")
async def register_self():
    payloads = [
        {
            "agent_id": "supplier-1",
            "role": "Supplier",
            "capabilities": {
                "parts": ["wheels", "tires", "engines"],
                "inventory": {
                    "wheels": {"unit_price": 5000, "available": 150},
                    "tires": {"unit_price": 7000, "available": 80},
                    "engines": {"unit_price": 120000, "available": 20},
                },
            },
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "NG", "compliance": "basic", "currency": "NGN"},
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
            "capabilities": {
                "parts": ["sensors", "electronics", "control units"],
                "inventory": {
                    "sensors": {"unit_price": 18, "available": 400},
                    "electronics": {"unit_price": 55, "available": 250},
                    "control units": {"unit_price": 75, "available": 150},
                },
            },
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "EU", "compliance": "strict", "currency": "EUR"},
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
            "capabilities": {
                "parts": ["steel", "aluminum", "fasteners"],
                "inventory": {
                    "steel": {"unit_price": 30, "available": 300},
                    "aluminum": {"unit_price": 25, "available": 150},
                    "fasteners": {"unit_price": 5, "available": 1000},
                },
            },
            "endpoint": ENDPOINT_URL,
            "policies": {"region": "US", "compliance": "standard", "currency": "USD"},
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
    # Static inventory-driven response (no LLM pricing)
    inventory = None
    currency = "USD"
    region_currency = REGION_TO_CURRENCY.get(req.region.upper()) if req.region else None
    for payload in SUPPLIER_CATALOG:
        if region_currency and payload.get("currency") == region_currency:
            if req.part in payload["inventory"]:
                inventory = payload["inventory"]
                currency = payload["currency"]
                break
        # fallback: pick any inventory containing the part
        if req.part in payload["inventory"]:
            inventory = payload["inventory"]
            currency = payload["currency"]
            break

    if not inventory or req.part not in inventory:
        return {"status": "error", "details": f"No inventory for part: {req.part}"}

    item = inventory[req.part]
    unit_price = item["unit_price"]
    available = item["available"]
    requested = req.quantity
    available_now = min(available, requested)
    remaining = max(0, requested - available)
    lead_days_remaining = 30 if remaining > 0 else 0

    total_price_now = unit_price * available_now
    total_price_full = unit_price * requested

    details = {
        "unit_price": unit_price,
        "currency": currency,
        "available_now": available_now,
        "remaining_qty": remaining,
        "lead_days_remaining": lead_days_remaining,
        "total_price_now": total_price_now,
        "total_price_full": total_price_full,
        "notes": (
            "Partial available now; remainder in ~30 days."
            if remaining > 0
            else "All units available now."
        ),
    }
    return {"status": "offer_sent", "details": details}
