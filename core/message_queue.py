# src/core/message_queue.py
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime, timezone
import uuid

import redis.asyncio as redis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Message structure for inter-agent communication"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str
    to_agent: Optional[str] = None  # None for broadcast
    message_type: str
    payload: Dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10)  # 1=highest, 10=lowest
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None  # For request-response patterns


class MessageQueue:
    """Redis-based message queue for inter-agent communication"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("✅ Connected to Redis message queue")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("📤 Disconnected from Redis")
    
    async def publish_message(
        self, 
        message: Message,
        channel: Optional[str] = None
    ) -> bool:
        """
        Publish a message to a specific channel or agent queue
        
        Args:
            message: Message to publish
            channel: Optional specific channel, defaults to agent-specific queue
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            # Default channel based on target agent
            if not channel:
                channel = f"agent:{message.to_agent}" if message.to_agent else "broadcast"
            
            # Serialize message
            message_data = message.model_dump_json()
            
            # Publish to channel
            await self.redis.publish(channel, message_data)
            
            # Also add to priority queue for persistence
            priority_score = message.priority * 1000000 - int(message.created_at.timestamp())
            queue_key = f"queue:{channel}"
            
            await self.redis.zadd(
                queue_key,
                {message_data: priority_score}
            )
            
            # Set expiration if specified
            if message.expires_at:
                ttl = int((message.expires_at - message.created_at).total_seconds())
                await self.redis.expire(queue_key, ttl)
            
            logger.debug(f"📤 Published message {message.id} to {channel}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish message: {e}")
            return False
    
    async def subscribe_to_channel(
        self, 
        channel: str, 
        callback: Callable[[Message], None]
    ):
        """
        Subscribe to a specific channel
        
        Args:
            channel: Channel to subscribe to
            callback: Function to call when message received
        """
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)
        
        logger.info(f"📥 Subscribed to channel: {channel}")
    
    async def start_listening(self):
        """Start the message listener"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        self.running = True
        
        # Subscribe to all registered channels
        if not self.subscribers:
            logger.warning("⚠️ No subscribers registered")
            return
        
        pubsub = self.redis.pubsub()
        
        try:
            # Subscribe to all channels
            for channel in self.subscribers.keys():
                await pubsub.subscribe(channel)
                logger.info(f"🎧 Listening on channel: {channel}")
            
            # Listen for messages
            while self.running:
                try:
                    message = await pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        await self._process_message(message['channel'], message['data'])
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error in message listener: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"❌ Failed to start message listener: {e}")
        finally:
            await pubsub.close()
            self.running = False
    
    async def _process_message(self, channel: str, data: str):
        """Process incoming message"""
        try:
            message = Message.model_validate_json(data)
            
            # Call registered callbacks
            callbacks = self.subscribers.get(channel, [])
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Error in message callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def stop_listening(self):
        """Stop the message listener"""
        self.running = False
        logger.info("🛑 Message listener stopped")
    
    async def get_message_from_queue(
        self, 
        channel: str, 
        timeout: int = 5
    ) -> Optional[Message]:
        """
        Get a message from persistent queue
        
        Args:
            channel: Channel/queue name
            timeout: Timeout in seconds
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            queue_key = f"queue:{channel}"
            
            # Get highest priority message
            result = await self.redis.zpopmin(queue_key, 1)
            
            if result:
                message_data = result[0][0]  # First item, message data
                return Message.model_validate_json(message_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting message from queue: {e}")
            return None
    
    async def send_message_to_agent(self, agent_id: str, message: Message) -> bool:
        """Send message directly to an agent"""
        channel = f"agent:{agent_id}"
        return await self.publish_message(message, channel)
    
    async def broadcast_message(self, message: Message) -> bool:
        """Send broadcast message to all agents"""
        return await self.publish_message(message, "broadcast")
    
    async def subscribe_to_agent(self, agent_id: str, callback: Callable[[Message], None]):
        """Subscribe to messages for a specific agent"""
        channel = f"agent:{agent_id}"
        await self.subscribe_to_channel(channel, callback)
    
    async def subscribe_to_broadcast(self, callback: Callable[[Message], None]):
        """Subscribe to broadcast messages"""
        await self.subscribe_to_channel("broadcast", callback)
    
    async def get_queue_length(self, queue_name: str) -> int:
        """Get the length of a queue"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            queue_key = f"queue:{queue_name}"
            length = await self.redis.zcard(queue_key)
            return length
        except Exception as e:
            logger.error(f"❌ Error getting queue length: {e}")
            return 0
    
    async def create_task_queue(self, queue_name: str):
        """Create/initialize a task queue"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            queue_key = f"queue:{queue_name}"
            # Just ensure the key exists (Redis will create it on first use)
            await self.redis.exists(queue_key)
            logger.info(f"Task queue '{queue_name}' created/initialized")
        except Exception as e:
            logger.error(f"❌ Error creating task queue: {e}")
            raise
    
    async def add_task_to_queue(
        self, 
        queue_name: str, 
        task: Dict[str, Any], 
        priority: int = 5
    ) -> bool:
        """Add a task to a queue"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            queue_key = f"queue:{queue_name}"
            task_data = json.dumps(task)
            
            # Use priority and timestamp for scoring
            score = priority * 1000000 - int(datetime.now(timezone.utc).timestamp())
            
            await self.redis.zadd(queue_key, {task_data: score})
            
            task_id = task.get('task_id', 'unknown')
            logger.info(f"Task added to queue '{queue_name}': {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding task to queue: {e}")
            return False
    
    async def get_task_from_queue(
        self, 
        queue_name: str, 
        timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Get a task from a queue"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            queue_key = f"queue:{queue_name}"
            
            # Get highest priority task
            result = await self.redis.zpopmin(queue_key, 1)
            
            if result:
                task_data = result[0][0]  # First item, task data
                return json.loads(task_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting task from queue: {e}")
            return None
    
    async def get_message_history(
        self, 
        agent_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get message history for an agent"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        try:
            history_key = f"history:{agent_id}"
            
            # Get recent messages (stored as JSON strings)
            messages = await self.redis.lrange(history_key, 0, limit - 1)
            
            return [json.loads(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"❌ Error getting message history: {e}")
            return []
    
    async def store_message_in_history(self, agent_id: str, message: Message):
        """Store message in agent's history"""
        if not self.redis:
            return
        
        try:
            history_key = f"history:{agent_id}"
            message_data = json.dumps({
                "id": message.id,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "message_type": message.message_type,
                "payload": message.payload,
                "created_at": message.created_at.isoformat(),
                "correlation_id": message.correlation_id
            })
            
            # Store message and keep only recent 1000 messages
            await self.redis.lpush(history_key, message_data)
            await self.redis.ltrim(history_key, 0, 999)
            
        except Exception as e:
            logger.error(f"❌ Error storing message history: {e}")
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy"""
        if not self.redis:
            return False
        
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get message queue statistics"""
        if not self.redis:
            return {"status": "disconnected"}
        
        try:
            info = await self.redis.info()
            return {
                "status": "connected",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "subscribers": len(self.subscribers)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global message queue instance
_message_queue: Optional[MessageQueue] = None




async def get_message_queue() -> MessageQueue:
    """Get or create the global message queue instance"""
    global _message_queue
    
    if _message_queue is None:
        _message_queue = MessageQueue()
        await _message_queue.connect()
    
    return _message_queue

async def shutdown_message_queue():
    """Shutdown the global message queue"""
    global _message_queue
    
    if _message_queue:
        await _message_queue.stop_listening()
        await _message_queue.disconnect()
        _message_queue = None
        logger.info("📡 Message queue shutdown complete")

