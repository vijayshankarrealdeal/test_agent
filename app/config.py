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
