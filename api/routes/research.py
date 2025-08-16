from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from pydantic import BaseModel
import uuid

from core.database import get_db
from models.research import ResearchTask, ResearchResult

router = APIRouter(prefix="/research", tags=["research"])

class ResearchTaskCreate(BaseModel):
    query: str
    priority: int = 1
    task_metadata: Dict[str, Any] = {}

class ResearchTaskResponse(BaseModel):
    id: int
    task_id: str
    query: str
    status: str
    priority: int
    task_metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True

@router.post("/tasks", response_model=ResearchTaskResponse)
async def create_research_task(
    task_data: ResearchTaskCreate,
    db: AsyncSession = Depends(get_db)
) -> ResearchTaskResponse:
    """Create a new research task"""
    task = ResearchTask(
        task_id=str(uuid.uuid4()),
        query=task_data.query,
        priority=task_data.priority,
        task_metadata=task_data.task_metadata
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return ResearchTaskResponse.from_orm(task)

@router.get("/tasks", response_model=List[ResearchTaskResponse])
async def get_research_tasks(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> List[ResearchTaskResponse]:
    """Get list of research tasks"""
    result = await db.execute(
        select(ResearchTask).offset(skip).limit(limit)
    )
    tasks = result.scalars().all()
    
    return [ResearchTaskResponse.from_orm(task) for task in tasks]

@router.get("/tasks/{task_id}", response_model=ResearchTaskResponse)
async def get_research_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> ResearchTaskResponse:
    """Get a specific research task"""
    result = await db.execute(
        select(ResearchTask).where(ResearchTask.task_id == task_id)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")
    
    return ResearchTaskResponse.from_orm(task)

@router.get("/tasks/{task_id}/results")
async def get_task_results(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get results for a specific research task"""
    result = await db.execute(
        select(ResearchResult).where(ResearchResult.task_id == task_id)
    )
    results = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "agent_type": r.agent_type,
            "result_type": r.result_type,
            "content": r.content,
            "confidence_score": r.confidence_score,
            "result_metadata": r.result_metadata,
            "created_at": r.created_at
        }
        for r in results
    ]