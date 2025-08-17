from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid
import asyncio
from datetime import datetime
import logging

from core.config import settings
from core.database import get_db
from models.agent_state import AgentState

@dataclass
class AgentMessage:
    id: str
    sender_id: str
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None

class BaseAgent(ABC):
    def __init__(self, agent_type: str, agent_id: str = None):
        self.agent_id = agent_id or f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.status = "idle"
        self.logger = logging.getLogger(f"{agent_type}.{self.agent_id}")
        self.message_queue = []
        self.current_task = None
        
    async def initialize(self):
        """Initialize agent resources"""
        await self._register_agent()
        await self._setup_message_handling()
        self.logger.info(f"Agent {self.agent_id} initialized")
    
    async def _register_agent(self):
        """Register agent in database"""
        async with get_db() as db:
            agent_state = AgentState(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                status=self.status,
                last_heartbeat=datetime.utcnow()
            )
            db.add(agent_state)
            await db.commit()
    
    async def _setup_message_handling(self):
        """Setup message queue handling"""
        # Setup Redis pub/sub or similar
        pass
    
    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a specific task - must be implemented by subclasses"""
        pass
    
    async def send_message(self, receiver_id: str, message_type: str, content: Dict[str, Any]):
        """Send message to another agent"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            timestamp=datetime.utcnow()
        )
        # Implement message sending via Redis/RabbitMQ
        self.logger.info(f"Sent message to {receiver_id}: {message_type}")
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive message from queue"""
        if self.message_queue:
            return self.message_queue.pop(0)
        return None
    
    async def heartbeat(self):
        """Update agent heartbeat"""
        async with get_db() as db:
            agent_state = await db.query(AgentState).filter(
                AgentState.agent_id == self.agent_id
            ).first()
            if agent_state:
                agent_state.last_heartbeat = datetime.utcnow()
                agent_state.status = self.status
                agent_state.current_task = self.current_task
                await db.commit()
    
    async def run(self):
        """Main agent loop"""
        await self.initialize()
        
        while True:
            try:
                # Send heartbeat
                await self.heartbeat()
                
                # Check for messages
                message = await self.receive_message()
                if message:
                    await self._handle_message(message)
                
                # Process any pending tasks
                if self.status == "idle":
                    task = await self._get_next_task()
                    if task:
                        await self._execute_task(task)
                
                await asyncio.sleep(1)  # Prevent busy waiting
                
            except Exception as e:
                self.logger.error(f"Error in agent loop: {e}")
                self.status = "error"
                await asyncio.sleep(5)  # Back off on error
    
    async def _handle_message(self, message: AgentMessage):
        """Handle incoming message"""
        self.logger.info(f"Received message: {message.message_type}")
        # Implement message handling logic
    
    async def _get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from queue"""
        # Implement task retrieval logic
        pass
    
    async def _execute_task(self, task: Dict[str, Any]):
        """Execute a task"""
        self.status = "busy"
        self.current_task = task.get("task_id")
        
        try:
            result = await self.process_task(task)
            await self._save_result(task, result)
            self.status = "idle"
            self.current_task = None
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            self.status = "error"
    
    async def _save_result(self, task: Dict[str, Any], result: Dict[str, Any]):
        """Save task result"""
        # Implement result saving logic
        pass

    # Add this method to your BaseAgent class in agents/base/agent.py

async def _register_agent_safe(self):
    """Register agent with duplicate handling"""
    try:
        async with AsyncSession(engine) as session:
            # Check if agent already exists
            result = await session.execute(
                select(AgentState).where(AgentState.agent_id == self.agent_id)
            )
            existing_agent = result.scalar_one_or_none()
            
            if existing_agent:
                # Update existing agent
                existing_agent.status = "active"
                existing_agent.last_heartbeat = datetime.utcnow()
                existing_agent.agent_metadata = {}
                self.logger.info(f"Updated existing agent registration: {self.agent_id}")
            else:
                # Create new agent
                agent_state = AgentState(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    status="active",
                    last_heartbeat=datetime.utcnow(),
                    agent_metadata={}
                )
                session.add(agent_state)
                self.logger.info(f"Created new agent registration: {self.agent_id}")
            
            await session.commit()
            
    except Exception as e:
        self.logger.error(f"Failed to register agent {self.agent_id}: {e}")
        # Don't raise exception, allow agent to continue
        
# Replace the _register_agent call in the initialize method with _register_agent_safe