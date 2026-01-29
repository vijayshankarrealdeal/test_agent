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
