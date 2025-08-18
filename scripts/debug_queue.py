# message_queue/debug_queue.py
import asyncio
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class MessageQueueDebugger:
    """Debug and fix message queue issues"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Establish Redis connection with error handling"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
    
    async def test_basic_operations(self):
        """Test basic Redis operations"""
        if not self.redis_client:
            return False
        
        try:
            # Test SET/GET
            await self.redis_client.set("test_key", "test_value", ex=10)
            value = await self.redis_client.get("test_key")
            assert value == "test_value", f"Expected 'test_value', got {value}"
            
            # Test LIST operations
            await self.redis_client.lpush("test_list", "item1", "item2")
            items = await self.redis_client.lrange("test_list", 0, -1)
            assert len(items) == 2, f"Expected 2 items, got {len(items)}"
            
            # Cleanup
            await self.redis_client.delete("test_key", "test_list")
            
            logger.info("✅ Basic Redis operations working")
            return True
        except Exception as e:
            logger.error(f"❌ Basic operations failed: {e}")
            return False
    
    async def test_pub_sub(self):
        """Test Redis Pub/Sub functionality"""
        if not self.redis_client:
            return False
        
        try:
            # Create subscriber
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("test_channel")
            
            # Publish message
            await self.redis_client.publish("test_channel", "test_message")
            
            # Check for message (with timeout)
            message = await asyncio.wait_for(pubsub.get_message(), timeout=2.0)
            if message and message['type'] == 'message':
                logger.info("✅ Pub/Sub working")
                await pubsub.unsubscribe("test_channel")
                return True
            else:
                logger.warning("⚠️ No message received in Pub/Sub test")
                return False
                
        except asyncio.TimeoutError:
            logger.error("❌ Pub/Sub test timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Pub/Sub test failed: {e}")
            return False
    
    async def diagnose_queue_issues(self):
        """Run comprehensive diagnostics"""
        logger.info("🔍 Starting message queue diagnostics...")
        
        results = {
            "connection": await self.connect(),
            "basic_ops": False,
            "pub_sub": False
        }
        
        if results["connection"]:
            results["basic_ops"] = await self.test_basic_operations()
            results["pub_sub"] = await self.test_pub_sub()
        
        # Print diagnostic report
        self._print_diagnostic_report(results)
        return results
    
    def _print_diagnostic_report(self, results: Dict[str, bool]):
        """Print formatted diagnostic report"""
        print("\n" + "="*50)
        print("📊 MESSAGE QUEUE DIAGNOSTIC REPORT")
        print("="*50)
        
        for test, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test.upper():<15}: {status}")
        
        overall = all(results.values())
        print(f"\nOVERALL STATUS: {'✅ HEALTHY' if overall else '❌ ISSUES DETECTED'}")
        
        if not overall:
            print("\n🔧 RECOMMENDED FIXES:")
            if not results["connection"]:
                print("- Check Redis server is running: docker-compose ps")
                print("- Verify Redis port 6379 is accessible")
                print("- Check network connectivity")
            if not results["basic_ops"]:
                print("- Redis may be misconfigured")
                print("- Check Redis logs: docker-compose logs redis")
            if not results["pub_sub"]:
                print("- Pub/Sub may need Redis restart")
                print("- Check for Redis memory issues")
        
        print("="*50)

# Fixed MessageQueue implementation
class MessageQueue:
    """Production-ready message queue with proper error handling"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.subscribers = {}
        self._running = False
    
    async def connect(self):
        """Connect to Redis with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding='utf-8',
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30,
                    retry_on_timeout=True
                )
                
                await self.redis_client.ping()
                logger.info(f"✅ Connected to Redis (attempt {attempt + 1})")
                return True
                
            except Exception as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error("❌ Failed to connect to Redis after all retries")
                    return False
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish message with error handling"""
        if not self.redis_client:
            await self.connect()
        
        try:
            message_str = json.dumps({
                **message,
                "timestamp": datetime.utcnow().isoformat(),
                "channel": channel
            })
            
            result = await self.redis_client.publish(channel, message_str)
            logger.debug(f"Published to {channel}: {result} subscribers")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False
    
    async def subscribe(self, channel: str, handler):
        """Subscribe to channel with proper error handling"""
        if not self.redis_client:
            await self.connect()
        
        try:
            if not self.pubsub:
                self.pubsub = self.redis_client.pubsub()
            
            await self.pubsub.subscribe(channel)
            self.subscribers[channel] = handler
            
            logger.info(f"✅ Subscribed to channel: {channel}")
            
            # Start message processing if not already running
            if not self._running:
                asyncio.create_task(self._process_messages())
                self._running = True
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            return False
    
    async def _process_messages(self):
        """Process incoming messages"""
        logger.info("🔄 Starting message processor")
        
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    await self._handle_message(message)
        except Exception as e:
            logger.error(f"Message processor error: {e}")
            self._running = False
    
    async def _handle_message(self, message):
        """Handle individual message"""
        try:
            channel = message['channel']
            data = json.loads(message['data'])
            
            handler = self.subscribers.get(channel)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            else:
                logger.warning(f"No handler for channel: {channel}")
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    async def disconnect(self):
        """Clean disconnect"""
        self._running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Disconnected from Redis")

# Test script
async def main():
    """Run diagnostics and test fixed implementation"""
    
    # Run diagnostics first
    debugger = MessageQueueDebugger()
    results = await debugger.diagnose_queue_issues()
    
    if not all(results.values()):
        print("❌ Fix the issues above before proceeding")
        return
    
    # Test the fixed implementation
    print("\n🧪 Testing fixed MessageQueue implementation...")
    
    queue = MessageQueue()
    await queue.connect()
    
    # Test handler
    received_messages = []
    
    async def test_handler(message):
        received_messages.append(message)
        print(f"📨 Received: {message}")
    
    # Subscribe and publish
    await queue.subscribe("test_agent_channel", test_handler)
    await asyncio.sleep(1)  # Let subscription settle
    
    # Send test message
    test_msg = {
        "agent_id": "test_agent",
        "task_id": "task_123",
        "status": "completed",
        "data": {"result": "success"}
    }
    
    success = await queue.publish("test_agent_channel", test_msg)
    await asyncio.sleep(2)  # Wait for message processing
    
    print(f"\n📊 Test Results:")
    print(f"Message published: {'✅' if success else '❌'}")
    print(f"Message received: {'✅' if received_messages else '❌'}")
    
    if received_messages:
        print(f"Received {len(received_messages)} message(s)")
    
    await queue.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())