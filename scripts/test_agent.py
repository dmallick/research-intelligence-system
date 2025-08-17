# scripts/test_agent.py
import asyncio
import sys
import os
from typing import Dict, Any
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#from agents.base import BaseAgent
from agents.base.agent import BaseAgent

from core.message_queue import Message


class TestAgent(BaseAgent):
    """Test agent for development and testing purposes"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, agent_type="test")
        self.task_count = 0
        self.received_messages = []
        
        # Register custom handlers
        self._message_handlers.update({
            "test_task": self._handle_test_task,
            "echo": self._handle_echo,
        })
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a test task"""
        self.task_count += 1
        
        task_type = task.get("type", "unknown")
        
        if task_type == "simple_test":
            result = {
                "task_id": task.get("task_id", "unknown"),
                "status": "completed",
                "result": f"Test task executed by {self.agent_id}",
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "task_count": self.task_count
            }
        elif task_type == "echo":
            result = {
                "task_id": task.get("task_id", "unknown"),
                "status": "completed",
                "echo_data": task.get("data", {}),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            result = {
                "task_id": task.get("task_id", "unknown"),
                "status": "error",
                "error": f"Unknown task type: {task_type}",
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        
        self.logger.info(f"Executed task {task.get('task_id')}: {result['status']}")
        return result
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current test agent status"""
        return {
            "tasks_executed": self.task_count,
            "messages_received": len(self.received_messages),
            "last_message": self.received_messages[-1] if self.received_messages else None,
            "capabilities": ["test_task", "echo", "ping", "pong"]
        }
    
    async def _handle_test_task(self, message: Message):
        """Handle test task messages"""
        try:
            task_data = message.payload
            self.logger.info(f"Received test task from {message.from_agent}: {task_data}")
            
            # Execute the task
            result = await self.execute_task(task_data)
            
            # Send response back
            await self.send_message(
                message.from_agent,
                "task_result",
                {
                    "original_task": task_data,
                    "result": result,
                    "processed_by": self.agent_id
                },
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            self.logger.error(f"Error handling test task: {e}")
            
            # Send error response
            await self.send_message(
                message.from_agent,
                "task_error",
                {
                    "original_task": message.payload,
                    "error": str(e),
                    "processed_by": self.agent_id
                },
                correlation_id=message.correlation_id
            )
    
    async def _handle_echo(self, message: Message):
        """Handle echo messages"""
        echo_response = {
            "original_message": message.payload,
            "echo_from": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.send_message(
            message.from_agent,
            "echo_response",
            echo_response,
            correlation_id=message.correlation_id
        )
        
        self.logger.info(f"Echoed message back to {message.from_agent}")
    
    async def handle_custom_message(self, message: Message):
        """Handle any custom messages not covered by registered handlers"""
        self.received_messages.append({
            "message_type": message.message_type,
            "from_agent": message.from_agent,
            "timestamp": message.created_at.isoformat(),
            "payload": message.payload
        })
        
        self.logger.info(f"Received custom message: {message.message_type} from {message.from_agent}")
        
        # If it's a task_result or task_error, just log it
        if message.message_type in ["task_result", "task_error"]:
            result_status = message.payload.get("result", {}).get("status", "unknown")
            self.logger.info(f"Task result received: {result_status}")
        
        # For unhandled message types, send an acknowledgment
        elif message.message_type not in ["pong", "heartbeat", "status_response"]:
            await self.send_message(
                message.from_agent,
                "message_ack",
                {
                    "ack_for": message.message_type,
                    "message_id": message.id,
                    "received_by": self.agent_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                correlation_id=message.correlation_id
            )
    
    async def send_test_ping(self, target_agent: str):
        """Send a test ping to another agent"""
        await self.send_message(
            target_agent,
            "ping",
            {
                "ping_from": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_data": {"value": 42, "message": "Hello from test agent!"}
            },
            correlation_id=f"ping_{self.agent_id}_{target_agent}"
        )
    
    async def send_test_task(self, target_agent: str, task_data: Dict[str, Any]):
        """Send a test task to another agent"""
        await self.send_message(
            target_agent,
            "test_task",
            task_data,
            correlation_id=f"task_{task_data.get('task_id', 'unknown')}"
        )
    
    async def get_message_history(self) -> list:
        """Get the history of received messages"""
        return self.received_messages.copy()
    
    async def clear_message_history(self):
        """Clear the message history"""
        self.received_messages.clear()
        self.logger.info("Message history cleared")