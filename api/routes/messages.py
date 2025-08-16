from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import uuid
from datetime import datetime

from core.message_queue import get_message_queue
from agents.base.agent import AgentMessage

router = APIRouter(prefix="/messages", tags=["messages"])

class SendMessageRequest(BaseModel):
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    correlation_id: str = None

class BroadcastMessageRequest(BaseModel):
    message_type: str
    content: Dict[str, Any]
    agent_types: List[str] = None

class TaskRequest(BaseModel):
    queue_name: str
    task: Dict[str, Any]

@router.post("/send")
async def send_message(request: SendMessageRequest) -> Dict[str, str]:
    """Send a message to a specific agent"""
    try:
        mq = await get_message_queue()
        
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender_id="api_user",
            receiver_id=request.receiver_id,
            message_type=request.message_type,
            content=request.content,
            timestamp=datetime.utcnow(),
            correlation_id=request.correlation_id
        )
        
        success = await mq.send_message(message)
        
        if success:
            return {
                "status": "success",
                "message_id": message.id,
                "message": f"Message sent to {request.receiver_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/broadcast")
async def broadcast_message(request: BroadcastMessageRequest) -> Dict[str, str]:
    """Broadcast a message to multiple agents"""
    try:
        mq = await get_message_queue()
        
        success = await mq.broadcast_message(
            sender_id="api_user",
            message_type=request.message_type,
            content=request.content,
            agent_types=request.agent_types
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Message broadcasted to {request.agent_types or 'all agents'}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to broadcast message")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{agent_id}")
async def get_message_history(agent_id: str, limit: int = 50) -> Dict[str, Any]:
    """Get message history for an agent"""
    try:
        mq = await get_message_queue()
        history = await mq.get_message_history(agent_id, limit)
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "message_count": len(history),
            "messages": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/add")
async def add_task_to_queue(request: TaskRequest) -> Dict[str, str]:
    """Add a task to a specific queue"""
    try:
        mq = await get_message_queue()
        
        # Ensure queue exists
        await mq.create_task_queue(request.queue_name)
        
        # Add task
        success = await mq.add_task_to_queue(request.queue_name, request.task)
        
        if success:
            return {
                "status": "success",
                "message": f"Task added to queue '{request.queue_name}'",
                "task_id": request.task.get("task_id", "unknown")
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add task to queue")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queues/{queue_name}/length")
async def get_queue_length(queue_name: str) -> Dict[str, Any]:
    """Get the length of a specific queue"""
    try:
        mq = await get_message_queue()
        length = await mq.get_queue_length(queue_name)
        
        return {
            "status": "success",
            "queue_name": queue_name,
            "length": length
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queues/{queue_name}/next")
async def get_next_task(queue_name: str, timeout: int = 5) -> Dict[str, Any]:
    """Get the next task from a queue"""
    try:
        mq = await get_message_queue()
        task = await mq.get_task_from_queue(queue_name, timeout)
        
        if task:
            return {
                "status": "success",
                "queue_name": queue_name,
                "task": task
            }
        else:
            return {
                "status": "no_task",
                "queue_name": queue_name,
                "message": "No tasks available in queue"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/ping")
async def test_ping_agent(agent_id: str) -> Dict[str, str]:
    """Send a test ping message to an agent"""
    try:
        mq = await get_message_queue()
        
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender_id="api_test",
            receiver_id=agent_id,
            message_type="ping",
            content={"test": "ping from API", "timestamp": datetime.utcnow().isoformat()},
            timestamp=datetime.utcnow(),
            correlation_id=f"ping_test_{uuid.uuid4().hex[:8]}"
        )
        
        success = await mq.send_message(message)
        
        if success:
            return {
                "status": "success",
                "message_id": message.id,
                "message": f"Ping sent to {agent_id}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send ping")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))