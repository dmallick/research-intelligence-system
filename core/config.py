from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Database Settings
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    
    # Vector Database Settings
    VECTOR_DB_TYPE: str = "chroma"  # chroma, pinecone
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    PINECONE_API_KEY: Optional[str] = None
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"
    
    # LLM Settings
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Agent Settings
    MAX_CONCURRENT_AGENTS: int = 10
    AGENT_TIMEOUT: int = 300  # seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "detailed"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()