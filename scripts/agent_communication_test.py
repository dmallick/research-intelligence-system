#!/usr/bin/env python3
"""
Agent-to-Agent Communication Test
Tests message passing, request-response patterns, and multi-agent coordination
"""

import asyncio
import sys
import os
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import logging

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.research.research_agent import ResearchAgent, ResearchTaskTemplates
from agents.base.agent import BaseAgent
from core.message_queue import Message, MessageQueue

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestCoordinatorAgent(BaseAgent):
    """Test agent that coordinates and manages other agents"""
    
    def __init__(self, agent_id: str = "test_coordinator"):
        super().__init__(agent_id, agent_type="coordinator")
        self.pending_requests = {}
        self.completed_tasks = []
        self.agent_responses = {}
        self.started_at = datetime.now(timezone.utc)  # Add missing attribute
        
        # Register message handlers
        self._message_handlers.update({
            "research_result": self._handle_research_result,
            "research_error": self._handle_research_error,
            "agent_status_response": self._handle_status_response,
            "task_completed": self._handle_task_completed,
            "status_response": self._handle_status_response,  # Add alternative handler
            "task_result": self._handle_research_result,  # Add alternative handler
            "task_error": self._handle_research_error,    # Add alternative handler
        })
    
    async def initialize(self):
        """Initialize the coordinator agent"""
        await super().initialize()
        self.logger.info("🎯 Test Coordinator Agent initialized")
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coordination tasks"""
        task_type = task.get("type", "unknown")
        
        if task_type == "coordinate_research":
            return await self._coordinate_research_task(task)
        elif task_type == "agent_health_check":
            return await self._check_agent_health(task)
        else:
            return {"status": "unknown_task_type", "task_type": task_type}
    
    async def _coordinate_research_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate a research task with the research agent"""
        correlation_id = str(uuid.uuid4())
        research_task = task.get("research_task", {})
        target_agent = task.get("target_agent", "research_agent")
        
        # Store pending request
        self.pending_requests[correlation_id] = {
            "task": research_task,
            "target_agent": target_agent,
            "started_at": datetime.now(timezone.utc),
            "timeout": task.get("timeout", 30)
        }
        
        # Send research task to research agent
        await self.send_message(
            target_agent,
            "research_task",
            research_task,
            correlation_id=correlation_id
        )
        
        # Wait for response
        timeout = task.get("timeout", 30)
        start_time = time.time()
        
        while correlation_id in self.pending_requests:
            if time.time() - start_time > timeout:
                del self.pending_requests[correlation_id]
                return {
                    "status": "timeout",
                    "correlation_id": correlation_id,
                    "timeout_seconds": timeout
                }
            
            await asyncio.sleep(0.1)
        
        # Return completed result
        if correlation_id in self.agent_responses:
            result = self.agent_responses.pop(correlation_id)
            self.completed_tasks.append(result)
            return result
        
        return {"status": "no_response", "correlation_id": correlation_id}
    
    async def _check_agent_health(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check health status of specified agents"""
        target_agents = task.get("agents", ["research_agent"])
        results = {}
        
        for agent_id in target_agents:
            correlation_id = str(uuid.uuid4())
            
            # Send status request
            await self.send_message(
                agent_id,
                "get_status",
                {"requested_at": datetime.now(timezone.utc).isoformat()},
                correlation_id=correlation_id
            )
            
            # Wait for response
            timeout = 10
            start_time = time.time()
            
            while correlation_id not in self.agent_responses:
                if time.time() - start_time > timeout:
                    results[agent_id] = {"status": "timeout", "available": False}
                    break
                await asyncio.sleep(0.1)
            
            if correlation_id in self.agent_responses:
                response = self.agent_responses.pop(correlation_id)
                results[agent_id] = {"status": "healthy", "available": True, "details": response}
        
        return {"agent_health": results}
    
    # Message Handlers
    async def _handle_research_result(self, message: Message):
        """Handle research results from research agents"""
        correlation_id = message.correlation_id
        if correlation_id in self.pending_requests:
            del self.pending_requests[correlation_id]
            self.agent_responses[correlation_id] = {
                "status": "success",
                "result": message.payload,
                "from_agent": message.from_agent,
                "received_at": datetime.now(timezone.utc).isoformat()
            }
            self.logger.info(f"✅ Received research result from {message.from_agent}")
    
    async def _handle_research_error(self, message: Message):
        """Handle research errors from research agents"""
        correlation_id = message.correlation_id
        if correlation_id in self.pending_requests:
            del self.pending_requests[correlation_id]
            self.agent_responses[correlation_id] = {
                "status": "error",
                "error": message.payload,
                "from_agent": message.from_agent,
                "received_at": datetime.now(timezone.utc).isoformat()
            }
            self.logger.warning(f"⚠️ Received research error from {message.from_agent}")
    
    async def _handle_status_response(self, message: Message):
        """Handle status responses from agents"""
        correlation_id = message.correlation_id
        self.agent_responses[correlation_id] = message.payload
        self.logger.info(f"📊 Received status from {message.from_agent}")
    
    async def _handle_task_completed(self, message: Message):
        """Handle task completion notifications"""
        self.logger.info(f"✅ Task completed by {message.from_agent}: {message.payload}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get coordinator agent status (required by BaseAgent)"""
        uptime = datetime.now(timezone.utc) - self.started_at
        
        return {
            "agent_type": self.agent_type,
            "capabilities": {
                "coordination": True,
                "research_delegation": True,
                "health_checking": True,
                "concurrent_tasks": True
            },
            "statistics": {
                "pending_requests": len(self.pending_requests),
                "completed_tasks": len(self.completed_tasks),
                "total_responses": len(self.agent_responses),
                "uptime_seconds": uptime.total_seconds(),
                "success_rate": (
                    len(self.completed_tasks) / max(len(self.completed_tasks) + len(self.pending_requests), 1)
                ) * 100
            },
            "configuration": {
                "max_timeout": 30,
                "health_check_timeout": 10
            }
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        return {
            "pending_requests": len(self.pending_requests),
            "completed_tasks": len(self.completed_tasks),
            "total_responses": len(self.agent_responses),
            "uptime": (datetime.now(timezone.utc) - self.started_at).total_seconds()
        }


async def test_basic_communication():
    """Test 1: Basic agent-to-agent communication"""
    print("\n" + "="*60)
    print("=== TEST 1: Basic Agent Communication ===")
    print("="*60)
    
    # Create agents
    coordinator = TestCoordinatorAgent("test_coordinator")
    research_agent = ResearchAgent("test_research_agent")
    
    try:
        # Initialize agents
        await coordinator.initialize()
        await research_agent.initialize()
        
        print("✅ Both agents initialized successfully")
        
        # Test simple message exchange
        correlation_id = str(uuid.uuid4())
        test_message = {"test": "hello", "timestamp": datetime.now().isoformat()}
        
        print(f"📤 Coordinator sending test message to research agent...")
        await coordinator.send_message(
            "test_research_agent",
            "research_task",
            {
                "type": "web_scrape",
                "url": "https://httpbin.org/html",
                "task_id": "test_communication"
            },
            correlation_id=correlation_id
        )
        
        # Wait for response
        timeout = 10
        start_time = time.time()
        
        while correlation_id not in coordinator.agent_responses:
            if time.time() - start_time > timeout:
                print("❌ Communication test timed out")
                return False
            await asyncio.sleep(0.1)
        
        response = coordinator.agent_responses[correlation_id]
        print(f"✅ Received response: {response['status']}")
        print(f"📊 Response from: {response['from_agent']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic communication test failed: {e}")
        return False
        
    finally:
        await coordinator.shutdown()
        await research_agent.shutdown()


async def test_coordinated_research_tasks():
    """Test 2: Coordinated research tasks"""
    print("\n" + "="*60)
    print("=== TEST 2: Coordinated Research Tasks ===")
    print("="*60)
    
    coordinator = TestCoordinatorAgent("task_coordinator")
    research_agent = ResearchAgent("research_worker")
    
    try:
        await coordinator.initialize()
        await research_agent.initialize()
        
        # Define multiple research tasks
        research_tasks = [
            {
                "type": "coordinate_research",
                "target_agent": "research_worker",
                "research_task": ResearchTaskTemplates.web_scrape_task("https://httpbin.org/html"),
                "timeout": 15
            },
            {
                "type": "coordinate_research", 
                "target_agent": "research_worker",
                "research_task": ResearchTaskTemplates.arxiv_search_task("quantum computing", 3),
                "timeout": 15
            },
            {
                "type": "coordinate_research",
                "target_agent": "research_worker", 
                "research_task": ResearchTaskTemplates.batch_url_extract_task([
                    "https://httpbin.org/json",
                    "https://example.com"
                ]),
                "timeout": 20
            }
        ]
        
        successful_tasks = 0
        
        for i, task in enumerate(research_tasks, 1):
            print(f"\n📋 Executing coordinated task {i}/3...")
            
            result = await coordinator.execute_task(task)
            
            if result.get("status") in ["success", "completed"]:
                successful_tasks += 1
                print(f"✅ Task {i} completed successfully")
                print(f"   Agent: {result.get('from_agent', 'unknown')}")
                print(f"   Type: {task['research_task'].get('type', 'unknown')}")
            else:
                print(f"❌ Task {i} failed: {result.get('status', 'unknown')}")
        
        print(f"\n📊 Coordination Results:")
        print(f"   Successful: {successful_tasks}/3")
        print(f"   Success Rate: {(successful_tasks/3)*100:.1f}%")
        
        # Get coordinator statistics
        stats = await coordinator.get_statistics()
        print(f"   Completed Tasks: {stats['completed_tasks']}")
        print(f"   Pending Requests: {stats['pending_requests']}")
        
        return successful_tasks >= 2  # At least 2/3 should succeed
        
    except Exception as e:
        print(f"❌ Coordinated research test failed: {e}")
        return False
        
    finally:
        await coordinator.shutdown()
        await research_agent.shutdown()


async def test_agent_discovery():
    """Test 3: Agent discovery and health checking"""
    print("\n" + "="*60)
    print("=== TEST 3: Agent Discovery & Health Check ===")
    print("="*60)
    
    coordinator = TestCoordinatorAgent("health_coordinator")
    research_agent = ResearchAgent("health_research_agent")
    
    try:
        await coordinator.initialize()
        await research_agent.initialize()
        
        # Test agent health check
        health_task = {
            "type": "agent_health_check",
            "agents": ["health_research_agent"]
        }
        
        print("🏥 Performing agent health check...")
        
        result = await coordinator.execute_task(health_task)
        
        agent_health = result.get("agent_health", {})
        
        for agent_id, health in agent_health.items():
            if health.get("available"):
                print(f"✅ Agent {agent_id}: Healthy")
                capabilities = health.get("details", {}).get("capabilities", {})
                print(f"   Capabilities: {list(capabilities.keys())}")
            else:
                print(f"❌ Agent {agent_id}: Not available ({health.get('status')})")
        
        # Test with non-existent agent
        print("\n🔍 Testing with non-existent agent...")
        health_task["agents"] = ["nonexistent_agent"]
        
        result = await coordinator.execute_task(health_task)
        agent_health = result.get("agent_health", {})
        
        for agent_id, health in agent_health.items():
            if not health.get("available"):
                print(f"✅ Correctly detected non-existent agent: {agent_id}")
            else:
                print(f"❌ False positive for non-existent agent: {agent_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent discovery test failed: {e}")
        return False
        
    finally:
        await coordinator.shutdown()
        await research_agent.shutdown()


async def test_concurrent_communication():
    """Test 4: Concurrent agent communication"""
    print("\n" + "="*60)
    print("=== TEST 4: Concurrent Communication ===")
    print("="*60)
    
    coordinator = TestCoordinatorAgent("concurrent_coordinator")
    research_agents = [
        ResearchAgent(f"concurrent_research_{i}") 
        for i in range(3)
    ]
    
    try:
        # Initialize all agents
        await coordinator.initialize()
        for agent in research_agents:
            await agent.initialize()
        
        print(f"✅ Initialized 1 coordinator + {len(research_agents)} research agents")
        
        # Create concurrent tasks
        concurrent_tasks = []
        for i, agent in enumerate(research_agents):
            task = {
                "type": "coordinate_research",
                "target_agent": agent.agent_id,
                "research_task": ResearchTaskTemplates.web_scrape_task(f"https://httpbin.org/html#{i}"),
                "timeout": 15
            }
            concurrent_tasks.append(coordinator.execute_task(task))
        
        print(f"🚀 Executing {len(concurrent_tasks)} concurrent tasks...")
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        successful_concurrent = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Concurrent task {i+1} failed with exception: {result}")
            elif result.get("status") in ["success", "completed"]:
                successful_concurrent += 1
                print(f"✅ Concurrent task {i+1} completed")
            else:
                print(f"❌ Concurrent task {i+1} failed: {result.get('status')}")
        
        print(f"\n📊 Concurrent Communication Results:")
        print(f"   Successful: {successful_concurrent}/{len(concurrent_tasks)}")
        print(f"   Execution Time: {execution_time:.2f}s")
        print(f"   Average Time per Task: {execution_time/len(concurrent_tasks):.2f}s")
        
        return successful_concurrent >= len(concurrent_tasks) // 2  # At least half should succeed
        
    except Exception as e:
        print(f"❌ Concurrent communication test failed: {e}")
        return False
        
    finally:
        await coordinator.shutdown()
        for agent in research_agents:
            await agent.shutdown()


async def main():
    """Run all agent communication tests"""
    print("🚀 Starting Agent Communication Tests")
    print("Make sure Redis is running (docker-compose up)")
    
    tests = [
        ("Basic Communication", test_basic_communication),
        ("Coordinated Research Tasks", test_coordinated_research_tasks),
        ("Agent Discovery & Health Check", test_agent_discovery),
        ("Concurrent Communication", test_concurrent_communication)
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
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "="*60)
    print("🏁 AGENT COMMUNICATION TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<35} {status}")
    
    print(f"\nOverall Results: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All agent communication tests passed!")
        print("Your multi-agent system is ready for production!")
    elif passed >= total * 0.75:
        print("✅ Most tests passed - system is largely functional")
        print("Minor issues to address before production")
    else:
        print("⚠️ Several communication issues detected")
        print("Significant debugging needed before production")


if __name__ == "__main__":
    asyncio.run(main())