import os
import asyncpg
import ssl

# Your provided connection string
# Note: In production, keep this in .env
DB_URL = "postgresql://hexa:cggdJ2XIbBT2iuzgW0QxSNsafmnguytP@dpg-d5tnhk4hg0os739su1pg-a.virginia-postgres.render.com/hexa_grts"

class ChatLogger:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Initialize the connection pool and create table if missing."""
        try:
            # Render requires SSL for external connections
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            self.pool = await asyncpg.create_pool(dsn=DB_URL, ssl=ctx)
            
            # Create table
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id SERIAL PRIMARY KEY,
                        user_query TEXT,
                        bot_response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            print("PostgreSQL: Connected and Table Verified.")
        except Exception as e:
            print(f"PostgreSQL Error: {e}")
            self.pool = None

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def save_chat(self, query: str, response: str):
        """Insert a chat log into the database."""
        if not self.pool:
            print("Warning: PostgreSQL not connected. Chat not saved.")
            return

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO chat_history (user_query, bot_response) VALUES ($1, $2)",
                    query, response
                )
        except Exception as e:
            print(f"Failed to save chat history: {e}")

# Global instance
db_logger = ChatLogger()