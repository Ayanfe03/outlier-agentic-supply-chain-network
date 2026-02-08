from pydantic import BaseModel
from typing import Dict, Any, Optional

class AgentMessage(BaseModel):
    task_id: str
    sender: str
    receiver: str
    intent: str                       
    context: Dict[str, Any]            
    status: str = "pending"            
    result: Optional[Dict[str, Any]] = None
    verification: Optional[Dict] = None 
    timestamp: str                     