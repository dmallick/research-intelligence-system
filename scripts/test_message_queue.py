#!/usr/bin/env python3
"""
Test script for Redis message queue system
Run this after starting the API to test message queue functionality
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.test_agent import TestAgent
from core.message_queue import get_message_queue
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_basic_message_queue():
    """Test basic message queue functionality"""
    print("=== Testing Basic Message Queue ===")
    
    try:
        # Get message queue
        mq = await get_message_queue()
        print("✅ Message queue connected")
        
        # Test health check
        health = await mq.health_check()
        print(f"✅ Redis health check: {'PASS' if health else 'FAIL'}")
        
        if not health:
            print("❌ Redis is not healthy. Please check your Docker containers.")
            return False
            
    except Exception as e:
        print(f"❌ Failed to connect to message queue: {e}")
        return False
    
    return True

async def test_agent_communication():
    """Test agent-to-agent communication"""
    print("\n=== Testing Agent Communication ===")
    
    try:
        # Create and initialize test agents
        print("Creating test agents...")
        agent1 = TestAgent("test_agent_1")
        agent2 = TestAgent("test_agent_2")
        
        await agent1.initialize()
        await agent2.initialize()
        print("✅ Test agents initialized")
        
        # Test ping-pong
        print("Testing ping-pong communication...")
        await agent1.send_message(
            "test_agent_2",
            "ping",
            {"message": "Hello from Agent 1!"},
            correlation_id="test_ping_123"
        )
        print("✅ Ping message sent")
        
        # Wait for response
        await asyncio.sleep(2)
        
        # Test task message
        print("Testing task message...")
        await agent1.send_message(
            "test_agent_2",
            "test_task",
            {
                "task_id": "test_task_001",
                "task_type": "simple_test",
                "data": {"value": 42, "description": "Test task from script"}
            },
            correlation_id="test_task_456"
        )
        print("✅ Task message sent")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Check message history
        mq = await get_message_queue()
        history1 = await mq.get_message_history("test_agent_1", 10)
        history2 = await mq.get_message_history("test_agent_2", 10)
        
        print(f"✅ Agent 1 message history: {len(history1)} messages")
        print(f"✅ Agent 2 message history: {len(history2)} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent communication test failed: {e}")
        return False

async def test_task_queues():
    """Test task queue functionality"""
    print("\n=== Testing Task Queues ===")
    
    try:
        mq = await get_message_queue()
        
        # Create test queue
        queue_name = "test_queue"
        await mq.create_task_queue(queue_name)
        print(f"✅ Created task queue: {queue_name}")
        
        # Add tasks to queue
        test_tasks = [
            {"task_id": "task_001", "type": "test", "data": "First task"},
            {"task_id": "task_002", "type": "test", "data": "Second task"},
            {"task_id": "task_003", "type": "test", "data": "Third task"}
        ]
        
        for task in test_tasks:
            success = await mq.add_task_to_queue(queue_name, task)
            if success:
                print(f"✅ Added task: {task['task_id']}")
            else:
                print(f"❌ Failed to add task: {task['task_id']}")
        
        # Check queue length
        length = await mq.get_queue_length(queue_name)
        print(f"✅ Queue length: {length}")
        
        # Get tasks from queue
        print("Getting tasks from queue...")
        for i in range(length):
            task = await mq.get_task_from_queue(queue_name, timeout=2)
            if task:
                print(f"✅ Got task: {task['task_id']}")
            else:
                print("❌ No task received")
        
        # Check final queue length
        final_length = await mq.get_queue_length(queue_name)
        print(f"✅ Final queue length: {final_length}")
        
        return True
        
    except Exception as e:
        print(f"❌ Task queue test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Message Queue Tests")
    print("Make sure Redis is running (docker-compose up)")
    
    # Test basic connectivity
    basic_test = await test_basic_message_queue()
    if not basic_test:
        print("❌ Basic tests failed. Exiting.")
        return
    
    # Test agent communication
    comm_test = await test_agent_communication()
    
    # Test task queues
    queue_test = await test_task_queues()
    
    # Summary
    print("\n" + "="*50)
    print("🏁 TEST SUMMARY")
    print("="*50)
    print(f"Basic Message Queue: {'✅ PASS' if basic_test else '❌ FAIL'}")
    print(f"Agent Communication: {'✅ PASS' if comm_test else '❌ FAIL'}")
    print(f"Task Queues: {'✅ PASS' if queue_test else '❌ FAIL'}")
    
    if all([basic_test, comm_test, queue_test]):
        print("\n🎉 All tests passed! Message queue system is working.")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    asyncio.run(main())