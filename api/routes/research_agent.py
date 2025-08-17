# api/routes/research_agent.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

from agents.research.research_agent import ResearchAgent, create_research_agent
from core.message_queue import get_message_queue
#from agents.base.agent import AgentMessage

router = APIRouter(prefix="/research-agent", tags=["research-agent"])

# Global research agent instance
research_agent: Optional[ResearchAgent] = None

# Pydantic models for request/response
class WebResearchRequest(BaseModel):
    query: str
    max_results: int = 10
    search_type: str = "web"
    domain_filter: Optional[List[str]] = None

class AcademicSearchRequest(BaseModel):
    query: str
    max_results: int = 10
    date_filter: Optional[str] = None

class NewsSearchRequest(BaseModel):
    query: str
    max_results: int = 20
    sources: Optional[List[str]] = None

class DocumentExtractionRequest(BaseModel):
    url: str
    document_type: str = "auto"  # auto, pdf, docx, html

class UrlAnalysisRequest(BaseModel):
    url: str
    detailed_analysis: bool = False

class ResearchTaskRequest(BaseModel):
    task_type: str
    parameters: Dict[str, Any]
    priority: str = "normal"

class ResearchResponse(BaseModel):
    status: str
    task_id: str
    message: str
    data: Optional[Dict[str, Any]] = None

async def get_research_agent() -> ResearchAgent:
    """Get or create research agent instance"""
    global research_agent
    if research_agent is None:
        research_agent = await create_research_agent("research_agent_api")
    return research_agent

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for research agent"""
    try:
        agent = await get_research_agent()
        return {
            "status": "healthy",
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type,
            "capabilities": [
                "web_research",
                "academic_search", 
                "news_search",
                "document_extraction",
                "url_analysis"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research agent health check failed: {str(e)}")

@router.post("/web-research", response_model=ResearchResponse)
async def web_research(request: WebResearchRequest, background_tasks: BackgroundTasks) -> ResearchResponse:
    """Perform web research"""
    try:
        agent = await get_research_agent()
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "task_type": "web_research",
            "query": {
                "query": request.query,
                "search_type": request.search_type,
                "max_results": request.max_results,
                "domain_filter": request.domain_filter
            }
        }
        
        # Process task asynchronously
        background_tasks.add_task(process_research_task, agent, task)
        
        return ResearchResponse(
            status="accepted",
            task_id=task_id,
            message=f"Web research task submitted for query: '{request.query}'"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/academic-search", response_model=ResearchResponse)
async def academic_search(request: AcademicSearchRequest, background_tasks: BackgroundTasks) -> ResearchResponse:
    """Search academic papers"""
    try:
        agent = await get_research_agent()
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "task_type": "academic_search",
            "query": request.query,
            "max_results": request.max_results,
            "date_filter": request.date_filter
        }
        
        background_tasks.add_task(process_research_task, agent, task)
        
        return ResearchResponse(
            status="accepted",
            task_id=task_id,
            message=f"Academic search submitted for: '{request.query}'"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/news-search", response_model=ResearchResponse)
async def news_search(request: NewsSearchRequest, background_tasks: BackgroundTasks) -> ResearchResponse:
    """Search news articles"""
    try:
        agent = await get_research_agent()
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "task_type": "news_search",
            "query": request.query,
            "max_results": request.max_results,
            "sources": request.sources
        }
        
        background_tasks.add_task(process_research_task, agent, task)
        
        return ResearchResponse(
            status="accepted",
            task_id=task_id,
            message=f"News search submitted for: '{request.query}'"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-document", response_model=ResearchResponse)
async def extract_document(request: DocumentExtractionRequest, background_tasks: BackgroundTasks) -> ResearchResponse:
    """Extract content from document"""
    try:
        agent = await get_research_agent()
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "task_type": "document_extraction",
            "url": request.url,
            "document_type": request.document_type
        }
        
        background_tasks.add_task(process_research_task, agent, task)
        
        return ResearchResponse(
            status="accepted",
            task_id=task_id,
            message=f"Document extraction submitted for: {request.url}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-url", response_model=ResearchResponse)
async def analyze_url(request: UrlAnalysisRequest, background_tasks: BackgroundTasks) -> ResearchResponse:
    """Analyze specific URL"""
    try:
        agent = await get_research_agent()
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "task_type": "url_analysis",
            "url": request.url,
            "detailed_analysis": request.detailed_analysis
        }
        
        background_tasks.add_task(process_research_task, agent, task)
        
        return ResearchResponse(
            status="accepted",
            task_id=task_id,
            message=f"URL analysis submitted for: {request.url}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-task", response_model=ResearchResponse)
async def custom_research_task(request: ResearchTaskRequest, background_tasks: BackgroundTasks) -> ResearchResponse:
    """Submit custom research task"""
    try:
        agent = await get_research_agent()
        task_id = str(uuid.uuid4())
        
        task = {
            "task_id": task_id,
            "task_type": request.task_type,
            "priority": request.priority,
            **request.parameters
        }
        
        background_tasks.add_task(process_research_task, agent, task)
        
        return ResearchResponse(
            status="accepted", 
            task_id=task_id,
            message=f"Custom research task submitted: {request.task_type}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a research task"""
    try:
        # In a real implementation, you'd store task status in database or cache
        # For now, return a placeholder response
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Task status tracking not fully implemented yet",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}/result")
async def get_task_result(task_id: str) -> Dict[str, Any]:
    """Get result of a completed research task"""
    try:
        # In a real implementation, you'd retrieve results from database or cache
        # For now, return a placeholder response
        return {
            "task_id": task_id,
            "status": "completed",
            "result": "Task result retrieval not fully implemented yet",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/web-research")
async def sync_web_research(request: WebResearchRequest) -> Dict[str, Any]:
    """Synchronous web research (for testing)"""
    try:
        agent = await get_research_agent()
        
        task = {
            "task_id": str(uuid.uuid4()),
            "task_type": "web_research",
            "query": {
                "query": request.query,
                "search_type": request.search_type,
                "max_results": request.max_results,
                "domain_filter": request.domain_filter
            }
        }
        
        result = await agent.process_task(task)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/academic-search")
async def sync_academic_search(request: AcademicSearchRequest) -> Dict[str, Any]:
    """Synchronous academic search (for testing)"""
    try:
        agent = await get_research_agent()
        
        task = {
            "task_id": str(uuid.uuid4()),
            "task_type": "academic_search",
            "query": request.query,
            "max_results": request.max_results,
            "date_filter": request.date_filter
        }
        
        result = await agent.process_task(task)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/url-analysis")
async def sync_url_analysis(request: UrlAnalysisRequest) -> Dict[str, Any]:
    """Synchronous URL analysis (for testing)"""
    try:
        agent = await get_research_agent()
        
        task = {
            "task_id": str(uuid.uuid4()),
            "task_type": "url_analysis",
            "url": request.url,
            "detailed_analysis": request.detailed_analysis
        }
        
        result = await agent.process_task(task)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capabilities")
async def get_capabilities() -> Dict[str, Any]:
    """Get research agent capabilities"""
    return {
        "agent_type": "research",
        "version": "1.0.0",
        "capabilities": {
            "web_research": {
                "description": "Search and extract content from web pages",
                "parameters": ["query", "max_results", "search_type", "domain_filter"]
            },
            "academic_search": {
                "description": "Search academic papers via arXiv",
                "parameters": ["query", "max_results", "date_filter"]
            },
            "news_search": {
                "description": "Search news articles via RSS feeds",
                "parameters": ["query", "max_results", "sources"]
            },
            "document_extraction": {
                "description": "Extract text from PDF, DOCX, and HTML documents",
                "parameters": ["url", "document_type"]
            },
            "url_analysis": {
                "description": "Detailed analysis of specific URLs",
                "parameters": ["url", "detailed_analysis"]
            }
        },
        "supported_formats": ["text/html", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        "max_concurrent_requests": 5,
        "max_content_length": 50000
    }

# Background task processor
async def process_research_task(agent: ResearchAgent, task: Dict[str, Any]):
    """Process research task in background"""
    try:
        result = await agent.process_task(task)
        
        # In a real implementation, you would:
        # 1. Store result in database/cache
        # 2. Send notification via message queue
        # 3. Update task status
        # 4. Potentially send to vector store for indexing
        
        print(f"Task {task['task_id']} completed: {result['status']}")
        
        # Example: Send result to message queue for other agents
        if result["status"] == "completed":
            mq = await get_message_queue()
            await mq.broadcast_message(
                sender_id=agent.agent_id,
                message_type="research_completed",
                content={
                    "task_id": task["task_id"],
                    "task_type": task["task_type"],
                    "result_summary": {
                        "status": result["status"],
                        "results_count": result.get("results_found", 0)
                    }
                }
            )
        
    except Exception as e:
        print(f"Background task {task['task_id']} failed: {e}")
        # Handle error, update task status, etc.