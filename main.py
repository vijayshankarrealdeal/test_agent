import os
import asyncio
from typing import List, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from dotenv import load_dotenv

import chromadb
from chromadb.utils import embedding_functions

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel

# 1. Load Environment Variables
# Make sure you have GEMINI_API_KEY in your .env file or environment
load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY is required.")

# ------------------------------------------------------------------
# 2. Database Layer (ChromaDB)
# ------------------------------------------------------------------

class ChromaKnowledgeBase:
    def __init__(self):
        # We use a persistent client or ephemeral for testing
        self.client = chromadb.Client() 
        
        # Use default sentence-transformers for embedding
        # In production, you might want to use Google's embedding model here too
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="docs", 
            embedding_function=self.ef
        )

    def add_documents(self, documents: List[str], ids: List[str]):
        self.collection.add(documents=documents, ids=ids)

    def search(self, query: str, n_results: int = 3) -> str:
        results = self.collection.query(
            query_texts=[query], 
            n_results=n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant information found in the database."
            
        return "\n".join(results['documents'][0])

# Global instance (In production, manage this via dependencies/lifecycle)
db = ChromaKnowledgeBase()

# ------------------------------------------------------------------
# 3. Pydantic AI Agent Setup
# ------------------------------------------------------------------

# Define dependencies that will be injected into the agent per request
@dataclass
class AgentDeps:
    db: ChromaKnowledgeBase

# Define the model (Gemini 1.5 Flash is fast and cheap)
model = GeminiModel(
    'gemini-1.5-flash', 
    api_key=os.getenv("GEMINI_API_KEY")
)

# Initialize the Agent
agent = Agent(
    model,
    deps_type=AgentDeps,
    system_prompt=(
        "You are a helpful assistant with access to a knowledge base. "
        "Always check the knowledge base first before answering questions about specific data. "
        "Be concise."
    )
)

# Define the RAG Tool
@agent.tool
def retrieve_knowledge(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Search the knowledge base for relevant information to answer the user's query.
    Use this tool whenever the user asks for factual information.
    """
    print(f"--- Tool Called: Searching for '{query}' ---")
    return ctx.deps.db.search(query)

# ------------------------------------------------------------------
# 4. FastAPI Setup
# ------------------------------------------------------------------

# Request/Response Models
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    tool_used: bool = False

# Lifespan to load dummy data on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load some dummy data into ChromaDB for testing
    print("Loading knowledge base...")
    db.add_documents(
        documents=[
            "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python.",
            "Pydantic AI is a Python agent framework designed to make it less painful to build production grade applications with Generative AI.",
            "ChromaDB is the AI-native open-source embedding database.",
            "The secret code for the admin panel is 1234-SUPER-SECRET."
        ],
        ids=["doc1", "doc2", "doc3", "doc4"]
    )
    yield
    print("Shutting down...")

app = FastAPI(title="Pydantic AI + Gemini RAG", lifespan=lifespan)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Create dependencies for this run
        deps = AgentDeps(db=db)
        
        # Run the agent
        # The agent determines if it needs to call the 'retrieve_knowledge' tool
        result = await agent.run(request.query, deps=deps)
        
        return ChatResponse(
            response=result.data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)