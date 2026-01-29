from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    history: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
