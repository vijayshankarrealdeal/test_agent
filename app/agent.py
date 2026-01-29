from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from app.database import KnowledgeBase
from app.config import get_settings

settings = get_settings()

# Define dependencies injected per request
@dataclass
class AgentDeps:
    db: KnowledgeBase

provider = GoogleProvider(api_key=settings.gemini_api_key)
model = GoogleModel('gemini-2.5-flash-lite', provider=provider)


# Initialize Agent
agent = Agent(
    model,
    deps_type=AgentDeps,
    system_prompt=(
        "You are a helpful support assistant for Anantya.ai company people also say Anantya"
        "Your task is to answer user questions based on the provided context. "
        "ALWAYS use the `retrieve_knowledge` tool to find information before answering, not thing on your trained data. "
        "If the tool returns no results, admit you don't know."
    )
)

@agent.tool
def retrieve_knowledge(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Search the knowledge base for information about Anantya.ai, features, or pricing.
    """
    print(f"--- Agent Tool: Searching for '{query}' ---")
    return ctx.deps.db.search(query)