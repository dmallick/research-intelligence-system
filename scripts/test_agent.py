import asyncio
from typing import Dict, Any
from agents.base.agent import BaseAgent, AgentMessage

class TestAgent(BaseAgent):
    """Simple test agent to verify message queue functionality"""
    
    def __init__(self, agent_id: str = None):
        super().__init__("test", agent_id)
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a test task"""
        self.logger.info(f"Processing test task: {task}")
        
        # Simulate some work
        await asyncio.sleep(2)
        
        result = {
            "status": "completed",
            "task_id": task.get("task_id"),
            "result": f"Test task completed by {self.agent_id}",
            "processed_at": str(asyncio.get_event_loop().time())
        }
        
        return result
    
    async def _handle_message(self, message: AgentMessage):
        """Handle incoming message"""
        self.logger.info(f"Received message from {message.sender_id}: {message.message_type}")
        
        if message.message_type == "ping":
            # Respond to ping with pong
            await self.send_message(
                message.sender_id,
                "pong",
                {"original_message_id": message.id, "response": "Hello back!"},
                correlation_id=message.correlation_id
            )
        
        elif message.message_type == "test_task":
            # Handle test task message
            task_data = message.content
            result = await self.process_task(task_data)
            
            # Send result back
            await self.send_message(
                message.sender_id,
                "task_result",
                result,
                correlation_id=message.correlation_id
            )
        
        else:
            self.logger.info(f"Unknown message type: {message.message_type}")

# Test functions for manual testing
async def test_message_queue():
    """Test message queue functionality"""
    print("Starting message queue test...")
    
    # Create two test agents
    agent1 = TestAgent("test_agent_1")
    agent2 = TestAgent("test_agent_2")
    
    # Initialize agents
    await agent1.initialize()
    await agent2.initialize()
    
    print("Agents initialized...")
    
    # Agent 1 sends ping to Agent 2
    await agent1.send_message(
        "test_agent_2",
        "ping", 
        {"message": "Hello Agent 2!"},
        correlation_id="test_correlation_123"
    )
    
    print("Message sent...")
    
    # Wait a bit for message processing
    await asyncio.sleep(3)
    
    # Send a test task
    await agent1.send_message(
        "test_agent_2",
        "test_task",
        {
            "task_id": "test_task_001",
            "task_type": "simple_test",
            "data": {"value": 42}
        },
        correlation_id="task_test_456"
    )
    
    print("Task sent...")
    
    # Wait for processing
    await asyncio.sleep(5)
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_message_queue())