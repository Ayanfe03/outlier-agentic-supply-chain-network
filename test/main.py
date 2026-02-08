from fastapi import FastAPI, Body
from sqlalchemy import create_engine, Column, Integer, String, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
import uvicorn

app = FastAPI()
Base = declarative_base()
engine = create_engine('postgresql://agentuser:Jesusis4me**@localhost/agent_registry')
Session = sessionmaker(bind=engine)

class Agent(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key=True)
    identity = Column(String)
    role = Column(String)
    capabilities = Column(JSONB)  
    endpoint = Column(String)
    policies = Column(JSONB)
    jurisdiction = Column(JSONB)  

    __table_args__ = (
        Index('ix_agents_role', 'role'),
        Index('ix_agents_identity', 'identity', unique=True),
        Index('ix_agents_jurisdiction', 'jurisdiction'),
    )

    def __repr__(self):
        return f"<Agent(identity='{self.identity}', role='{self.role}', endpoint='{self.endpoint}')>"

Base.metadata.create_all(engine)

@app.post("/register")
def register_agent(identity: str = Body(...), role: str = Body(...), capabilities: dict = Body(...), endpoint: str = Body(...), policies: dict = Body(...), jurisdiction: dict = Body(...)):
    session = Session()
    new_agent = Agent(identity=identity, role=role, capabilities=capabilities, endpoint=endpoint, policies=policies, jurisdiction=jurisdiction)
    session.add(new_agent)
    session.commit()
    return {"status": "registered"}

@app.get("/discover")
def discover(query: str):  
    session = Session()
    results = session.query(Agent).filter(Agent.role.ilike(f"%{query}%")).all()
    return [{"id": a.id, "role": a.role, "identity": a.identity, "endpoint": a.endpoint, "capabilities": a.capabilities, "policies": a.policies, "jurisdiction": a.jurisdiction} for a in results]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)