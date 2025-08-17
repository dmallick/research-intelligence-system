# src/agents/base_agent.py
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from core.message_queue import get_message_queue, Message

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents in the system"""
    
    def __init__(self, agent_id: str, agent_type: str = "base"):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.is_active = False
        self.message_queue = None
        self.logger = logging.getLogger(f"{agent_type}.{agent_id}")
        self._message_handlers = {}
        self._running = False
        
        # Register default message handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default message handlers"""
        self._message_handlers.update({
            "ping": self._handle_ping,
            "pong": self._handle_pong,
            "heartbeat": self._handle_heartbeat,
            "shutdown": self._handle_shutdown,
            "status_request": self._handle_status_request,
        })
    
    async def initialize(self):
        """Initialize the agent and connect to message queue"""
        try:
            # Get message queue instance
            self.message_queue = await get_message_queue()
            
            # Subscribe to agent-specific channel
            await self.message_queue.subscribe_to_agent(self.agent_id, self._handle_message)
            
            # Subscribe to broadcast channel
            await self.message_queue.subscribe_to_broadcast(self._handle_message)
            
            self.is_active = True
            self._running = True
            
            # Send initialization message
            await self._send_heartbeat()
            
            self.logger.info(f"Agent {self.agent_id} initialized")
            
            # Start message processing loop
            asyncio.create_task(self._message_processing_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the agent"""
        self._running = False
        self.is_active = False
        
        if self.message_queue:
            # Send shutdown notification
            await self.send_broadcast_message(
                "agent_shutdown",
                {"agent_id": self.agent_id, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
        
        self.logger.info(f"Agent {self.agent_id} shutdown")
    
    async def send_message(
        self, 
        to_agent: str, 
        message_type: str, 
        payload: Dict[str, Any],
        priority: int = 5,
        correlation_id: Optional[str] = None,
        expires_in_seconds: Optional[int] = None
    ) -> bool:
        """
        Send a message to another agent
        
        Args:
            to_agent: Target agent ID
            message_type: Type of message
            payload: Message payload
            priority: Message priority (1=highest, 10=lowest)
            correlation_id: Optional correlation ID for request-response patterns
            expires_in_seconds: Optional expiration time in seconds
        """
        if not self.message_queue:
            self.logger.error("Message queue not initialized")
            return False
        
        try:
            expires_at = None
            if expires_in_seconds:
                expires_at = datetime.now(timezone.utc).timestamp() + expires_in_seconds
                expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)
            
            message = Message(
                from_agent=self.agent_id,
                to_agent=to_agent,
                message_type=message_type,
                payload=payload,
                priority=priority,
                correlation_id=correlation_id,
                expires_at=expires_at
            )
            
            success = await self.message_queue.send_message_to_agent(to_agent, message)
            
            if success:
                self.logger.debug(f"Sent {message_type} message to {to_agent}")
            else:
                self.logger.error(f"Failed to send {message_type} message to {to_agent}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
    
    async def send_broadcast_message(
        self, 
        message_type: str, 
        payload: Dict[str, Any],
        priority: int = 5,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send a broadcast message to all agents"""
        if not self.message_queue:
            self.logger.error("Message queue not initialized")
            return False
        
        try:
            message = Message(
                from_agent=self.agent_id,
                to_agent=None,  # Broadcast
                message_type=message_type,
                payload=payload,
                priority=priority,
                correlation_id=correlation_id
            )
            
            success = await self.message_queue.broadcast_message(message)
            
            if success:
                self.logger.debug(f"Broadcast {message_type} message")
            else:
                self.logger.error(f"Failed to broadcast {message_type} message")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error broadcasting message: {e}")
            return False
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages"""
        try:
            # Don't process our own messages
            if message.from_agent == self.agent_id:
                return
            
            self.logger.debug(f"Received {message.message_type} from {message.from_agent}")
            
            # Check if we have a handler for this message type
            handler = self._message_handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                # Try custom handler
                await self.handle_custom_message(message)
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def _message_processing_loop(self):
        """Background loop for processing messages"""
        while self._running:
            try:
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e}")
    
    # Default message handlers
    async def _handle_ping(self, message: Message):
        """Handle ping messages with pong response"""
        await self.send_message(
            message.from_agent,
            "pong",
            {
                "original_payload": message.payload,
                "pong_from": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            correlation_id=message.correlation_id
        )
        self.logger.debug(f"Responded to ping from {message.from_agent}")
    
    async def _handle_pong(self, message: Message):
        """Handle pong responses"""
        self.logger.info(f"Received pong from {message.from_agent}: {message.payload}")
    
    async def _handle_heartbeat(self, message: Message):
        """Handle heartbeat messages"""
        self.logger.debug(f"Heartbeat from {message.from_agent}")
    
    async def _handle_shutdown(self, message: Message):
        """Handle shutdown messages"""
        if message.payload.get("target_agent") == self.agent_id:
            self.logger.info(f"Shutdown requested by {message.from_agent}")
            await self.shutdown()
    
    async def _handle_status_request(self, message: Message):
        """Handle status request messages"""
        status = {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "is_active": self.is_active,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": await self.get_status()
        }
        
        await self.send_message(
            message.from_agent,
            "status_response",
            status,
            correlation_id=message.correlation_id
        )
    
    async def _send_heartbeat(self):
        """Send heartbeat message"""
        await self.send_broadcast_message(
            "heartbeat",
            {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    # Abstract methods that subclasses must implement
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task"""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        pass
    
    # Optional method for custom message handling
    async def handle_custom_message(self, message: Message):
        """Handle custom message types - override in subclasses"""
        self.logger.warning(f"Unhandled message type: {message.message_type} from {message.from_agent}")
    
    # Utility methods
    async def register_message_handler(self, message_type: str, handler):
        """Register a custom message handler"""
        self._message_handlers[message_type] = handler
        self.logger.debug(f"Registered handler for {message_type}")
    
    async def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "is_active": self.is_active,
            "uptime": "Not implemented",  # TODO: Track uptime
            "messages_sent": "Not implemented",  # TODO: Track message counts
            "messages_received": "Not implemented",
            "last_activity": datetime.now(timezone.utc).isoformat()
        }