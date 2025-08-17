import sys
import asyncio
import os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.message_queue import get_message_queue, Message

# This line adds the project's root directory to the Python path.


async def main():
    try:

        print("Connecting to the message queue...")
        mq = await get_message_queue()
        
        print("Successfully connected to the message queue.")
        
        message = Message(
            from_agent="my_agent",
            to_agent="other_agent",
            message_type="command",
            payload={"action": "start_task"}
        )
        
        success = await mq.publish_message(message)
        if success:
            print(f"Message published: {message.id}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())