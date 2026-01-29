from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from app.models import ChatRequest, ChatResponse
from app.agent import agent, AgentDeps
from app.database import KnowledgeBase

# 1. Initialize the Database (Qdrant)
# We initialize this once. It connects to the local folder created by ingest.py
try:
    db_instance = KnowledgeBase()
except Exception as e:
    print(f"Warning: Database could not be initialized. Make sure you ran ingest.py. Error: {e}")
    db_instance = None

# 2. Lifespan (Optional setup on startup)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Starting up Anantya.ai RAG Chatbot ---")
    if db_instance:
        print("Knowledge Base: Connected")
    else:
        print("Knowledge Base: Not found (Did you run ingest.py?)")
    yield
    print("--- Shutting down ---")

# 3. FastAPI App
app = FastAPI(title="Anantya.ai RAG Chatbot", lifespan=lifespan)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not db_instance:
        raise HTTPException(
            status_code=500, 
            detail="Database not initialized. Please run ingest.py first."
        )

    try:
        # Create dependencies for this specific request
        # We inject the Qdrant database instance into the agent
        deps = AgentDeps(db=db_instance)
        
        # Run the agent with the user's query
        result = await agent.run(request.query, deps=deps)
        
        # Return the response
        return ChatResponse(
            response=result.output
        )
        
    except Exception as e:
        print(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
