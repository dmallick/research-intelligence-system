import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import asdict
import redis.asyncio as redis
from datetime import datetime
import uuid

from core.config import settings
from agents.base.agent import AgentMessage

class MessageQueue:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = None
        self.pubsub = None
        self.subscribers = {}  # agent_id -> callback function
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize Redis connection and pub/sub"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
            
            # Initialize pub/sub
            self.pubsub = self.redis_client.pubsub()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connections"""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        self.logger.info("Redis connections closed")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send message to specific agent via Redis pub/sub"""
        try:
            channel = f"agent:{message.receiver_id}"
            message_data = {
                "id": message.id,
                "sender_id": message.sender_id,
                "receiver_id": message.receiver_id,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "correlation_id": message.correlation_id
            }
            
            # Publish message
            await self.redis_client.publish(channel, json.dumps(message_data))
            
            # Also store in message history for reliability
            await self._store_message_history(message)
            
            self.logger.info(f"Message sent from {message.sender_id} to {message.receiver_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    async def subscribe_to_messages(self, agent_id: str, callback: Callable):
        """Subscribe agent to receive messages"""
        try:
            channel = f"agent:{agent_id}"
            await self.pubsub.subscribe(channel)
            
            self.subscribers[agent_id] = callback
            self.logger.info(f"Agent {agent_id} subscribed to messages")
            
            # Start message listener task
            asyncio.create_task(self._message_listener(agent_id))
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe agent {agent_id}: {e}")
    
    async def unsubscribe_from_messages(self, agent_id: str):
        """Unsubscribe agent from messages"""
        try:
            channel = f"agent:{agent_id}"
            await self.pubsub.unsubscribe(channel)
            
            if agent_id in self.subscribers:
                del self.subscribers[agent_id]
            
            self.logger.info(f"Agent {agent_id} unsubscribed from messages")
            
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe agent {agent_id}: {e}")
    
    async def _message_listener(self, agent_id: str):
        """Listen for messages for a specific agent"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        message_data = json.loads(message["data"])
                        agent_message = AgentMessage(
                            id=message_data["id"],
                            sender_id=message_data["sender_id"],
                            receiver_id=message_data["receiver_id"],
                            message_type=message_data["message_type"],
                            content=message_data["content"],
                            timestamp=datetime.fromisoformat(message_data["timestamp"]),
                            correlation_id=message_data.get("correlation_id")
                        )
                        
                        # Call the agent's message handler
                        if agent_id in self.subscribers:
                            await self.subscribers[agent_id](agent_message)
                            
                    except Exception as e:
                        self.logger.error(f"Error processing message for {agent_id}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Message listener error for {agent_id}: {e}")
    
    async def broadcast_message(self, sender_id: str, message_type: str, content: Dict[str, Any], agent_types: List[str] = None):
        """Broadcast message to multiple agents or all agents of specific types"""
        try:
            message_id = str(uuid.uuid4())
            
            if agent_types:
                # Broadcast to specific agent types
                for agent_type in agent_types:
                    channel = f"agent_type:{agent_type}"
                    message_data = {
                        "id": message_id,
                        "sender_id": sender_id,
                        "receiver_id": f"broadcast:{agent_type}",
                        "message_type": message_type,
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat(),
                        "correlation_id": None
                    }
                    await self.redis_client.publish(channel, json.dumps(message_data))
            else:
                # Broadcast to all agents
                channel = "agent_broadcast"
                message_data = {
                    "id": message_id,
                    "sender_id": sender_id,
                    "receiver_id": "broadcast:all",
                    "message_type": message_type,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": None
                }
                await self.redis_client.publish(channel, json.dumps(message_data))
            
            self.logger.info(f"Broadcast message sent from {sender_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
            return False
    
    async def get_message_history(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get message history for an agent"""
        try:
            key = f"messages:{agent_id}"
            messages = await self.redis_client.lrange(key, 0, limit - 1)
            
            return [json.loads(msg) for msg in messages]
            
        except Exception as e:
            self.logger.error(f"Failed to get message history for {agent_id}: {e}")
            return []
    
    async def _store_message_history(self, message: AgentMessage):
        """Store message in history for both sender and receiver"""
        try:
            message_data = {
                "id": message.id,
                "sender_id": message.sender_id,
                "receiver_id": message.receiver_id,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "correlation_id": message.correlation_id
            }
            
            # Store for receiver
            receiver_key = f"messages:{message.receiver_id}"
            await self.redis_client.lpush(receiver_key, json.dumps(message_data))
            await self.redis_client.ltrim(receiver_key, 0, 999)  # Keep last 1000 messages
            
            # Store for sender
            sender_key = f"messages:{message.sender_id}"
            await self.redis_client.lpush(sender_key, json.dumps(message_data))
            await self.redis_client.ltrim(sender_key, 0, 999)  # Keep last 1000 messages
            
        except Exception as e:
            self.logger.error(f"Failed to store message history: {e}")
    
    async def create_task_queue(self, queue_name: str):
        """Create a task queue for work distribution"""
        try:
            # Initialize queue if it doesn't exist
            key = f"queue:{queue_name}"
            if not await self.redis_client.exists(key):
                await self.redis_client.lpush(key, "initialized")
                await self.redis_client.lpop(key)
            
            self.logger.info(f"Task queue '{queue_name}' created/initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to create task queue {queue_name}: {e}")
    
    async def add_task_to_queue(self, queue_name: str, task: Dict[str, Any]) -> bool:
        """Add task to a queue"""
        try:
            key = f"queue:{queue_name}"
            task_data = json.dumps(task)
            await self.redis_client.lpush(key, task_data)
            
            self.logger.info(f"Task added to queue '{queue_name}': {task.get('task_id', 'unknown')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add task to queue {queue_name}: {e}")
            return False
    
    async def get_task_from_queue(self, queue_name: str, timeout: int = 1) -> Optional[Dict[str, Any]]:
        """Get task from queue (blocking with timeout)"""
        try:
            key = f"queue:{queue_name}"
            result = await self.redis_client.brpop(key, timeout=timeout)
            
            if result:
                _, task_data = result
                return json.loads(task_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get task from queue {queue_name}: {e}")
            return None
    
    async def get_queue_length(self, queue_name: str) -> int:
        """Get number of tasks in queue"""
        try:
            key = f"queue:{queue_name}"
            return await self.redis_client.llen(key)
            
        except Exception as e:
            self.logger.error(f"Failed to get queue length for {queue_name}: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False

# Global message queue instances
message_queue = MessageQueue()

async def get_message_queue() -> MessageQueue:
    """Get message queue instance"""
    if not message_queue.redis_client:
        await message_queue.initialize()
    return message_queue