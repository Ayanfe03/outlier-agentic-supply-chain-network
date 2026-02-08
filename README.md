## Supply Chain Agent Network (In-Memory Registry)

### Overview
This project simulates a decentralized supply chain using independent AI agents
(buyer, supplier, logistics, compliance) with a lightweight, in-memory registry
for agent discovery and semantic search.

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

Dashboard:
```powershell
streamlit run dashboard/app.py
```

### Notes
- The registry is in-memory. Agents re-register on startup.
- Reports are written to `reports/coord_report.json`.
