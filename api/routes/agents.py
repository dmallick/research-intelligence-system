from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from pydantic import BaseModel

from core.database import get_db
from models.agent_state import AgentState

router = APIRouter(prefix="/agents", tags=["agents"])

class AgentStateResponse(BaseModel):
    id: int
    agent_id: str
    agent_type: str
    status: str
    current_task: str = None
    last_heartbeat: str
    agent_metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[AgentStateResponse])
async def get_all_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[AgentStateResponse]:
    """Get list of all registered agents"""
    result = await db.execute(
        select(AgentState).offset(skip).limit(limit)
    )
    agents = result.scalars().all()
    
    return [
        AgentStateResponse(
            id=agent.id,
            agent_id=agent.agent_id,
            agent_type=agent.agent_type,
            status=agent.status,
            current_task=agent.current_task,
            last_heartbeat=str(agent.last_heartbeat),
            agent_metadata=agent.agent_metadata
        )
        for agent in agents
    ]

@router.get("/{agent_id}", response_model=AgentStateResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentStateResponse:
    """Get specific agent information"""
    result = await db.execute(
        select(AgentState).where(AgentState.agent_id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentStateResponse(
        id=agent.id,
        agent_id=agent.agent_id,
        agent_type=agent.agent_type,
        status=agent.status,
        current_task=agent.current_task,
        last_heartbeat=str(agent.last_heartbeat),
        agent_metadata=agent.agent_metadata
    )

@router.get("/type/{agent_type}", response_model=List[AgentStateResponse])
async def get_agents_by_type(
    agent_type: str,
    db: AsyncSession = Depends(get_db)
) -> List[AgentStateResponse]:
    """Get all agents of a specific type"""
    result = await db.execute(
        select(AgentState).where(AgentState.agent_type == agent_type)
    )
    agents = result.scalars().all()
    
    return [
        AgentStateResponse(
            id=agent.id,
            agent_id=agent.agent_id,
            agent_type=agent.agent_type,
            status=agent.status,
            current_task=agent.current_task,
            last_heartbeat=str(agent.last_heartbeat),
            agent_metadata=agent.agent_metadata
        )
        for agent in agents
    ]