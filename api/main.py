from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging
import time  # Missing import

from core.config import settings
from core.database import create_tables, close_db_connection
# Import routes - these need to be created
# from api.routes import research, health, agents
from api.routes import research, health, agents

from utils.logging import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    await create_tables()
    logging.info("Application startup complete")
    
    yield
    
    # Shutdown
    await close_db_connection()
    logging.info("Application shutdown complete")

app = FastAPI(
    title="Research Intelligence System",
    description="Multi-Agent Research and Content Intelligence System",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Basic health check endpoint (before routes are implemented)
@app.get("/")
async def root():
    return {"message": "Research Intelligence System API", "status": "running"}

@app.get("/health")
async def health_check():
    from core.database import check_db_health
    
    db_healthy = await check_db_health()
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "version": "1.0.0"
    }

# Routes - uncomment when route files are created
# app.include_router(health.router, prefix=settings.API_PREFIX)
# app.include_router(research.router, prefix=settings.API_PREFIX)
# app.include_router(agents.router, prefix=settings.API_PREFIX)

app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(research.router, prefix=settings.API_PREFIX)
app.include_router(agents.router, prefix=settings.API_PREFIX)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logging.info(
        f"{request.method} {request.url} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )