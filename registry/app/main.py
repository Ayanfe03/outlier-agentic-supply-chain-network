from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from dotenv import load_dotenv
try:
    from .embedder import embed_text, flatten_metadata
except ImportError:
    from embedder import embed_text, flatten_metadata
import numpy as np

load_dotenv()

app = FastAPI(title="Agent Registry")

class AgentRegister(BaseModel):
    agent_id: str
    role: str
    capabilities: Dict
    endpoint: str
    policies: Dict
    jurisdiction: Dict

class AgentOut(BaseModel):
    agent_id: str
    role: str
    capabilities: Dict
    endpoint: str
    policies: Dict
    jurisdiction: Dict
    match_score: float = 0.0

# In-memory registry
AGENTS: Dict[str, Dict] = {}

@app.post("/register", response_model=AgentOut)
def register(agent: AgentRegister):
    if agent.agent_id in AGENTS:
        raise HTTPException(400, "Agent already registered")
    flat = flatten_metadata(agent.role, agent.capabilities, agent.policies, agent.jurisdiction)
    emb = embed_text(flat).tolist()
    record = agent.dict()
    record["embedding"] = emb
    AGENTS[agent.agent_id] = record
    return AgentOut(**agent.dict(), match_score=1.0)

@app.get("/discover", response_model=List[AgentOut])
def discover(q: str = "", region: str = None):
    if not q: return []
    query_emb = embed_text(q)
    agents = list(AGENTS.values())
    results = []
    q_lc = q.lower()
    for a in agents:
        if a.get("embedding"):
            emb = np.array(a.get("embedding"))
        else:
            flat = flatten_metadata(a.get("role"), a.get("capabilities", {}), a.get("policies", {}), a.get("jurisdiction", {}))
            emb = embed_text(flat)
        similarity = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
        score = float(similarity)
        if region and a.get("policies", {}).get("region") != region:
            score *= 0.3
        if score >= 0.35:
            results.append(AgentOut(**a, match_score=round(score, 3)))
    # Lexical fallback if semantic search returns nothing
    if not results:
        for a in agents:
            if region and a.get("policies", {}).get("region") != region:
                continue
            role = a.get("role")
            role_match = role and role.lower() in q_lc
            # Check capabilities values for lexical hits
            cap_hit = False
            caps = a.get("capabilities", {})
            if isinstance(caps, dict):
                for v in caps.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item.lower() in q_lc:
                                cap_hit = True
                                break
                    elif isinstance(v, str) and v.lower() in q_lc:
                        cap_hit = True
                    if cap_hit:
                        break
            if role_match or cap_hit:
                results.append(AgentOut(**a, match_score=0.2))
    results.sort(key=lambda x: x.match_score, reverse=True)
    return results