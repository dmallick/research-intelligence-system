from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import asyncio
import time

from core.database import get_db, check_db_health
from core.message_queue import get_message_queue
from core.config import settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "Research Intelligence System",
        "version": "1.0.0",
        "timestamp": str(time.time())
    }

@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check including dependencies"""
    start_time = time.time()
    
    # Check database
    db_healthy = await check_db_health()
    
    # Check Redis
    redis_healthy = True
    try:
        mq = await get_message_queue()
        redis_healthy = await mq.health_check()
    except Exception as e:
        redis_healthy = False
    
    # Check Vector Store (you can implement this later) 
    vector_store_healthy = True  # Placeholder
    
    response_time = time.time() - start_time
    
    return {
        "status": "healthy" if all([db_healthy, redis_healthy, vector_store_healthy]) else "unhealthy",
        "service": "Research Intelligence System",
        "version": "1.0.0",
        "timestamp": str(time.time()),
        "response_time_seconds": response_time,
        "dependencies": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy", 
            "vector_store": "healthy" if vector_store_healthy else "unhealthy"
        },
        "environment": settings.ENVIRONMENT
    }