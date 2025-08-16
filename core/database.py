from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, text
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from core.config import settings

# Create async engine
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
)

# Create sync engine for migrations
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", ""),  # Remove async driver for sync operations
    echo=settings.LOG_LEVEL == "DEBUG",
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all models
Base = declarative_base()

@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def create_tables():
    """
    Create all database tables
    """
    try:
        # Import all models to ensure they're registered
        from models import research, content, agent_state
        
        async with async_engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {e}")
        raise

async def drop_tables():
    """
    Drop all database tables (useful for testing)
    """
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logging.info("Database tables dropped successfully")
    except Exception as e:
        logging.error(f"Error dropping database tables: {e}")
        raise

async def close_db_connection():
    """
    Close database connection
    """
    try:
        await async_engine.dispose()
        logging.info("Database connection closed")
    except Exception as e:
        logging.error(f"Error closing database connection: {e}")

# Health check function
async def check_db_health() -> bool:
    """
    Check if database is healthy
    """
    try:
        async with get_db() as db:
            #await db.execute('SELECT 1')
            await db.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        return False