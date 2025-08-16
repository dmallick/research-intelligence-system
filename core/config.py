from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Environment Settings
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/research_db"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/test_research_db"
    
    # Vector Database Settings
    VECTOR_DB_TYPE: str = "chroma"  # chroma, pinecone
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001  # Changed to avoid conflict with API port
    PINECONE_API_KEY: Optional[str] = None
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"
    
    # LLM Settings
    OPENAI_API_KEY: str = "your-openai-api-key-here"
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Agent Settings
    MAX_CONCURRENT_AGENTS: int = 10
    AGENT_TIMEOUT: int = 300  # seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "detailed"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # External APIs
    ARXIV_API_BASE: str = "http://export.arxiv.org/api/query"
    SCHOLAR_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow extra fields to prevent validation errors
        extra = "allow"

settings = Settings()