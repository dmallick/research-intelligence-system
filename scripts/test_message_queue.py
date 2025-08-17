#!/usr/bin/env python3
"""
Fixed test script for Redis message queue system
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
        
        # Give agents time to subscribe to channels
        await asyncio.sleep(1)
        
        # Test ping-pong communication
        print("Testing ping-pong communication...")
        await agent1.send_test_ping("test_agent_2")
        print("✅ Ping message sent")
        
        # Wait for response
        await asyncio.sleep(2)
        
        # Test task message
        print("Testing task message...")
        task_data = {
            "task_id": "test_task_001",
            "type": "simple_test", 
            "data": {"value": 42, "description": "Test task from fixed script"}
        }
        
        await agent1.send_test_task("test_agent_2", task_data)
        print("✅ Task message sent")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Check message history
        history1 = await agent1.get_message_history()
        history2 = await agent2.get_message_history()
        
        print(f"✅ Agent 1 message history: {len(history1)} messages")
        print(f"✅ Agent 2 message history: {len(history2)} messages")
        
        # Look for specific message types
        agent1_pongs = [msg for msg in history1 if msg["message_type"] == "pong"]
        agent1_results = [msg for msg in history1 if msg["message_type"] == "task_result"]
        
        if agent1_pongs:
            print("✅ Received pong response")
        else:
            print("⚠️  No pong response received")
        
        if agent1_results:
            print("✅ Received task result")
        else:
            print("⚠️  No task result received")
        
        # Clean up
        await agent1.shutdown()
        await agent2.shutdown()
        
        return len(agent1_pongs) > 0 or len(agent1_results) > 0
        
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
        retrieved_tasks = []
        for i in range(length):
            task = await mq.get_task_from_queue(queue_name, timeout=2)
            if task:
                print(f"✅ Got task: {task['task_id']}")
                retrieved_tasks.append(task)
            else:
                print("❌ No task received")
        
        # Check final queue length
        final_length = await mq.get_queue_length(queue_name)
        print(f"✅ Final queue length: {final_length}")
        
        return len(retrieved_tasks) == len(test_tasks)
        
    except Exception as e:
        print(f"❌ Task queue test failed: {e}")
        return False

async def test_broadcast_messages():
    """Test broadcast messaging"""
    print("\n=== Testing Broadcast Messages ===")
    
    try:
        # Create multiple test agents
        agents = []
        for i in range(3):
            agent = TestAgent(f"broadcast_test_agent_{i}")
            await agent.initialize()
            agents.append(agent)
        
        print(f"✅ Created {len(agents)} test agents")
        
        # Give agents time to subscribe
        await asyncio.sleep(1)
        
        # Send broadcast message from first agent
        broadcast_agent = agents[0]
        await broadcast_agent.send_broadcast_message(
            "test_broadcast",
            {
                "message": "Hello to all agents!",
                "sender": broadcast_agent.agent_id,
                "timestamp": "test_broadcast_001"
            }
        )
        
        print("✅ Broadcast message sent")
        
        # Wait for message propagation
        await asyncio.sleep(2)
        
        # Check if other agents received the broadcast
        received_count = 0
        for agent in agents[1:]:  # Skip the sender
            history = await agent.get_message_history()
            broadcasts = [msg for msg in history if msg["message_type"] == "test_broadcast"]
            if broadcasts:
                received_count += 1
                print(f"✅ {agent.agent_id} received broadcast")
            else:
                print(f"❌ {agent.agent_id} did not receive broadcast")
        
        # Clean up
        for agent in agents:
            await agent.shutdown()
        
        print(f"📊 Broadcast test: {received_count}/{len(agents)-1} agents received message")
        return received_count > 0
        
    except Exception as e:
        print(f"❌ Broadcast test failed: {e}")
        return False

async def test_message_correlation():
    """Test message correlation IDs"""
    print("\n=== Testing Message Correlation ===")
    
    try:
        # Create test agents
        requester = TestAgent("correlation_requester")
        responder = TestAgent("correlation_responder")
        
        await requester.initialize()
        await responder.initialize()
        
        # Give agents time to subscribe
        await asyncio.sleep(1)
        
        # Send message with correlation ID
        correlation_id = "test_correlation_123"
        await requester.send_message(
            "correlation_responder",
            "echo",
            {"test_data": "correlation test message"},
            correlation_id=correlation_id
        )
        
        print("✅ Message with correlation ID sent")
        
        # Wait for response
        await asyncio.sleep(2)
        
        # Check if response has matching correlation ID
        history = await requester.get_message_history()
        echo_responses = [msg for msg in history if msg["message_type"] == "echo_response"]
        
        matching_responses = [
            msg for msg in echo_responses 
            if msg.get("correlation_id") == correlation_id
        ]
        
        if matching_responses:
            print("✅ Received response with matching correlation ID")
            success = True
        else:
            print("❌ No response with matching correlation ID")
            success = False
        
        # Clean up
        await requester.shutdown()
        await responder.shutdown()
        
        return success
        
    except Exception as e:
        print(f"❌ Message correlation test failed: {e}")
        return False

async def test_error_handling():
    """Test error handling in message queue"""
    print("\n=== Testing Error Handling ===")
    
    try:
        agent = TestAgent("error_test_agent")
        await agent.initialize()
        
        # Test sending to non-existent agent
        print("Testing message to non-existent agent...")
        success = await agent.send_message(
            "non_existent_agent",
            "test_message",
            {"data": "this should work even if agent doesn't exist"}
        )
        
        if success:
            print("✅ Message sent to non-existent agent (queued)")
        else:
            print("❌ Failed to send message to non-existent agent")
        
        # Test invalid message format (this should be handled gracefully)
        print("Testing message queue resilience...")
        
        # The message queue should handle various edge cases
        await agent.send_message(
            agent.agent_id,  # Send to self
            "self_test",
            {"message": "testing self-messaging"}
        )
        
        await asyncio.sleep(1)
        
        # Clean up
        await agent.shutdown()
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Fixed Message Queue Tests")
    print("Make sure Redis is running (docker-compose up)")
    
    # Test results tracking
    test_results = {}
    
    # Test basic connectivity
    basic_test = await test_basic_message_queue()
    test_results["Basic Message Queue"] = basic_test
    
    if not basic_test:
        print("❌ Basic tests failed. Exiting.")
        return
    
    # Test agent communication
    comm_test = await test_agent_communication()
    test_results["Agent Communication"] = comm_test
    
    # Test task queues
    queue_test = await test_task_queues()
    test_results["Task Queues"] = queue_test
    
    # Test broadcast messages
    broadcast_test = await test_broadcast_messages()
    test_results["Broadcast Messages"] = broadcast_test
    
    # Test message correlation
    correlation_test = await test_message_correlation()
    test_results["Message Correlation"] = correlation_test
    
    # Test error handling
    error_test = await test_error_handling()
    test_results["Error Handling"] = error_test
    
    # Summary
    print("\n" + "="*60)
    print("🏁 FIXED MESSAGE QUEUE TEST SUMMARY")
    print("="*60)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\nSuccess Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
    
    if success_rate == 100:
        print("\n🎉 All tests passed! Message queue system is fully functional.")
    elif success_rate >= 80:
        print("\n✅ Most tests passed! Message queue system is working well.")
    elif success_rate >= 60:
        print("\n⚠️  Some tests failed. Message queue system has issues but basic functionality works.")
    else:
        print("\n❌ Many tests failed. Message queue system has significant issues.")
    
    print("\n📋 Next steps:")
    if passed_tests == total_tests:
        print("  • Message queue system is ready for production use")
        print("  • You can now test the Research Agent")
        print("  • Run: python scripts/test_research_agent.py")
    else:
        print("  • Fix failing tests before proceeding")
        print("  • Check Redis connection and configuration")
        print("  • Review error messages above")

if __name__ == "__main__":
    asyncio.run(main())