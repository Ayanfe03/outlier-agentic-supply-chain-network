## Supply Chain Agent Network (In-Memory Registry)

### Overview
This project simulates a decentralized supply chain using independent AI agents
(buyer, supplier, logistics, compliance) with a lightweight, in-memory registry
for agent discovery and semantic search.

### Current Agents (Demo)
- **Buyer (Procurement)**: Orchestrates discovery, supplier request, logistics routing, and compliance checks.
- **Supplier**: Responds to part/quantity requests with availability, pricing, and lead time.
- **Logistics**: Proposes routes, costs, and risk notes for origin/destination shipments.
- **Compliance**: Verifies offers and routes against jurisdiction and policy constraints.
- **Registry**: Stores AgentFacts (role, capabilities, policies, jurisdiction) and supports semantic discovery.

### Prerequisites
- Python 3.11+
- `OPENAI_API_KEY` in your environment

### LLM Configuration
This project is LLM-agnostic. By default it uses OpenAI (`OPENAI_API_KEY`).
You can swap to any OpenAI-compatible endpoint by changing the `base_url`,
`api_key`, and `model` in the agent files.

### Install
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run Locally (No DB)
Start each service in a separate terminal (same virtualenv):

Registry:
```powershell
uvicorn registry.app.main:app --host 0.0.0.0 --port 8000
```

Supplier:
```powershell
uvicorn agents.supplier_agent.app.main:app --host 0.0.0.0 --port 8001
```

Buyer:
```powershell
uvicorn agents.buyer_agent.app.main:app --host 0.0.0.0 --port 8002
```

Logistics:
```powershell
uvicorn agents.logistics_agent.app.main:app --host 0.0.0.0 --port 8003
```

Compliance:
```powershell
uvicorn agents.compliance_agent.app.main:app --host 0.0.0.0 --port 8004
```

### Frontend (Vite)
From the `frontend` folder:
```powershell
cd frontend
npm install
set VITE_REGISTRY_URL=http://localhost:8000
set VITE_BUYER_URL=http://localhost:8002
npm run dev
```

The frontend expects:
- Registry: `GET /agents`
- Buyer: `POST /intent` with `{ "intent": "..." }`

### Notes
- The registry is in-memory. Agents re-register on startup.
- Reports are written to `reports/coord_report.json`.

### TODO / Next Steps
- **Real agent onboarding**: allow external agents to self-register securely.
- **Auth & rate limiting**: protect registry and orchestration endpoints.
- **Persistence**: move registry to a DB for production durability.
- **Interoperability**: add a cross-framework agent (LangGraph/AutoGen/etc.).
- **Health checks**: add `/health` endpoints for each service.
