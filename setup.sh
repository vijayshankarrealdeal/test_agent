#!/bin/bash

# 1. Create Directory Structure
echo "Creating project structure..."
mkdir -p my_rag_app/app
mkdir -p my_rag_app/data
cd my_rag_app

# 2. Create requirements.txt
echo "Creating requirements.txt..."
cat << 'EOF' > requirements.txt
fastapi
uvicorn
pydantic-ai
chromadb
google-generativeai
python-dotenv
pydantic-settings
EOF

# 3. Create .env
echo "Creating .env..."
cat << 'EOF' > .env
# REPLACE THIS WITH YOUR ACTUAL KEY
GEMINI_API_KEY=your_actual_gemini_api_key_here
CHROMA_DB_DIR=chroma_data
EOF


# 5. Create app/__init__.py
touch app/__init__.py

# 6. Create app/config.py
echo "Creating app/config.py..."
cat << 'EOF' > app/config.py
import os
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    chroma_db_dir: str = "chroma_data"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
EOF

# 7. Create app/database.py
echo "Creating app/database.py..."
cat << 'EOF' > app/database.py
import chromadb
from chromadb.utils import embedding_functions
from app.config import get_settings

settings = get_settings()

class ChromaKnowledgeBase:
    def __init__(self):
        # PersistentClient saves data to disk
        self.client = chromadb.PersistentClient(path=settings.chroma_db_dir)
        
        # Default sentence-transformers model
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name="anantya_docs", 
            embedding_function=self.ef
        )

    def upsert_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """Add or update documents in the vector store."""
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, n_results: int = 3) -> str:
        """Search for relevant documents."""
        results = self.collection.query(
            query_texts=[query], 
            n_results=n_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant information found in the knowledge base."
            
        # Combine the results into a single string context
        context_parts = []
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i] if results['metadatas'] else {}
            source = meta.get('source', 'Unknown')
            context_parts.append(f"[Source: {source}]\n{doc}")
            
        return "\n\n".join(context_parts)
EOF

# 8. Create app/models.py
echo "Creating app/models.py..."
cat << 'EOF' > app/models.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
EOF

# 9. Create app/agent.py
echo "Creating app/agent.py..."
cat << 'EOF' > app/agent.py
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from app.database import ChromaKnowledgeBase
from app.config import get_settings

settings = get_settings()

# Define dependencies injected per request
@dataclass
class AgentDeps:
    db: ChromaKnowledgeBase

# Initialize Gemini Model
model = GeminiModel(
    'gemini-1.5-flash', 
    api_key=settings.gemini_api_key
)

# Initialize Agent
agent = Agent(
    model,
    deps_type=AgentDeps,
    system_prompt=(
        "You are a helpful support assistant for Anantya.ai. "
        "Your task is to answer user questions based on the provided context. "
        "ALWAYS use the `retrieve_knowledge` tool to find information before answering. "
        "If the tool returns no results, admit you don't know."
    )
)

@agent.tool
def retrieve_knowledge(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Search the knowledge base for information about Anantya.ai, features, or pricing.
    """
    return ctx.deps.db.search(query)
EOF

# 10. Create app/main.py
echo "Creating app/main.py..."
cat << 'EOF' > app/main.py
from fastapi import FastAPI, HTTPException
from app.agent import agent, AgentDeps
from app.database import ChromaKnowledgeBase
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="Anantya.ai RAG Chatbot")

# Initialize DB once (connection pool)
db_instance = ChromaKnowledgeBase()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Inject the database instance into the agent's dependencies
        deps = AgentDeps(db=db_instance)
        
        # Run the agent
        result = await agent.run(request.query, deps=deps)
        
        return ChatResponse(response=result.data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# 11. Create ingest.py
echo "Creating ingest.py..."
cat << 'EOF' > ingest.py
import json
import os
from app.database import ChromaKnowledgeBase

# Ensure data directory exists
DATA_FILE = "data/source_data.jsonl"

def load_data():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Please create it.")
        return

    print("Initializing Database...")
    db = ChromaKnowledgeBase()
    
    docs = []
    metadatas = []
    ids = []
    
    print(f"Reading {DATA_FILE}...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                
                # Extract fields based on your JSONL structure
                doc_id = item.get("id")
                text = item.get("text")
                meta = item.get("metadata", {})
                
                if doc_id and text:
                    ids.append(doc_id)
                    docs.append(text)
                    # Chroma requires metadata values to be str, int, float, or bool
                    metadatas.append(meta)
            except json.JSONDecodeError:
                print("Skipping invalid JSON line")

    if docs:
        print(f"Embedding and storing {len(docs)} documents...")
        db.upsert_documents(documents=docs, metadatas=metadatas, ids=ids)
        print("Success! Data ingested.")
    else:
        print("No valid data found to ingest.")

if __name__ == "__main__":
    # Create dummy data if file doesn't exist for testing
    if not os.path.exists("data"):
        os.makedirs("data")
        
    # Run ingestion
    load_data()
EOF

echo "--------------------------------------------------------"
echo "Project 'my_rag_app' created successfully!"
echo "--------------------------------------------------------"
echo "NEXT STEPS:"
echo "1. cd my_rag_app"
echo "2. Edit .env and put your real GEMINI_API_KEY inside."
echo "3. pip install -r requirements.txt"
echo "4. python ingest.py   (Do this once to load the JSONL data)"
echo "5. python -m app.main (Run the server)"