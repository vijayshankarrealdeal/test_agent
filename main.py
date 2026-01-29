from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.models import ChatRequest, ChatResponse
from app.agent import agent, AgentDeps
from app.database import KnowledgeBase
from app.history import db_logger  # Import the Postgres logger
from uuid import uuid4

# 1. Initialize Vector DB (Qdrant)
try:
    vector_db = KnowledgeBase()
except Exception as e:
    print(f"Warning: Vector DB could not be initialized. Error: {e}")
    vector_db = None

# 2. Lifespan (Startup/Shutdown logic)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Starting up Anantya.ai RAG Chatbot ---")
    
    # Connect to PostgreSQL
    await db_logger.connect()
    
    if vector_db:
        print("Knowledge Base: Connected")
    
    yield
    
    # Close PostgreSQL connection
    await db_logger.disconnect()
    print("--- Shutting down ---")

# 3. FastAPI App
app = FastAPI(title="Anantya.ai RAG Chatbot", lifespan=lifespan)

# --- CORS FIX IS HERE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (localhost, your website, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not vector_db:
        raise HTTPException(
            status_code=500, 
            detail="Database not initialized. Please run ingest.py first."
        )

    try:
        # 1. Run the Agent
        deps = AgentDeps(db=vector_db)
        result = await agent.run(request.query, deps=deps)
        
        # 2. Extract Response
        bot_reply = result.data

        # 3. Save to PostgreSQL (Background Task-like)
        # We await it here to ensure data integrity, but you could use BackgroundTasks for speed
        session_id = request.session_id or str(uuid4())
        await db_logger.save_chat(session_id, request.query, bot_reply)
        
        return ChatResponse(
            response=bot_reply
        )
        
    except Exception as e:
        print(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
