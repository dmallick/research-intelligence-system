#!/usr/bin/env python3
"""
Simple Communication Debug Test
Focused test to debug message queue communication issues
"""

import asyncio
import sys
import os
import uuid
import time
from datetime import datetime, timezone
import logging

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.research.research_agent import ResearchAgent
from agents.base.agent import BaseAgent
from core.message_queue import Message

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleTestAgent(BaseAgent):
    """Simple test agent for debugging communication"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, agent_type="simple_test")
        self.started_at = datetime.now(timezone.utc)
        self.received_messages = []
        self.responses = {}
        
        # Register message handlers
        self._message_handlers.update({
            "ping": self._handle_ping,
            "pong": self._handle_pong,
            "test_message": self._handle_test_message,
            "research_task": self._handle_research_task,
        })
    
    async def initialize(self):
        """Initialize the simple test agent"""
        await super().initialize()
        self.logger.info(f"🤖 Simple Test Agent {self.agent_id} initialized")
    
    async def execute_task(self, task):
        """Execute a simple task"""
        return {
            "status": "completed",
            "result": f"Task executed by {self.agent_id}",
            "task": task
        }
    
    async def get_status(self):
        """Get agent status"""
        return {
            "agent_type": self.agent_type,
            "messages_received": len(self.received_messages),
            "responses_sent": len(self.responses),
            "uptime": (datetime.now(timezone.utc) - self.started_at).total_seconds(),
            "capabilities": ["ping", "pong", "test_message"]
        }
    
    async def _handle_ping(self, message: Message):
        """Handle ping messages"""
        self.logger.info(f"📨 Received PING from {message.from_agent}")
        self.received_messages.append(message)
        
        # Send pong response
        await self.send_message(
            message.from_agent,
            "pong",
            {
                "original_ping": message.payload,
                "pong_from": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            correlation_id=message.correlation_id
        )
        
        self.logger.info(f"📤 Sent PONG to {message.from_agent}")
    
    async def _handle_pong(self, message: Message):
        """Handle pong messages"""
        self.logger.info(f"📨 Received PONG from {message.from_agent}")
        self.received_messages.append(message)
        
        # Store response for correlation
        if message.correlation_id:
            self.responses[message.correlation_id] = message.payload
    
    async def _handle_test_message(self, message: Message):
        """Handle test messages"""
        self.logger.info(f"📨 Received TEST_MESSAGE from {message.from_agent}")
        self.received_messages.append(message)
        
        # Send acknowledgment
        await self.send_message(
            message.from_agent,
            "test_ack",
            {
                "original_message": message.payload,
                "ack_from": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            correlation_id=message.correlation_id
        )
    
    async def _handle_research_task(self, message: Message):
        """Handle research task messages (for research agent compatibility)"""
        self.logger.info(f"📨 Received RESEARCH_TASK from {message.from_agent}")
        self.received_messages.append(message)
        
        # Execute simple task
        result = await self.execute_task(message.payload)
        
        # Send result back
        await self.send_message(
            message.from_agent,
            "research_result",
            {
                "task_id": message.payload.get("task_id", "unknown"),
                "status": "completed",
                "result": result,
                "agent_id": self.agent_id
            },
            correlation_id=message.correlation_id
        )
        
        self.logger.info(f"📤 Sent RESEARCH_RESULT to {message.from_agent}")
    
    async def send_ping(self, target_agent: str) -> str:
        """Send ping to another agent and return correlation ID"""
        correlation_id = f"ping_{self.agent_id}_{target_agent}_{int(time.time())}"
        
        await self.send_message(
            target_agent,
            "ping",
            {
                "ping_from": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_data": "Hello from simple test agent!"
            },
            correlation_id=correlation_id
        )
        
        self.logger.info(f"📤 Sent PING to {target_agent}")
        return correlation_id
    
    async def wait_for_response(self, correlation_id: str, timeout: int = 10) -> dict:
        """Wait for a response with given correlation ID"""
        start_time = time.time()
        
        while correlation_id not in self.responses:
            if time.time() - start_time > timeout:
                return {"status": "timeout"}
            await asyncio.sleep(0.1)
        
        return self.responses.pop(correlation_id)


async def test_basic_ping_pong():
    """Test basic ping-pong communication"""
    print("\n" + "="*60)
    print("=== BASIC PING-PONG TEST ===")
    print("="*60)
    
    agent_a = SimpleTestAgent("agent_a")
    agent_b = SimpleTestAgent("agent_b")
    
    try:
        # Initialize both agents
        await agent_a.initialize()
        await agent_b.initialize()
        
        print("✅ Both agents initialized")
        
        # Give agents time to fully start listening
        await asyncio.sleep(1)
        
        # Agent A sends ping to Agent B
        print("📤 Agent A sending PING to Agent B...")
        correlation_id = await agent_a.send_ping("agent_b")
        
        # Wait for response
        print("⏳ Waiting for PONG response...")
        response = await agent_a.wait_for_response(correlation_id, timeout=5)
        
        if response.get("status") == "timeout":
            print("❌ PING-PONG test timed out")
            
            # Debug info
            print(f"Agent A received {len(agent_a.received_messages)} messages")
            print(f"Agent B received {len(agent_b.received_messages)} messages")
            
            for msg in agent_b.received_messages:
                print(f"  Agent B got: {msg.message_type} from {msg.from_agent}")
            
            return False
        else:
            print("✅ Received PONG response!")
            print(f"   Response from: {response.get('pong_from')}")
            print(f"   Original data echoed: {response.get('original_ping', {}).get('test_data')}")
            return True
    
    except Exception as e:
        print(f"❌ PING-PONG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await agent_a.shutdown()
        await agent_b.shutdown()


async def test_research_agent_communication():
    """Test communication with actual ResearchAgent"""
    print("\n" + "="*60)
    print("=== RESEARCH AGENT COMMUNICATION TEST ===")
    print("="*60)
    
    test_agent = SimpleTestAgent("test_coordinator")
    research_agent = ResearchAgent("test_research_agent")
    
    try:
        await test_agent.initialize()
        await research_agent.initialize()
        
        print("✅ Both agents initialized")
        
        # Give agents time to start
        await asyncio.sleep(1)
        
        # Send a simple research task
        print("📤 Sending research task to research agent...")
        
        correlation_id = f"research_test_{int(time.time())}"
        
        await test_agent.send_message(
            "test_research_agent",
            "research_task",
            {
                "type": "web_scrape",
                "url": "https://httpbin.org/html",
                "task_id": "simple_test"
            },
            correlation_id=correlation_id
        )
        
        # Wait for response
        print("⏳ Waiting for research result...")
        response = await test_agent.wait_for_response(correlation_id, timeout=15)
        
        if response.get("status") == "timeout":
            print("❌ Research task timed out")
            
            # Debug info
            print(f"Test agent received {len(test_agent.received_messages)} messages")
            for msg in test_agent.received_messages:
                print(f"  Got: {msg.message_type} from {msg.from_agent}")
            
            return False
        else:
            print("✅ Received research result!")
            print(f"   Status: {response.get('status', 'unknown')}")
            print(f"   Agent: {response.get('agent_id', 'unknown')}")
            return True
    
    except Exception as e:
        print(f"❌ Research agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await test_agent.shutdown()
        await research_agent.shutdown()


async def test_message_queue_health():
    """Test message queue connection and basic functionality"""
    print("\n" + "="*60)
    print("=== MESSAGE QUEUE HEALTH CHECK ===")
    print("="*60)
    
    try:
        # Test Redis connection
        from core.message_queue import MessageQueue, get_message_queue
        
        #mq = MessageQueue("redis://localhost:6379/")
        #await mq.initialize()
        #mq.connect
        mq = await get_message_queue()
        
        
        print("✅ Message queue connection established")
        
        # Check if we can connect and publish/subscribe -- Start
        if mq.is_connected():
            print("Successfully connected to Message Queue.")
        # Now you can use the instance to interact with the message queue
        mq.publish("my_topic", "Hello, Message Queue!")
        message = mq.get("my_topic")
        if message:
            print(f"Received message: {message}")
        else:
            print("No message received from the topic.")
        # Check if we can connect and publish/subscribe -- End    

        # Test basic pub/sub
        test_channel = "test_health_check"
        test_message = {"test": "message", "timestamp": datetime.now().isoformat()}
        
        # Subscribe to test channel
        async def message_handler(channel, message):
            print(f"✅ Received test message on {channel}: {message}")
        
        await mq.subscribe(test_channel, message_handler)
        print(f"✅ Subscribed to {test_channel}")
        
        # Give subscription time to register
        await asyncio.sleep(0.5)
        
        # Publish test message
        await mq.publish(test_channel, test_message)
        print(f"✅ Published test message to {test_channel}")
        
        # Give time for message processing
        await asyncio.sleep(1)
        
        await mq.shutdown()
        print("✅ Message queue health check completed")
        
        return True
    
    except Exception as e:
        print(f"❌ Message queue health check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run communication debug tests"""
    print("🚀 Starting Communication Debug Tests")
    print("Make sure Redis is running (docker-compose up)")
    
    tests = [
        ("Message Queue Health", test_message_queue_health),
        ("Basic Ping-Pong", test_basic_ping_pong),
        ("Research Agent Communication", test_research_agent_communication),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n⚡ Running {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
            results.append((test_name, False))
        
        # Delay between tests
        await asyncio.sleep(2)
    
    # Summary
    print("\n" + "="*60)
    print("🏁 COMMUNICATION DEBUG SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All debug tests passed! Communication system is working.")
    else:
        print("⚠️ Some tests failed - check the logs above for details.")


if __name__ == "__main__":
    asyncio.run(main())