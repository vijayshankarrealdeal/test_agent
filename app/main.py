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
        
        return ChatResponse(response=result.output)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
